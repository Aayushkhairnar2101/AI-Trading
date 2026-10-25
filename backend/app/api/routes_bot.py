"""
Bot Runtime Controls and Trade Approval Endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.schemas.passport import ExecutionMode
from app.services.execution.bot_engine import bot

router = APIRouter(prefix="/bot", tags=["Bot Execution & Controls"])


class StartBotRequest(BaseModel):
    mode: Optional[ExecutionMode] = None


class ApproveTradeRequest(BaseModel):
    decision_id: str


class EmergencyActionRequest(BaseModel):
    symbol: Optional[str] = "BTCUSDT"
    confirm_action: bool


@router.post("/start")
async def start_bot(req: Optional[StartBotRequest] = None):
    mode = req.mode if req else None
    return await bot.start_session(mode=mode)


@router.post("/pause")
async def pause_bot():
    return bot.pause_session()


@router.post("/resume")
async def resume_bot():
    return bot.resume_session()


@router.post("/stop")
async def stop_bot():
    return await bot.stop_session()


@router.post("/approve")
async def approve_trade(req: ApproveTradeRequest):
    res = await bot.approve_trade(req.decision_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error") or res.get("message"))
    return res


@router.post("/emergency-close")
async def emergency_close(req: EmergencyActionRequest):
    if not req.confirm_action:
        raise HTTPException(status_code=400, detail="Action confirmation is required.")
    return await bot.order_manager.emergency_close_bot_positions(symbol=req.symbol)
