import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  LayoutDashboard,
  LineChart,
  Brain,
  Sliders,
  ShieldAlert,
  BookOpen,
  FileText,
  Calculator,
  RefreshCw,
  TrendingUp
} from "lucide-react";

import { api } from "./services/api";
import Navbar from "./components/Navbar";
import DemoBanner from "./components/DemoBanner";
import DecisionCard from "./components/DecisionCard";
import RiskPassportModal from "./components/RiskPassportModal";
import CandleChart from "./components/CandleChart";
import WhatIfSimulator from "./components/WhatIfSimulator";
import RiskMonitor from "./components/RiskMonitor";
import OrderTable from "./components/OrderTable";
import StrategyLab from "./components/StrategyLab";
import AuditLogView from "./components/AuditLogView";
import SessionReportModal from "./components/SessionReportModal";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  // State
  const [health, setHealth] = useState(null);
  const [connectivity, setConnectivity] = useState(null);
  const [accountStatus, setAccountStatus] = useState(null);
  const [ticker, setTicker] = useState(null);
  const [candles, setCandles] = useState([]);
  const [passport, setPassport] = useState(null);
  const [presets, setPresets] = useState(null);
  const [balance, setBalance] = useState(null);
  const [positions, setPositions] = useState([]);
  const [trades, setTrades] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [circuitBreaker, setCircuitBreaker] = useState(null);
  const [strategyConfig, setStrategyConfig] = useState(null);
  const [strategyStatus, setStrategyStatus] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);

  // Modals & UI Controls
  const [passportOpen, setPassportOpen] = useState(false);
  const [sessionReport, setSessionReport] = useState(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [lastMarketUpdate, setLastMarketUpdate] = useState(null);
  const [marketFeedStatus, setMarketFeedStatus] = useState("CONNECTING");

  // Prevent overlapping concurrent polling requests
  const isPollingRef = useRef(false);

  // Initial Data Fetch
  const loadInitialData = useCallback(async () => {
    try {
      const [
        healthRes,
        connRes,
        acctRes,
        passRes,
        presRes,
        balRes,
        posRes,
        trdRes,
        perfRes,
        cbRes,
        stratRes,
        statRes,
        decRes,
        audRes
      ] = await Promise.allSettled([
        api.getHealth(),
        api.getConnectivity(),
        api.getAccountStatus(),
        api.getPassport(),
        api.getPresets(),
        api.getBalance(),
        api.getPositions(),
        api.getTrades(50),
        api.getPerformance(),
        api.getCircuitBreaker(),
        api.getStrategyConfig(),
        api.getStrategyStatus(),
        api.getDecisions(30),
        api.getAuditLogs(50)
      ]);

      if (healthRes.status === "fulfilled") setHealth(healthRes.value);
      if (connRes.status === "fulfilled") setConnectivity(connRes.value);
      if (acctRes.status === "fulfilled") setAccountStatus(acctRes.value);
      if (passRes.status === "fulfilled") setPassport(passRes.value);
      if (presRes.status === "fulfilled") setPresets(presRes.value);
      if (balRes.status === "fulfilled") setBalance(balRes.value);
      if (posRes.status === "fulfilled") setPositions(posRes.value);
      if (trdRes.status === "fulfilled") setTrades(trdRes.value);
      if (perfRes.status === "fulfilled") setPerformance(perfRes.value);
      if (cbRes.status === "fulfilled") setCircuitBreaker(cbRes.value);
      if (stratRes.status === "fulfilled") setStrategyConfig(stratRes.value);
      if (statRes.status === "fulfilled") setStrategyStatus(statRes.value);
      if (decRes.status === "fulfilled") setDecisions(decRes.value);
      if (audRes.status === "fulfilled") setAuditLogs(audRes.value);
    } catch (err) {
      console.error("Initial load error:", err);
    }
  }, []);

  // Market poll with concurrency guard and live health tracking
  const pollMarket = useCallback(async () => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;
    const symbol = passport?.symbol || "BTCUSDT";

    try {
      const [tickRes, cndlRes, posRes, cbRes, decRes, balRes, acctRes] = await Promise.allSettled([
        api.getTicker(symbol),
        api.getCandles(symbol, passport?.timeframe || "5m", 80),
        api.getPositions(),
        api.getCircuitBreaker(),
        api.getDecisions(15),
        api.getBalance(),
        api.getAccountStatus()
      ]);

      if (tickRes.status === "fulfilled" && tickRes.value) {
        setTicker(tickRes.value);
        setLastMarketUpdate(new Date());
        const healthStatus = tickRes.value?.feed_health?.status;
        setMarketFeedStatus(healthStatus || (tickRes.value?.is_mock ? "SIMULATED" : "LIVE_HEALTHY"));
      }
      if (cndlRes.status === "fulfilled" && Array.isArray(cndlRes.value)) {
        setCandles(cndlRes.value);
      }
      if (posRes.status === "fulfilled") setPositions(posRes.value);
      if (cbRes.status === "fulfilled") setCircuitBreaker(cbRes.value);
      if (decRes.status === "fulfilled") setDecisions(decRes.value);
      if (balRes.status === "fulfilled") setBalance(balRes.value);
      if (acctRes.status === "fulfilled") setAccountStatus(acctRes.value);
    } catch (err) {
      console.error("Market poll error:", err);
      setMarketFeedStatus("ERROR");
    } finally {
      isPollingRef.current = false;
    }
  }, [passport]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    pollMarket();
    const interval = setInterval(pollMarket, 4000);
    return () => clearInterval(interval);
  }, [pollMarket]);

  // Actions
  const handleStartBot = async () => {
    try {
      await api.startBot(passport?.execution_mode);
      const h = await api.getHealth();
      setHealth(h);
    } catch (err) {
      alert("Error starting bot: " + err.message);
    }
  };

  const handlePauseBot = async () => {
    try {
      await api.pauseBot();
      const h = await api.getHealth();
      setHealth(h);
    } catch (err) {
      alert("Error pausing bot: " + err.message);
    }
  };

  const handleResumeBot = async () => {
    try {
      await api.resumeBot();
      const h = await api.getHealth();
      setHealth(h);
    } catch (err) {
      alert("Error resuming bot: " + err.message);
    }
  };

  const handleStopBot = async () => {
    try {
      const res = await api.stopBot();
      const h = await api.getHealth();
      setHealth(h);
      if (res?.report) {
        setSessionReport(res.report);
        setReportOpen(true);
      }
      loadInitialData();
    } catch (err) {
      alert("Error stopping bot: " + err.message);
    }
  };

  const handleEvaluateNow = async () => {
    setIsEvaluating(true);
    try {
      const card = await api.evaluateNow();
      setDecisions((prev) => [card, ...prev.filter((d) => d.id !== card.id)]);
      pollMarket();
    } catch (err) {
      alert("Evaluation failed: " + err.message);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleApproveTrade = async (decisionId) => {
    setIsApproving(true);
    try {
      const res = await api.approveTrade(decisionId);
      if (res?.success) {
        alert("Trade approved and executed on Delta Testnet!");
        loadInitialData();
      }
    } catch (err) {
      alert("Trade approval failed: " + err.message);
    } finally {
      setIsApproving(false);
    }
  };

  const handleSavePassport = async (newConfig) => {
    const updated = await api.updatePassport(newConfig);
    setPassport(updated);
    await loadInitialData();
    return updated;
  };

  const handleResetCircuitBreaker = async () => {
    await api.resetCircuitBreaker();
    const cb = await api.getCircuitBreaker();
    setCircuitBreaker(cb);
  };

  const handleEmergencyClose = async (symbol) => {
    await api.emergencyClose(symbol);
    loadInitialData();
  };

  const latestDecision = decisions && decisions.length > 0 ? decisions[0] : null;

  return (
    <div className="app-container">
      {/* Demo Safe Header Banner */}
      <DemoBanner connectivity={connectivity} accountStatus={accountStatus} />

      {/* Main Navbar */}
      <Navbar
        botStatus={health}
        accountStatus={accountStatus}
        circuitBreaker={circuitBreaker}
        passport={passport}
        onOpenPassport={() => setPassportOpen(true)}
        onStartBot={handleStartBot}
        onPauseBot={handlePauseBot}
        onResumeBot={handleResumeBot}
        onStopBot={handleStopBot}
        onEvaluateNow={handleEvaluateNow}
        isEvaluating={isEvaluating}
      />

      {/* Navigation Tabs Bar */}
      <nav className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => setActiveTab("dashboard")}
        >
          <LayoutDashboard size={16} /> Overview Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === "terminal" ? "active" : ""}`}
          onClick={() => setActiveTab("terminal")}
        >
          <LineChart size={16} /> Live Trading Terminal
        </button>
        <button
          className={`tab-btn ${activeTab === "decisions" ? "active" : ""}`}
          onClick={() => setActiveTab("decisions")}
        >
          <Brain size={16} /> AI Decision Center
        </button>
        <button
          className={`tab-btn ${activeTab === "simulator" ? "active" : ""}`}
          onClick={() => setActiveTab("simulator")}
        >
          <Calculator size={16} /> What-If Simulator
        </button>
        <button
          className={`tab-btn ${activeTab === "risk" ? "active" : ""}`}
          onClick={() => setActiveTab("risk")}
        >
          <ShieldAlert size={16} /> Risk Monitor
        </button>
        <button
          className={`tab-btn ${activeTab === "journal" ? "active" : ""}`}
          onClick={() => setActiveTab("journal")}
        >
          <BookOpen size={16} /> Performance & Journal
        </button>
        <button
          className={`tab-btn ${activeTab === "strategylab" ? "active" : ""}`}
          onClick={() => setActiveTab("strategylab")}
        >
          <Sliders size={16} /> Strategy Lab
        </button>
        <button
          className={`tab-btn ${activeTab === "audit" ? "active" : ""}`}
          onClick={() => setActiveTab("audit")}
        >
          <FileText size={16} /> Audit Trail
        </button>
      </nav>

      {/* Main Page Content */}
      <main className="main-content">
        {/* TAB 1: OVERVIEW DASHBOARD */}
        {activeTab === "dashboard" && (
          <div>
            {/* Top Metric Bar */}
            <div className="grid-cols-4">
              <div className="metric-tile">
                <span className="metric-label">
                  {balance?.is_mock ? "Simulated Account Balance" : "Verified Testnet Balance"}
                </span>
                <span
                  className="metric-value"
                  style={{
                    color: (balance?.available_balance || 0) <= 0 && !balance?.is_mock ? "#d97706" : undefined
                  }}
                >
                  ${(balance?.available_balance ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {balance?.asset || "USDT"}
                </span>
                <span className="metric-sub">
                  {balance?.is_mock ? (
                    "Demo Simulation Mode (All values simulated)"
                  ) : (balance?.available_balance || 0) <= 0 ? (
                    <span style={{ color: "#d97706", fontWeight: 600 }}>
                      ⚠ Zero Balance — Account unfunded. Order execution blocked.
                    </span>
                  ) : (
                    `Allocated: $${passport?.allocated_capital?.toLocaleString()} ${passport?.settlement_asset}`
                  )}
                </span>
              </div>

              <div className="metric-tile">
                <span className="metric-label">Current Instrument & Price</span>
                <span className="metric-value">
                  ${ticker?.mark_price ? ticker.mark_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"}
                </span>
                <span className="metric-sub" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.25rem" }}>
                  <span>
                    {passport?.symbol || "BTCUSDT"} ({ticker?.exchange_symbol || "BTCUSD"}) &bull; Spread: {ticker?.spread_pct ? ticker.spread_pct.toFixed(3) : "0.020"}%
                  </span>
                  <span style={{ fontSize: "0.7rem", fontWeight: 600, color: ticker?.is_mock ? "#d97706" : "#059669" }}>
                    {ticker?.is_mock ? "● Simulated Feed" : "● Live Testnet Feed"}
                  </span>
                </span>
              </div>

              <div className="metric-tile">
                <span className="metric-label">Market Regime</span>
                <span className="metric-value" style={{ fontSize: "1.1rem" }}>
                  {latestDecision?.market_regime || "TRENDING_BULLISH"}
                </span>
                <span className="metric-sub">Adaptive Regime Filter Active</span>
              </div>

              <div className="metric-tile">
                <span className="metric-label">Session Realized PnL</span>
                <span
                  className="metric-value"
                  style={{ color: (performance?.net_pnl || 0) >= 0 ? "var(--success)" : "var(--danger)" }}
                >
                  {(performance?.net_pnl || 0) >= 0 ? "+" : ""}{performance?.net_pnl || 0} USDT
                </span>
                <span className="metric-sub">
                  Win Rate: {performance?.win_rate_pct || 0}% ({performance?.total_trades || 0} trades)
                </span>
              </div>
            </div>

            {/* Split Grid: Chart + Latest Decision Card */}
            <div className="grid-cols-2">
              <div>
                <CandleChart
                  candles={candles}
                  decisionCard={latestDecision}
                  symbol={passport?.symbol || "BTCUSDT"}
                />
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Latest Pre-Trade Decision</h3>
                  <button className="btn btn-outline btn-sm" onClick={handleEvaluateNow} disabled={isEvaluating}>
                    <RefreshCw size={12} className={isEvaluating ? "spin" : ""} /> Evaluate
                  </button>
                </div>
                <DecisionCard
                  card={latestDecision}
                  onApprove={handleApproveTrade}
                  isApproving={isApproving}
                  ordersEnabled={accountStatus?.orders_enabled}
                />
              </div>
            </div>

            {/* Open Positions & Risk Monitor Quick View */}
            <div style={{ marginTop: "1rem" }}>
              <RiskMonitor
                circuitBreaker={circuitBreaker}
                passport={passport}
                onResetCircuitBreaker={handleResetCircuitBreaker}
                onEmergencyClose={handleEmergencyClose}
              />
            </div>
          </div>
        )}

        {/* TAB 2: LIVE TRADING TERMINAL */}
        {activeTab === "terminal" && (
          <div>
            <CandleChart
              candles={candles}
              decisionCard={latestDecision}
              symbol={passport?.symbol || "BTCUSDT"}
            />
            <DecisionCard
              card={latestDecision}
              onApprove={handleApproveTrade}
              isApproving={isApproving}
              ordersEnabled={accountStatus?.orders_enabled}
            />
            <OrderTable
              positions={positions}
              trades={trades}
              performance={performance}
            />
          </div>
        )}

        {/* TAB 3: AI DECISION CENTER */}
        {activeTab === "decisions" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div>
                <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>AI Decision Center & Receipts</h2>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Immutable audit records of all opportunity evaluations, plain English rationales, and risk verdicts.
                </p>
              </div>
              <button className="btn btn-primary btn-sm" onClick={handleEvaluateNow} disabled={isEvaluating}>
                <RefreshCw size={14} className={isEvaluating ? "spin" : ""} />
                {isEvaluating ? "Evaluating..." : "Generate New Decision"}
              </button>
            </div>

            {decisions && decisions.length > 0 ? (
              decisions.map((dec) => (
                <DecisionCard
                  key={dec.id}
                  card={dec}
                  onApprove={handleApproveTrade}
                  isApproving={isApproving}
                  ordersEnabled={accountStatus?.orders_enabled}
                />
              ))
            ) : (
              <div className="card" style={{ textAlign: "center", padding: "2.5rem", color: "var(--text-light)" }}>
                No decision cards generated yet. Click "Generate New Decision" to evaluate current market state.
              </div>
            )}
          </div>
        )}

        {/* TAB 4: WHAT-IF RISK SIMULATOR */}
        {activeTab === "simulator" && (
          <div>
            <WhatIfSimulator initialDecision={latestDecision} />
          </div>
        )}

        {/* TAB 5: RISK MONITOR */}
        {activeTab === "risk" && (
          <div>
            <RiskMonitor
              circuitBreaker={circuitBreaker}
              passport={passport}
              onResetCircuitBreaker={handleResetCircuitBreaker}
              onEmergencyClose={handleEmergencyClose}
            />
          </div>
        )}

        {/* TAB 6: PERFORMANCE & TRADE JOURNAL */}
        {activeTab === "journal" && (
          <div>
            <OrderTable
              positions={positions}
              trades={trades}
              performance={performance}
            />
          </div>
        )}

        {/* TAB 7: STRATEGY LAB */}
        {activeTab === "strategylab" && (
          <div>
            <StrategyLab
              strategyConfig={strategyConfig}
              onSaveStrategy={async (cfg) => {
                const res = await api.updateStrategyConfig(cfg);
                setStrategyConfig(res);
              }}
            />
          </div>
        )}

        {/* TAB 8: AUDIT TRAIL */}
        {activeTab === "audit" && (
          <div>
            <AuditLogView logs={auditLogs} />
          </div>
        )}
      </main>

      {/* Risk Passport Configuration Modal */}
      <RiskPassportModal
        isOpen={passportOpen}
        onClose={() => setPassportOpen(false)}
        currentPassport={passport}
        presets={presets}
        availableBalance={typeof balance?.available_balance === "number" ? balance.available_balance : 0.0}
        onSave={handleSavePassport}
      />

      {/* Session Performance Report Modal */}
      <SessionReportModal
        report={sessionReport}
        isOpen={reportOpen}
        onClose={() => setReportOpen(false)}
      />
    </div>
  );
}
