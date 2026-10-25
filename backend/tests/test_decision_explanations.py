"""
Unit & Integration Tests for AI Decision Card Explanations, Strategy Rationale,
Genuine Risk Rejection, ML Advisory Guardrails, and Zero-Balance Order Blocking.
"""

import pytest
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from app.schemas.passport import RiskPassportConfig, ExecutionMode
from app.schemas.strategy import StrategyConfig
from app.schemas.decision import TradeDirection, MarketRegime, DecisionStatus
from app.schemas.order import AccountBalance, PositionInfo
from app.services.strategy.signal_engine import SignalEngine, StrategySignal
from app.services.risk.risk_manager import RiskManager
from app.services.risk.circuit_breaker import CircuitBreaker
from app.services.risk.position_sizer import ProductSpecification
from app.services.execution.bot_engine import BotEngine
from app.services.exchange.delta_client import DeltaExchangeClient
from app.services.storage.database import db


def generate_candles_bullish_low_adx(count: int = 50) -> pd.DataFrame:
    """
    Creates candles where EMA 9 is above EMA 21 (bullish bias),
    but price is oscillating sideways so ADX is low (< 20).
    """
    base = 65000.0
    times = list(range(count))
    closes = []
    for i in range(count):
        # Initial slight upward drift then flat oscillation
        drift = i * 2.0
        osc = 5.0 * np.sin(i * 0.5)
        closes.append(base + drift + osc)

    opens = [c - 2.0 for c in closes]
    highs = [max(o, c) + 5.0 for o, c in zip(opens, closes)]
    lows = [min(o, c) - 5.0 for o, c in zip(opens, closes)]
    volumes = [100.0] * count

    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })


@pytest.fixture
def risk_environment():
    passport = RiskPassportConfig(
        allocated_capital=1000.0,
        risk_per_trade_pct=1.0,
        max_daily_loss_pct=3.0,
        max_open_positions=1,
        max_leverage=3.0,
        execution_mode=ExecutionMode.APPROVAL
    )
    cb = CircuitBreaker(session_start_equity=1000.0, max_daily_loss_pct=3.0, max_consecutive_losses=3)
    rm = RiskManager(passport, cb)
    spec = ProductSpecification(symbol="BTCUSDT", contract_value=0.001, min_order_size=1.0, lot_size=1.0, tick_size=0.5)
    return rm, cb, spec, passport


# =====================================================================
# 1. Bullish EMA Condition and NO TRADE Explanations Tests
# =====================================================================

def test_bullish_ema_in_strategy_rationale_not_rejection_reasons():
    """
    When EMA 9 > EMA 21, the bullish bias must be reported under Strategy Rationale
    (signal.reasons / card.strategy_signals), and NEVER as a Trade Rejection Reason.
    """
    engine = SignalEngine(StrategyConfig(adx_threshold=25.0, rsi_long_min=50.0, rsi_long_max=70.0))
    candles = generate_candles_bullish_low_adx(count=60)
    signal = engine.evaluate(candles)

    # If NO_TRADE was chosen due to low ADX or RSI
    if signal.direction == TradeDirection.NO_TRADE:
        # Bullish trend structure must be in reasons (Strategy Rationale)
        assert any("bullish" in r.lower() for r in signal.reasons), "Bullish observation must be in Strategy Rationale"
        
        # Bullish trend structure must NEVER be in no_trade_reasons (Trade Rejection Reasons)
        for rejection in signal.no_trade_reasons:
            assert "bullish bias" not in rejection.lower(), f"Bullish bias was incorrectly placed in rejection reasons: {rejection}"
            assert "ema 9 is above ema 21" not in rejection.lower(), f"Bullish EMA was incorrectly placed in rejection reasons: {rejection}"

        # Rejection reasons must specify genuine unfulfilled criteria (e.g. ADX, RSI, or spread)
        assert len(signal.no_trade_reasons) > 0
        assert any(
            "adx" in r.lower() or "rsi" in r.lower() or "spread" in r.lower() or "ranging" in r.lower() or "whipsaw" in r.lower()
            for r in signal.no_trade_reasons
        )


def test_decision_card_separates_rationale_from_rejection_reasons(risk_environment):
    """
    Verify that PreTradeDecisionCard preserves strategy_signals (Rationale)
    and rejection_reasons (Trade Rejection Reasons) separately.
    """
    rm, cb, spec, passport = risk_environment
    signal = StrategySignal(
        direction=TradeDirection.NO_TRADE,
        entry_price=67500.0,
        stop_loss=0.0,
        take_profit=0.0,
        stop_distance=0.0,
        target_distance=0.0,
        reward_to_risk_ratio=0.0,
        regime=MarketRegime.RANGING,
        reasons=[
            "Bullish trend structure: EMA 9 (67520.00) is above EMA 21 (67480.00)",
            "Momentum snapshot: RSI is 46.2",
            "Trend strength snapshot: ADX is 16.4 (+DI: 18.2, -DI: 15.1)"
        ],
        no_trade_reasons=[
            "Insufficient trend strength: ADX (16.4) is below trend threshold 22.0",
            "RSI filter unfulfilled: RSI (46.2) is outside required long entry bounds (48.0–70.0)"
        ],
        indicator_snapshot={"close": 67500.0, "rsi": 46.2, "adx": 16.4}
    )
    balance = AccountBalance(asset="USDT", available_balance=0.0, total_balance=0.0, is_mock=False)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        data_timestamp=datetime.now(timezone.utc)
    )

    assert card.final_decision == DecisionStatus.NO_TRADE
    # Strategy signals contains the bullish observation
    assert any("bullish" in s.lower() for s in card.strategy_signals)

    # Rejection reasons contains the actual reasons (ADX, RSI, unfunded balance)
    assert any("adx" in r.lower() for r in card.rejection_reasons)
    assert any("rsi" in r.lower() for r in card.rejection_reasons)
    assert any("unfunded" in r.lower() or "0.00" in r.lower() for r in card.rejection_reasons)

    # Bullish EMA is NOT in rejection reasons
    for r in card.rejection_reasons:
        assert "bullish bias" not in r.lower()
        assert "is above ema 21" not in r.lower()


