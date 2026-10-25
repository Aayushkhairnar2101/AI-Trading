import React, { useState, useEffect } from "react";
import { Sliders, Brain, RefreshCw, CheckCircle, BarChart2 } from "lucide-react";
import { api } from "../services/api";

export default function StrategyLab({ strategyConfig, onSaveStrategy }) {
  const [formData, setFormData] = useState({ ...strategyConfig });
  const [mlStatus, setMlStatus] = useState(null);
  const [training, setTraining] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (strategyConfig) setFormData({ ...strategyConfig });
  }, [strategyConfig]);

  useEffect(() => {
    loadMLStatus();
  }, []);

  const loadMLStatus = async () => {
    try {
      const res = await api.getMLStatus();
      setMlStatus(res);
    } catch (err) {
      console.error("Failed to load ML status:", err);
    }
  };

  const handleChange = (field, val) => {
    setFormData((prev) => ({ ...prev, [field]: parseFloat(val) || val }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      await onSaveStrategy(formData);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch (err) {
      alert("Error saving strategy: " + err.message);
    }
  };

  const handleTrainML = async () => {
    setTraining(true);
    try {
      await api.trainML();
      await loadMLStatus();
    } catch (err) {
      alert("Error training ML: " + err.message);
    } finally {
      setTraining(false);
    }
  };

  return (
    <div>
      {/* Strategy Indicator Lab */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Sliders size={18} color="var(--primary)" />
            <span>Regime-Aware Strategy Indicator Tuner</span>
          </div>
          {saveSuccess && (
            <span className="badge badge-success">
              <CheckCircle size={14} /> Parameters Updated
            </span>
          )}
        </div>

        <form onSubmit={handleSave}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
            <div className="form-group">
              <label className="form-label">EMA Fast Period</label>
              <input
                type="number"
                className="form-input"
                value={formData.ema_fast_period || 9}
                onChange={(e) => handleChange("ema_fast_period", e.target.value)}
                min={2}
                max={50}
              />
            </div>

            <div className="form-group">
              <label className="form-label">EMA Slow Period</label>
              <input
                type="number"
                className="form-input"
                value={formData.ema_slow_period || 21}
                onChange={(e) => handleChange("ema_slow_period", e.target.value)}
                min={5}
                max={200}
              />
            </div>

            <div className="form-group">
              <label className="form-label">RSI Period</label>
              <input
                type="number"
                className="form-input"
                value={formData.rsi_period || 14}
                onChange={(e) => handleChange("rsi_period", e.target.value)}
                min={2}
                max={50}
              />
            </div>

            <div className="form-group">
              <label className="form-label">RSI Long Sweet Spot (Min - Max)</label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  type="number"
                  className="form-input"
                  value={formData.rsi_long_min || 52}
                  onChange={(e) => handleChange("rsi_long_min", e.target.value)}
                />
                <input
                  type="number"
                  className="form-input"
                  value={formData.rsi_long_max || 68}
                  onChange={(e) => handleChange("rsi_long_max", e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">RSI Short Sweet Spot (Min - Max)</label>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  type="number"
                  className="form-input"
                  value={formData.rsi_short_min || 32}
                  onChange={(e) => handleChange("rsi_short_min", e.target.value)}
                />
                <input
                  type="number"
                  className="form-input"
                  value={formData.rsi_short_max || 48}
                  onChange={(e) => handleChange("rsi_short_max", e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">ADX Trend Threshold</label>
              <input
                type="number"
                className="form-input"
                value={formData.adx_threshold || 20}
                onChange={(e) => handleChange("adx_threshold", e.target.value)}
                min={10}
                max={50}
              />
            </div>

            <div className="form-group">
              <label className="form-label">ATR Stop Multiplier</label>
              <input
                type="number"
                step="0.1"
                className="form-input"
                value={formData.atr_stop_multiplier || 1.5}
                onChange={(e) => handleChange("atr_stop_multiplier", e.target.value)}
                min={0.5}
                max={4.0}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Min Reward-to-Risk</label>
              <input
                type="number"
                step="0.1"
                className="form-input"
                value={formData.min_reward_to_risk || 1.5}
                onChange={(e) => handleChange("min_reward_to_risk", e.target.value)}
                min={1.0}
                max={5.0}
              />
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button type="submit" className="btn btn-primary">
              <CheckCircle size={16} /> Save Strategy Settings
            </button>
          </div>
        </form>
      </div>

      {/* Machine Learning Model Center */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Brain size={18} color="var(--primary)" />
            <span>Machine Learning Module (Walk-Forward Validation)</span>
          </div>
          <span className="badge badge-neutral">Status: {mlStatus?.status || "NOT_TRAINED"}</span>
        </div>

        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          Trains a Scikit-Learn Gradient Boosting Classifier on chronological candle return sequences,
          EMA divergence, RSI, ADX, and volume ratios. Strict leakage-free walk-forward validation (80/20 split).
          <em> Note: High ML confidence can never override a failed safety check.</em>
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
          <div className="metric-tile">
            <span className="metric-label">Model Status</span>
            <span className="metric-value" style={{ fontSize: "1.1rem" }}>{mlStatus?.status || "NOT_TRAINED"}</span>
            <span className="metric-sub">Samples: {mlStatus?.sample_count || 0}</span>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Validation Accuracy</span>
            <span className="metric-value" style={{ color: "var(--primary)" }}>
              {mlStatus?.validation_accuracy ? `${(mlStatus.validation_accuracy * 100).toFixed(1)}%` : "N/A"}
            </span>
            <span className="metric-sub">Out-of-sample forward test</span>
          </div>
          <div className="metric-tile">
            <span className="metric-label">Feature Columns</span>
            <span className="metric-value" style={{ fontSize: "1.1rem" }}>9 Features</span>
            <span className="metric-sub">Returns, EMAs, RSI, ADX, ATR, Vol</span>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-primary" onClick={handleTrainML} disabled={training}>
            <RefreshCw size={14} className={training ? "spin" : ""} />
            {training ? "Training Chronological Model..." : "Train / Revalidate Model"}
          </button>
        </div>
      </div>
    </div>
  );
}
