"""
Adaptive Market Regime Detection.
Classifies the market into:
- TRENDING_BULLISH: Strong uptrend (EMA fast > slow, ADX > 20, +DI > -DI)
- TRENDING_BEARISH: Strong downtrend (EMA fast < slow, ADX > 20, -DI > +DI)
- RANGING: Low directional momentum (ADX < 20), risk of whipsaws
- HIGH_VOLATILITY: Abnormal volatility where spread or ATR spikes beyond safe thresholds
- INSUFFICIENT_DATA: History too brief to calculate indicators safely
"""

from typing import Dict, Any, Tuple
from app.schemas.decision import MarketRegime


class RegimeDetector:
    def __init__(
        self,
        adx_trending_threshold: float = 20.0,
        max_safe_atr_pct: float = 3.5,
        min_required_candles: int = 35
    ):
        self.adx_trending_threshold = adx_trending_threshold
        self.max_safe_atr_pct = max_safe_atr_pct
        self.min_required_candles = min_required_candles

    def detect_regime(
        self,
        indicator_snapshot: Dict[str, Any],
        candle_count: int
    ) -> Tuple[MarketRegime, str]:
        """
        Detects current market regime and returns (regime, explanation).
        """
        if candle_count < self.min_required_candles or not indicator_snapshot:
            return (
                MarketRegime.INSUFFICIENT_DATA,
                f"Insufficient historical candles ({candle_count}/{self.min_required_candles}) to determine market regime."
            )

        atr_pct = indicator_snapshot.get("atr_pct", 0.0)
        adx = indicator_snapshot.get("adx", 0.0)
        ema_fast = indicator_snapshot.get("ema_fast", 0.0)
        ema_slow = indicator_snapshot.get("ema_slow", 0.0)
        plus_di = indicator_snapshot.get("plus_di", 0.0)
        minus_di = indicator_snapshot.get("minus_di", 0.0)

        # 1. Abnormal Volatility Check
        if atr_pct > self.max_safe_atr_pct:
            return (
                MarketRegime.HIGH_VOLATILITY,
                f"Abnormal volatility detected: ATR is {atr_pct:.2f}% of price (safe ceiling: {self.max_safe_atr_pct}%). Trading paused."
            )

        # 2. Trending Check (ADX >= threshold)
        if adx >= self.adx_trending_threshold:
            if ema_fast > ema_slow and plus_di >= minus_di:
                return (
                    MarketRegime.TRENDING_BULLISH,
                    f"Trending Bullish: EMA 9 ({ema_fast:.2f}) > EMA 21 ({ema_slow:.2f}), ADX ({adx:.1f}) confirms trend strength, +DI ({plus_di:.1f}) dominates."
                )
            elif ema_fast < ema_slow and minus_di > plus_di:
                return (
                    MarketRegime.TRENDING_BEARISH,
                    f"Trending Bearish: EMA 9 ({ema_fast:.2f}) < EMA 21 ({ema_slow:.2f}), ADX ({adx:.1f}) confirms trend strength, -DI ({minus_di:.1f}) dominates."
                )
            else:
                return (
                    MarketRegime.RANGING,
                    f"Conflicting directional signals: ADX is {adx:.1f} but EMA and DI components are diverged. Classified as RANGING."
                )

        # 3. Ranging / Consolidation
        return (
            MarketRegime.RANGING,
            f"Ranging / Consolidation: ADX is {adx:.1f} (below trending threshold {self.adx_trending_threshold:.1f}). Market lacks directional momentum."
        )
