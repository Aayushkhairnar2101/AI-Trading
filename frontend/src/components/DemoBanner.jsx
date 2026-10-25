import React from "react";
import { ShieldCheck, Info, AlertTriangle, WifiOff, Ban } from "lucide-react";

/**
 * DemoBanner — top-of-page status strip.
 *
 * Distinguishes four states:
 *   LIVE_TESTNET + funded     → green  "Connected — Testnet"
 *   LIVE_TESTNET + zero bal   → amber  "Connected — Testnet balance is zero"
 *   AUTHENTICATION_FAILED     → red    "Authentication Failed"
 *   Demo / Simulation Mode    → yellow "Demo-Safe Simulation Mode"
 */
export default function DemoBanner({ connectivity, accountStatus }) {
  const mode          = connectivity?.mode;
  const isLive        = mode === "LIVE_TESTNET" && connectivity?.authenticated;
  const isAuthFailed  = mode === "AUTHENTICATION_FAILED";
  const isDemo        = !isLive && !isAuthFailed;

  // accountStatus comes from GET /api/status/account (fetched separately in App.jsx)
  const ordersEnabled  = accountStatus?.orders_enabled;
  const fundingWarning = accountStatus?.funding_warning;
  const isFunded       = accountStatus?.account_funded;
  const availBal       = accountStatus?.balance?.available_balance ?? 0;

  // Resolve visual state
  const isLiveZero = isLive && !isFunded && !accountStatus?.balance?.is_mock;

  const bg     = isAuthFailed  ? "#fee2e2"
               : isLiveZero    ? "#fffbeb"
               : isLive        ? "#ecfdf5"
                               : "#fef3c7";
  const border = isAuthFailed  ? "#fca5a5"
               : isLiveZero    ? "#fde68a"
               : isLive        ? "#a7f3d0"
                               : "#fde68a";
  const color  = isAuthFailed  ? "#991b1b"
               : isLiveZero    ? "#92400e"
               : isLive        ? "#065f46"
                               : "#92400e";

  const Icon = isAuthFailed  ? AlertTriangle
             : isLiveZero    ? Ban
             : isLive        ? ShieldCheck
                             : Info;
  const iconColor = isAuthFailed  ? "#dc2626"
                  : isLiveZero    ? "#d97706"
                  : isLive        ? "#059669"
                                  : "#d97706";

  const statusText =
    isLive && isFunded
      ? "Authenticated Live Testnet — Connected. Real testnet market feeds active. Order submission enabled."
      : isLiveZero
      ? "Connected to Delta Exchange India Testnet but USDT balance is 0. Order submission is DISABLED until the testnet account is funded at demo.delta.exchange."
      : isAuthFailed
      ? "Authentication Failed. Please check DELTA_API_KEY and DELTA_API_SECRET in backend/.env."
      : "Demo-Safe Simulation Mode active. All figures and trades are safely simulated — no live order mutation.";

  return (
    <div
      className="demo-banner"
      style={{
        backgroundColor: bg,
        borderBottom: `1px solid ${border}`,
        color,
        flexWrap: "wrap",
        gap: "0.35rem"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1 }}>
        <Icon size={16} color={iconColor} />
        <span>
          <strong>Environment:</strong> Delta Exchange India Testnet (
          <code style={{ fontSize: "0.75rem" }}>cdn-ind.testnet.deltaex.org</code>)
          &bull;{" "}
          {statusText}
        </span>
      </div>

      {/* Right side: balance pill + orders status */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", fontSize: "0.725rem" }}>
        {isLive && (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              padding: "0.15rem 0.5rem",
              borderRadius: "9999px",
              fontWeight: 600,
              background: isFunded ? "#d1fae5" : "#fef3c7",
              color: isFunded ? "#065f46" : "#92400e",
              border: `1px solid ${isFunded ? "#6ee7b7" : "#fde68a"}`
            }}
          >
            Balance: {availBal.toFixed(2)} USDT
          </span>
        )}
        <span style={{ color: "#64748b" }}>
          Production Endpoints Blocked &bull; Testnet Protected &bull;{" "}
          {ordersEnabled ? (
            <span style={{ color: "#059669", fontWeight: 700 }}>Orders ENABLED</span>
          ) : (
            <span style={{ color: "#dc2626", fontWeight: 700 }}>Orders DISABLED</span>
          )}
        </span>
      </div>
    </div>
  );
}
