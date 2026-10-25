"""
Analytics, Performance, Circuit Breaker, Audit Logs & CSV Export Endpoints.
"""

from fastapi import APIRouter, Response
from typing import List, Dict, Any, Optional
import io
import csv

from app.schemas.order import AccountBalance, PositionInfo
from app.schemas.analytics import PerformanceMetrics, CircuitBreakerStatus, SessionReport
from app.services.execution.bot_engine import bot
from app.services.storage.database import db

router = APIRouter(prefix="/analytics", tags=["Analytics & Monitoring"])


@router.get("/balance", response_model=AccountBalance)
async def get_balance():
    return await bot.exchange.get_balance(asset=bot.passport.settlement_asset)


@router.get("/positions", response_model=List[PositionInfo])
async def get_positions():
    return await bot.exchange.get_positions()


@router.get("/trades")
async def get_trades(limit: int = 100):
    return db.get_trades(limit=limit)


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance():
    return db.get_performance_metrics()


@router.get("/circuit-breaker", response_model=CircuitBreakerStatus)
async def get_circuit_breaker():
    return bot.circuit_breaker.get_status()


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker():
    bot.circuit_breaker.reset(new_start_equity=bot.passport.allocated_capital)
    return {"success": True, "message": "Circuit breaker reset to normal armed state."}


@router.get("/audit-logs")
async def get_audit_logs(limit: int = 100):
    return db.get_audit_logs(limit=limit)


@router.get("/session-report")
async def get_latest_session_report():
    report = db.get_latest_session_report()
    return report or {"message": "No session report available yet."}


@router.get("/trades/export-csv")
async def export_trades_csv():
    trades = db.get_trades(limit=1000)
    output = io.StringIO()
    if not trades:
        output.write("id,symbol,direction,entry_price,exit_price,quantity,status,realized_pnl,opened_at,closed_at\n")
    else:
        fieldnames = list(trades[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=riskpilot_trade_journal.csv"
    return response
