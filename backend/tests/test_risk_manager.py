"""
Unit Tests for Central Risk Manager: Multi-Factor Rule Verification and Rejections.
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.schemas.passport import RiskPassportConfig, ExecutionMode
from app.schemas.decision import TradeDirection, MarketRegime, DecisionStatus
from app.schemas.order import AccountBalance, PositionInfo
from app.services.strategy.signal_engine import StrategySignal
from app.services.risk.risk_manager import RiskManager
from app.services.risk.circuit_breaker import CircuitBreaker
from app.services.risk.position_sizer import ProductSpecification


@pytest.fixture
def risk_setup():
    passport = RiskPassportConfig(
        allocated_capital=1000.0,
        risk_per_trade_pct=0.5,
        max_daily_loss_pct=2.0,
        max_open_positions=1,
        max_leverage=2.0,
        execution_mode=ExecutionMode.APPROVAL
    )
    cb = CircuitBreaker(session_start_equity=1000.0, max_daily_loss_pct=2.0, max_consecutive_losses=3)
    rm = RiskManager(passport, cb)
    spec = ProductSpecification(symbol="BTCUSDT", contract_value=0.001, min_order_size=1.0, lot_size=1.0, tick_size=0.5)
    return rm, cb, spec


def test_valid_long_opportunity_approved(risk_setup):
    rm, cb, spec = risk_setup
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=60000.0,
        stop_loss=59500.0,
        take_profit=61000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish EMA crossover", "RSI 58 confirmed"],
        no_trade_reasons=[],
        indicator_snapshot={"close": 60000.0}
    )
    balance = AccountBalance(asset="USDT", available_balance=2500.0, total_balance=2500.0)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        data_timestamp=datetime.now(timezone.utc)
    )

    assert card.final_decision == DecisionStatus.WAITING_FOR_APPROVAL
    assert all(chk.passed for chk in card.risk_checks)
    assert card.calculated_quantity > 0


def test_insufficient_balance_rejected(risk_setup):
    rm, cb, spec = risk_setup
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=60000.0,
        stop_loss=59500.0,
        take_profit=61000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover"],
        no_trade_reasons=[],
        indicator_snapshot={}
    )
    # Available balance 200 USDT < allocated 1,000 USDT (not mock)
    balance = AccountBalance(asset="USDT", available_balance=200.0, total_balance=200.0, is_mock=False)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        data_timestamp=datetime.now(timezone.utc)
    )

    assert card.final_decision == DecisionStatus.REJECTED
    assert any("exceeds available balance" in r.lower() or "allocated capital" in r.lower() for r in card.rejection_reasons)


def test_duplicate_position_rejected(risk_setup):
    rm, cb, spec = risk_setup
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=60000.0,
        stop_loss=59500.0,
        take_profit=61000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover"],
        no_trade_reasons=[],
        indicator_snapshot={}
    )
    balance = AccountBalance(asset="USDT", available_balance=5000.0, total_balance=5000.0)
    existing_pos = [PositionInfo(symbol="BTCUSDT", size=10.0, entry_price=59800.0, mark_price=60000.0, bot_managed=True)]

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=existing_pos,
        data_timestamp=datetime.now(timezone.utc)
    )

    assert card.final_decision == DecisionStatus.REJECTED
    assert any("duplicate" in r.lower() for r in card.rejection_reasons)


def test_stale_data_rejected(risk_setup):
    rm, cb, spec = risk_setup
    signal = StrategySignal(
        direction=TradeDirection.LONG,
        entry_price=60000.0,
        stop_loss=59500.0,
        take_profit=61000.0,
        stop_distance=500.0,
        target_distance=1000.0,
        reward_to_risk_ratio=2.0,
        regime=MarketRegime.TRENDING_BULLISH,
        reasons=["Bullish crossover"],
        no_trade_reasons=[],
        indicator_snapshot={}
    )
    balance = AccountBalance(asset="USDT", available_balance=5000.0, total_balance=5000.0)
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=300)

    card = rm.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=balance,
        open_positions=[],
        data_timestamp=stale_time
    )

    assert card.final_decision == DecisionStatus.REJECTED
    assert any("stale" in r.lower() for r in card.rejection_reasons)
