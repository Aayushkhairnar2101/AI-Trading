/**
 * RiskPilot AI - Frontend API Service
 * Connects to Python FastAPI backend endpoints.
 */

const API_BASE = "http://127.0.0.1:8000/api";

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  try {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Status & Connectivity
  getHealth: () => request("/status/health"),
  getConnectivity: () => request("/status/connectivity"),
  getAccountStatus: () => request("/status/account"),

  // Market Data
  getInstruments: () => request("/market/instruments"),
  getTicker: (symbol = "BTCUSDT") => request(`/market/ticker?symbol=${symbol}`),
  getCandles: (symbol = "BTCUSDT", timeframe = "5m", limit = 80) =>
    request(`/market/candles?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`),

  // Personal Risk Passport
  getPassport: () => request("/passport"),
  getPassportSummary: () => request("/passport/summary"),
  updatePassport: (config) =>
    request("/passport", { method: "POST", body: JSON.stringify(config) }),
  getPresets: () => request("/passport/presets"),

  // Strategy & Decisions
  getStrategyConfig: () => request("/strategy/config"),
  updateStrategyConfig: (config) =>
    request("/strategy/config", { method: "POST", body: JSON.stringify(config) }),
  getStrategyStatus: () => request("/strategy/status"),
  evaluateNow: () => request("/strategy/evaluate", { method: "POST" }),
  getDecisions: (limit = 50) => request(`/strategy/decisions?limit=${limit}`),
  getDecisionById: (id) => request(`/strategy/decision/${id}`),
  simulateWhatIf: (params) =>
    request("/strategy/simulate-what-if", { method: "POST", body: JSON.stringify(params) }),
  getMLStatus: () => request("/strategy/ml-status"),
  trainML: () => request("/strategy/train-ml", { method: "POST" }),

  // Bot Lifecycle Controls
  startBot: (mode) =>
    request("/bot/start", { method: "POST", body: JSON.stringify(mode ? { mode } : {}) }),
  pauseBot: () => request("/bot/pause", { method: "POST" }),
  resumeBot: () => request("/bot/resume", { method: "POST" }),
  stopBot: () => request("/bot/stop", { method: "POST" }),
  approveTrade: (decisionId) =>
    request("/bot/approve", { method: "POST", body: JSON.stringify({ decision_id: decisionId }) }),
  emergencyClose: (symbol = "BTCUSDT") =>
    request("/bot/emergency-close", {
      method: "POST",
      body: JSON.stringify({ symbol, confirm_action: true })
    }),

  // Analytics & Monitoring
  getBalance: () => request("/analytics/balance"),
  getPositions: () => request("/analytics/positions"),
  getTrades: (limit = 100) => request(`/analytics/trades?limit=${limit}`),
  getPerformance: () => request("/analytics/performance"),
  getCircuitBreaker: () => request("/analytics/circuit-breaker"),
  resetCircuitBreaker: () => request("/analytics/circuit-breaker/reset", { method: "POST" }),
  getAuditLogs: (limit = 100) => request(`/analytics/audit-logs?limit=${limit}`),
  getSessionReport: () => request("/analytics/session-report"),
  exportTradesCsvUrl: `${API_BASE}/analytics/trades/export-csv`
};
