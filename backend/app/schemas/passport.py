"""
Personal Risk Passport Schemas and Presets.
Enforces hard safety limits and supports Conservative, Balanced, and Aggressive profiles.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from app.config import ABSOLUTE_MAX_RISK_PER_TRADE_PCT, ABSOLUTE_MAX_DAILY_LOSS_PCT, ABSOLUTE_MAX_LEVERAGE


class RiskProfileTier(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"
    CUSTOM = "CUSTOM"


class ExecutionMode(str, Enum):
    APPROVAL = "APPROVAL"
    AUTOMATIC_TESTNET = "AUTOMATIC_TESTNET"


class SLTPMethod(str, Enum):
    ATR_BASED = "ATR_BASED"
    PERCENTAGE = "PERCENTAGE"


class RiskPassportConfig(BaseModel):
    profile_tier: RiskProfileTier = Field(
        default=RiskProfileTier.BALANCED,
        description="Preset risk tier or custom"
    )
    allocated_capital: float = Field(
        default=1000.0,
        gt=0,
        description="Capital allocated to the bot in settlement asset units"
    )
    settlement_asset: str = Field(
        default="USDT",
        description="Verified settlement asset (e.g. USDT, USD) - never silently converted"
    )
    symbol: str = Field(
        default="BTCUSDT",
        description="Delta Exchange Testnet trading symbol"
    )
    timeframe: str = Field(
        default="5m",
        description="Candle timeframe (e.g. 1m, 5m, 15m, 1h)"
    )
    risk_per_trade_pct: float = Field(
        default=0.5,
        gt=0,
        le=ABSOLUTE_MAX_RISK_PER_TRADE_PCT,
        description=f"Risk budget per trade (max {ABSOLUTE_MAX_RISK_PER_TRADE_PCT}%)"
    )
    max_daily_loss_pct: float = Field(
        default=2.0,
        gt=0,
        le=ABSOLUTE_MAX_DAILY_LOSS_PCT,
        description=f"Maximum session daily loss (max {ABSOLUTE_MAX_DAILY_LOSS_PCT}%)"
    )
    max_open_positions: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum concurrent open positions managed by bot"
    )
    max_leverage: float = Field(
        default=2.0,
        ge=1.0,
        le=ABSOLUTE_MAX_LEVERAGE,
        description="Configured leverage ceiling"
    )
    min_reward_to_risk: float = Field(
        default=1.5,
        ge=1.0,
        description="Minimum reward-to-risk ratio required to approve trade"
    )
    sltp_method: SLTPMethod = Field(
        default=SLTPMethod.ATR_BASED,
        description="Method for determining stop-loss and take-profit"
    )
    atr_stop_multiplier: float = Field(
        default=1.5,
        ge=0.5,
        le=5.0,
        description="ATR multiplier for stop loss"
    )
    atr_target_multiplier: float = Field(
        default=2.25,  # 1.5 * 1.5 = 2.25 => 1.5R
        ge=0.5,
        le=10.0,
        description="ATR multiplier for profit target"
    )
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.APPROVAL,
        description="APPROVAL (manual review required) or AUTOMATIC_TESTNET"
    )
    max_consecutive_losses: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Circuit breaker trigger after N consecutive losses"
    )
    session_duration_minutes: Optional[int] = Field(
        default=None,
        description="Optional session auto-stop duration in minutes"
    )

    @model_validator(mode="after")
    def enforce_hard_limits(self) -> "RiskPassportConfig":
        if self.risk_per_trade_pct > ABSOLUTE_MAX_RISK_PER_TRADE_PCT:
            raise ValueError(
                f"Risk per trade {self.risk_per_trade_pct}% exceeds code-level maximum {ABSOLUTE_MAX_RISK_PER_TRADE_PCT}%"
            )
        if self.max_daily_loss_pct > ABSOLUTE_MAX_DAILY_LOSS_PCT:
            raise ValueError(
                f"Daily loss limit {self.max_daily_loss_pct}% exceeds code-level maximum {ABSOLUTE_MAX_DAILY_LOSS_PCT}%"
            )
        if self.max_leverage > ABSOLUTE_MAX_LEVERAGE:
            raise ValueError(
                f"Leverage {self.max_leverage}x exceeds code-level ceiling {ABSOLUTE_MAX_LEVERAGE}x"
            )
        return self


# Preset definitions
PRESET_CONFIGS = {
    RiskProfileTier.CONSERVATIVE: {
        "profile_tier": RiskProfileTier.CONSERVATIVE,
        "risk_per_trade_pct": 0.25,
        "max_daily_loss_pct": 1.0,
        "max_open_positions": 1,
        "max_leverage": 1.0,
        "min_reward_to_risk": 1.5,
        "atr_stop_multiplier": 1.5,
        "atr_target_multiplier": 2.25,
        "max_consecutive_losses": 2,
    },
    RiskProfileTier.BALANCED: {
        "profile_tier": RiskProfileTier.BALANCED,
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 2.0,
        "max_open_positions": 1,
        "max_leverage": 2.0,
        "min_reward_to_risk": 1.5,
        "atr_stop_multiplier": 1.5,
        "atr_target_multiplier": 2.25,
        "max_consecutive_losses": 3,
    },
    RiskProfileTier.AGGRESSIVE: {
        "profile_tier": RiskProfileTier.AGGRESSIVE,
        "risk_per_trade_pct": 1.0,
        "max_daily_loss_pct": 3.0,
        "max_open_positions": 2,
        "max_leverage": 3.0,
        "min_reward_to_risk": 1.5,
        "atr_stop_multiplier": 1.5,
        "atr_target_multiplier": 2.25,
        "max_consecutive_losses": 4,
    }
}


class RiskPassportSummary(BaseModel):
    profile_tier: RiskProfileTier
    allocated_capital: float
    settlement_asset: str
    symbol: str
    risk_per_trade_pct: float
    risk_budget_monetary: float
    max_daily_loss_pct: float
    max_daily_loss_monetary: float
    max_leverage: float
    max_open_positions: int
    execution_mode: ExecutionMode
    hard_limit_risk_ceiling: float = ABSOLUTE_MAX_RISK_PER_TRADE_PCT
    hard_limit_daily_loss_ceiling: float = ABSOLUTE_MAX_DAILY_LOSS_PCT
