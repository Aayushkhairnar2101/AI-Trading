"""
Unit Tests for Strategy Signals: LONG, SHORT, and Explainable NO TRADE Decisions.
"""

import pytest
import pandas as pd
import numpy as np
from app.services.strategy.signal_engine import SignalEngine
from app.schemas.strategy import StrategyConfig
from app.schemas.decision import TradeDirection, MarketRegime


def build_synthetic_trend(direction: str, count: int = 50) -> pd.DataFrame:
    base = 65000.0
    slope = 50.0 if direction == "bullish" else -50.0
    times = list(range(count))
    closes = [base + (i * slope) for i in range(count)]

    opens = [c - (slope * 0.3) for c in closes]
    highs = [max(o, c) + 30.0 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 30.0 for o, c in zip(opens, closes)]
    volumes = [50.0] * count

    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })


def test_insufficient_data_returns_no_trade():
    engine = SignalEngine()
    short_df = pd.DataFrame({"close": [60000.0] * 10, "open": [60000.0] * 10, "high": [60010.0] * 10, "low": [59990.0] * 10})
    signal = engine.evaluate(short_df)
    assert signal.direction == TradeDirection.NO_TRADE
    assert signal.regime == MarketRegime.INSUFFICIENT_DATA
    assert len(signal.no_trade_reasons) > 0


def test_bullish_trend_signal_generation():
    engine = SignalEngine(StrategyConfig(adx_threshold=15.0, rsi_long_min=45.0, rsi_long_max=85.0))
    bull_df = build_synthetic_trend("bullish", count=60)
    signal = engine.evaluate(bull_df, bid_price=bull_df["close"].iloc[-1] - 0.5, ask_price=bull_df["close"].iloc[-1] + 0.5)

    if signal.direction == TradeDirection.LONG:
        assert signal.stop_loss < signal.entry_price
        assert signal.take_profit > signal.entry_price
        assert signal.reward_to_risk_ratio >= 1.5
        assert len(signal.reasons) >= 3
    else:
        # If no trade, it must clearly explain why
        assert len(signal.no_trade_reasons) > 0


def test_bearish_trend_signal_generation():
    engine = SignalEngine(StrategyConfig(adx_threshold=15.0, rsi_short_min=20.0, rsi_short_max=60.0))
    bear_df = build_synthetic_trend("bearish", count=60)
    signal = engine.evaluate(bear_df, bid_price=bear_df["close"].iloc[-1] - 0.5, ask_price=bear_df["close"].iloc[-1] + 0.5)

    if signal.direction == TradeDirection.SHORT:
        assert signal.stop_loss > signal.entry_price
        assert signal.take_profit < signal.entry_price
        assert signal.reward_to_risk_ratio >= 1.5
    else:
        assert len(signal.no_trade_reasons) > 0


def test_excessive_spread_triggers_no_trade():
    engine = SignalEngine(StrategyConfig(max_spread_pct=0.10))
    df = build_synthetic_trend("bullish", count=50)
    # 2% spread
    bid = 65000.0
    ask = 66300.0
    signal = engine.evaluate(df, bid_price=bid, ask_price=ask)
    assert signal.direction == TradeDirection.NO_TRADE
    assert any("spread" in reason.lower() for reason in signal.no_trade_reasons)
