import React from "react";
import {
  TrendingUp,
  TrendingDown,
  MinusCircle,
  CheckCircle,
  XCircle,
  AlertOctagon,
  ShieldAlert,
  Brain,
  Clock,
  ArrowRight,
  WalletCards,
  Compass,
  AlertCircle,
  Layers,
  Info
} from "lucide-react";

export default function DecisionCard({ card, onApprove, isApproving, ordersEnabled }) {
  if (!card) {
    return (
      <div className="card">
        <div style={{ textAlign: "center", padding: "2.5rem 1rem", color: "var(--text-light)" }}>
          <Clock size={36} style={{ marginBottom: "0.75rem", opacity: 0.45 }} />
          <h4 style={{ margin: "0 0 0.5rem", color: "var(--text-main)" }}>No Evaluation Recorded Yet</h4>
          <p style={{ margin: 0, fontSize: "0.875rem" }}>
            Click <strong>Evaluate Now</strong> in the top navigation or <strong>Start Bot</strong> to trigger live candle evaluation.
          </p>
        </div>
      </div>
    );
  }

  const isLong = card.proposed_direction === "LONG";
  const isShort = card.proposed_direction === "SHORT";
  const isNoTrade = card.proposed_direction === "NO_TRADE";
  const isRejected = card.final_decision === "REJECTED";

  const getStatusBadge = () => {
    switch (card.final_decision) {
      case "ALLOWED":
        return <span className="badge badge-success"><CheckCircle size={14} /> ALLOWED</span>;
      case "EXECUTED":
        return <span className="badge badge-success"><CheckCircle size={14} /> EXECUTED</span>;
      case "WAITING_FOR_APPROVAL":
        return <span className="badge badge-primary"><Clock size={14} /> WAITING APPROVAL</span>;
      case "REJECTED":
        return <span className="badge badge-danger"><XCircle size={14} /> BLOCKED BY RISK</span>;
      default:
        return <span className="badge badge-neutral"><MinusCircle size={14} /> NO TRADE</span>;
    }
  };

  const getDirectionBadge = () => {
    if (isLong) {
      return (
        <span className="badge badge-success" style={{ fontSize: "0.85rem", padding: "0.3rem 0.75rem" }}>
          <TrendingUp size={16} /> LONG ENTRY
        </span>
      );
    }
    if (isShort) {
      return (
        <span className="badge badge-danger" style={{ fontSize: "0.85rem", padding: "0.3rem 0.75rem" }}>
          <TrendingDown size={16} /> SHORT ENTRY
        </span>
      );
    }
    return (
      <span className="badge badge-neutral" style={{ fontSize: "0.85rem", padding: "0.3rem 0.75rem" }}>
        <MinusCircle size={16} /> NO TRADE
      </span>
    );
  };

  // ordersEnabled=false means real testnet USDT balance is zero or account is unfunded
  const canApprove = ordersEnabled !== false;
  const approveBlockedReason = !canApprove
    ? "Order submission disabled — Testnet USDT balance is zero. Fund your account at demo.delta.exchange."
    : null;

  return (
    <div className={`card decision-card ${card.final_decision}`}>
      {/* 1. Header */}
      <div className="card-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
          <span style={{ fontSize: "1.1rem", fontWeight: 700 }}>
            {card.symbol} @ {card.current_price?.toLocaleString()} {card.settlement_asset}
          </span>
          {getDirectionBadge()}
          <span className="badge badge-neutral" title="Detected Market Regime">
            <Layers size={13} /> {card.market_regime}
          </span>
          {card.timestamp && (
            <span style={{ fontSize: "0.75rem", color: "var(--text-light)" }}>
              Evaluated: {new Date(card.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>
        <div>{getStatusBadge()}</div>
      </div>

      {/* 2. Strategy Rationale (Market Observations) */}
      <div className="rationale-box">
        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", fontWeight: 700, marginBottom: "0.4rem", color: "var(--text-main)" }}>
          <Compass size={16} color="var(--primary)" />
          <span>Strategy Rationale & Indicator Observations</span>
        </div>
        {card.strategy_signals && card.strategy_signals.length > 0 ? (
          <ul style={{ paddingLeft: "1.25rem", margin: "0 0 0.5rem 0", fontSize: "0.825rem", lineHeight: 1.55 }}>
            {card.strategy_signals.map((sig, i) => (
              <li key={i}>{sig}</li>
            ))}
          </ul>
        ) : (
          <div style={{ fontSize: "0.825rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
            No directional bias detected in current candle period.
          </div>
        )}

        {/* Indicator Snapshot Pills */}
        {card.indicators && Object.keys(card.indicators).length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", fontSize: "0.75rem", paddingTop: "0.4rem", borderTop: "1px dashed var(--border-light)" }}>
            <span style={{ background: "#e2e8f0", padding: "0.15rem 0.5rem", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>
              EMA 9: <strong>{card.indicators.ema_fast?.toFixed(2)}</strong>
            </span>
            <span style={{ background: "#e2e8f0", padding: "0.15rem 0.5rem", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>
              EMA 21: <strong>{card.indicators.ema_slow?.toFixed(2)}</strong>
            </span>
            <span style={{ background: "#e2e8f0", padding: "0.15rem 0.5rem", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>
              RSI (14): <strong>{card.indicators.rsi?.toFixed(1)}</strong>
            </span>
            <span style={{ background: "#e2e8f0", padding: "0.15rem 0.5rem", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>
              ADX: <strong>{card.indicators.adx?.toFixed(1)}</strong> (+DI: {card.indicators.plus_di?.toFixed(1)}, -DI: {card.indicators.minus_di?.toFixed(1)})
            </span>
            <span style={{ background: "#e2e8f0", padding: "0.15rem 0.5rem", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>
              Spread: <strong>{card.indicators.spread_pct?.toFixed(3)}%</strong>
            </span>
          </div>
        )}
      </div>

      {/* 3. Trade Rejection Reasons OR Conditions Preventing Entry */}
      {card.rejection_reasons && card.rejection_reasons.length > 0 && (
        <div className={isRejected ? "rejections-box" : "unfulfilled-box"}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", fontWeight: 700, marginBottom: "0.35rem" }}>
            {isRejected ? (
              <>
                <ShieldAlert size={16} />
                <span>Trade Blocked by Code-Level Risk Guardrails:</span>
              </>
            ) : (
              <>
                <AlertCircle size={16} />
                <span>Conditions Preventing Trade Entry (Unfulfilled Strategy / Risk Criteria):</span>
              </>
            )}
          </div>
          <ul style={{ paddingLeft: "1.25rem", margin: 0, fontSize: "0.825rem", lineHeight: 1.5 }}>
            {card.rejection_reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 4. Plain English Synthesis */}
      <div className="explanation-box" style={{ margin: "0.75rem 0" }}>
        <strong>Evaluation Summary: </strong>
        {card.plain_english_explanation}
      </div>

      {/* 5. Trade Structure & Position Sizing Grid (Only when trade setup is active or evaluated) */}
      {!isNoTrade ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: "0.75rem", margin: "1rem 0" }}>
          <div className="metric-tile">
            <span className="metric-label">Estimated Entry</span>
            <span className="metric-value">{card.estimated_entry?.toLocaleString()}</span>
            <span className="metric-sub">{card.settlement_asset}</span>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Proposed Stop Loss</span>
            <span className="metric-value" style={{ color: "var(--danger)" }}>
              {card.proposed_stop_loss?.toLocaleString()}
            </span>
            <span className="metric-sub">Distance: {card.stop_distance} pts</span>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Proposed Take Profit</span>
            <span className="metric-value" style={{ color: "var(--success)" }}>
              {card.proposed_take_profit?.toLocaleString()}
            </span>
            <span className="metric-sub">R:R: {card.reward_to_risk_ratio}R</span>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Position Size (Contracts)</span>
            <span className="metric-value">{card.calculated_quantity}</span>
            <span className="metric-sub">Notional: ${card.notional_exposure}</span>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Risk Budget</span>
            <span className="metric-value" style={{ color: "var(--danger)" }}>
              {card.risk_budget_monetary} {card.settlement_asset}
            </span>
            <span className="metric-sub">{card.risk_percentage}% of Capital</span>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Required Margin</span>
            <span className="metric-value">
              {card.estimated_margin} {card.settlement_asset}
            </span>
            <span className="metric-sub">Lev: {card.effective_leverage}x</span>
          </div>
        </div>
      ) : (
        <div
          style={{
            padding: "0.75rem 1rem",
            background: "#f8fafc",
            borderRadius: "6px",
            border: "1px dashed var(--border-light)",
            fontSize: "0.825rem",
            color: "var(--text-muted)",
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
            margin: "0.75rem 0"
          }}
        >
          <Info size={16} color="#64748b" />
          <span>
            <strong>Market Observation Mode:</strong> No active entry orders proposed for this cycle. The system continuously tracks candles; position sizing and SL/TP levels will be computed upon confirmed signal generation.
          </span>
        </div>
      )}

      {/* 6. Machine Learning Advisory Analysis (Visually Distinct Section) */}
      <div className="ml-card-box">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, fontSize: "0.875rem", color: "#6b21a8" }}>
            <Brain size={18} color="#7c3aed" />
            <span>Machine Learning Advisory Classifier (GradientBoosting Walk-Forward)</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              className={`badge ${
                card.ml_status === "READY"
                  ? "badge-success"
                  : card.ml_status === "VALIDATING"
                  ? "badge-primary"
                  : "badge-warning"
              }`}
              style={{ fontSize: "0.725rem" }}
            >
              Status: {card.ml_status}
            </span>
            {card.ml_prediction && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  padding: "0.2rem 0.55rem",
                  borderRadius: "9999px",
                  fontSize: "0.75rem",
                  fontWeight: 700,
                  background: card.ml_prediction === "UP" ? "#dcfce7" : card.ml_prediction === "DOWN" ? "#fee2e2" : "#f1f5f9",
                  color: card.ml_prediction === "UP" ? "#15803d" : card.ml_prediction === "DOWN" ? "#b91c1c" : "#475569",
                  border: `1px solid ${card.ml_prediction === "UP" ? "#86efac" : card.ml_prediction === "DOWN" ? "#fca5a5" : "#cbd5e1"}`
                }}
              >
                Output: {card.ml_prediction} ({Math.round((card.ml_confidence || 0) * 100)}% confidence)
              </span>
            )}
          </div>
        </div>

        {card.ml_status !== "READY" && (
          <div style={{ fontSize: "0.775rem", color: "#92400e", background: "#fef3c7", padding: "0.4rem 0.75rem", borderRadius: "4px", marginBottom: "0.5rem" }}>
            ⚠ Model validation status: <strong>{card.ml_status}</strong>. Insufficient historical samples for walk-forward validation split. Algorithmic trade decisions rely strictly on confirmed technical indicators and risk limits.
          </div>
        )}

        <div style={{ fontSize: "0.725rem", color: "#64748b", lineHeight: 1.45, borderTop: "1px solid #f3e8ff", paddingTop: "0.45rem" }}>
          <strong>Advisory Output Notice:</strong> The displayed confidence is a statistical model classification score over historical candle features (returns, momentum, volatility), <em>not a guaranteed probability of trading profit</em>. ML predictions are advisory and <strong>never bypass strategy confirmation, balance verification, or code-level risk checks</strong>.
        </div>
      </div>

      {/* 7. Risk Engine Pre-Trade Verification Table */}
      {card.risk_checks && card.risk_checks.length > 0 && (
        <div style={{ marginTop: "1rem" }}>
          <div style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: "0.5rem", display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <ShieldAlert size={15} color="var(--primary)" />
            <span>Risk Engine Pre-Trade Verification ({card.risk_checks.filter(c => c.passed).length}/{card.risk_checks.length} Passed)</span>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Safety Check</th>
                <th>Status</th>
                <th>Threshold Limit</th>
                <th>Evaluated Value</th>
                <th>Verification Notes</th>
              </tr>
            </thead>
            <tbody>
              {card.risk_checks.map((chk, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{chk.check_name}</td>
                  <td>
                    {chk.passed ? (
                      <span className="badge badge-success"><CheckCircle size={12} /> PASSED</span>
                    ) : (
                      <span className="badge badge-danger"><XCircle size={12} /> FAILED</span>
                    )}
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.775rem" }}>{chk.threshold}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.775rem" }}>{chk.actual}</td>
                  <td style={{ fontSize: "0.775rem", color: "var(--text-muted)" }}>{chk.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 8. Action Footer for Manual Approval Mode */}
      {card.final_decision === "WAITING_FOR_APPROVAL" && (
        <div style={{ marginTop: "1.25rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border-light)" }}>
          {/* Insufficient balance warning banner */}
          {!canApprove && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.6rem 0.85rem",
                marginBottom: "0.75rem",
                borderRadius: "6px",
                background: "#fef3c7",
                border: "1px solid #fde68a",
                color: "#92400e",
                fontSize: "0.825rem",
                fontWeight: 600
              }}
            >
              <WalletCards size={16} color="#d97706" />
              {approveBlockedReason}
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
            <button
              className="btn btn-success"
              onClick={() => onApprove(card.id)}
              disabled={isApproving || !canApprove}
              title={canApprove ? "Submit order to Delta Exchange India Testnet" : approveBlockedReason}
              style={!canApprove ? { opacity: 0.45, cursor: "not-allowed" } : {}}
            >
              <CheckCircle size={16} />
              {isApproving
                ? "Submitting Order..."
                : !canApprove
                ? "Approve Disabled (0 USDT Testnet Balance)"
                : "Approve & Submit Testnet Order"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
