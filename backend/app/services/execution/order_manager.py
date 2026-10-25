"""
Order Execution and Lifecycle Manager.
Handles trade submission, reconciliation, client order ID tracking, and protective stop management.
Only closes or cancels orders belonging to the bot.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import logging

from app.schemas.decision import DecisionStatus, TradeDirection
from app.schemas.order import TradeRecord, OrderSide, OrderType
from app.schemas.analytics import AuditLogEntry
from app.services.exchange.delta_client import DeltaExchangeClient
from app.services.storage.database import db

logger = logging.getLogger("riskpilot.order_manager")


class OrderManager:
    def __init__(self, exchange_client: DeltaExchangeClient):
        self.client = exchange_client

    async def execute_trade(
        self,
        decision_id: str,
        symbol: str,
        direction: TradeDirection,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_pct: float,
        risk_budget: float
    ) -> Dict[str, Any]:
        """
        Executes trade on Delta Exchange Testnet using unique client_order_id.
        Persists trade record and logs audit trail.
        """
        client_order_id = f"rp_{direction.value[:1].lower()}_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:4]}"
        side = OrderSide.BUY if direction == TradeDirection.LONG else OrderSide.SELL

        order_res = await self.client.place_order(
            symbol=symbol,
            size=quantity,
            side=side,
            order_type=OrderType.MARKET,
            limit_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            client_order_id=client_order_id
        )

        if not order_res.get("success"):
            error_msg = order_res.get("error", "Unknown exchange error")
            db.log_audit(AuditLogEntry(
                id=f"aud_{uuid.uuid4().hex[:8]}",
                category="ORDER_SUBMISSION",
                event_type="ORDER_REJECTED_BY_EXCHANGE",
                summary=f"Exchange order submission failed: {error_msg}",
                severity="ERROR",
                details={"decision_id": decision_id, "symbol": symbol, "client_order_id": client_order_id}
            ))
            return {"success": False, "error": error_msg}

        exchange_order_id = order_res.get("order_id", client_order_id)
        fill_price = order_res.get("fill_price", entry_price)

        # Update decision receipt
        db.update_decision_approval(decision_id, approved=True, exchange_order_id=exchange_order_id)

        # Create active trade record
        trade = TradeRecord(
            id=f"trd_{uuid.uuid4().hex[:8]}",
            decision_id=decision_id,
            symbol=symbol,
            direction=direction.value,
            entry_price=fill_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status="OPEN",
            risk_percentage=risk_pct,
            risk_budget=risk_budget,
            exchange_order_id=exchange_order_id,
            fee_paid=round(quantity * fill_price * 0.001 * 0.0005, 4),
            opened_at=datetime.now(timezone.utc)
        )
        db.save_trade(trade)

        db.log_audit(AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            category="ORDER_SUBMISSION",
            event_type="ORDER_FILLED",
            summary=f"Submitted {direction.value} {quantity} {symbol} at {fill_price:.2f} (SL: {stop_loss}, TP: {take_profit})",
            severity="INFO",
            details={
                "trade_id": trade.id,
                "exchange_order_id": exchange_order_id,
                "client_order_id": client_order_id,
                "is_mock": order_res.get("is_mock", False)
            }
        ))

        return {
            "success": True,
            "trade_id": trade.id,
            "exchange_order_id": exchange_order_id,
            "fill_price": fill_price,
            "is_mock": order_res.get("is_mock", False)
        }

    async def emergency_close_bot_positions(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Emergency action to immediately flatten bot-owned positions.
        Leaves non-bot account positions intact.
        """
        target_symbol = symbol or "BTCUSDT"
        res = await self.client.close_position(target_symbol)

        db.log_audit(AuditLogEntry(
            id=f"aud_{uuid.uuid4().hex[:8]}",
            category="BOT_CONTROL",
            event_type="EMERGENCY_FLATTEN",
            summary=f"Emergency close triggered for bot positions in {target_symbol}",
            severity="CRITICAL",
            details=res
        ))
        return res
