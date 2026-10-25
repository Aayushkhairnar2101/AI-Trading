"""
Personal Risk Passport Configuration Endpoints.
"""

from fastapi import APIRouter, HTTPException
from app.schemas.passport import RiskPassportConfig, RiskPassportSummary, PRESET_CONFIGS, RiskProfileTier
from app.services.execution.bot_engine import bot

import logging

logger = logging.getLogger("riskpilot.passport")

router = APIRouter(prefix="/passport", tags=["Personal Risk Passport"])


@router.get("", response_model=RiskPassportConfig)
async def get_passport():
    return bot.passport


@router.get("/summary", response_model=RiskPassportSummary)
async def get_passport_summary():
    cfg = bot.passport
    risk_budget = cfg.allocated_capital * (cfg.risk_per_trade_pct / 100.0)
    max_daily_loss = cfg.allocated_capital * (cfg.max_daily_loss_pct / 100.0)

    return RiskPassportSummary(
        profile_tier=cfg.profile_tier,
        allocated_capital=cfg.allocated_capital,
        settlement_asset=cfg.settlement_asset,
        symbol=cfg.symbol,
        risk_per_trade_pct=cfg.risk_per_trade_pct,
        risk_budget_monetary=round(risk_budget, 4),
        max_daily_loss_pct=cfg.max_daily_loss_pct,
        max_daily_loss_monetary=round(max_daily_loss, 4),
        max_leverage=cfg.max_leverage,
        max_open_positions=cfg.max_open_positions,
        execution_mode=cfg.execution_mode
    )


@router.post("", response_model=RiskPassportConfig)
async def update_passport(config: RiskPassportConfig):
    # Enforce strategy capital validity
    if config.allocated_capital <= 0:
        raise HTTPException(
            status_code=400,
            detail="Allocated strategy capital must be strictly greater than 0."
        )

    # Informational check: distinguish strategy capital model from verified testnet wallet balance
    try:
        balance = await bot.exchange.get_balance(asset=config.settlement_asset)
        avail = balance.available_balance if balance else 0.0
        if not (balance and balance.is_mock) and avail <= 0.0:
            logger.info(
                "[PASSPORT] Saved strategy capital %.2f %s. Verified balance is 0.00 %s "
                "— order execution remains strictly disabled until testnet account is funded.",
                config.allocated_capital, config.settlement_asset, config.settlement_asset
            )
    except Exception as e:
        logger.warning("[PASSPORT] Could not fetch live balance during passport update: %s", e)

    bot.configure_passport(config)
    return bot.passport


@router.get("/presets")
async def get_presets():
    return PRESET_CONFIGS
