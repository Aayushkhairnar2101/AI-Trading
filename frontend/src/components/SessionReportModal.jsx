import React from "react";
import { Award, CheckCircle, X, DollarSign, Activity } from "lucide-react";

export default function SessionReportModal({ report, isOpen, onClose }) {
  if (!isOpen || !report) return null;

  const perf = report.performance || {};
  const isProfit = (report.net_pnl || 0) >= 0;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: "600px" }}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Award size={22} color="var(--primary)" />
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Trading Session Performance Receipt</h2>
          </div>
          <button onClick={onClose} style={{ color: "var(--text-light)" }}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="explanation-box" style={{ background: isProfit ? "var(--success-light)" : "var(--danger-light)", borderColor: isProfit ? "var(--success)" : "var(--danger)" }}>
            <div style={{ fontSize: "1.1rem", fontWeight: 700, color: isProfit ? "var(--success)" : "var(--danger)" }}>
              {isProfit ? "+" : ""}{report.net_pnl} USDT ({report.net_pnl_pct}%)
            </div>
            <div style={{ fontSize: "0.825rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
              {report.summary_text}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", margin: "1rem 0" }}>
            <div className="metric-tile">
              <span className="metric-label">Initial Capital</span>
              <span className="metric-value">${report.initial_allocated_capital}</span>
            </div>
            <div className="metric-tile">
              <span className="metric-label">Closing Equity</span>
              <span className="metric-value">${report.current_capital}</span>
            </div>
            <div className="metric-tile">
              <span className="metric-label">Total Trades</span>
              <span className="metric-value">{perf.total_trades || 0}</span>
              <span className="metric-sub">{perf.winning_trades || 0} Wins &bull; {perf.losing_trades || 0} Losses</span>
            </div>
            <div className="metric-tile">
              <span className="metric-label">Win Rate</span>
              <span className="metric-value" style={{ color: isProfit ? "var(--success)" : "var(--text-main)" }}>
                {perf.win_rate_pct || 0}%
              </span>
              <span className="metric-sub">Profit Factor: {perf.profit_factor || 0}</span>
            </div>
          </div>

          <div style={{ marginTop: "1rem" }}>
            <h4 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              Decision Breakdown
            </h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem", textAlign: "center" }}>
              <div style={{ background: "var(--bg-main)", padding: "0.5rem", borderRadius: "6px" }}>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--success)" }}>
                  {report.decisions_approved || 0}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-light)" }}>Approved Trades</div>
              </div>
              <div style={{ background: "var(--bg-main)", padding: "0.5rem", borderRadius: "6px" }}>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--danger)" }}>
                  {report.decisions_rejected || 0}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-light)" }}>Risk Blocked</div>
              </div>
              <div style={{ background: "var(--bg-main)", padding: "0.5rem", borderRadius: "6px" }}>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text-muted)" }}>
                  {report.decisions_no_trade || 0}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-light)" }}>No-Trade Setups</div>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>
            Close Receipt
          </button>
        </div>
      </div>
    </div>
  );
}
