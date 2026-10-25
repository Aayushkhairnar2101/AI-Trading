# RiskPilot AI — Personalized, Explainable Algorithmic Trading System

[![Test Suite](https://img.shields.io/badge/pytest-68%20passed-brightgreen.svg)]()
[![Environment](https://img.shields.io/badge/Delta%20Exchange-India%20Testnet-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)]()
[![React](https://img.shields.io/badge/React-19-61dafb.svg)]()
[![Vite](https://img.shields.io/badge/Vite-8-646cff.svg)]()
[![Safety](https://img.shields.io/badge/Production%20Switch-Blocked%20at%20Code%20Level-red.svg)]()

> *"The user defines the risk. AI evaluates the opportunity. The risk engine decides whether the trade is allowed."*

---

## 1. Problem Statement
Retail traders and quantitative enthusiasts face two catastrophic pitfalls:
1. **Emotional & Uncontrolled Risk**: Lack of strict position sizing, revenge trading after losses, and failure to respect maximum daily drawdowns.
2. **Black-Box AI Models**: Proprietary trading bots that generate opaque signals without explanation, frequently forcing unsafe trades in ranging or illiquid market regimes.

## 2. Innovation & Value Proposition
**RiskPilot AI** connects directly to the **Delta Exchange India Testnet** (`cdn-ind.testnet.deltaex.org`) to solve both challenges:
- **Personal Risk Passport**: Before a single trade is evaluated, the user configures their capital allocation, risk budget per trade, maximum daily loss, and leverage ceiling. Code-level hard limits (maximum 2% risk per trade, 5% daily loss) **cannot be overridden** by any profile.
- **Pre-Trade Decision Card**: Every opportunity is explained in plain English, breaking down the technical rationale, mathematical position sizing, and 11 distinct risk checks. If a trade is blocked, the user is told exactly why.
- **Circuit Breaker System**: Automatically trips and freezes new entries if session daily drawdown reaches the user's ceiling or if consecutive losses hit the streak threshold.
- **Demo-Safe Presentation Mode**: Runs seamlessly in live testnet mode or realistic simulation mode when external testnet keys are unconfigured, ensuring zero demo failures during evaluations.

---

## 3. Technology Stack

### Backend
- **Python 3.13 / FastAPI**: High-performance asynchronous REST API.
- **Pydantic v2 & Pydantic-Settings**: Strict input validation and environment safety enforcement.
- **Pandas & NumPy**: Vectorized technical indicator calculation (Wilder-smoothed RSI, ATR, EMA, ADX).
- **Scikit-Learn**: Machine learning classification module with chronological walk-forward validation (80/20 train/validation split, zero lookahead leakage).
- **SQLite**: Local relational database for immutable Trade Decision Receipts, trade journals, performance analytics, and audit logs.
- **HTTPX / HMAC-SHA256**: Official Delta Exchange Testnet REST client and request signing.

### Frontend
- **React.js 19 & Vite 8**: Clean, modern financial dashboard.
- **Lightweight Charts (TradingView v5)**: Interactive candlestick charts with EMA 9/21 overlays and volume histograms.
- **Lucide Icons & Vanilla CSS**: Polished light-theme design system with accessible typography, responsive grids, and clear risk badges.

---

## 4. Key Mathematical Formulas

### A. Position Sizing
$$\text{Monetary Risk Budget} = \text{Allocated Capital} \times \left( \frac{\text{Risk Per Trade } \%}{100} \right)$$
$$\text{Contracts} = \left\lfloor \frac{\text{Monetary Risk Budget}}{|\text{Entry} - \text{Stop Loss}| \times \text{Contract Multiplier}} \right\rfloor_{\text{Lot Size}}$$

### B. Technical Indicators
- **EMA**: $\text{EMA}_t = \alpha \cdot P_t + (1 - \alpha) \cdot \text{EMA}_{t-1}$, where $\alpha = \frac{2}{N + 1}$
- **RSI (Wilder)**: $\text{RSI} = 100 - \frac{100}{1 + \text{RS}}$, where $\alpha = \frac{1}{14}$
- **ATR (Wilder)**: $\text{TR} = \max(H - L, |H - C_{t-1}|, |L - C_{t-1}|)$
- **ADX (14)**: Measures trend strength. Trades are permitted only when $\text{ADX} \ge 20.0$.

---

## 5. Personal Risk Passport Presets

| Preset Tier | Risk Budget / Trade | Max Daily Loss | Leverage Cap | Max Open Positions | Default Confirmation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Conservative** | 0.25% of capital | 1.0% of equity | 1.0x (Spot equiv.) | 1 Position | ADX $\ge 22$, tighter RSI |
| **Balanced** | 0.50% of capital | 2.0% of equity | 2.0x | 1-2 Positions | Standard regime checks |
| **Aggressive (Testnet Only)** | 1.00% of capital | 3.0% of equity | 3.0x | 2 Positions | Responsive crossover |
| **Hard Code Limit** | **Max 2.0%** | **Max 5.0%** | **Max 10.0x** | **Max 5** | **Strictly Enforced** |

---

## 6. Project Structure

```
Token iq/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entrypoint & lifespan
│   │   ├── config.py                  # Environment config & production host safety blockers
│   │   ├── api/                       # REST routes (status, market, passport, strategy, bot, analytics)
│   │   ├── schemas/                   # Pydantic models for cards, orders, passport, analytics
│   │   ├── services/
│   │   │   ├── exchange/              # delta_client.py (HMAC-SHA256, testnet endpoints)
│   │   │   ├── strategy/              # indicators.py, regime_detector.py, signal_engine.py, ml_model.py
│   │   │   ├── risk/                  # risk_manager.py, position_sizer.py, circuit_breaker.py
│   │   │   ├── execution/             # order_manager.py, bot_engine.py
│   │   │   └── storage/               # database.py (SQLite receipts & audit logs)
│   ├── tests/                         # Pytest test suite (68 passing unit tests)
│   │   ├── test_delta_client.py       # HMAC signing, auth, rate-limit, redaction tests
│   │   ├── test_integration_safety.py # Extended security, env validation, logging safety
│   │   ├── test_circuit_breaker.py    # Daily drawdown, consecutive-loss, prod URL block
│   │   ├── test_risk_manager.py       # Risk checks, balance, duplicate, stale data
│   │   ├── test_indicators.py         # EMA, RSI, ATR, ADX correctness
│   │   ├── test_position_sizer.py     # Position sizing, leverage ceiling
│   │   └── test_signals.py            # Signal generation for LONG, SHORT, NO TRADE
│   ├── requirements.txt
│   ├── pytest.ini                     # anyio async test configuration
│   ├── conftest.py                    # Pytest marker registration
│   ├── .env.example                   # Safe template — commit this, NEVER the real .env
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── components/                # Navbar, DecisionCard, CandleChart, WhatIfSimulator, etc.
│   │   ├── services/                  # api.js client
│   │   ├── App.jsx                    # Main dashboard application
│   │   └── index.css                  # Custom light-theme design system
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
├── docs/
│   ├── architecture.md                # System architecture & component interaction
│   ├── strategy.md                    # Strategy rules, indicators, and ML pipeline
│   ├── risk_management.md             # Position sizing & risk framework
│   └── demo_script.md                 # 5-minute live hackathon presentation script
├── .gitignore                         # Root Git exclusion rules (.env strictly ignored)
└── README.md
```

---

## 7. Windows Setup & Startup Instructions

### Prerequisites
- Python 3.10+ (Tested on Python 3.13.7)
- Node.js 18+ and npm (Tested on Node v24.14.0)

### Step 1: Backend Setup
Open PowerShell in the project root (`Token iq/`):
```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### Step 2: Configure Environment (Local Only — Never Commit)
```powershell
# Still in the backend/ directory:
copy .env.example .env
```
Open `backend\.env` in any text editor (Notepad, VS Code, etc.) and fill in your credentials:
```env
DELTA_ENV=india_testnet
DELTA_REST_BASE_URL=https://cdn-ind.testnet.deltaex.org
DELTA_WS_PUBLIC_URL=wss://socket-ind-pub.testnet.deltaex.org
DELTA_WS_PRIVATE_URL=wss://socket-ind.testnet.deltaex.org
DELTA_API_KEY=your_fresh_india_testnet_api_key_here
DELTA_API_SECRET=your_fresh_india_testnet_api_secret_here
HOST=127.0.0.1
PORT=8000
DEBUG=true
```
> **Important:** Never paste your keys into AI chat, screenshots, or any public system.

Verify Git is ignoring your `.env` file (must be listed under Ignored files):
```powershell
git status --ignored
```

### Step 3: Run Unit Tests
```powershell
.\venv\Scripts\pytest tests -v
```
*Expected: **68 passed** unit tests covering HMAC-SHA256 signing, environment validation, production URL rejection, testnet host validation, auth failure handling, rate-limit handling, safe credential redaction, connection isolation (no orders placed during tests), duplicate-order prevention, risk rejections, circuit breakers, indicators, and position sizing.*

### Step 4: Start the Backend Server
```powershell
.\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Interactive API Documentation: `http://127.0.0.1:8000/docs`

### Step 5: Start the Frontend Application
Open a new PowerShell terminal (from the project root `Token iq/`):
```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Open your browser and navigate to `http://127.0.0.1:5173/`.

---

## 8. Delta Exchange India Testnet Integration & Credential Setup

### A. Security First: Revoke Exposed Credentials & Create Fresh Keys

> **Critical:** If you previously shared or exposed any API credentials (e.g., in AI chat, screenshots, or source code), you **must revoke them immediately** before proceeding.

1. Log in to [Delta Exchange India Testnet](https://cdn-ind.testnet.deltaex.org).
2. Navigate to **Profile → API Keys**.
3. **Delete/Revoke** any previously exposed key pairs.
4. Click **Create New API Key** with these settings:
   - Environment: **India Testnet** (`cdn-ind.testnet.deltaex.org`)
   - Permissions: **Read** (minimum for connection verification) or **Read & Trade** for live execution
   - IP whitelist: Your machine's IP (recommended for security)
5. Copy the new key and secret — they will only be shown once.
6. Open your local `backend/.env` and paste the new values in `DELTA_API_KEY` and `DELTA_API_SECRET`.
7. **Never paste these values into AI chat, GitHub, or any external system.**

### B. Verifying the Testnet Connection (Read-Only)

Once `backend/.env` is saved with valid credentials, navigate to:
```
GET http://127.0.0.1:8000/api/status/connectivity
```
or check the dashboard connectivity banner. This endpoint verifies:
- ✅ India Testnet environment is active (`india_testnet`)
- ✅ HMAC-SHA256 signed request is accepted by Delta Exchange Testnet
- ✅ USDT account balance is retrievable
- ✅ Available perpetual instruments are listed
- 🚫 **No orders or trades are ever placed during this check**

**Successful response example:**
```json
{
  "connected": true,
  "authenticated": true,
  "environment": "india_testnet",
  "mode": "LIVE_TESTNET",
  "key_status": "1JqH...WmjA",
  "message": "Successfully authenticated with Delta Exchange India Testnet. Found 42 products.",
  "balance": { "asset": "USDT", "available_balance": 5000.0, "total_balance": 5000.0, "is_mock": false },
  "settlement_asset": "USDT"
}
```

**Demo/Simulation Mode** (no credentials configured):
```json
{
  "connected": false,
  "authenticated": false,
  "mode": "DEMO_SAFE_SIMULATION",
  "message": "Demo-Safe Simulation Mode active. No API credentials configured..."
}
```

### C. Enabling Order Execution (After All Checks Pass)

Order execution is **disabled by default** (manual approval mode). To enable:
1. Verify the `GET /api/status/connectivity` returns `"connected": true, "authenticated": true`.
2. Configure your Risk Passport via `POST /api/passport/configure`.
3. Start the bot via `POST /api/bot/start` with `{"mode": "approval"}` (safe, requires explicit per-trade approval).
4. For automatic testnet execution: `{"mode": "automatic_testnet"}` — use with caution.
5. Each trade is re-validated against all risk checks at the exact moment of submission.

---

## 9. Security & Safety Controls

- **Production Lockout**: `app/config.py:Settings` validates that REST and WebSocket URLs match approved testnet patterns at startup. Any production URL (e.g., `cdn.delta.exchange`) triggers an immediate `ValueError` and prevents the application from starting.
- **Zero Secret Leakage**: API secrets are stored exclusively in the backend environment file. They are never sent to the React frontend, never exposed in FastAPI JSON responses, never printed in logs, and never appear in error messages.
- **Credential Redaction**: `DeltaExchangeClient.redacted_api_key` and `Settings.redacted_api_key` expose only `XXXX...XXXX` (first 4 + last 4 characters). The secret is never exposed through any property.
- **No Automatic Fallback to Production**: If a testnet URL fails, the system reports `CONNECTIVITY_FAILED` — it does **not** silently switch to production endpoints.
- **Read-Only Connection Verification**: `check_connection()` uses only `GET` requests. It never calls `place_order()` or `POST` any endpoint.
- **Idempotency via Client Order IDs**: Orders use unique `client_order_id` values (`rp_{direction}_{timestamp}_{uuid4[:4]}`). Every manual trade approval re-evaluates all risk checks at submission time.
- **Hard-Coded Safety Ceilings** (cannot be overridden by any profile):
  - Max risk per trade: **2.0%** of capital
  - Max daily loss: **5.0%** of session equity
  - Max leverage: **10.0x**

---

## 10. HMAC-SHA256 Authentication Implementation

The Delta Exchange API uses the following signing specification:

```
message = METHOD.upper() + TIMESTAMP_UNIX_SECONDS + PATH + QUERY_STRING + REQUEST_BODY
signature = HMAC-SHA256(api_secret, message).hexdigest()
```

Request headers:
```
api-key: <your_api_key>
timestamp: <unix_timestamp_seconds>
signature: <computed_hmac_sha256>
Content-Type: application/json
Accept: application/json
User-Agent: RiskPilot-AI-Testnet/1.0
```

Notes:
- Timestamp is in **Unix seconds** (not milliseconds).
- Query string is included with its leading `?` character.
- A **fresh signature is generated for every request**.
- The secret is encoded as UTF-8 bytes.
- The signature is the lowercase hex digest (64 characters).

---

## 11. License & Disclaimers
This software is built for hackathons and testnet research purposes only. Algorithmic trading carries substantial financial risk. Past simulated performance is no guarantee of future results. Never trade with money you cannot afford to lose.
