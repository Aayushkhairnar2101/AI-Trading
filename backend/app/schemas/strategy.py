"""
Strategy Configuration and Status Schemas.
"""

from typing import List
from pydantic import BaseModel, Field


class StrategyConfig(BaseModel):
    name: str = "Regime-Aware Trend Follower"
    ema_fast_period: int = Field(default=9, ge=2, le=50)
    ema_slow_period: int = Field(default=21, ge=5, le=200)
    rsi_period: int = Field(default=14, ge=2, le=50)
    rsi_long_min: float = Field(default=52.0, ge=30.0, le=80.0)
    rsi_long_max: float = Field(default=68.0, ge=40.0, le=90.0)
    rsi_short_min: float = Field(default=32.0, ge=10.0, le=60.0)
    rsi_short_max: float = Field(default=48.0, ge=20.0, le=70.0)
    adx_period: int = Field(default=14, ge=5, le=50)
    adx_threshold: float = Field(default=20.0, ge=10.0, le=50.0)
    atr_period: int = Field(default=14, ge=5, le=50)
    atr_stop_multiplier: float = Field(default=1.5, ge=0.5, le=5.0)
    min_reward_to_risk: float = Field(default=1.5, ge=1.0, le=5.0)
    max_spread_pct: float = Field(default=0.15, description="Max allowed bid-ask spread % (e.g. 0.15%)")
    max_atr_pct: float = Field(default=4.0, description="Max ATR as % of price to filter abnormal volatility")
    require_confirmed_candles: bool = True
    enable_ml_filter: bool = False
    ml_confidence_threshold: float = Field(default=0.60, ge=0.5, le=0.95)


class StrategyStatus(BaseModel):
    is_active: bool
    symbol: str
    timeframe: str
    last_evaluation_time: str
    total_evaluations: int
    signals_generated: int
    trades_executed: int
    no_trade_count: int
    rejections_count: int
    last_decision_id: str
    last_decision_summary: str
