"""
Central Risk Engine (risk_manager.py).
"The user defines the risk. AI evaluates the opportunity. The risk engine decides whether the trade is allowed."

Enforces all safety boundaries, calculates position sizing, verifies available margin,
and generates structured risk checks for the Pre-Trade Decision Card.
"""

from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from app.config import ABSOLUTE_MAX_RISK_PER_TRADE_PCT, ABSOLUTE_MAX_DAILY_LOSS_PCT, ABSOLUTE_MAX_LEVERAGE
from app.schemas.passport import RiskPassportConfig
from app.schemas.decision import (
    PreTradeDecisionCard,
    DecisionStatus,
    TradeDirection,
    MarketRegime,
    RiskCheckResult
)
from app.schemas.order import AccountBalance, PositionInfo
from app.services.risk.position_sizer import PositionSizer, ProductSpecification, SizingResult
from app.services.risk.circuit_breaker import CircuitBreaker
from app.services.strategy.signal_engine import StrategySignal
import logging

logger = logging.getLogger("riskpilot.risk_manager")


class RiskManager:
    def __init__(
        self,
        passport_config: RiskPassportConfig,
        circuit_breaker: CircuitBreaker
    ):
        self.passport = passport_config
        self.circuit_breaker = circuit_breaker
        self.sizer = PositionSizer()

    def update_passport(self, new_passport: RiskPassportConfig) -> None:
        """Updates user risk parameters."""
        self.passport = new_passport
        self.circuit_breaker.max_daily_loss_pct = new_passport.max_daily_loss_pct
        self.circuit_breaker.max_consecutive_losses = new_passport.max_consecutive_losses
        logger.info(f"Risk Passport updated: tier={new_passport.profile_tier}, risk_pct={new_passport.risk_per_trade_pct}%")

    def evaluate_opportunity(
        self,
        signal: StrategySignal,
        product_spec: ProductSpecification,
        account_balance: AccountBalance,
        open_positions: List[PositionInfo],
        active_orders_count: int = 0,
        data_timestamp: Optional[datetime] = None,
        ml_prediction: Optional[str] = None,
        ml_confidence: Optional[float] = None,
        ml_status: str = "NOT_TRAINED"
    ) -> PreTradeDecisionCard:
        """
        Executes comprehensive multi-factor risk validation on proposed signal.
        Generates Pre-Trade Decision Card with ALLOWED, REJECTED, or NO_TRADE verdict.
        """
        decision_id = f"dec_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        risk_checks: List[RiskCheckResult] = []
        rejection_reasons: List[str] = []

        # If signal is inherently NO_TRADE from the strategy
        if signal.direction == TradeDirection.NO_TRADE:
            # Execute environmental baseline safety checks so user and dashboard have full audit visibility
            cb_status = self.circuit_breaker.get_status()
            cb_passed = not cb_status.is_tripped
            risk_checks.append(RiskCheckResult(
                check_name="Circuit Breaker Status",
                passed=cb_passed,
                threshold="Active & Untripped",
                actual="TRIPPED" if not cb_passed else "Normal",
                message=cb_status.trip_reason if not cb_passed else "Circuit breaker is normal."
            ))

            avail = account_balance.available_balance
            alloc = self.passport.allocated_capital
            balance_passed = avail >= alloc or account_balance.is_mock
            if not account_balance.is_mock and avail <= 0.0:
                bal_msg = f"Available balance is 0.00 {account_balance.asset} — account is unfunded. Order submission disabled."
            elif not balance_passed:
                bal_msg = f"Allocated capital ({alloc:.2f}) exceeds available balance ({avail:.2f} {account_balance.asset})."
            else:
                bal_msg = f"Verified balance ({avail:.2f} {account_balance.asset}) sufficient."

            risk_checks.append(RiskCheckResult(
                check_name="Capital Allocation Verification",
                passed=balance_passed,
                threshold=f"Available balance >= {alloc:.2f} {self.passport.settlement_asset}",
                actual=f"{avail:.2f} {account_balance.asset}",
                message=bal_msg
            ))

            if data_timestamp:
                age_seconds = (datetime.now(timezone.utc) - data_timestamp.replace(tzinfo=timezone.utc)).total_seconds()
                fresh_passed = age_seconds <= 120.0
                risk_checks.append(RiskCheckResult(
                    check_name="Market Data Freshness",
                    passed=fresh_passed,
                    threshold="<= 120s lag",
                    actual=f"{age_seconds:.1f}s lag",
                    message="Market feed is fresh." if fresh_passed else f"Market feed is stale ({age_seconds:.1f}s lag)."
                ))

            # Compile genuine rejection reasons (strategy unfulfilled criteria + any failed environmental checks)
            no_trade_reasons = list(signal.no_trade_reasons)
            for chk in risk_checks:
                if not chk.passed:
                    no_trade_reasons.append(f"{chk.check_name}: {chk.message}")

            explanation = (
                "NO TRADE: " + " | ".join(no_trade_reasons)
                if no_trade_reasons
                else "NO TRADE: Market conditions do not satisfy strategy entry criteria."
            )

            return PreTradeDecisionCard(
                id=decision_id,
                symbol=product_spec.symbol,
                settlement_asset=product_spec.settlement_asset,
                current_price=signal.entry_price,
                market_regime=signal.regime,
                proposed_direction=TradeDirection.NO_TRADE,
                estimated_entry=signal.entry_price,
                proposed_stop_loss=0.0,
                proposed_take_profit=0.0,
                stop_distance=0.0,
                target_distance=0.0,
                reward_to_risk_ratio=0.0,
                allocated_capital=self.passport.allocated_capital,
                risk_budget_monetary=0.0,
                risk_percentage=self.passport.risk_per_trade_pct,
                calculated_quantity=0.0,
                notional_exposure=0.0,
                estimated_margin=0.0,
                effective_leverage=0.0,
                indicators=signal.indicator_snapshot,
                strategy_signals=signal.reasons,  # Clean Strategy Rationale (e.g. Bullish EMA bias, RSI, ADX)
                plain_english_explanation=explanation,
                rejection_reasons=no_trade_reasons,  # Genuine reasons why trade was not taken (never bullish EMA)
                ml_status=ml_status,
                ml_prediction=ml_prediction,
                ml_confidence=ml_confidence,
                risk_checks=risk_checks,
                final_decision=DecisionStatus.NO_TRADE
            )

        # 1. Circuit Breaker Check
        cb_status = self.circuit_breaker.get_status()
        cb_passed = not cb_status.is_tripped
        risk_checks.append(RiskCheckResult(
            check_name="Circuit Breaker Status",
            passed=cb_passed,
            threshold="Active & Untripped",
            actual="TRIPPED" if not cb_passed else "Normal",
            message=cb_status.trip_reason if not cb_passed else "Circuit breaker is normal."
        ))
        if not cb_passed:
            rejection_reasons.append(f"Circuit breaker tripped: {cb_status.trip_reason}")

        # 2. Capital Allocation vs Available Balance
        # Never allow allocation to exceed verified available balance
        avail = account_balance.available_balance
        alloc = self.passport.allocated_capital
        balance_passed = avail >= alloc or account_balance.is_mock
        if not account_balance.is_mock and avail <= 0.0:
            bal_msg = f"Zero available balance (0.00 {account_balance.asset}) — account is unfunded. Live order submission blocked."
        elif not balance_passed:
            bal_msg = f"Allocated capital ({alloc:.2f} {self.passport.settlement_asset}) exceeds available balance ({avail:.2f} {account_balance.asset})."
        else:
            bal_msg = "Verified available balance covers allocated capital."

        risk_checks.append(RiskCheckResult(
            check_name="Capital Allocation Verification",
            passed=balance_passed,
            threshold=f"Available balance >= {alloc:.2f} {self.passport.settlement_asset}",
            actual=f"{avail:.2f} {account_balance.asset}",
            message=bal_msg
        ))
        if not balance_passed:
            rejection_reasons.append(bal_msg)

        # 3. Open Positions Limit Check
        # Count bot-managed open positions
        bot_positions = [p for p in open_positions if p.bot_managed]
        pos_passed = len(bot_positions) < self.passport.max_open_positions
        risk_checks.append(RiskCheckResult(
            check_name="Max Open Positions Limit",
            passed=pos_passed,
            threshold=f"<= {self.passport.max_open_positions} positions",
            actual=f"{len(bot_positions)} open positions",
            message=f"Current bot positions {len(bot_positions)} within limit {self.passport.max_open_positions}." if pos_passed else "Maximum open positions limit reached."
        ))
        if not pos_passed:
            rejection_reasons.append(f"Maximum open position limit ({self.passport.max_open_positions}) reached.")

        # 4. Duplicate Position / Order Check for same symbol
        duplicate = any(p.symbol == product_spec.symbol for p in open_positions) or (active_orders_count > 0)
        dup_passed = not duplicate
        risk_checks.append(RiskCheckResult(
            check_name="Duplicate Position / Order Guard",
            passed=dup_passed,
            threshold="No existing open position or order in symbol",
            actual="Existing position/order found" if duplicate else "Clear",
            message="No duplicate position or pending order found." if dup_passed else f"An active order or position already exists for {product_spec.symbol}."
        ))
        if not dup_passed:
            rejection_reasons.append(f"Duplicate protection: open position or order already active for {product_spec.symbol}.")

        # 5. Position Sizing & Margin Calculation
        sizing: SizingResult = self.sizer.calculate_position(
            allocated_capital=self.passport.allocated_capital,
            risk_per_trade_pct=self.passport.risk_per_trade_pct,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            product=product_spec,
            max_leverage_ceiling=self.passport.max_leverage
        )

        size_passed = sizing.is_valid and sizing.calculated_quantity >= product_spec.min_order_size
        risk_checks.append(RiskCheckResult(
            check_name="Position Sizing & Minimum Contract Size",
            passed=size_passed,
            threshold=f">= {product_spec.min_order_size} contracts",
            actual=f"{sizing.calculated_quantity} contracts",
            message=f"Calculated {sizing.calculated_quantity} contracts based on risk budget {sizing.risk_budget_monetary:.2f} {product_spec.settlement_asset}." if size_passed else (sizing.rejection_reason or "Sizing failed.")
        ))
        if not size_passed:
            rejection_reasons.append(sizing.rejection_reason or "Calculated size invalid.")

        # 6. Leverage Limit Check
        leverage_passed = sizing.effective_leverage <= self.passport.max_leverage and sizing.effective_leverage <= ABSOLUTE_MAX_LEVERAGE
        risk_checks.append(RiskCheckResult(
            check_name="Leverage Ceiling Check",
            passed=leverage_passed,
            threshold=f"<= {self.passport.max_leverage}x (Code limit: {ABSOLUTE_MAX_LEVERAGE}x)",
            actual=f"{sizing.effective_leverage:.2f}x",
            message="Effective leverage complies with user passport cap." if leverage_passed else f"Effective leverage {sizing.effective_leverage:.2f}x breaches limit {self.passport.max_leverage}x."
        ))
        if not leverage_passed:
            rejection_reasons.append(f"Effective leverage ({sizing.effective_leverage:.2f}x) exceeds limit ({self.passport.max_leverage}x)")

        # 7. Reward to Risk Check
        rr_passed = sizing.reward_to_risk >= self.passport.min_reward_to_risk
        risk_checks.append(RiskCheckResult(
            check_name="Reward-to-Risk Requirement",
            passed=rr_passed,
            threshold=f">= {self.passport.min_reward_to_risk:.2f}R",
            actual=f"{sizing.reward_to_risk:.2f}R",
            message=f"Reward-to-risk ratio {sizing.reward_to_risk:.2f}R satisfies criteria." if rr_passed else f"Reward-to-risk {sizing.reward_to_risk:.2f}R is below required {self.passport.min_reward_to_risk:.2f}R."
        ))
        if not rr_passed:
            rejection_reasons.append(f"Reward-to-risk {sizing.reward_to_risk:.2f}R below minimum {self.passport.min_reward_to_risk:.2f}R")

        # 8. Market Data Freshness Check
        if data_timestamp:
            age_seconds = (datetime.now(timezone.utc) - data_timestamp.replace(tzinfo=timezone.utc)).total_seconds()
            fresh_passed = age_seconds <= 120.0
            risk_checks.append(RiskCheckResult(
                check_name="Market Data Freshness",
                passed=fresh_passed,
                threshold="<= 120s lag",
                actual=f"{age_seconds:.1f}s lag",
                message="Market feed is fresh." if fresh_passed else f"Market feed is stale ({age_seconds:.1f}s lag). Trading blocked."
            ))
            if not fresh_passed:
                rejection_reasons.append(f"Market data is stale ({age_seconds:.1f}s old)")

        # Determine Final Decision
        all_passed = all(check.passed for check in risk_checks)
        if all_passed:
            final_status = (
                DecisionStatus.WAITING_FOR_APPROVAL
                if self.passport.execution_mode.value == "APPROVAL"
                else DecisionStatus.ALLOWED
            )
            plain_english = (
                f"{signal.direction.value} opportunity detected at {signal.entry_price:.2f}. "
                + " ".join(signal.reasons)
                + f" Risk Engine verified all {len(risk_checks)} safety rules. "
                + f"Calculated position: {sizing.calculated_quantity} contracts risking {sizing.risk_budget_monetary:.2f} {product_spec.settlement_asset} "
                + f"({self.passport.risk_per_trade_pct}% of capital). Decision: {final_status.value}."
            )
        else:
            final_status = DecisionStatus.REJECTED
            failed_checks = [c.check_name for c in risk_checks if not c.passed]
            plain_english = (
                f"{signal.direction.value} opportunity detected at {signal.entry_price:.2f}, but the trade is BLOCKED by the Risk Engine. "
                f"Failed safety checks: {', '.join(failed_checks)}. "
                f"Reasons: {' | '.join(rejection_reasons)}."
            )

        return PreTradeDecisionCard(
            id=decision_id,
            symbol=product_spec.symbol,
            settlement_asset=product_spec.settlement_asset,
            current_price=signal.entry_price,
            market_regime=signal.regime,
            proposed_direction=signal.direction,
            estimated_entry=sizing.entry_price,
            proposed_stop_loss=sizing.stop_loss,
            proposed_take_profit=sizing.take_profit,
            stop_distance=sizing.stop_distance,
            target_distance=sizing.target_distance,
            reward_to_risk_ratio=sizing.reward_to_risk,
            allocated_capital=self.passport.allocated_capital,
            risk_budget_monetary=sizing.risk_budget_monetary,
            risk_percentage=self.passport.risk_per_trade_pct,
            calculated_quantity=sizing.calculated_quantity,
            notional_exposure=sizing.notional_exposure,
            estimated_margin=sizing.estimated_margin,
            effective_leverage=sizing.effective_leverage,
            estimated_fees=sizing.estimated_fees,
            estimated_slippage=sizing.estimated_slippage,
            indicators=signal.indicator_snapshot,
            strategy_signals=signal.reasons,
            plain_english_explanation=plain_english,
            rejection_reasons=rejection_reasons,
            ml_status=ml_status,
            ml_prediction=ml_prediction,
            ml_confidence=ml_confidence,
            risk_checks=risk_checks,
            final_decision=final_status
        )
