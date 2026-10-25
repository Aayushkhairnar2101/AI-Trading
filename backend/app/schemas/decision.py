"""
Pre-Trade Decision Card Schema.
Every trade opportunity (or rejected setup) generates a structured decision card.
Explains the rationale, risk checks, sizing, and mathematical justification.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class MarketRegime(str, Enum):
    TRENDING_BULLISH = "TRENDING_BULLISH"
    TRENDING_BEARISH = "TRENDING_BEARISH"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DecisionStatus(str, Enum):
    ALLOWED = "ALLOWED"
    REJECTED = "REJECTED"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    NO_TRADE = "NO_TRADE"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class RiskCheckResult(BaseModel):
    check_name: str
    passed: bool
    threshold: str
    actual: str
    message: str


class PreTradeDecisionCard(BaseModel):
    id: str = Field(description="Unique decision ID (e.g. dec_20261025_001)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    symbol: str
    settlement_asset: str
    current_price: float
    market_regime: MarketRegime
    proposed_direction: TradeDirection

    # Price levels
    estimated_entry: float
    proposed_stop_loss: float
    proposed_take_profit: float
    stop_distance: float
    target_distance: float
    reward_to_risk_ratio: float

    # Sizing & Exposure
    allocated_capital: float
    risk_budget_monetary: float
    risk_percentage: float
    calculated_quantity: float
    notional_exposure: float
    estimated_margin: float
    effective_leverage: float
    estimated_fees: float = 0.0
    estimated_slippage: float = 0.0

    # Indicator values at decision time
    indicators: Dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of EMA 9, EMA 21, RSI, ADX, ATR, Spread"
    )

    # Strategy signals & explanation
    strategy_signals: List[str] = Field(default_factory=list)
    plain_english_explanation: str
    rejection_reasons: List[str] = Field(default_factory=list)

    # ML component (optional)
    ml_status: str = "NOT_TRAINED"  # NOT_TRAINED, INSUFFICIENT_DATA, VALIDATING, READY
    ml_prediction: Optional[str] = None
    ml_confidence: Optional[float] = None

    # Risk checks
    risk_checks: List[RiskCheckResult] = Field(default_factory=list)

    # Final verdict
    final_decision: DecisionStatus
    approved_by_user: Optional[bool] = None
    exchange_order_id: Optional[str] = None
    execution_notes: Optional[str] = None
