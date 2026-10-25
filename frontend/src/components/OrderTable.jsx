import React from "react";
import { Download, CheckCircle, Clock, TrendingUp, TrendingDown } from "lucide-react";
import { api } from "../services/api";

export default function OrderTable({ positions, trades, performance }) {
  return (
    <div>
      {/* Performance Summary Banner */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem", marginBottom: "1.25rem" }}>
        <div className="metric-tile">
          <span className="metric-label">Total Trades</span>
          <span className="metric-value">{performance?.total_trades || 0}</span>
          <span className="metric-sub">{performance?.winning_trades || 0}W - {performance?.losing_trades || 0}L</span>
        </div>
        <div className="metric-tile">
          <span className="metric-label">Win Rate</span>
          <span className="metric-value" style={{ color: (performance?.win_rate_pct || 0) >= 50 ? "var(--success)" : "var(--text-main)" }}>
            {performance?.win_rate_pct || 0}%
          </span>
          <span className="metric-sub">Verified testnet outcomes</span>
        </div>
        <div className="metric-tile">
          <span className="metric-label">Profit Factor</span>
          <span className="metric-value">{performance?.profit_factor || 0}</span>
          <span className="metric-sub">Gross Win / Gross Loss</span>
        </div>
        <div className="metric-tile">
          <span className="metric-label">Net Realized PnL</span>
          <span
            className="metric-value"
            style={{ color: (performance?.net_pnl || 0) >= 0 ? "var(--success)" : "var(--danger)" }}
          >
            {(performance?.net_pnl || 0) >= 0 ? "+" : ""}{performance?.net_pnl || 0} USDT
          </span>
          <span className="metric-sub">Fees Paid: ${performance?.total_fees_paid || 0}</span>
        </div>
      </div>

      {/* Open Positions Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <span>Verified Open Positions ({positions?.length || 0})</span>
          </div>
        </div>

        {positions && positions.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side / Size</th>
                <th>Entry Price</th>
                <th>Mark Price</th>
                <th>Unrealized PnL</th>
                <th>Margin</th>
                <th>Leverage</th>
                <th>Stop Loss</th>
                <th>Take Profit</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 700 }}>{p.symbol}</td>
                  <td>
                    <span className={`badge ${p.size > 0 ? "badge-success" : "badge-danger"}`}>
                      {p.size > 0 ? "LONG" : "SHORT"} {Math.abs(p.size)}
                    </span>
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)" }}>${p.entry_price?.toLocaleString()}</td>
                  <td style={{ fontFamily: "var(--font-mono)" }}>${p.mark_price?.toLocaleString()}</td>
                  <td style={{ fontFamily: "var(--font-mono)", color: p.unrealized_pnl >= 0 ? "var(--success)" : "var(--danger)", fontWeight: 700 }}>
                    {p.unrealized_pnl >= 0 ? "+" : ""}{p.unrealized_pnl?.toFixed(2)} USDT
                  </td>
                  <td>${p.margin?.toFixed(2)}</td>
                  <td>{p.leverage}x</td>
                  <td style={{ color: "var(--danger)" }}>${p.stop_loss || "-"}</td>
                  <td style={{ color: "var(--success)" }}>${p.take_profit || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-light)", fontSize: "0.85rem" }}>
            No open bot-managed positions on testnet.
          </div>
        )}
      </div>

      {/* Trade Journal Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <span>Completed Trade Journal ({trades?.length || 0})</span>
          </div>
          <a
            href={api.exportTradesCsvUrl}
            download="riskpilot_trades.csv"
            className="btn btn-outline btn-sm"
          >
            <Download size={14} /> Export CSV
          </a>
        </div>

        {trades && trades.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Date / Time</th>
                <th>Symbol</th>
                <th>Direction</th>
                <th>Size</th>
                <th>Entry Price</th>
                <th>Exit Price</th>
                <th>Realized PnL</th>
                <th>Exit Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t, i) => (
                <tr key={i}>
                  <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {new Date(t.opened_at).toLocaleString()}
                  </td>
                  <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                  <td>
                    <span className={`badge ${t.direction === "LONG" ? "badge-success" : "badge-danger"}`}>
                      {t.direction}
                    </span>
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)" }}>{t.quantity}</td>
                  <td style={{ fontFamily: "var(--font-mono)" }}>${t.entry_price?.toLocaleString()}</td>
                  <td style={{ fontFamily: "var(--font-mono)" }}>${t.exit_price ? t.exit_price.toLocaleString() : "-"}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: (t.realized_pnl || 0) >= 0 ? "var(--success)" : "var(--danger)" }}>
                    {t.realized_pnl !== null ? `${(t.realized_pnl || 0) >= 0 ? "+" : ""}${t.realized_pnl} USDT` : "-"}
                  </td>
                  <td>
                    <span className="badge badge-neutral" style={{ fontSize: "0.7rem" }}>
                      {t.exit_reason || "ACTIVE"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${t.status === "CLOSED" ? "badge-neutral" : "badge-primary"}`}>
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-light)", fontSize: "0.85rem" }}>
            No trades executed in this session yet.
          </div>
        )}
      </div>
    </div>
  );
}
