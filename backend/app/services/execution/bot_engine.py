"""
Bot Engine: Orchestrates continuous market monitoring, signal generation,
risk assessment, and execution in Approval or Automatic Testnet mode.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
import logging

from app.schemas.passport import RiskPassportConfig, ExecutionMode
from app.schemas.strategy import StrategyConfig
from app.schemas.decision import PreTradeDecisionCard, DecisionStatus, TradeDirection
from app.schemas.order import TradeRecord
from app.schemas.analytics import AuditLogEntry, SessionReport
from app.services.exchange.delta_client import DeltaExchangeClient
from app.services.strategy.signal_engine import SignalEngine
from app.services.strategy.ml_model import MLStrategyModel
from app.services.risk.risk_manager import RiskManager
from app.services.risk.circuit_breaker import CircuitBreaker
from app.services.execution.order_manager import OrderManager
from app.services.storage.database import db

logger = logging.getLogger("riskpilot.bot_engine")


class BotEngine:
    def __init__(self):
        self.exchange = DeltaExchangeClient()
        self.order_manager = OrderManager(self.exchange)
        self.passport = RiskPassportConfig()
        self.strategy_config = StrategyConfig()
        self.signal_engine = SignalEngine(self.strategy_config)
        self.ml_model = MLStrategyModel()
        self.circuit_breaker = CircuitBreaker(
            session_start_equity=self.passport.allocated_capital,
            max_daily_loss_pct=self.passport.max_daily_loss_pct,
            max_consecutive_losses=self.passport.max_consecutive_losses
        )
        self.risk_manager = RiskManager(self.passport, self.circuit_breaker)

        # Bot Runtime State
        self.is_running: bool = False
        self.is_paused: bool = False
        self.session_id: Optional[str] = None
        self.session_started_at: Optional[datetime] = None
        self.last_evaluation_time: Optional[datetime] = None
        self.total_evaluations: int = 0
        self.signals_count: int = 0
        self.no_trade_count: int = 0
        self.rejections_count: int = 0
        self.latest_decision: Optional[PreTradeDecisionCard] = None

        self._task: Optional[asyncio.Task] = None

    def configure_passport(self, new_config: RiskPassportConfig) -> None:
        """Applies new Risk Passport configuration."""
        self.passport = new_config
        self.risk_manager.update_passport(new_config)
        self.circuit_breaker.session_start_equity = new_config.allocated_capital
        db.log_audit(AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            category="BOT_CONTROL",
            event_type="PASSPORT_CONFIGURED",
            summary=f"Risk Passport configured: {new_config.profile_tier.value} preset, capital {new_config.allocated_capital} {new_config.settlement_asset}, risk {new_config.risk_per_trade_pct}%",
            severity="INFO",
            details=new_config.model_dump()
        ))

    async def start_session(self, mode: Optional[ExecutionMode] = None) -> Dict[str, Any]:
        """Starts trading session in either Approval or Automatic Testnet mode."""
        if self.is_running:
            return {"success": False, "message": "Bot is already running."}

        if mode:
            self.passport.execution_mode = mode

        self.session_id = f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        self.session_started_at = datetime.now(timezone.utc)
        self.is_running = True
        self.is_paused = False
        self.total_evaluations = 0
        self.signals_count = 0
        self.no_trade_count = 0
        self.rejections_count = 0

        # Reset circuit breaker for new session
        self.circuit_breaker.reset(new_start_equity=self.passport.allocated_capital)

        # Train ML model in background on historical candles
        asyncio.create_task(self._warmup_ml_model())

        # Start background evaluation loop
        self._task = asyncio.create_task(self._evaluation_loop())

        db.log_audit(AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            category="BOT_CONTROL",
            event_type="SESSION_STARTED",
            summary=f"RiskPilot AI started in {self.passport.execution_mode.value} mode on {self.passport.symbol}",
            severity="INFO",
            details={"session_id": self.session_id, "mode": self.passport.execution_mode.value}
        ))

        return {
            "success": True,
            "session_id": self.session_id,
            "mode": self.passport.execution_mode.value,
            "message": f"Bot started in {self.passport.execution_mode.value} mode."
        }

    async def _warmup_ml_model(self) -> None:
        """Fetches candles and initializes ML model."""
        try:
            candles = await self.exchange.get_candles(symbol=self.passport.symbol, limit=120)
            if len(candles) >= 60:
                res = self.ml_model.train_and_validate(candles)
                logger.info(f"ML Model warmup completed: {res}")
        except Exception as e:
            logger.warning(f"ML warmup skipped: {e}")

    def pause_session(self) -> Dict[str, Any]:
        if not self.is_running:
            return {"success": False, "message": "Bot is not running."}
        self.is_paused = True
        db.log_audit(AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            category="BOT_CONTROL",
            event_type="SESSION_PAUSED",
            summary="Trading session paused by user. New opportunity evaluation suspended.",
            severity="INFO",
            details={"session_id": self.session_id}
        ))
        return {"success": True, "message": "Bot paused."}

    def resume_session(self) -> Dict[str, Any]:
        if not self.is_running:
            return {"success": False, "message": "Bot is not running."}
        self.is_paused = False
        db.log_audit(AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            category="BOT_CONTROL",
            event_type="SESSION_RESUMED",
            summary="Trading session resumed by user.",
            severity="INFO",
            details={"session_id": self.session_id}
        ))
        return {"success": True, "message": "Bot resumed."}

    async def stop_session(self) -> Dict[str, Any]:
        """Stops trading bot and generates Session Report."""
        if not self.is_running:
            return {"success": False, "message": "Bot is not running."}

        self.is_running = False
        self.is_paused = False

        if self._task and not self._task.done():
            self._task.cancel()

        ended_at = datetime.now(timezone.utc)
        metrics = db.get_performance_metrics()
        net_pnl = metrics.net_pnl
        current_capital = self.passport.allocated_capital + net_pnl
        net_pct = (net_pnl / self.passport.allocated_capital) * 100.0 if self.passport.allocated_capital > 0 else 0.0

        report = SessionReport(
            session_id=self.session_id or "session_unknown",
            started_at=self.session_started_at or ended_at,
            ended_at=ended_at,
            initial_allocated_capital=self.passport.allocated_capital,
            current_capital=round(current_capital, 2),
            net_pnl=round(net_pnl, 2),
            net_pnl_pct=round(net_pct, 2),
            performance=metrics,
            decisions_total=self.total_evaluations,
            decisions_approved=self.signals_count,
            decisions_rejected=self.rejections_count,
            decisions_no_trade=self.no_trade_count,
            circuit_breaker_tripped=self.circuit_breaker.is_tripped,
            summary_text=f"Session completed with {metrics.total_trades} trades. Net PnL: {net_pnl:.2f} {self.passport.settlement_asset} ({net_pct:.2f}%)."
        )
        db.save_session_report(report)

        db.log_audit(AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            category="BOT_CONTROL",
            event_type="SESSION_STOPPED",
            summary=f"Trading session stopped. Net PnL: {net_pnl:.2f} {self.passport.settlement_asset}. Session report generated.",
            severity="INFO",
            details=report.model_dump()
        ))

        return {
            "success": True,
            "session_id": self.session_id,
            "report": report.model_dump(),
            "message": "Bot stopped and session report generated."
        }

    async def _evaluation_loop(self) -> None:
        """Continuous evaluation cycle."""
        logger.info("Bot evaluation loop started.")
        while self.is_running:
            try:
                if not self.is_paused:
                    await self.evaluate_market()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in evaluation cycle: {e}", exc_info=True)
            # Evaluate every 5 seconds
            await asyncio.sleep(5)

    async def evaluate_market(self) -> Optional[PreTradeDecisionCard]:
        """Performs a single complete evaluation pass."""
        symbol = self.passport.symbol
        spec = self.exchange.get_product_spec(symbol)
        spec.settlement_asset = self.passport.settlement_asset

        # 1. Fetch candles & ticker
        candles = await self.exchange.get_candles(symbol=symbol, resolution=self.passport.timeframe, limit=80)
        ticker = await self.exchange.get_ticker(symbol=symbol)
        balance = await self.exchange.get_balance(asset=self.passport.settlement_asset)
        positions = await self.exchange.get_positions()

        # 2. Monitor open positions for SL/TP hits (Trade Lifecycle)
        await self._monitor_open_positions(ticker["mark_price"])

        # 3. Strategy Signal Evaluation
        signal = self.signal_engine.evaluate(
            candle_df=candles,
            bid_price=ticker.get("bid"),
            ask_price=ticker.get("ask")
        )

        # 4. Optional ML Model prediction
        ml_pred, ml_conf = self.ml_model.predict(candles)

        # 5. Risk Manager Assessment
        card = self.risk_manager.evaluate_opportunity(
            signal=signal,
            product_spec=spec,
            account_balance=balance,
            open_positions=positions,
            active_orders_count=0,
            data_timestamp=datetime.now(timezone.utc),
            ml_prediction=ml_pred,
            ml_confidence=ml_conf,
            ml_status=self.ml_model.status
        )

        self.last_evaluation_time = datetime.now(timezone.utc)
        self.total_evaluations += 1
        self.latest_decision = card

        # Track statistics
        if card.final_decision == DecisionStatus.NO_TRADE:
            self.no_trade_count += 1
        elif card.final_decision == DecisionStatus.REJECTED:
            self.rejections_count += 1
            db.log_audit(AuditLogEntry(
                id=f"aud_{uuid.uuid4().hex[:8]}",
                category="RISK_CHECK",
                event_type="OPPORTUNITY_REJECTED",
                summary=f"Risk Engine BLOCKED proposed {card.proposed_direction.value} trade on {symbol}",
                severity="WARNING",
                details={"reasons": card.rejection_reasons}
            ))
        elif card.final_decision in [DecisionStatus.ALLOWED, DecisionStatus.WAITING_FOR_APPROVAL]:
            self.signals_count += 1

        # Persist decision receipt in SQLite
        db.save_decision(card)

        # 6. Automatic Execution if configured and ALLOWED
        if (
            self.passport.execution_mode == ExecutionMode.AUTOMATIC_TESTNET
            and card.final_decision == DecisionStatus.ALLOWED
            and card.proposed_direction != TradeDirection.NO_TRADE
        ):
            logger.info(f"Auto-executing trade {card.id} on Delta Testnet...")
            exec_res = await self.order_manager.execute_trade(
                decision_id=card.id,
                symbol=card.symbol,
                direction=card.proposed_direction,
                quantity=card.calculated_quantity,
                entry_price=card.estimated_entry,
                stop_loss=card.proposed_stop_loss,
                take_profit=card.proposed_take_profit,
                risk_pct=card.risk_percentage,
                risk_budget=card.risk_budget_monetary
            )
            if exec_res.get("success"):
                card.final_decision = DecisionStatus.EXECUTED
                card.exchange_order_id = exec_res.get("exchange_order_id")
                card.execution_notes = f"Auto-executed on testnet (Order ID: {card.exchange_order_id})"
                db.save_decision(card)

        return card

    async def _monitor_open_positions(self, current_price: float) -> None:
        """
        Monitors active positions against stop-loss and take-profit targets.
        Closes completed trades, calculates realized PnL, and updates circuit breaker.
        """
        trades = db.get_trades(limit=20)
        open_trades = [t for t in trades if t["status"] == "OPEN"]

        for trade_dict in open_trades:
            symbol = trade_dict["symbol"]
            direction = trade_dict["direction"]
            entry = float(trade_dict["entry_price"])
            sl = float(trade_dict["stop_loss"])
            tp = float(trade_dict["take_profit"])
            qty = float(trade_dict["quantity"])
            trade_id = trade_dict["id"]

            close_reason = None
            exit_price = None

            if direction == "LONG":
                if current_price <= sl:
                    close_reason = "STOP_LOSS"
                    exit_price = sl
                elif current_price >= tp:
                    close_reason = "TAKE_PROFIT"
                    exit_price = tp
            elif direction == "SHORT":
                if current_price >= sl:
                    close_reason = "STOP_LOSS"
                    exit_price = sl
                elif current_price <= tp:
                    close_reason = "TAKE_PROFIT"
                    exit_price = tp

            if close_reason and exit_price is not None:
                # Realize PnL
                multiplier = 0.001 if symbol == "BTCUSDT" else (0.01 if symbol == "ETHUSDT" else 0.1)
                if direction == "LONG":
                    realized_pnl = (exit_price - entry) * qty * multiplier
                else:
                    realized_pnl = (entry - exit_price) * qty * multiplier

                fee = round(qty * exit_price * multiplier * 0.0005, 4)
                net_trade_pnl = round(realized_pnl - fee, 4)

                # Update database
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                    UPDATE trades
                    SET exit_price = ?, realized_pnl = ?, fee_paid = fee_paid + ?,
                        status = 'CLOSED', exit_reason = ?, closed_at = ?
                    WHERE id = ?
                    """, (
                        exit_price,
                        net_trade_pnl,
                        fee,
                        close_reason,
                        datetime.now(timezone.utc).isoformat(),
                        trade_id
                    ))
                    conn.commit()

                # Feed result to circuit breaker
                self.circuit_breaker.record_trade_result(net_trade_pnl)

                # Close position on exchange client
                await self.exchange.close_position(symbol)

                db.log_audit(AuditLogEntry(
                    id=f"aud_{uuid.uuid4().hex[:8]}",
                    category="ORDER_SUBMISSION",
                    event_type=f"TRADE_CLOSED_{close_reason}",
                    summary=f"Position {trade_id} closed via {close_reason} at {exit_price:.2f}. Realized PnL: {net_trade_pnl:.2f} {self.passport.settlement_asset}",
                    severity="INFO" if net_trade_pnl >= 0 else "WARNING",
                    details={"realized_pnl": net_trade_pnl, "exit_reason": close_reason}
                ))

    async def approve_trade(self, decision_id: str) -> Dict[str, Any]:
        """User manual approval of a pending trade in Approval Mode."""
        decision_data = db.get_decision(decision_id)
        if not decision_data:
            return {"success": False, "message": f"Decision {decision_id} not found."}

        card = PreTradeDecisionCard(**decision_data)
        if card.final_decision != DecisionStatus.WAITING_FOR_APPROVAL:
            return {"success": False, "message": f"Decision {decision_id} is in status {card.final_decision.value}, cannot approve."}

        # Immediate re-check of risk limits at execution time
        cb_status = self.circuit_breaker.get_status()
        if cb_status.is_tripped:
            return {"success": False, "message": f"Execution blocked: Circuit breaker tripped ({cb_status.trip_reason})."}

        # Pre-execution balance check: block if testnet account balance is insufficient
        try:
            live_balance = await self.exchange.get_balance(asset=self.passport.settlement_asset)
            available = live_balance.available_balance if live_balance else 0.0
            required_margin = float(card.estimated_margin or 0.0)
            if live_balance.is_mock:
                # In demo mode the mock balance is not a real funded account; warn but allow simulation
                logger.warning(
                    "[DEMO] Order running against simulated balance %.2f %s (not a funded testnet account).",
                    available, self.passport.settlement_asset
                )
            elif available <= 0.0:
                return {
                    "success": False,
                    "message": (
                        "ORDER BLOCKED — Insufficient Testnet Balance: "
                        f"Verified USDT available balance on Delta Exchange India Testnet is {available:.4f} USDT. "
                        "Fund your testnet account at demo.delta.exchange before submitting orders."
                    ),
                    "balance_check": {
                        "available_balance": available,
                        "required_margin": required_margin,
                        "asset": self.passport.settlement_asset,
                        "is_mock": False
                    }
                }
            elif required_margin > 0.0 and available < required_margin:
                return {
                    "success": False,
                    "message": (
                        f"ORDER BLOCKED — Insufficient Margin: "
                        f"Required margin is {required_margin:.4f} USDT but only {available:.4f} USDT is available "
                        f"on Delta Exchange India Testnet. Reduce position size or fund the testnet account."
                    ),
                    "balance_check": {
                        "available_balance": available,
                        "required_margin": required_margin,
                        "asset": self.passport.settlement_asset,
                        "is_mock": False
                    }
                }
        except Exception as e:
            logger.error(f"Error checking live balance at approval: {e}")

        # Check market data freshness: block order approval if live market feed is stale (> 60s)
        feed_health = self.exchange.get_feed_status()
        if self.exchange.is_authenticated and feed_health.get("status") == "STALE_OR_DISCONNECTED":
            return {
                "success": False,
                "message": (
                    f"ORDER BLOCKED — Stale Market Data Feed: Testnet market data lag is "
                    f"{feed_health.get('ticker_lag_seconds')}s (exceeds safety threshold). "
                    "Order execution is prohibited when market feed is stale or disconnected."
                )
            }
            logger.warning("Balance pre-check failed: %s — proceeding with caution.", e)

        # Execute
        res = await self.order_manager.execute_trade(
            decision_id=card.id,
            symbol=card.symbol,
            direction=card.proposed_direction,
            quantity=card.calculated_quantity,
            entry_price=card.estimated_entry,
            stop_loss=card.proposed_stop_loss,
            take_profit=card.proposed_take_profit,
            risk_pct=card.risk_percentage,
            risk_budget=card.risk_budget_monetary
        )
        return res


bot = BotEngine()
