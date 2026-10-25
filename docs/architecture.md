# RiskPilot AI — System Architecture

## 1. Architectural Philosophy
RiskPilot AI is designed around a single non-negotiable principle:
> **"The user defines the risk. AI evaluates the opportunity. The risk engine decides whether the trade is allowed."**

In standard algorithmic trading systems, a machine learning model or strategy directly executes trades. In RiskPilot AI, the Strategy & ML layers are decoupled from the Risk Management layer. Even if a signal produces a 99% probability, the trade **must** be blocked if it breaches the user's Personal Risk Passport or code-level safety limits.

```
       +-------------------------------------------------------------+
       |               Delta Exchange Testnet Environment             |
       |             https://cdn-ind.testnet.deltaex.org             |
       +------------------------------+------------------------------+
                                      |
                         REST / HMAC-SHA256 / WS
                                      |
                                      v
       +-------------------------------------------------------------+
       |                       FastAPI Backend                       |
       |  +--------------------+  +-------------------------------+  |
       |  | DeltaClient        |  | SignalEngine (EMA/RSI/ADX/ATR)|  |
       |  +--------------------+  +-------------------------------+  |
       |  +--------------------+  +-------------------------------+  |
       |  | MLStrategyModel    |  | Central Risk Manager          |  |
       |  +--------------------+  +-------------------------------+  |
       |  +--------------------+  +-------------------------------+  |
       |  | Circuit Breaker    |  | Position Sizer                |  |
       |  +--------------------+  +-------------------------------+  |
       |  +--------------------+  +-------------------------------+  |
       |  | Order Manager      |  | SQLite Storage (Receipts/Logs)|  |
       |  +--------------------+  +-------------------------------+  |
       +------------------------------+------------------------------+
                                      |
                             JSON REST APIs
                                      |
                                      v
       +-------------------------------------------------------------+
       |                  React.js + Vite Frontend                   |
       |  +--------------------+  +-------------------------------+  |
       |  | Overview Dashboard |  | Lightweight Candlestick Chart |  |
       |  +--------------------+  +-------------------------------+  |
       |  +--------------------+  +-------------------------------+  |
       |  | AI Decision Center |  | Personal Risk Passport Wizard |  |
       |  +--------------------+  +-------------------------------+  |
       |  +--------------------+  +-------------------------------+  |
       |  | What-If Simulator  |  | Risk Monitor & Breaker Status |  |
       |  +--------------------+  +-------------------------------+  |
       |  +--------------------+  +-------------------------------+  |
       |  | Trade Journal      |  | Strategy Lab & ML Center      |  |
       |  +--------------------+  +-------------------------------+  |
       +-------------------------------------------------------------+
```

## 2. Component Breakdown

### A. Exchange Integration Layer (`app.services.exchange.delta_client`)
- Direct integration with **Delta Exchange India Testnet** (`cdn-ind.testnet.deltaex.org`).
- Official HMAC-SHA256 request signing using `method + timestamp + path + query_string + payload`.
- Endpoint validation: Refuses to start if production endpoints are configured.
- Seamless fallback to Demo-Safe Simulation Mode when API credentials are omitted for hackathon demos.

### B. Signal Generation & Technical Indicators (`app.services.strategy`)
- **Indicators** (`indicators.py`): Vectorized EMA 9/21, Wilder-smoothed RSI 14, ATR 14, and ADX 14 with +DI/-DI.
- **Market Regime Detector** (`regime_detector.py`): Dynamically classifies conditions into `TRENDING_BULLISH`, `TRENDING_BEARISH`, `RANGING`, or `HIGH_VOLATILITY`.
- **Signal Engine** (`signal_engine.py`): Requires confirmed closed candles to eliminate repaint artifacts.

### C. Machine Learning Module (`app.services.strategy.ml_model`)
- Scikit-Learn Gradient Boosting Classifier trained on chronological walk-forward splits (80/20 train/validation).
- Computes probability of upward or downward moves based on non-leaking features: return lags, EMA distance %, RSI, ADX, ATR %, and volume ratios.
- Provides model state indicator: `NOT_TRAINED`, `INSUFFICIENT_DATA`, `VALIDATING`, `READY`.

### D. Central Risk Engine (`app.services.risk`)
- **Position Sizer** (`position_sizer.py`): Computes quantity strictly from monetary risk budget and stop distance.
- **Circuit Breaker** (`circuit_breaker.py`): Tracks session drawdown and loss streaks, halting new trades when limits are breached.
- **Risk Manager** (`risk_manager.py`): Evaluates 11 safety rules before emitting a verdict.

### E. Storage Layer (`app.services.storage.database`)
- Local SQLite database (`riskpilot.db`).
- Generates immutable **Trade Decision Receipts** with timestamps, signals, and sizing data.
- Persists trade journals, performance metrics, and audit logs.
