import React from "react";
import {
  Shield,
  Activity,
  Play,
  Pause,
  Square,
  Sliders,
  AlertTriangle,
  RefreshCw,
  Ban,
  CheckCircle2
} from "lucide-react";

export default function Navbar({
  botStatus,
  accountStatus,
  circuitBreaker,
  passport,
  onOpenPassport,
  onStartBot,
  onPauseBot,
  onResumeBot,
  onStopBot,
  onEvaluateNow,
  isEvaluating
}) {
  const isRunning = botStatus?.bot_running;
  const isPaused = botStatus?.bot_paused;
  const mode = passport?.execution_mode || "APPROVAL";

  // Account & Execution enablement
  const ordersEnabled = accountStatus?.orders_enabled;
  const isMock = accountStatus?.balance?.is_mock;
  const availBal = accountStatus?.balance?.available_balance ?? 0;
  const isZeroBalance = !isMock && availBal <= 0;

  return (
    <header className="navbar">
      <div className="brand-section">
        <div className="brand-icon">
          <Shield size={22} />
        </div>
        <div>
          <h1 className="brand-title">RiskPilot AI</h1>
          <p className="brand-tagline">Personalized, Explainable Algorithmic Trading</p>
        </div>
      </div>

      <div className="nav-actions">
        {/* Circuit Breaker Status */}
        {circuitBreaker?.is_tripped ? (
          <span className="badge badge-danger" title={circuitBreaker?.trip_reason}>
            <AlertTriangle size={14} />
            Circuit Breaker TRIPPED
          </span>
        ) : (
          <span className="badge badge-success">
            <Shield size={14} />
            Circuit Breaker ARMED
          </span>
        )}

        {/* 1. Market Analysis Status (Distinguished from execution) */}
        <span
          className={`badge ${
            isRunning
              ? isPaused
                ? "badge-warning"
                : "badge-success"
              : "badge-neutral"
          }`}
          title={
            isRunning
              ? isPaused
                ? "Market analysis is paused by user."
                : "The bot is actively evaluating live candles and computing risk metrics every 5 seconds."
              : "Market analysis is stopped. Click Start Bot or Evaluate Now to inspect current candles."
          }
        >
          <Activity size={14} className={isRunning && !isPaused ? "spin-slow" : ""} />
          Analysis: {isRunning ? (isPaused ? "PAUSED" : "RUNNING") : "IDLE"}
        </span>

        {/* 2. Order Execution Status (Explicitly distinct) */}
        {isZeroBalance ? (
          <span
            className="badge badge-danger"
            title="Order execution blocked: Account is unfunded (0 USDT on Testnet). Fund at demo.delta.exchange."
          >
            <Ban size={14} />
            Orders: DISABLED (0 USDT)
          </span>
        ) : (
          <span
            className="badge badge-primary"
            title={
              mode === "AUTOMATIC_TESTNET"
                ? "Automatic testnet execution enabled for confirmed setups meeting all risk limits."
                : "Approval Mode: All orders require manual user review and confirmation before execution."
            }
          >
            <Shield size={14} />
            Orders: {mode === "AUTOMATIC_TESTNET" ? "AUTO TESTNET" : "APPROVAL MODE"}
          </span>
        )}

        {/* Evaluate Now Button */}
        <button
          className="btn btn-outline btn-sm"
          onClick={onEvaluateNow}
          disabled={isEvaluating}
          title="Trigger immediate market & risk evaluation"
        >
          <RefreshCw size={14} className={isEvaluating ? "spin" : ""} />
          Evaluate Now
        </button>

        {/* Risk Passport Button */}
        <button className="btn btn-outline btn-sm" onClick={onOpenPassport}>
          <Sliders size={14} />
          Risk Passport
        </button>

        {/* Bot Controls */}
        {!isRunning ? (
          <button className="btn btn-primary btn-sm" onClick={onStartBot}>
            <Play size={14} />
            Start Bot
          </button>
        ) : (
          <>
            {isPaused ? (
              <button className="btn btn-primary btn-sm" onClick={onResumeBot}>
                <Play size={14} />
                Resume
              </button>
            ) : (
              <button className="btn btn-outline btn-sm" onClick={onPauseBot}>
                <Pause size={14} />
                Pause
              </button>
            )}
            <button className="btn btn-danger btn-sm" onClick={onStopBot}>
              <Square size={14} />
              Stop
            </button>
          </>
        )}
      </div>
    </header>
  );
}
