import React, { useState, useEffect } from "react";
import { Calculator, AlertTriangle, ShieldCheck, DollarSign } from "lucide-react";
import { api } from "../services/api";

export default function WhatIfSimulator({ initialDecision }) {
  const [params, setParams] = useState({
    entry_price: initialDecision?.estimated_entry || 65000.0,
    stop_loss: initialDecision?.proposed_stop_loss || 64500.0,
    take_profit: initialDecision?.proposed_take_profit || 66000.0,
    quantity: initialDecision?.calculated_quantity || 10.0,
    direction: initialDecision?.proposed_direction || "LONG",
    fee_rate_bps: 5.0,
    slippage_bps: 2.0,
    adverse_move_pct: 1.0
  });

  const [simResult, setSimResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialDecision) {
      setParams((prev) => ({
        ...prev,
        entry_price: initialDecision.estimated_entry || prev.entry_price,
        stop_loss: initialDecision.proposed_stop_loss || prev.stop_loss,
        take_profit: initialDecision.proposed_take_profit || prev.take_profit,
        quantity: initialDecision.calculated_quantity || prev.quantity,
        direction: initialDecision.proposed_direction !== "NO_TRADE" ? initialDecision.proposed_direction : "LONG"
      }));
    }
  }, [initialDecision]);

  useEffect(() => {
    let isMounted = true;
    const runSim = async () => {
      setLoading(true);
      try {
        const res = await api.simulateWhatIf(params);
        if (isMounted) setSimResult(res);
      } catch (err) {
        console.error("Simulation failed:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    runSim();
    return () => {
      isMounted = false;
    };
  }, [params]);

  const handleChange = (field, val) => {
    setParams((prev) => ({ ...prev, [field]: parseFloat(val) || 0 }));
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <Calculator size={18} color="var(--primary)" />
          <span>What-If Pre-Trade Risk Simulator</span>
        </div>
        <span className="badge badge-neutral">Pre-Execution Scenario Modeling</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
        <div className="form-group">
          <label className="form-label">Entry Price</label>
          <input
            type="number"
            className="form-input"
            value={params.entry_price}
            onChange={(e) => handleChange("entry_price", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Stop Loss</label>
          <input
            type="number"
            className="form-input"
            value={params.stop_loss}
            onChange={(e) => handleChange("stop_loss", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Take Profit</label>
          <input
            type="number"
            className="form-input"
            value={params.take_profit}
            onChange={(e) => handleChange("take_profit", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Quantity (Contracts)</label>
          <input
            type="number"
            className="form-input"
            value={params.quantity}
            onChange={(e) => handleChange("quantity", e.target.value)}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Adverse Move Excursion: {params.adverse_move_pct}%</label>
          <input
            type="range"
            min="0.25"
            max="3.0"
            step="0.25"
            value={params.adverse_move_pct}
            onChange={(e) => handleChange("adverse_move_pct", e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
      </div>

      {simResult && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem", marginBottom: "1rem" }}>
          <div className="metric-tile" style={{ borderLeft: "4px solid var(--danger)" }}>
            <span className="metric-label">Max Loss at Stop Loss</span>
            <span className="metric-value" style={{ color: "var(--danger)" }}>
              -${simResult.effective_loss_with_costs}
            </span>
            <span className="metric-sub">Includes fees & slippage</span>
          </div>

          <div className="metric-tile" style={{ borderLeft: "4px solid var(--success)" }}>
            <span className="metric-label">Net Gain at Take Profit</span>
            <span className="metric-value" style={{ color: "var(--success)" }}>
              +${simResult.effective_gain_with_costs}
            </span>
            <span className="metric-sub">R:R: {simResult.reward_to_risk_ratio}R</span>
          </div>

          <div className="metric-tile" style={{ borderLeft: "4px solid var(--warning)" }}>
            <span className="metric-label">Adverse Excursion ({params.adverse_move_pct}%)</span>
            <span className="metric-value" style={{ color: "var(--warning)" }}>
              -${simResult.adverse_move_loss}
            </span>
            <span className="metric-sub">Intra-trade drawdown</span>
          </div>

          <div className="metric-tile">
            <span className="metric-label">Est. Fees & Slippage</span>
            <span className="metric-value" style={{ fontSize: "1.1rem" }}>
              ${simResult.estimated_roundtrip_fees + simResult.estimated_slippage_cost}
            </span>
            <span className="metric-sub">Fees: ${simResult.estimated_roundtrip_fees} | Slip: ${simResult.estimated_slippage_cost}</span>
          </div>
        </div>
      )}

      <div style={{ fontSize: "0.75rem", color: "var(--text-light)", fontStyle: "italic", textAlign: "right" }}>
        * Disclaimer: Calculations are mathematical models for pre-trade risk evaluation and do not guarantee exchange execution prices.
      </div>
    </div>
  );
}
