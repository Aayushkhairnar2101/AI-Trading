"""
Strategy, Pre-Trade Decision Cards, What-If Simulator & ML Endpoints.
"""

from fastapi import APIRouter
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.schemas.strategy import StrategyConfig, StrategyStatus
from app.schemas.decision import PreTradeDecisionCard
from app.schemas.analytics import WhatIfSimulationRequest, WhatIfSimulationResponse
from app.services.execution.bot_engine import bot
from app.services.storage.database import db

router = APIRouter(prefix="/strategy", tags=["Strategy & Decisions"])


@router.get("/config", response_model=StrategyConfig)
async def get_strategy_config():
    return bot.strategy_config


@router.post("/config", response_model=StrategyConfig)
async def update_strategy_config(cfg: StrategyConfig):
    bot.strategy_config = cfg
    bot.signal_engine.config = cfg
    bot.signal_engine.regime_detector.adx_trending_threshold = cfg.adx_threshold
    bot.signal_engine.regime_detector.max_safe_atr_pct = cfg.max_atr_pct
    return bot.strategy_config


@router.get("/status", response_model=StrategyStatus)
async def get_strategy_status():
    last_card = bot.latest_decision
    return StrategyStatus(
        is_active=bot.is_running and not bot.is_paused,
        symbol=bot.passport.symbol,
        timeframe=bot.passport.timeframe,
        last_evaluation_time=bot.last_evaluation_time.isoformat() if bot.last_evaluation_time else "Never",
        total_evaluations=bot.total_evaluations,
        signals_generated=bot.signals_count,
        trades_executed=len([t for t in db.get_trades() if t["status"] in ["OPEN", "CLOSED"]]),
        no_trade_count=bot.no_trade_count,
        rejections_count=bot.rejections_count,
        last_decision_id=last_card.id if last_card else "None",
        last_decision_summary=last_card.plain_english_explanation if last_card else "No evaluation performed yet."
    )


@router.post("/evaluate", response_model=PreTradeDecisionCard)
async def evaluate_now():
    """Triggers an immediate market evaluation pass."""
    card = await bot.evaluate_market()
    return card


@router.get("/decisions")
async def get_decisions(limit: int = 50):
    return db.get_recent_decisions(limit=limit)


@router.get("/decision/{decision_id}")
async def get_decision_by_id(decision_id: str):
    dec = db.get_decision(decision_id)
    return dec or {"error": "Not found"}


@router.post("/simulate-what-if", response_model=WhatIfSimulationResponse)
async def simulate_what_if(req: WhatIfSimulationRequest):
    """
    What-If Risk Simulator: Calculates hypothetical outcomes for proposed entry,
    stop-loss, take-profit, adverse price excursion, and estimated round-trip transaction costs.
    """
    multiplier = 0.001  # standard BTC perpetual multiplier
    is_long = req.direction.upper() == "LONG"

    # Price differences
    if is_long:
        sl_diff = max(0.0, req.entry_price - req.stop_loss)
        tp_diff = max(0.0, req.take_profit - req.entry_price)
        adverse_price = req.entry_price * (1.0 - (req.adverse_move_pct / 100.0))
        adverse_loss = (req.entry_price - adverse_price) * req.quantity * multiplier
    else:
        sl_diff = max(0.0, req.stop_loss - req.entry_price)
        tp_diff = max(0.0, req.entry_price - req.take_profit)
        adverse_price = req.entry_price * (1.0 + (req.adverse_move_pct / 100.0))
        adverse_loss = (adverse_price - req.entry_price) * req.quantity * multiplier

    risk_at_sl = sl_diff * req.quantity * multiplier
    reward_at_tp = tp_diff * req.quantity * multiplier
    rr = round(reward_at_tp / risk_at_sl, 2) if risk_at_sl > 0 else 0.0

    notional = req.quantity * multiplier * req.entry_price
    fee_rate = req.fee_rate_bps / 10000.0
    slippage_rate = req.slippage_bps / 10000.0

    roundtrip_fees = round(notional * fee_rate * 2.0, 4)
    slippage_cost = round(notional * slippage_rate, 4)

    effective_loss = round(risk_at_sl + roundtrip_fees + slippage_cost, 4)
    effective_gain = round(max(0.0, reward_at_tp - roundtrip_fees - slippage_cost), 4)

    return WhatIfSimulationResponse(
        risk_at_stop_loss=round(risk_at_sl, 4),
        reward_at_take_profit=round(reward_at_tp, 4),
        reward_to_risk_ratio=rr,
        adverse_move_loss=round(adverse_loss, 4),
        estimated_roundtrip_fees=roundtrip_fees,
        estimated_slippage_cost=slippage_cost,
        effective_loss_with_costs=effective_loss,
        effective_gain_with_costs=effective_gain
    )


@router.get("/ml-status")
async def get_ml_status():
    return {
        "status": bot.ml_model.status,
        "validation_accuracy": bot.ml_model.validation_accuracy,
        "feature_columns": bot.ml_model.feature_columns,
        "sample_count": bot.ml_model.last_trained_sample_count
    }


@router.post("/train-ml")
async def trigger_ml_training():
    candles = await bot.exchange.get_candles(symbol=bot.passport.symbol, limit=150)
    result = bot.ml_model.train_and_validate(candles)
    return result
