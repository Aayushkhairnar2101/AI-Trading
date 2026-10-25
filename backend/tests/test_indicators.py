"""
Unit Tests for Technical Indicators: EMA, RSI, ATR, and ADX.
"""

import pytest
import pandas as pd
import numpy as np
from app.services.strategy.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_atr,
    calculate_adx,
    compute_all_indicators
)


@pytest.fixture
def sample_ohlcv_data():
    """Generates 50 synthetic candle rows."""
    np.random.seed(42)
    n = 50
    base = 65000.0
    drift = np.linspace(0, 1000, n)
    noise = np.random.normal(0, 50, n)
    closes = base + drift + noise

    highs = closes + np.random.uniform(20, 80, n)
    lows = closes - np.random.uniform(20, 80, n)
    opens = closes + np.random.uniform(-30, 30, n)
    volumes = np.random.uniform(10, 100, n)

    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })


def test_calculate_ema(sample_ohlcv_data):
    ema9 = calculate_ema(sample_ohlcv_data["close"], period=9)
    assert len(ema9) == len(sample_ohlcv_data)
    # EMA responds to trend
    assert ema9.iloc[-1] > ema9.iloc[0]
    # EMA smoothing property: last EMA is within recent prices
    assert sample_ohlcv_data["close"].min() <= ema9.iloc[-1] <= sample_ohlcv_data["close"].max()


def test_calculate_rsi(sample_ohlcv_data):
    rsi = calculate_rsi(sample_ohlcv_data["close"], period=14)
    assert len(rsi) == len(sample_ohlcv_data)
    # RSI must be strictly bounded between 0 and 100
    assert (rsi >= 0.0).all()
    assert (rsi <= 100.0).all()
    # In an uptrend, RSI should be above 50
    assert rsi.iloc[-1] > 50.0


def test_calculate_atr(sample_ohlcv_data):
    atr = calculate_atr(sample_ohlcv_data, period=14)
    assert len(atr) == len(sample_ohlcv_data)
    # ATR must always be strictly positive
    assert (atr > 0.0).all()
    # Typical true range is around 40-160 for this synthetic data
    assert 20.0 < atr.iloc[-1] < 200.0


def test_calculate_adx(sample_ohlcv_data):
    adx, plus_di, minus_di = calculate_adx(sample_ohlcv_data, period=14)
    assert len(adx) == len(sample_ohlcv_data)
    assert len(plus_di) == len(sample_ohlcv_data)
    assert len(minus_di) == len(sample_ohlcv_data)

    # Values must be non-negative
    assert (adx >= 0.0).all()
    assert (plus_di >= 0.0).all()
    assert (minus_di >= 0.0).all()


def test_compute_all_indicators(sample_ohlcv_data):
    enriched = compute_all_indicators(sample_ohlcv_data)
    required_cols = ["ema_fast", "ema_slow", "rsi", "atr", "adx", "plus_di", "minus_di", "atr_pct"]
    for col in required_cols:
        assert col in enriched.columns
        assert not enriched[col].isna().all()