# =====================================================================
# 2. Genuine Risk Rejections Tests
# =====================================================================

def test_genuine_risk_rejection_insufficient_balance(risk_environment):
    """Real testnet account with 0 balance must reject trade setup with clear explanation."""
    rm, cb, spec, passport = risk_environment
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=67000.0,
        stop_loss=66500.0,
        take_profit=68000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover", "RSI confirms momentum", "ADX strong"],
        no_trade_reasons=[],
        indicator_snapshot={"close": 67000.0}
    )
    # Live unfunded account (0 USDT, is_mock=False)
    balance = AccountBalance(asset="USDT", available_balance=0.0, total_balance=0.0, is_mock=False)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        data_timestamp=datetime.now(timezone.utc)
    )

    assert card.final_decision == DecisionStatus.REJECTED
    assert any("unfunded" in r.lower() or "0.00" in r.lower() or "exceeds available balance" in r.lower() for r in card.rejection_reasons)


def test_genuine_risk_rejection_circuit_breaker(risk_environment):
    """Tripped circuit breaker must block trade and document trip reason."""
    rm, cb, spec, passport = risk_environment
    # Drawdown 100 USDT (10% > 3% threshold) trips circuit breaker
    cb.update_equity(current_equity=900.0)
    assert cb.is_tripped is True
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=67000.0,
        stop_loss=66500.0,
        take_profit=68000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover"],
        no_trade_reasons=[],
        indicator_snapshot={"close": 67000.0}
    )
    balance = AccountBalance(asset="USDT", available_balance=5000.0, total_balance=5000.0, is_mock=True)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        data_timestamp=datetime.now(timezone.utc)
    )

    assert card.final_decision == DecisionStatus.REJECTED
    assert any("circuit breaker" in r.lower() for r in card.rejection_reasons)


# =====================================================================
# 3. ML Prediction versus Final Decision Tests
# =====================================================================

def test_ml_prediction_cannot_override_no_trade_strategy(risk_environment):
    """
    Even if ML model predicts UP with 99.9% confidence,
    if strategy returned NO_TRADE, the final decision MUST be NO_TRADE.
    ML can never force an entry without strategy confirmation.
    """
    rm, cb, spec, passport = risk_environment
    signal = StrategySignal(
        direction=TradeDirection.NO_TRADE,
        entry_price=67000.0,
        stop_loss=0.0,
        take_profit=0.0,
        stop_distance=0.0,
        target_distance=0.0,
        reward_to_risk_ratio=0.0,
        regime=MarketRegime.RANGING,
        reasons=["RSI is neutral"],
        no_trade_reasons=["Insufficient trend strength: ADX is below threshold"],
        indicator_snapshot={}
    )
    balance = AccountBalance(asset="USDT", available_balance=5000.0, total_balance=5000.0)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        ml_prediction="UP",
        ml_confidence=0.999,
        ml_status="READY",
        data_timestamp=datetime.now(timezone.utc)
    )

    assert card.final_decision == DecisionStatus.NO_TRADE
    assert card.ml_prediction == "UP"
    assert card.ml_confidence == 0.999
    assert card.proposed_direction == TradeDirection.NO_TRADE


def test_ml_prediction_cannot_bypass_risk_checks(risk_environment):
    """
    Even if ML model predicts UP with 95% confidence and strategy is LONG,
    if risk checks fail (e.g. zero balance or stale data), trade MUST be REJECTED.
    """
    rm, cb, spec, passport = risk_environment
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=67000.0,
        stop_loss=66500.0,
        take_profit=68000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover"],
        no_trade_reasons=[],
        indicator_snapshot={"close": 67000.0}
    )
    # Stale data > 120s
    stale_ts = datetime.now(timezone.utc) - timedelta(seconds=200)
    balance = AccountBalance(asset="USDT", available_balance=5000.0, total_balance=5000.0)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        ml_prediction="UP",
        ml_confidence=0.95,
        ml_status="READY",
        data_timestamp=stale_ts
    )

    assert card.final_decision == DecisionStatus.REJECTED
    assert any("stale" in r.lower() for r in card.rejection_reasons)


# =====================================================================
# 4. Zero-Balance Order Blocking Tests
# =====================================================================

def test_order_approval_blocked_when_balance_zero():
    """
    When account USDT available balance is zero on live testnet,
    bot.approve_trade must strictly refuse execution and return a descriptive blocked message.
    """
    import asyncio
    bot = BotEngine()
    
    # Create a dummy decision in WAITING_FOR_APPROVAL
    spec = ProductSpecification(symbol="BTCUSDT", contract_value=0.001, min_order_size=1.0, lot_size=1.0, tick_size=0.5)
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=67000.0,
        stop_loss=66500.0,
        take_profit=68000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover"],
        no_trade_reasons=[],
        indicator_snapshot={"close": 67000.0}
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

    # Now simulate exchange returning verified 0.0 balance (is_mock=False)
    async def fake_get_balance(asset="USDT"):
        return AccountBalance(asset="USDT", available_balance=0.0, total_balance=0.0, is_mock=False)

    bot.exchange.get_balance = fake_get_balance

    result = asyncio.run(bot.approve_trade(card.id))
    assert result["success"] is False
    assert "ORDER BLOCKED" in result["message"]
    assert "Insufficient Testnet Balance" in result["message"]
