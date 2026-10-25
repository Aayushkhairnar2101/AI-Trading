"""
Market Data & Chart Endpoints.
"""

from fastapi import APIRouter, Query
from typing import List, Dict, Any
from app.services.execution.bot_engine import bot
from app.services.strategy.indicators import compute_all_indicators

import numpy as np

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/instruments")
async def get_instruments() -> List[Dict[str, Any]]:
    return await bot.exchange.get_products()


@router.get("/ticker")
async def get_ticker(symbol: str = Query(default="BTCUSDT")):
    ticker = await bot.exchange.get_ticker(symbol=symbol)
    ticker["feed_health"] = bot.exchange.get_feed_status()
    return ticker


@router.get("/feed-status")
async def get_feed_status() -> Dict[str, Any]:
    return bot.exchange.get_feed_status()


@router.get("/candles")
async def get_candles(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="5m"),
    limit: int = Query(default=80, ge=30, le=300)
):
    df = await bot.exchange.get_candles(symbol=symbol, resolution=timeframe, limit=limit)
    enriched = compute_all_indicators(
        df,
        ema_fast_period=bot.strategy_config.ema_fast_period,
        ema_slow_period=bot.strategy_config.ema_slow_period,
        rsi_period=bot.strategy_config.rsi_period,
        adx_period=bot.strategy_config.adx_period,
        atr_period=bot.strategy_config.atr_period
    )
    # Ensure time is integer seconds and replace NaN with None for standard JSON serialization
    enriched["time"] = enriched["time"].astype(int)
    clean_records = enriched.replace({np.nan: None}).to_dict(orient="records")
    return clean_records
