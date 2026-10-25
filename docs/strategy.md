# RiskPilot AI — Trading Strategy & Mathematical Rationale

## 1. Strategy Overview: Regime-Aware Trend Follower
The default baseline strategy implemented in RiskPilot AI is a transparent, explainable momentum and trend-following model designed for crypto perpetual contracts.

### Technical Indicators Used
1. **EMA 9 & EMA 21 (Exponential Moving Averages)**: Identifies short-to-intermediate trend direction and momentum crossovers.
2. **RSI 14 (Relative Strength Index)**: Evaluates directional momentum using Wilder's smoothing algorithm.
3. **ADX 14 (Average Directional Index)**: Measures trend strength independent of direction.
4. **ATR 14 (Average True Range)**: Quantifies market volatility to dynamically anchor stop-loss distances and calculate contract quantities.

---

## 2. Signal Generation Rules

### LONG ENTRY
- **Crossover**: Confirmed bullish EMA 9 > EMA 21 on closed candles.
- **Momentum Filter**: RSI 14 in the bullish sweet spot ($52 \le \text{RSI} \le 68$). Avoids overbought exhaustion.
- **Trend Strength**: $\text{ADX} \ge 20.0$ and $+\text{DI} > -\text{DI}$.
- **Volatility Filter**: $\text{ATR } \% \le 3.5\%$ of price (avoids erratic market spikes).
- **Execution**:
  $$\text{Stop Loss} = \text{Entry} - (1.5 \times \text{ATR})$$
  $$\text{Take Profit} = \text{Entry} + (\text{Stop Distance} \times \text{R:R})$$

### SHORT ENTRY
- **Crossover**: Confirmed bearish EMA 9 < EMA 21 on closed candles.
- **Momentum Filter**: RSI 14 in the bearish sweet spot ($32 \le \text{RSI} \le 48$). Avoids oversold bounce traps.
- **Trend Strength**: $\text{ADX} \ge 20.0$ and $-\text{DI} > +\text{DI}$.
- **Volatility Filter**: Normal market spread and ATR.
- **Execution**:
  $$\text{Stop Loss} = \text{Entry} + (1.5 \times \text{ATR})$$
  $$\text{Take Profit} = \text{Entry} - (\text{Stop Distance} \times \text{R:R})$$

### NO TRADE Engine
A `NO_TRADE` decision is treated as an active, successful protective outcome. The engine explicitly logs why trading is paused:
- **Weak Trend**: $\text{ADX} < 20.0$ indicates consolidation/ranging market; whipsaw danger is high.
- **Indicator Conflict**: Fast EMA above Slow EMA, but RSI outside bounds or $-\text{DI} > +\text{DI}$.
- **Excessive Spread**: Market bid-ask spread exceeds $0.15\%$ threshold.
- **Insufficient History**: Fewer than 35 confirmed candles available.

---

## 3. Machine Learning Module
The optional Scikit-Learn module runs a walk-forward Gradient Boosting Classifier. It predicts the directional probability of 3-candle forward returns based on 9 non-leaking features:
1. `return_1`, `return_3`, `return_5` (Past return lags)
2. `ema_diff_pct` (Normalized divergence between EMA 9 and EMA 21)
3. `rsi`
4. `adx`
5. `di_spread` ($+\text{DI} - -\text{DI}$)
6. `atr_pct` (ATR relative to close price)
7. `vol_ratio` (Current candle volume vs 10-period rolling average)

Validation is performed strictly on chronological splits (80% train / 20% validation) with zero random shuffling to prevent lookahead bias.
