# RiskPilot AI — 5-Minute Live Hackathon Demo Script

## Objective
Demonstrate that RiskPilot AI is not a generic mockup, but a functional, explainable algorithmic trading system connecting to Delta Exchange Testnet where **the user defines the risk, AI evaluates opportunities, and the risk engine enforces safety.**

---

### Minute 1: The Problem & The Value Proposition (0:00 - 1:00)
- **Presenter**: "Most retail traders blow up because emotion overrides discipline. Most AI bots fail because they operate as black boxes that force unsafe trades."
- **Screen**: Point to the **Delta Exchange India Testnet** environment badge (`cdn-ind.testnet.deltaex.org`) and the active **Circuit Breaker** status badge.
- **Key Message**: "In RiskPilot AI, our central innovation is: *The user defines the risk. AI evaluates the opportunity. The risk engine decides whether the trade is allowed.*"

---

### Minute 2: The Personal Risk Passport (1:00 - 2:00)
- **Action**: Click the **Risk Passport** button in the header.
- **Demonstration**:
  1. Show verified testnet balance ($1,000 USDT) and allocate capital ($1,000 USDT).
  2. Toggle between **Conservative** (0.25% risk, 1x leverage), **Balanced** (0.5% risk, 2x leverage), and **Aggressive** (1% risk, 3x leverage) presets.
  3. Attempt to drag risk percentage above 2%: Show the hard code-level safety ceiling preventing unsafe configurations.
  4. Point out the live **Risk Summary**: "With 1,000 USDT capital, each trade risks exactly $5.00 USDT, with a daily drawdown ceiling of $20.00 USDT."
  5. Click **Save & Confirm Passport**.

---

### Minute 3: Pre-Trade Decision Card & Explainability (2:00 - 3:00)
- **Action**: Click **Evaluate Now**.
- **Demonstration**:
  1. Show the generated **Pre-Trade Decision Card**.
  2. Highlight the **Plain English Strategy Rationale**: "LONG opportunity detected because EMA 9 crossed above EMA 21, ADX confirms trend strength, and RSI confirms positive momentum."
  3. Show the **Position Sizing Calculation**: Not an arbitrary guess, but derived mathematically from stop-loss distance ($10$ contracts, $0.6$x effective leverage).
  4. Show the **Risk Engine Verification Table**: Walk through the 11 passed checks (Circuit Breaker, Margin, Leverage Ceiling, Stale Data check).
  5. Show the **What-If Risk Simulator** tab: Drag the adverse excursion slider to show simulated intra-trade drawdown, fees, and slippage.

---

### Minute 4: Execution & Testnet Order Reconciliation (3:00 - 4:00)
- **Action**: Click **Approve & Submit Testnet Order** (or toggle to Automatic Testnet mode).
- **Demonstration**:
  1. Order is submitted to Delta Exchange Testnet using a unique client order ID (`rp_l_...`).
  2. Switch to **Live Trading Terminal**: Point to the Candlestick Chart with overlaid EMA 9, EMA 21 lines, Stop-Loss line (red), and Take-Profit line (green).
  3. Switch to **Performance & Journal**: Show the active trade in the Open Positions table with entry price, mark price, and unrealized PnL.
  4. Demonstrate the **CSV Export** button for local trade records.

---

### Minute 5: Safety Guardrails, Circuit Breaker & Session Report (4:00 - 5:00)
- **Action**:
  1. Switch to **Risk Monitor**: Show the Session Daily Drawdown meter and consecutive loss streak counter.
  2. Demonstrate the **Emergency Flatten Bot Positions** control: Explain that it closes bot-managed positions while leaving unrelated account trades untouched.
  3. Click **Stop Bot**: Show the automatically generated **Trading Session Performance Receipt** summarizing approved trades, blocked setups, win rate, and net PnL.
- **Presenter Closing**: "RiskPilot AI delivers institutional-grade risk management and full explainability to algorithmic trading on Delta Exchange."
