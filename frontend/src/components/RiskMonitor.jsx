import React, { useState } from "react";
import { ShieldAlert, AlertTriangle, RefreshCw, XCircle, ShieldCheck, Flame } from "lucide-react";

export default function RiskMonitor({ circuitBreaker, passport, onResetCircuitBreaker, onEmergencyClose }) {
  const [confirmEmergency, setConfirmEmergency] = useState(false);
  const [closing, setClosing] = useState(false);

  const drawdownPct = circuitBreaker?.current_daily_drawdown_pct || 0.0;
  const maxDrawdownPct = passport?.max_daily_loss_pct || 2.0;
  const consecutiveLosses = circuitBreaker?.consecutive_losses || 0;
  const maxConsecutive = circuitBreaker?.max_consecutive_losses || 3;
  const isTripped = circuitBreaker?.is_tripped;

  const handleEmergencyClick = async () => {
    if (!confirmEmergency) {
      setConfirmEmergency(true);
      return;
    }
    setClosing(true);
    try {
      await onEmergencyClose(passport?.symbol || "BTCUSDT");
      setConfirmEmergency(false);
    } catch (err) {
      alert("Emergency close error: " + err.message);
    } finally {
      setClosing(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <ShieldAlert size={18} color="var(--primary)" />
          <span>Real-Time Risk Monitor & Circuit Breaker</span>
        </div>
        <div>
          {isTripped ? (
            <span className="badge badge-danger">
              <AlertTriangle size={14} /> CIRCUIT BREAKER ENGAGED
            </span>
          ) : (
            <span className="badge badge-success">
              <ShieldCheck size={14} /> NORMAL PROTECTIVE STATE
            </span>
          )}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
        {/* Daily Drawdown Meter */}
        <div className="metric-tile">
          <span className="metric-label">Session Daily Drawdown</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
            <span className="metric-value" style={{ color: drawdownPct > 0 ? "var(--danger)" : "var(--text-main)" }}>
              {drawdownPct.toFixed(2)}%
            </span>
            <span style={{ fontSize: "0.85rem", color: "var(--text-light)" }}>/ {maxDrawdownPct}% cap</span>
          </div>
          {/* Progress bar */}
          <div style={{ height: "6px", backgroundColor: "#e2e8f0", borderRadius: "3px", overflow: "hidden", marginTop: "0.5rem" }}>
            <div
              style={{
                height: "100%",
                width: `${Math.min(100, (drawdownPct / maxDrawdownPct) * 100)}%`,
                backgroundColor: drawdownPct > maxDrawdownPct * 0.75 ? "var(--danger)" : "var(--primary)"
              }}
            />
          </div>
        </div>

        {/* Consecutive Loss Streak */}
        <div className="metric-tile">
          <span className="metric-label">Consecutive Loss Streak</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.25rem" }}>
            <span className="metric-value" style={{ color: consecutiveLosses >= maxConsecutive - 1 ? "var(--danger)" : "var(--text-main)" }}>
              {consecutiveLosses}
            </span>
            <span style={{ fontSize: "0.85rem", color: "var(--text-light)" }}>/ {maxConsecutive} threshold</span>
          </div>
          <span className="metric-sub">Halts bot upon {maxConsecutive} consecutive losses</span>
        </div>

        {/* Risk Budget per Trade */}
        <div className="metric-tile">
          <span className="metric-label">Configured Risk Budget</span>
          <span className="metric-value">
            {passport?.risk_per_trade_pct}%
          </span>
          <span className="metric-sub">
            Max ${((passport?.allocated_capital || 1000) * (passport?.risk_per_trade_pct || 0.5) / 100).toFixed(2)} {passport?.settlement_asset} per setup
          </span>
        </div>

        {/* Max Leverage Cap */}
        <div className="metric-tile">
          <span className="metric-label">Max Leverage Limit</span>
          <span className="metric-value">{passport?.max_leverage}x</span>
          <span className="metric-sub">Hard code limit: 10x ceiling</span>
        </div>
      </div>

      {/* Tripped Alert Box */}
      {isTripped && (
        <div className="rejections-box" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <strong>Circuit Breaker Triggered:</strong> {circuitBreaker?.trip_reason}
            <div style={{ fontSize: "0.775rem", marginTop: "0.25rem" }}>
              New trading opportunities are automatically frozen until safety conditions are reconciled.
            </div>
          </div>
          <button className="btn btn-outline btn-sm" onClick={onResetCircuitBreaker}>
            <RefreshCw size={14} /> Reset Breaker
          </button>
        </div>
      )}

      {/* Emergency Flatten Controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "0.75rem", borderTop: "1px solid var(--border-light)" }}>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          <strong>Emergency Guardrail:</strong> Immediately closes all open bot-managed positions on testnet.
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {confirmEmergency ? (
            <>
              <button className="btn btn-danger btn-sm" onClick={handleEmergencyClick} disabled={closing}>
                <Flame size={14} /> {closing ? "Closing..." : "CONFIRM EMERGENCY FLATTEN"}
              </button>
              <button className="btn btn-outline btn-sm" onClick={() => setConfirmEmergency(false)}>
                Cancel
              </button>
            </>
          ) : (
            <button className="btn btn-outline btn-sm" style={{ borderColor: "var(--danger)", color: "var(--danger)" }} onClick={handleEmergencyClick}>
              <XCircle size={14} /> Emergency Flatten Bot Positions
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
