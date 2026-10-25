"""
Analytics, Simulator, Audit, and Performance Schemas.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class WhatIfSimulationRequest(BaseModel):
    entry_price: float
    stop_loss: float
    take_profit: float
    quantity: float
    direction: str = "LONG"
    fee_rate_bps: float = 5.0  # 0.05% maker/taker estimate
    slippage_bps: float = 2.0
    adverse_move_pct: float = 1.0


class WhatIfSimulationResponse(BaseModel):
    risk_at_stop_loss: float
    reward_at_take_profit: float
    reward_to_risk_ratio: float
    adverse_move_loss: float
    estimated_roundtrip_fees: float
    estimated_slippage_cost: float
    effective_loss_with_costs: float
    effective_gain_with_costs: float
    disclaimer: str = "Calculations are mathematical estimates for risk assessment and do not guarantee actual fill prices."


class CircuitBreakerStatus(BaseModel):
    is_tripped: bool = False
    trip_reason: Optional[str] = None
    tripped_at: Optional[datetime] = None
    consecutive_losses: int = 0
    max_consecutive_losses: int = 3
    current_daily_drawdown_pct: float = 0.0
    max_daily_loss_pct: float = 2.0
    paused_trades: bool = False
    message: str = "Circuit breaker is armed and normal."


class AuditLogEntry(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    category: str  # BOT_CONTROL, STRATEGY, RISK_CHECK, ORDER_SUBMISSION, EXCHANGE_EVENT, CIRCUIT_BREAKER
    event_type: str
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL


class PerformanceMetrics(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    total_realized_pnl: float = 0.0
    total_fees_paid: float = 0.0
    net_pnl: float = 0.0
    average_trade_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    max_consecutive_losses_recorded: int = 0
    sharpe_ratio_estimate: Optional[float] = None


class SessionReport(BaseModel):
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    initial_allocated_capital: float
    current_capital: float
    net_pnl: float
    net_pnl_pct: float
    performance: PerformanceMetrics
    decisions_total: int = 0
    decisions_approved: int = 0
    decisions_rejected: int = 0
    decisions_no_trade: int = 0
    rejection_breakdown: Dict[str, int] = Field(default_factory=dict)
    circuit_breaker_tripped: bool = False
    summary_text: str = ""
