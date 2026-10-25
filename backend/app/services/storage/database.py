"""
SQLite Database Storage for RiskPilot AI.
Persists decisions, completed trades, audit logs, and session analytics.
Provides immutable Trade Decision Receipts and CSV export capability.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.config import settings
from app.schemas.decision import PreTradeDecisionCard, DecisionStatus
from app.schemas.order import TradeRecord
from app.schemas.analytics import AuditLogEntry, PerformanceMetrics, SessionReport
import logging

logger = logging.getLogger("riskpilot.database")


class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DB_PATH
        self._init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Initializes tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Decisions Table (Immutable Trade Decision Receipts)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                current_price REAL NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                reward_to_risk REAL NOT NULL,
                allocated_capital REAL NOT NULL,
                risk_percentage REAL NOT NULL,
                risk_budget REAL NOT NULL,
                quantity REAL NOT NULL,
                notional REAL NOT NULL,
                effective_leverage REAL NOT NULL,
                market_regime TEXT NOT NULL,
                plain_english_explanation TEXT NOT NULL,
                final_decision TEXT NOT NULL,
                approved_by_user INTEGER,
                exchange_order_id TEXT,
                details_json TEXT NOT NULL
            );
            """)

            # 2. Trades Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                realized_pnl REAL,
                pnl_percentage REAL,
                fee_paid REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                exit_reason TEXT,
                risk_percentage REAL NOT NULL,
                risk_budget REAL NOT NULL,
                exchange_order_id TEXT,
                opened_at TEXT NOT NULL,
                closed_at TEXT
            );
            """)

            # 3. Audit Logs Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                event_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                severity TEXT NOT NULL,
                details_json TEXT NOT NULL
            );
            """)

            # 4. Session Reports Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_reports (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                initial_capital REAL NOT NULL,
                current_capital REAL NOT NULL,
                net_pnl REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                win_rate_pct REAL NOT NULL,
                profit_factor REAL NOT NULL,
                report_json TEXT NOT NULL
            );
            """)

            conn.commit()

    def save_decision(self, card: PreTradeDecisionCard) -> None:
        """Stores decision receipt in SQLite."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO decisions (
                id, timestamp, symbol, direction, current_price, entry_price, stop_loss,
                take_profit, reward_to_risk, allocated_capital, risk_percentage, risk_budget,
                quantity, notional, effective_leverage, market_regime, plain_english_explanation,
                final_decision, approved_by_user, exchange_order_id, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card.id,
                card.timestamp.isoformat(),
                card.symbol,
                card.proposed_direction.value,
                card.current_price,
                card.estimated_entry,
                card.proposed_stop_loss,
                card.proposed_take_profit,
                card.reward_to_risk_ratio,
                card.allocated_capital,
                card.risk_percentage,
                card.risk_budget_monetary,
                card.calculated_quantity,
                card.notional_exposure,
                card.effective_leverage,
                card.market_regime.value,
                card.plain_english_explanation,
                card.final_decision.value,
                1 if card.approved_by_user else (0 if card.approved_by_user is False else None),
                card.exchange_order_id,
                card.model_dump_json()
            ))
            conn.commit()

    def get_recent_decisions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT details_json FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [json.loads(r["details_json"]) for r in rows]

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT details_json FROM decisions WHERE id = ?", (decision_id,))
            row = cursor.fetchone()
            return json.loads(row["details_json"]) if row else None

    def update_decision_approval(self, decision_id: str, approved: bool, exchange_order_id: Optional[str] = None) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE decisions
            SET approved_by_user = ?,
                final_decision = ?,
                exchange_order_id = COALESCE(?, exchange_order_id)
            WHERE id = ?
            """, (
                1 if approved else 0,
                DecisionStatus.ALLOWED.value if approved else DecisionStatus.REJECTED.value,
                exchange_order_id,
                decision_id
            ))
            conn.commit()

    def save_trade(self, trade: TradeRecord) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO trades (
                id, decision_id, symbol, direction, entry_price, exit_price,
                quantity, stop_loss, take_profit, realized_pnl, pnl_percentage,
                fee_paid, status, exit_reason, risk_percentage, risk_budget,
                exchange_order_id, opened_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id,
                trade.decision_id,
                trade.symbol,
                trade.direction,
                trade.entry_price,
                trade.exit_price,
                trade.quantity,
                trade.stop_loss,
                trade.take_profit,
                trade.realized_pnl,
                trade.pnl_percentage,
                trade.fee_paid,
                trade.status,
                trade.exit_reason,
                trade.risk_percentage,
                trade.risk_budget,
                trade.exchange_order_id,
                trade.opened_at.isoformat(),
                trade.closed_at.isoformat() if trade.closed_at else None
            ))
            conn.commit()

    def get_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades ORDER BY opened_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def log_audit(self, entry: AuditLogEntry) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_logs (id, timestamp, category, event_type, summary, severity, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.timestamp.isoformat(),
                entry.category,
                entry.event_type,
                entry.summary,
                entry.severity,
                json.dumps(entry.details)
            ))
            conn.commit()

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            logs = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item["details_json"])
                logs.append(item)
            return logs

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Calculates verified performance statistics from closed trades."""
        trades = self.get_trades(limit=500)
        closed_trades = [t for t in trades if t["status"] == "CLOSED" and t["realized_pnl"] is not None]

        if not closed_trades:
            return PerformanceMetrics()

        wins = [t for t in closed_trades if (t["realized_pnl"] or 0) > 0]
        losses = [t for t in closed_trades if (t["realized_pnl"] or 0) < 0]

        total_realized = sum(t["realized_pnl"] for t in closed_trades)
        total_fees = sum(t.get("fee_paid", 0.0) or 0.0 for t in closed_trades)
        net_pnl = total_realized - total_fees

        gross_profit = sum(t["realized_pnl"] for t in wins) if wins else 0.0
        gross_loss = abs(sum(t["realized_pnl"] for t in losses)) if losses else 0.0
        pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 0.0)

        win_rate = round((len(wins) / len(closed_trades)) * 100.0, 1)

        avg_win = round(gross_profit / len(wins), 2) if wins else 0.0
        avg_loss = round(gross_loss / len(losses), 2) if losses else 0.0

        # Calculate max drawdown
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in reversed(closed_trades):
            cumulative += t["realized_pnl"]
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        return PerformanceMetrics(
            total_trades=len(closed_trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=win_rate,
            profit_factor=pf,
            total_realized_pnl=round(total_realized, 2),
            total_fees_paid=round(total_fees, 2),
            net_pnl=round(net_pnl, 2),
            average_trade_pnl=round(net_pnl / len(closed_trades), 2),
            average_win=avg_win,
            average_loss=avg_loss,
            max_drawdown_pct=round(max_dd, 2)
        )

    def save_session_report(self, report: SessionReport) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO session_reports (
                session_id, started_at, ended_at, initial_capital, current_capital,
                net_pnl, total_trades, win_rate_pct, profit_factor, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.session_id,
                report.started_at.isoformat(),
                report.ended_at.isoformat() if report.ended_at else None,
                report.initial_allocated_capital,
                report.current_capital,
                report.net_pnl,
                report.performance.total_trades,
                report.performance.win_rate_pct,
                report.performance.profit_factor,
                report.model_dump_json()
            ))
            conn.commit()

    def get_latest_session_report(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_json FROM session_reports ORDER BY started_at DESC LIMIT 1")
            row = cursor.fetchone()
            return json.loads(row["report_json"]) if row else None


db = Database()
