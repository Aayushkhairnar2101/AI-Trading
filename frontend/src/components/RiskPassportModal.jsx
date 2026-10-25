import React, { useState, useEffect } from "react";
import { X, Shield, Sliders, AlertCircle, CheckCircle, Info, RefreshCw, AlertTriangle } from "lucide-react";

export default function RiskPassportModal({
  isOpen,
  onClose,
  currentPassport,
  presets,
  availableBalance = 0.0,
  onSave
}) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState({
    profile_tier: currentPassport?.profile_tier || "BALANCED",
    allocated_capital: currentPassport?.allocated_capital || 1000.0,
    settlement_asset: currentPassport?.settlement_asset || "USDT",
    symbol: currentPassport?.symbol || "BTCUSDT",
    timeframe: currentPassport?.timeframe || "5m",
    risk_per_trade_pct: currentPassport?.risk_per_trade_pct || 0.5,
    max_daily_loss_pct: currentPassport?.max_daily_loss_pct || 2.0,
    max_open_positions: currentPassport?.max_open_positions || 1,
    max_leverage: currentPassport?.max_leverage || 2.0,
    min_reward_to_risk: currentPassport?.min_reward_to_risk || 1.5,
    execution_mode: currentPassport?.execution_mode || "APPROVAL",
    max_consecutive_losses: currentPassport?.max_consecutive_losses || 3
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // Synchronize form values whenever modal is opened or currentPassport updates
  useEffect(() => {
    if (isOpen && currentPassport) {
      setFormData({
        profile_tier: currentPassport.profile_tier || "BALANCED",
        allocated_capital: currentPassport.allocated_capital || 1000.0,
        settlement_asset: currentPassport.settlement_asset || "USDT",
        symbol: currentPassport.symbol || "BTCUSDT",
        timeframe: currentPassport.timeframe || "5m",
        risk_per_trade_pct: currentPassport.risk_per_trade_pct ?? 0.5,
        max_daily_loss_pct: currentPassport.max_daily_loss_pct ?? 2.0,
        max_open_positions: currentPassport.max_open_positions ?? 1,
        max_leverage: currentPassport.max_leverage ?? 2.0,
        min_reward_to_risk: currentPassport.min_reward_to_risk ?? 1.5,
        execution_mode: currentPassport.execution_mode || "APPROVAL",
        max_consecutive_losses: currentPassport.max_consecutive_losses ?? 3
      });
      setError("");
      setFieldErrors({});
      setSuccessMessage("");
      setIsSaving(false);
    }
  }, [isOpen, currentPassport]);

  const applyPreset = (tier) => {
    const preset = presets?.[tier];
    if (preset) {
      setFormData((prev) => ({
        ...prev,
        profile_tier: tier,
        risk_per_trade_pct: preset.risk_per_trade_pct,
        max_daily_loss_pct: preset.max_daily_loss_pct,
        max_open_positions: preset.max_open_positions,
        max_leverage: preset.max_leverage,
        min_reward_to_risk: preset.min_reward_to_risk,
        max_consecutive_losses: preset.max_consecutive_losses
      }));
      setError("");
      setFieldErrors({});
    }
  };

  const handleChange = (field, val) => {
    setFormData((prev) => ({
      ...prev,
      [field]: val,
      // If user adjusts custom numbers, switch tier label to CUSTOM
      profile_tier:
        field.includes("risk") || field.includes("loss") || field.includes("leverage")
          ? "CUSTOM"
          : prev.profile_tier
    }));
    setError("");
    if (fieldErrors[field]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const validate = () => {
    const errs = {};
    const capital = parseFloat(formData.allocated_capital);
    if (isNaN(capital) || capital <= 0) {
      errs.allocated_capital = "Allocated strategy capital must be strictly greater than 0.";
    }

    const riskPct = parseFloat(formData.risk_per_trade_pct);
    if (isNaN(riskPct) || riskPct <= 0 || riskPct > 2.0) {
      errs.risk_per_trade_pct = "Risk per trade must be between 0.05% and 2.0% (hard system ceiling).";
    }

    const lossPct = parseFloat(formData.max_daily_loss_pct);
    if (isNaN(lossPct) || lossPct <= 0 || lossPct > 5.0) {
      errs.max_daily_loss_pct = "Daily loss limit must be between 0.25% and 5.0% (hard system ceiling).";
    }

    const lev = parseFloat(formData.max_leverage);
    if (isNaN(lev) || lev < 1.0 || lev > 10.0) {
      errs.max_leverage = "Max leverage must be between 1.0x and 10.0x (hard ceiling).";
    }

    const rrr = parseFloat(formData.min_reward_to_risk);
    if (isNaN(rrr) || rrr < 1.0) {
      errs.min_reward_to_risk = "Minimum reward-to-risk ratio must be at least 1.0R.";
    }

    return errs;
  };

  const handleSave = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (isSaving) return; // Prevent duplicate clicks

    setError("");
    setSuccessMessage("");

    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setError(Object.values(validationErrors)[0]);
      return;
    }

    setFieldErrors({});
    setIsSaving(true);

    try {
      await onSave(formData);
      setSuccessMessage("Personal Risk Passport confirmed and saved successfully!");
      setTimeout(() => {
        setIsSaving(false);
        onClose();
      }, 600);
    } catch (err) {
      setIsSaving(false);
      setError(err.message || "Failed to save passport. Please check connection and try again.");
    }
  };

  const safeCapital = parseFloat(formData.allocated_capital) || 0;
  const safeRiskPct = parseFloat(formData.risk_per_trade_pct) || 0;
  const safeLossPct = parseFloat(formData.max_daily_loss_pct) || 0;
  const monetaryRiskBudget = (safeCapital * (safeRiskPct / 100.0)).toFixed(2);
  const monetaryDailyLoss = (safeCapital * (safeLossPct / 100.0)).toFixed(2);

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: "620px" }}>
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Sliders size={20} color="var(--primary)" />
            <h2 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Personal Risk Passport</h2>
          </div>
          <button onClick={onClose} disabled={isSaving} style={{ color: "var(--text-light)" }}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {/* Top Error Alert */}
          {error && (
            <div className="rejections-box" style={{ marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: "0.85rem" }}>{error}</span>
            </div>
          )}

          {/* Top Success Alert */}
          {successMessage && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "var(--success)",
                borderRadius: "6px",
                padding: "0.6rem 0.85rem",
                marginBottom: "1rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                fontSize: "0.85rem",
                fontWeight: 600
              }}
            >
              <CheckCircle size={16} style={{ flexShrink: 0 }} />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Capital Allocation & Distinction Box */}
          <div style={{ marginBottom: "1.25rem" }}>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              A. Trading Capital & Instrument
            </h3>

            {/* Clear distinction between Configured Strategy Capital vs Verified Wallet Balance */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "var(--bg-main)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "0.6rem 0.85rem",
                marginBottom: "0.75rem",
                fontSize: "0.8rem"
              }}
            >
              <div>
                <span style={{ color: "var(--text-light)" }}>Strategy Capital Model: </span>
                <strong style={{ color: "var(--text)" }}>
                  {safeCapital.toFixed(2)} {formData.settlement_asset}
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-light)" }}>Verified Testnet Balance: </span>
                <strong style={{ color: availableBalance > 0 ? "var(--success)" : "var(--danger)" }}>
                  {availableBalance.toFixed(2)} {formData.settlement_asset}
                </strong>
              </div>
            </div>

            {availableBalance <= 0 && (
              <div
                style={{
                  background: "rgba(245, 158, 11, 0.08)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  borderRadius: "6px",
                  padding: "0.5rem 0.75rem",
                  marginBottom: "0.75rem",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.5rem",
                  fontSize: "0.775rem",
                  color: "#b45309"
                }}
              >
                <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: "2px" }} />
                <span>
                  <strong>Testnet Balance is 0.00 {formData.settlement_asset}:</strong> Configured strategy capital sets your risk budget & sizing blueprint. Order execution remains blocked in backend until testnet funds are credited at demo.delta.exchange.
                </span>
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div className="form-group">
                <label className="form-label">
                  Allocated Capital ({formData.settlement_asset})
                  <span style={{ float: "right", color: "var(--text-light)", fontWeight: 400 }}>
                    Verified Avail: {availableBalance.toFixed(2)}
                  </span>
                </label>
                <input
                  type="number"
                  className={`form-input ${fieldErrors.allocated_capital ? "border-danger" : ""}`}
                  value={formData.allocated_capital}
                  onChange={(e) => handleChange("allocated_capital", parseFloat(e.target.value) || 0)}
                  min={10}
                  step={50}
                  disabled={isSaving}
                />
                {fieldErrors.allocated_capital && (
                  <span style={{ color: "var(--danger)", fontSize: "0.75rem", marginTop: "2px", display: "block" }}>
                    {fieldErrors.allocated_capital}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">Trading Instrument</label>
                <select
                  className="form-select"
                  value={formData.symbol}
                  onChange={(e) => handleChange("symbol", e.target.value)}
                  disabled={isSaving}
                >
                  <option value="BTCUSDT">BTCUSDT (BTCUSD Perpetual)</option>
                  <option value="ETHUSDT">ETHUSDT (ETHUSD Perpetual)</option>
                  <option value="SOLUSDT">SOLUSDT (SOLUSD Perpetual)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section B: Risk Preference Presets */}
          <div style={{ marginBottom: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <h3 style={{ fontSize: "0.9rem", fontWeight: 700 }}>B. Risk Preference Presets</h3>
              <span className="badge badge-neutral">Selected: {formData.profile_tier}</span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem", marginBottom: "1rem" }}>
              <button
                type="button"
                className={`btn ${formData.profile_tier === "CONSERVATIVE" ? "btn-primary" : "btn-outline"}`}
                onClick={() => applyPreset("CONSERVATIVE")}
                disabled={isSaving}
                style={{ flexDirection: "column", padding: "0.6rem", textAlign: "center" }}
              >
                <div style={{ fontWeight: 700 }}>CONSERVATIVE</div>
                <div style={{ fontSize: "0.7rem", opacity: 0.85 }}>0.25% Risk &bull; 1x Lev</div>
              </button>

              <button
                type="button"
                className={`btn ${formData.profile_tier === "BALANCED" ? "btn-primary" : "btn-outline"}`}
                onClick={() => applyPreset("BALANCED")}
                disabled={isSaving}
                style={{ flexDirection: "column", padding: "0.6rem", textAlign: "center" }}
              >
                <div style={{ fontWeight: 700 }}>BALANCED</div>
                <div style={{ fontSize: "0.7rem", opacity: 0.85 }}>0.50% Risk &bull; 2x Lev</div>
              </button>

              <button
                type="button"
                className={`btn ${formData.profile_tier === "AGGRESSIVE" ? "btn-primary" : "btn-outline"}`}
                onClick={() => applyPreset("AGGRESSIVE")}
                disabled={isSaving}
                style={{ flexDirection: "column", padding: "0.6rem", textAlign: "center" }}
              >
                <div style={{ fontWeight: 700 }}>AGGRESSIVE</div>
                <div style={{ fontSize: "0.7rem", opacity: 0.85 }}>1.0% Risk &bull; 3x Lev</div>
              </button>
            </div>

            {/* Custom Sliders within code-level hard limits */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div className="form-group">
                <label className="form-label">
                  Risk Per Trade: <strong>{formData.risk_per_trade_pct}%</strong>
                  <span style={{ float: "right", color: "var(--danger)", fontSize: "0.7rem" }}>Hard Max: 2.0%</span>
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="2.0"
                  step="0.05"
                  value={formData.risk_per_trade_pct}
                  onChange={(e) => handleChange("risk_per_trade_pct", parseFloat(e.target.value))}
                  disabled={isSaving}
                  style={{ width: "100%" }}
                />
                {fieldErrors.risk_per_trade_pct && (
                  <span style={{ color: "var(--danger)", fontSize: "0.75rem", display: "block" }}>
                    {fieldErrors.risk_per_trade_pct}
                  </span>
                )}
              </div>

              <div className="form-group">
                <label className="form-label">
                  Daily Loss Limit: <strong>{formData.max_daily_loss_pct}%</strong>
                  <span style={{ float: "right", color: "var(--danger)", fontSize: "0.7rem" }}>Hard Max: 5.0%</span>
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="5.0"
                  step="0.25"
                  value={formData.max_daily_loss_pct}
                  onChange={(e) => handleChange("max_daily_loss_pct", parseFloat(e.target.value))}
                  disabled={isSaving}
                  style={{ width: "100%" }}
                />
                {fieldErrors.max_daily_loss_pct && (
                  <span style={{ color: "var(--danger)", fontSize: "0.75rem", display: "block" }}>
                    {fieldErrors.max_daily_loss_pct}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Section C: Controls & Execution Mode */}
          <div style={{ marginBottom: "1.25rem" }}>
            <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.5rem" }}>
              C. Execution Controls & Safeguards
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
              <div className="form-group">
                <label className="form-label">Max Leverage</label>
                <select
                  className="form-select"
                  value={formData.max_leverage}
                  onChange={(e) => handleChange("max_leverage", parseFloat(e.target.value))}
                  disabled={isSaving}
                >
                  <option value={1.0}>1x (Spot equivalent)</option>
                  <option value={2.0}>2x (Prudent)</option>
                  <option value={3.0}>3x (Balanced)</option>
                  <option value={5.0}>5x (Max testnet recommended)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Max Open Positions</label>
                <select
                  className="form-select"
                  value={formData.max_open_positions}
                  onChange={(e) => handleChange("max_open_positions", parseInt(e.target.value))}
                  disabled={isSaving}
                >
                  <option value={1}>1 position</option>
                  <option value={2}>2 positions</option>
                  <option value={3}>3 positions</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Execution Mode</label>
                <select
                  className="form-select"
                  value={formData.execution_mode}
                  onChange={(e) => handleChange("execution_mode", e.target.value)}
                  disabled={isSaving}
                >
                  <option value="APPROVAL">Manual Approval</option>
                  <option value="AUTOMATIC_TESTNET">Automatic Testnet</option>
                </select>
              </div>
            </div>
          </div>

          {/* Mathematical Summary Card */}
          <div className="explanation-box" style={{ background: "var(--bg-main)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontWeight: 700, marginBottom: "0.35rem" }}>
              <Info size={16} color="var(--primary)" />
              Personal Risk Summary
            </div>
            <p style={{ fontSize: "0.825rem", color: "var(--text-muted)", margin: 0 }}>
              With <strong>{safeCapital.toFixed(2)} {formData.settlement_asset}</strong> allocated strategy capital, each trade carries a maximum monetary risk budget of{" "}
              <strong style={{ color: "var(--danger)" }}>{monetaryRiskBudget} {formData.settlement_asset}</strong> ({formData.risk_per_trade_pct}%). The session daily loss limit is{" "}
              <strong>{monetaryDailyLoss} {formData.settlement_asset}</strong> ({formData.max_daily_loss_pct}%), after which the Circuit Breaker trips and halts further trading.
            </p>
          </div>
        </div>

        {/* Modal Footer with visible action state and error fallback */}
        <div className="modal-footer" style={{ flexDirection: "column", gap: "0.5rem", alignItems: "stretch" }}>
          {error && (
            <div className="rejections-box" style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <AlertCircle size={15} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>{error}</span>
            </div>
          )}
          {successMessage && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "var(--success)",
                borderRadius: "6px",
                padding: "0.5rem 0.75rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                fontSize: "0.825rem",
                fontWeight: 600
              }}
            >
              <CheckCircle size={15} style={{ flexShrink: 0 }} />
              <span>{successMessage}</span>
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", width: "100%" }}>
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={isSaving}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleSave}
              disabled={isSaving}
              style={{ minWidth: "210px", justifyContent: "center" }}
            >
              {isSaving ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Saving Passport...</span>
                </>
              ) : (
                <>
                  <CheckCircle size={16} />
                  <span>Save & Confirm Passport</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
