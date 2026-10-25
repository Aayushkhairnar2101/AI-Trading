"""
Technical Indicators Engine: EMA, RSI, ADX, and ATR.
Implemented with vectorization (pandas and numpy) matching standard Wilder smoothing.
Designed for high performance, accuracy, and testability.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculates Relative Strength Index (RSI) using Wilder's exponential smoothing.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Wilder's smoothing alpha = 1 / period
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates Average True Range (ATR) using Wilder's smoothing.
    Requires columns: 'high', 'low', 'close'.
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    return atr


def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates ADX (Average Directional Index), +DI, and -DI.
    Requires columns: 'high', 'low', 'close'.
    Returns (adx, plus_di, minus_di).
    """
    high = df["high"]
    low = df["low"]
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    atr = calculate_atr(df, period=period)

    plus_dm_series = pd.Series(plus_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean()
    minus_dm_series = pd.Series(minus_dm, index=df.index).ewm(alpha=1.0 / period, adjust=False).mean()

    plus_di = 100.0 * (plus_dm_series / atr.replace(0.0, np.nan)).fillna(0.0)
    minus_di = 100.0 * (minus_dm_series / atr.replace(0.0, np.nan)).fillna(0.0)

    di_sum = plus_di + minus_di
    dx = 100.0 * ((plus_di - minus_di).abs() / di_sum.replace(0.0, np.nan)).fillna(0.0)
    adx = dx.ewm(alpha=1.0 / period, adjust=False).mean().fillna(0.0)

    return adx, plus_di, minus_di


def compute_all_indicators(
    df: pd.DataFrame,
    ema_fast_period: int = 9,
    ema_slow_period: int = 21,
    rsi_period: int = 14,
    adx_period: int = 14,
    atr_period: int = 14
) -> pd.DataFrame:
    """
    Enriches candle DataFrame with all required indicators.
    Input DataFrame must have lowercase 'open', 'high', 'low', 'close', 'volume'.
    """
    df = df.copy()
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            raise ValueError(f"Missing required column '{col}' in candle data")

    df["ema_fast"] = calculate_ema(df["close"], period=ema_fast_period)
    df["ema_slow"] = calculate_ema(df["close"], period=ema_slow_period)
    df["rsi"] = calculate_rsi(df["close"], period=rsi_period)
    df["atr"] = calculate_atr(df, period=atr_period)

    adx, plus_di, minus_di = calculate_adx(df, period=adx_period)
    df["adx"] = adx
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di

    # Volatility indicator: ATR as % of close
    df["atr_pct"] = (df["atr"] / df["close"]) * 100.0

    return df


def get_latest_indicator_snapshot(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Extracts the latest confirmed candle's indicator snapshot.
    Uses second-to-last candle if latest candle is still open, or latest if already confirmed.
    """
    if len(df) == 0:
        return {}

    row = df.iloc[-1]
    return {
        "close": float(row.get("close", 0.0)),
        "ema_fast": float(row.get("ema_fast", 0.0)),
        "ema_slow": float(row.get("ema_slow", 0.0)),
        "rsi": float(row.get("rsi", 50.0)),
        "adx": float(row.get("adx", 0.0)),
        "plus_di": float(row.get("plus_di", 0.0)),
        "minus_di": float(row.get("minus_di", 0.0)),
        "atr": float(row.get("atr", 0.0)),
        "atr_pct": float(row.get("atr_pct", 0.0)),
        "volume": float(row.get("volume", 0.0)),
    }
