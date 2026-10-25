"""
Regime-Aware Trend Follower Signal Engine.
Evaluates closed candles for Bullish / Bearish crossovers, RSI momentum, and ADX strength.
Generates structured trading setups with Stop Loss and Take Profit levels, or explainable NO TRADE decisions.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from app.schemas.decision import TradeDirection, MarketRegime
from app.schemas.strategy import StrategyConfig
from app.services.strategy.indicators import compute_all_indicators
from app.services.strategy.regime_detector import RegimeDetector


class StrategySignal:
    def __init__(
        self,
        direction: TradeDirection,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        stop_distance: float,
        target_distance: float,
        reward_to_risk_ratio: float,
        regime: MarketRegime,
        reasons: List[str],
        no_trade_reasons: List[str],
        indicator_snapshot: Dict[str, Any]
    ):
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.stop_distance = stop_distance
        self.target_distance = target_distance
        self.reward_to_risk_ratio = reward_to_risk_ratio
        self.regime = regime
        self.reasons = reasons
        self.no_trade_reasons = no_trade_reasons
        self.indicator_snapshot = indicator_snapshot


class SignalEngine:
    def __init__(self, config: Optional[StrategyConfig] = None):
        self.config = config or StrategyConfig()
        self.regime_detector = RegimeDetector(
            adx_trending_threshold=self.config.adx_threshold,
            max_safe_atr_pct=self.config.max_atr_pct
        )

    def evaluate(
        self,
        candle_df: pd.DataFrame,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None
    ) -> StrategySignal:
        """
        Evaluates candles and returns a structured StrategySignal.
        Always inspects confirmed closed candles to eliminate repaint risk.
        """
        if len(candle_df) < 35:
            return StrategySignal(
                direction=TradeDirection.NO_TRADE,
                entry_price=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                stop_distance=0.0,
                target_distance=0.0,
                reward_to_risk_ratio=0.0,
                regime=MarketRegime.INSUFFICIENT_DATA,
                reasons=[],
                no_trade_reasons=[f"Insufficient candles: {len(candle_df)} loaded, minimum 35 required."],
                indicator_snapshot={}
            )

        # Enrich dataframe
        enriched = compute_all_indicators(
            candle_df,
            ema_fast_period=self.config.ema_fast_period,
            ema_slow_period=self.config.ema_slow_period,
            rsi_period=self.config.rsi_period,
            adx_period=self.config.adx_period,
            atr_period=self.config.atr_period
        )

        # Last closed candle (index -1 if input contains only closed candles)
        curr = enriched.iloc[-1]
        prev = enriched.iloc[-2]

        current_price = float(curr["close"])
        if bid_price and ask_price and bid_price > 0:
            spread_pct = ((ask_price - bid_price) / bid_price) * 100.0
        else:
            spread_pct = 0.02  # standard nominal testnet spread

        snapshot = {
            "close": current_price,
            "ema_fast": float(curr["ema_fast"]),
            "ema_slow": float(curr["ema_slow"]),
            "prev_ema_fast": float(prev["ema_fast"]),
            "prev_ema_slow": float(prev["ema_slow"]),
            "rsi": float(curr["rsi"]),
            "adx": float(curr["adx"]),
            "plus_di": float(curr["plus_di"]),
            "minus_di": float(curr["minus_di"]),
            "atr": float(curr["atr"]),
            "atr_pct": float(curr["atr_pct"]),
            "spread_pct": spread_pct
        }

        # Market regime check
        regime, regime_reason = self.regime_detector.detect_regime(snapshot, len(candle_df))

        # Check spread safety
        no_trade_reasons: List[str] = []
        if spread_pct > self.config.max_spread_pct:
            no_trade_reasons.append(
                f"Market spread {spread_pct:.3f}% exceeds maximum allowable spread {self.config.max_spread_pct:.3f}%."
            )

        if regime == MarketRegime.HIGH_VOLATILITY:
            no_trade_reasons.append(regime_reason)

        if regime == MarketRegime.RANGING:
            no_trade_reasons.append(
                f"Ranging market: ADX is {snapshot['adx']:.1f} (needs >={self.config.adx_threshold:.1f} for trend setup). Whipsaw risk high."
            )

        ema_fast_curr = snapshot["ema_fast"]
        ema_slow_curr = snapshot["ema_slow"]
        ema_fast_prev = snapshot["prev_ema_fast"]
        ema_slow_prev = snapshot["prev_ema_slow"]

        # Collect strategy rationale observations (what the indicators show)
        strategy_observations: List[str] = []
        if ema_fast_curr > ema_slow_curr:
            strategy_observations.append(f"Bullish trend structure: EMA 9 ({ema_fast_curr:.2f}) is above EMA 21 ({ema_slow_curr:.2f})")
        elif ema_fast_curr < ema_slow_curr:
            strategy_observations.append(f"Bearish trend structure: EMA 9 ({ema_fast_curr:.2f}) is below EMA 21 ({ema_slow_curr:.2f})")
        else:
            strategy_observations.append("Neutral trend structure: EMA 9 and EMA 21 are identical")

        strategy_observations.append(f"Momentum snapshot: RSI is {snapshot['rsi']:.1f}")
        strategy_observations.append(
            f"Trend strength snapshot: ADX is {snapshot['adx']:.1f} (+DI: {snapshot['plus_di']:.1f}, -DI: {snapshot['minus_di']:.1f})"
        )

        # If regime blocks trading or spread is abnormal, return NO_TRADE immediately with rationale preserved
        if no_trade_reasons:
            return StrategySignal(
                direction=TradeDirection.NO_TRADE,
                entry_price=current_price,
                stop_loss=0.0,
                take_profit=0.0,
                stop_distance=0.0,
                target_distance=0.0,
                reward_to_risk_ratio=0.0,
                regime=regime,
                reasons=strategy_observations,
                no_trade_reasons=no_trade_reasons,
                indicator_snapshot=snapshot
            )

        # Analyze LONG setup
        # Crossover: current EMA 9 > EMA 21, and either previous was <= or trending expansion
        bullish_crossover = (ema_fast_curr > ema_slow_curr) and (
            (ema_fast_prev <= ema_slow_prev) or ((ema_fast_curr - ema_slow_curr) > (ema_fast_prev - ema_slow_prev))
        )
        rsi_bullish = self.config.rsi_long_min <= snapshot["rsi"] <= self.config.rsi_long_max
        adx_strong = snapshot["adx"] >= self.config.adx_threshold

        # Analyze SHORT setup
        bearish_crossover = (ema_fast_curr < ema_slow_curr) and (
            (ema_fast_prev >= ema_slow_prev) or ((ema_slow_curr - ema_fast_curr) > (ema_slow_prev - ema_fast_prev))
        )
        rsi_bearish = self.config.rsi_short_min <= snapshot["rsi"] <= self.config.rsi_short_max

        atr = max(snapshot["atr"], current_price * 0.001)

        # Long Evaluation
        if bullish_crossover and rsi_bullish and adx_strong and snapshot["plus_di"] > snapshot["minus_di"]:
            stop_distance = atr * self.config.atr_stop_multiplier
            stop_loss = current_price - stop_distance
            target_distance = stop_distance * self.config.min_reward_to_risk
            take_profit = current_price + target_distance
            rr = target_distance / stop_distance if stop_distance > 0 else 0.0

            reasons = [
                f"Bullish EMA crossover: EMA 9 ({ema_fast_curr:.2f}) > EMA 21 ({ema_slow_curr:.2f})",
                f"RSI confirms positive momentum: {snapshot['rsi']:.1f} (in sweet spot {self.config.rsi_long_min}–{self.config.rsi_long_max})",
                f"Trend strength confirmed: ADX {snapshot['adx']:.1f} >= {self.config.adx_threshold} with +DI ({snapshot['plus_di']:.1f}) > -DI ({snapshot['minus_di']:.1f})",
                f"Stop-loss placed at 1.5 ATR ({stop_distance:.2f} pts) with target yielding {rr:.2f}R"
            ]
            return StrategySignal(
                direction=TradeDirection.LONG,
                entry_price=current_price,
                stop_loss=round(stop_loss, 2),
                take_profit=round(take_profit, 2),
                stop_distance=round(stop_distance, 2),
                target_distance=round(target_distance, 2),
                reward_to_risk_ratio=round(rr, 2),
                regime=regime,
                reasons=reasons,
                no_trade_reasons=[],
                indicator_snapshot=snapshot
            )

        # Short Evaluation
        if bearish_crossover and rsi_bearish and adx_strong and snapshot["minus_di"] > snapshot["plus_di"]:
            stop_distance = atr * self.config.atr_stop_multiplier
            stop_loss = current_price + stop_distance
            target_distance = stop_distance * self.config.min_reward_to_risk
            take_profit = current_price - target_distance
            rr = target_distance / stop_distance if stop_distance > 0 else 0.0

            reasons = [
                f"Bearish EMA crossover: EMA 9 ({ema_fast_curr:.2f}) < EMA 21 ({ema_slow_curr:.2f})",
                f"RSI confirms negative momentum: {snapshot['rsi']:.1f} (in sweet spot {self.config.rsi_short_min}–{self.config.rsi_short_max})",
                f"Trend strength confirmed: ADX {snapshot['adx']:.1f} >= {self.config.adx_threshold} with -DI ({snapshot['minus_di']:.1f}) > +DI ({snapshot['plus_di']:.1f})",
                f"Stop-loss placed at 1.5 ATR ({stop_distance:.2f} pts) with target yielding {rr:.2f}R"
            ]
            return StrategySignal(
                direction=TradeDirection.SHORT,
                entry_price=current_price,
                stop_loss=round(stop_loss, 2),
                take_profit=round(take_profit, 2),
                stop_distance=round(stop_distance, 2),
                target_distance=round(target_distance, 2),
                reward_to_risk_ratio=round(rr, 2),
                regime=regime,
                reasons=reasons,
                no_trade_reasons=[],
                indicator_snapshot=snapshot
            )

        # Explain why NO TRADE was selected — collect ONLY unfulfilled criteria (Trade Rejection Reasons)
        unfulfilled_conditions: List[str] = []
        if ema_fast_curr > ema_slow_curr:
            # Bullish bias exists, but confirmation criteria failed
            if not bullish_crossover:
                unfulfilled_conditions.append("EMA spread is contracting (no fresh crossover or momentum expansion)")
            if not rsi_bullish:
                unfulfilled_conditions.append(
                    f"RSI filter unfulfilled: RSI ({snapshot['rsi']:.1f}) is outside required long entry bounds ({self.config.rsi_long_min}–{self.config.rsi_long_max})"
                )
            if not adx_strong:
                unfulfilled_conditions.append(
                    f"Insufficient trend strength: ADX ({snapshot['adx']:.1f}) is below trend threshold {self.config.adx_threshold}"
                )
            if snapshot["plus_di"] <= snapshot["minus_di"]:
                unfulfilled_conditions.append(
                    f"Conflicting directional movement: +DI ({snapshot['plus_di']:.1f}) <= -DI ({snapshot['minus_di']:.1f})"
                )
        elif ema_fast_curr < ema_slow_curr:
            # Bearish bias exists, but confirmation criteria failed
            if not bearish_crossover:
                unfulfilled_conditions.append("EMA spread is contracting (no fresh crossover or momentum expansion)")
            if not rsi_bearish:
                unfulfilled_conditions.append(
                    f"RSI filter unfulfilled: RSI ({snapshot['rsi']:.1f}) is outside required short entry bounds ({self.config.rsi_short_min}–{self.config.rsi_short_max})"
                )
            if not adx_strong:
                unfulfilled_conditions.append(
                    f"Insufficient trend strength: ADX ({snapshot['adx']:.1f}) is below trend threshold {self.config.adx_threshold}"
                )
            if snapshot["minus_di"] <= snapshot["plus_di"]:
                unfulfilled_conditions.append(
                    f"Conflicting directional movement: -DI ({snapshot['minus_di']:.1f}) <= +DI ({snapshot['plus_di']:.1f})"
                )
        else:
            unfulfilled_conditions.append("EMA 9 and EMA 21 are identical (no directional bias established)")

        return StrategySignal(
            direction=TradeDirection.NO_TRADE,
            entry_price=current_price,
            stop_loss=0.0,
            take_profit=0.0,
            stop_distance=0.0,
            target_distance=0.0,
            reward_to_risk_ratio=0.0,
            regime=regime,
            reasons=strategy_observations,
            no_trade_reasons=unfulfilled_conditions,
            indicator_snapshot=snapshot
        )
