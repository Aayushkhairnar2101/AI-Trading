"""
Order, Position and Balance Schemas.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    LIMIT = "limit_order"
    MARKET = "market_order"


class OrderState(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class AccountBalance(BaseModel):
    asset: str = "USDT"
    total_balance: float = 0.0
    available_balance: float = 0.0
    locked_balance: float = 0.0
    is_mock: bool = False
    verified_at: datetime = Field(default_factory=datetime.utcnow)
    account_equity: float = 0.0


class PositionInfo(BaseModel):
    symbol: str
    size: float
    entry_price: float
    mark_price: float
    liquidation_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    margin: float = 0.0
    leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    bot_managed: bool = True
    client_order_id: Optional[str] = None
    opened_at: datetime = Field(default_factory=datetime.utcnow)


class TradeRecord(BaseModel):
    id: str
    decision_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float
    stop_loss: float
    take_profit: float
    realized_pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    fee_paid: float = 0.0
    status: str  # OPEN, CLOSED, CANCELLED
    risk_percentage: float
    risk_budget: float
    exchange_order_id: Optional[str] = None
    exit_exchange_order_id: Optional[str] = None
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    exit_reason: Optional[str] = None  # STOP_LOSS, TAKE_PROFIT, MANUAL, CIRCUIT_BREAKER
