import React, { useState } from "react";
import { FileText, Filter, AlertTriangle, CheckCircle, Info, ShieldAlert } from "lucide-react";

export default function AuditLogView({ logs }) {
  const [filterCategory, setFilterCategory] = useState("ALL");

  const filteredLogs = logs?.filter((log) => {
    if (filterCategory === "ALL") return true;
    return log.category === filterCategory;
  }) || [];

  const getSeverityBadge = (sev) => {
    switch (sev) {
      case "CRITICAL":
      case "ERROR":
        return <span className="badge badge-danger">{sev}</span>;
      case "WARNING":
        return <span className="badge badge-warning">{sev}</span>;
      default:
        return <span className="badge badge-neutral">{sev}</span>;
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <FileText size={18} color="var(--primary)" />
          <span>Immutable Audit & Activity Trail ({filteredLogs.length})</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Filter size={14} color="var(--text-light)" />
          <select
            className="form-select"
            style={{ width: "auto", padding: "0.25rem 0.5rem", fontSize: "0.8rem" }}
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
          >
            <option value="ALL">All Categories</option>
            <option value="BOT_CONTROL">Bot Controls</option>
            <option value="RISK_CHECK">Risk Checks</option>
            <option value="ORDER_SUBMISSION">Order Submissions</option>
            <option value="CIRCUIT_BREAKER">Circuit Breaker</option>
          </select>
        </div>
      </div>

      {filteredLogs.length > 0 ? (
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp (UTC)</th>
              <th>Category</th>
              <th>Event Type</th>
              <th>Severity</th>
              <th>Summary</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((log) => (
              <tr key={log.id}>
                <td style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                  {new Date(log.timestamp).toLocaleTimeString()}
                </td>
                <td style={{ fontWeight: 600, fontSize: "0.75rem" }}>{log.category}</td>
                <td>
                  <span className="badge badge-neutral" style={{ fontSize: "0.7rem" }}>
                    {log.event_type}
                  </span>
                </td>
                <td>{getSeverityBadge(log.severity)}</td>
                <td style={{ fontSize: "0.8rem" }}>{log.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-light)", fontSize: "0.85rem" }}>
          No audit logs recorded for this category yet.
        </div>
      )}
    </div>
  );
}
