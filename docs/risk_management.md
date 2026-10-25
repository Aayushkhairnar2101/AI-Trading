# RiskPilot AI — Risk Management & Position Sizing Framework

## 1. Core Risk Formula
RiskPilot AI **never** invests the entire capital allocation into a single position. Position quantity is derived solely from the monetary risk budget and distance to the protective stop-loss:

$$\text{Monetary Risk Budget} = \text{Allocated Capital} \times \left( \frac{\text{Risk Per Trade } \%}{100} \right)$$

$$\text{Stop Distance} = |\text{Entry Price} - \text{Stop Loss Price}|$$

$$\text{Risk Per Contract} = \text{Stop Distance} \times \text{Exchange Contract Multiplier}$$

$$\text{Calculated Contracts} = \left\lfloor \frac{\text{Monetary Risk Budget}}{\text{Risk Per Contract}} \right\rfloor_{\text{Lot Size}}$$

### Worked Example:
- **Allocated Capital**: $1,000$ USDT
- **Risk Budget**: $0.5\%$ per trade $\implies \$5.00$ USDT max risk
- **Product**: BTCUSDT Perpetual (Multiplier: $0.001$ BTC per contract, Lot Size: $1$ contract)
- **Current Price**: $\$60,000$
- **Stop Loss**: $\$59,500$ ($\text{Distance} = \$500$)
- **Risk per Contract**: $\$500 \times 0.001 = \$0.50$ USDT
- **Raw Quantity**: $\frac{\$5.00}{\$0.50} = 10$ contracts
- **Notional Exposure**: $10 \times 0.001 \times \$60,000 = \$600$ USDT
- **Effective Leverage**: $\frac{\$600}{\$1,000} = 0.6\text{x}$ (Comfortably within the 2.0x ceiling)

---

## 2. Personal Risk Passport Presets

| Setting | Conservative | Balanced | Aggressive (Testnet Only) | Hard Code Limit |
| :--- | :--- | :--- | :--- | :--- |
| **Risk per Trade** | 0.25% | 0.50% | 1.00% | **2.00% Maximum** |
| **Max Daily Loss** | 1.00% | 2.00% | 3.00% | **5.00% Maximum** |
| **Max Open Positions**| 1 | 1 | 2 | **5 Maximum** |
| **Leverage Cap** | 1.0x | 2.0x | 3.0x | **10.0x Ceiling** |
| **Min Reward-to-Risk**| 1.5R | 1.5R | 1.5R | **1.0R Minimum** |
| **Consecutive Losses**| 2 | 3 | 4 | **Circuit Trigger** |

*Note: Code-level limits are hardcoded constants. Even custom user profiles cannot override these ceilings.*

---

## 3. Circuit Breaker System
The `CircuitBreaker` module protects against intraday drawdown cascades:
1. **Daily Loss Ceiling**: Compares verified current equity against session-start equity. If drawdown reaches the configured threshold (e.g. 2%), the circuit breaker trips.
2. **Consecutive Loss Streak**: Halts new entries after $N$ consecutive losing trades.
3. **Behavior Upon Tripping**: Automatically blocks order generation, logs a `CRITICAL` audit event, and requires explicit user review/reset before resuming.
