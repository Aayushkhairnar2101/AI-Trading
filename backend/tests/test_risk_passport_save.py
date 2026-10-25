"""
Unit and Integration Tests for Risk Passport Save, Validation, Presets,
Capital Allocation Distinction, and Zero-Balance Order Protection.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.execution.bot_engine import bot
from app.schemas.passport import RiskPassportConfig, RiskProfileTier, ExecutionMode
from app.schemas.decision import TradeDirection, MarketRegime
from app.schemas.order import AccountBalance
from app.services.strategy.signal_engine import StrategySignal
from app.services.risk.position_sizer import ProductSpecification
from app.services.storage.database import db


@pytest.fixture
def client():
    return TestClient(app)


def test_passport_get_current(client):
    """GET /api/passport must return the active passport configuration."""
    response = client.get("/api/passport")
    assert response.status_code == 200
    data = response.json()
    assert "allocated_capital" in data
    assert "risk_per_trade_pct" in data
    assert "max_daily_loss_pct" in data
    assert "max_leverage" in data


def test_passport_save_success_with_zero_testnet_balance(client):
    """
    POST /api/passport must succeed even when verified testnet wallet balance is 0.0 USDT.
    Strategy capital sets sizing parameters; it is not proof of available exchange funds.
    """
    payload = {
        "profile_tier": "BALANCED",
        "allocated_capital": 1000.0,
        "settlement_asset": "USDT",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 2.0,
        "max_open_positions": 1,
        "max_leverage": 2.0,
        "min_reward_to_risk": 1.5,
        "execution_mode": "APPROVAL",
        "max_consecutive_losses": 3
    }
    response = client.post("/api/passport", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["allocated_capital"] == 1000.0
    assert data["risk_per_trade_pct"] == 0.5
    assert data["max_daily_loss_pct"] == 2.0
    assert data["max_leverage"] == 2.0
    assert data["profile_tier"] == "BALANCED"

    # Verify bot state was updated
    assert bot.passport.allocated_capital == 1000.0
    assert bot.passport.risk_per_trade_pct == 0.5


def test_passport_save_hard_limit_risk_rejected(client):
    """POST /api/passport must strictly reject risk_per_trade_pct > 2.0%."""
    payload = {
        "profile_tier": "CUSTOM",
        "allocated_capital": 1000.0,
        "settlement_asset": "USDT",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "risk_per_trade_pct": 2.5,  # Exceeds 2.0% hard limit
        "max_daily_loss_pct": 2.0,
        "max_open_positions": 1,
        "max_leverage": 2.0,
        "min_reward_to_risk": 1.5,
        "execution_mode": "APPROVAL",
        "max_consecutive_losses": 3
    }
    response = client.post("/api/passport", json=payload)
    assert response.status_code == 422


def test_passport_save_hard_limit_daily_loss_rejected(client):
    """POST /api/passport must strictly reject max_daily_loss_pct > 5.0%."""
    payload = {
        "profile_tier": "CUSTOM",
        "allocated_capital": 1000.0,
        "settlement_asset": "USDT",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 6.0,  # Exceeds 5.0% hard limit
        "max_open_positions": 1,
        "max_leverage": 2.0,
        "min_reward_to_risk": 1.5,
        "execution_mode": "APPROVAL",
        "max_consecutive_losses": 3
    }
    response = client.post("/api/passport", json=payload)
    assert response.status_code == 422


def test_passport_save_hard_limit_leverage_rejected(client):
    """POST /api/passport must strictly reject max_leverage > 10.0x."""
    payload = {
        "profile_tier": "CUSTOM",
        "allocated_capital": 1000.0,
        "settlement_asset": "USDT",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 2.0,
        "max_open_positions": 1,
        "max_leverage": 15.0,  # Exceeds 10x hard ceiling
        "min_reward_to_risk": 1.5,
        "execution_mode": "APPROVAL",
        "max_consecutive_losses": 3
    }
    response = client.post("/api/passport", json=payload)
    assert response.status_code == 422


def test_passport_save_zero_capital_rejected(client):
    """POST /api/passport must reject allocated_capital <= 0."""
    payload = {
        "profile_tier": "BALANCED",
        "allocated_capital": 0.0,
        "settlement_asset": "USDT",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 2.0,
        "max_open_positions": 1,
        "max_leverage": 2.0,
        "min_reward_to_risk": 1.5,
        "execution_mode": "APPROVAL",
        "max_consecutive_losses": 3
    }
    response = client.post("/api/passport", json=payload)
    assert response.status_code in [400, 422]


def test_passport_presets_endpoint(client):
    """GET /api/passport/presets must return standard Conservative, Balanced, and Aggressive presets."""
    response = client.get("/api/passport/presets")
    assert response.status_code == 200
    presets = response.json()
    assert "CONSERVATIVE" in presets
    assert "BALANCED" in presets
    assert "AGGRESSIVE" in presets
    assert presets["CONSERVATIVE"]["risk_per_trade_pct"] <= 0.25
    assert presets["BALANCED"]["risk_per_trade_pct"] <= 0.5
    assert presets["AGGRESSIVE"]["risk_per_trade_pct"] <= 1.0


def test_passport_summary_calculations(client):
    """GET /api/passport/summary must correctly compute risk budget and daily loss monetary figures."""
    # Configure 2000 USDT capital with 0.5% risk and 2.0% daily loss
    payload = {
        "profile_tier": "BALANCED",
        "allocated_capital": 2000.0,
        "settlement_asset": "USDT",
        "symbol": "BTCUSDT",
        "timeframe": "5m",
        "risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 2.0,
        "max_open_positions": 1,
        "max_leverage": 2.0,
        "min_reward_to_risk": 1.5,
        "execution_mode": "APPROVAL",
        "max_consecutive_losses": 3
    }
    client.post("/api/passport", json=payload)

    response = client.get("/api/passport/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["allocated_capital"] == 2000.0
    # 2000 * 0.005 = 10.0 USDT
    assert summary["risk_budget_monetary"] == 10.0
    # 2000 * 0.02 = 40.0 USDT
    assert summary["max_daily_loss_monetary"] == 40.0


def test_saving_passport_does_not_enable_zero_balance_order_execution():
    """
    Saving a valid Risk Passport with 1000 USDT allocated capital must NEVER
    bypass zero-balance order rejection at execution time.
    """
    # 1. Configure passport
    cfg = RiskPassportConfig(
        profile_tier=RiskProfileTier.BALANCED,
        allocated_capital=1000.0,
        settlement_asset="USDT",
        symbol="BTCUSDT",
        risk_per_trade_pct=0.5,
        max_daily_loss_pct=2.0,
        max_leverage=2.0
    )
    bot.configure_passport(cfg)

    # 2. Build opportunity
    spec = ProductSpecification(symbol="BTCUSDT", contract_value=0.001, min_order_size=1.0, lot_size=1.0, tick_size=0.5)
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=80000.0,
        stop_loss=79500.0,
        take_profit=81000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover"],
        no_trade_reasons=[],
        indicator_snapshot={"close": 80000.0}
    )
    mock_bal = AccountBalance(asset="USDT", available_balance=1000.0, total_balance=1000.0, is_mock=True)
    card = bot.risk_manager.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=mock_bal,
        open_positions=[],
        data_timestamp=datetime.now(timezone.utc)
    )
    db.save_decision(card)

    # 3. Simulate verified 0.0 balance on Testnet
    async def fake_zero_balance(asset="USDT"):
        return AccountBalance(asset="USDT", available_balance=0.0, total_balance=0.0, is_mock=False)

    bot.exchange.get_balance = fake_zero_balance

    # 4. Attempt trade approval
    result = asyncio.run(bot.approve_trade(card.id))
    assert result["success"] is False
    assert "ORDER BLOCKED" in result["message"]
    assert "Insufficient Testnet Balance" in result["message"]
