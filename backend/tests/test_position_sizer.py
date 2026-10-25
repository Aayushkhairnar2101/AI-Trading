"""
Unit Tests for Position Sizer: Capital Allocation, Monetary Risk Budget, and Leverage Ceilings.
"""

import pytest
from app.services.risk.position_sizer import PositionSizer, ProductSpecification


@pytest.fixture
def btc_spec():
    return ProductSpecification(
        symbol="BTCUSDT",
        contract_value=0.001,
        min_order_size=1.0,
        lot_size=1.0,
        tick_size=0.5,
        settlement_asset="USDT",
        max_exchange_leverage=100.0
    )


def test_position_sizing_standard(btc_spec):
    sizer = PositionSizer()
    # Allocated capital = 1,000 USDT, Risk = 0.5% => Budget = 5 USDT
    # Entry = 60,000, Stop Loss = 59,500 => Stop distance = 500
    # Contract value = 0.001 => Risk per contract = 500 * 0.001 = 0.5 USDT
    # Quantity = 5 / 0.5 = 10 contracts
    res = sizer.calculate_position(
        allocated_capital=1000.0,
        risk_per_trade_pct=0.5,
        entry_price=60000.0,
        stop_loss=59500.0,
        take_profit=61000.0,
        product=btc_spec,
        max_leverage_ceiling=2.0
    )
    assert res.is_valid is True
    assert res.risk_budget_monetary == 5.0
    assert res.calculated_quantity == 10.0
    # Notional = 10 * 0.001 * 60,000 = 600 USDT
    assert res.notional_exposure == 600.0
    # Margin at 2x leverage = 300 USDT
    assert res.estimated_margin == 300.0
    assert res.effective_leverage == 0.6  # 600 / 1000
    assert res.reward_to_risk == 2.0       # (61000 - 60000) / 500 = 2.0


def test_position_sizing_below_minimum_rejected(btc_spec):
    sizer = PositionSizer()
    # Tiny capital 10 USDT, Risk 0.5% => Budget = 0.05 USDT
    # 0.05 / 0.5 = 0.1 contracts < min_order_size 1.0 => Must be rejected!
    res = sizer.calculate_position(
        allocated_capital=10.0,
        risk_per_trade_pct=0.5,
        entry_price=60000.0,
        stop_loss=59500.0,
        take_profit=61000.0,
        product=btc_spec,
        max_leverage_ceiling=2.0
    )
    assert res.is_valid is False
    assert "below exchange minimum order size" in res.rejection_reason


def test_leverage_ceiling_cap(btc_spec):
    sizer = PositionSizer()
    # Capital = 1,000 USDT, Risk = 2.0% => Budget = 20 USDT
    # Tiny stop distance of 10 points => Risk per contract = 10 * 0.001 = 0.01 USDT
    # Raw contracts = 20 / 0.01 = 2000 contracts!
    # 2000 * 0.001 * 60,000 = 120,000 notional (120x leverage!)
    # But user leverage ceiling is 2.0x (max allowed notional = 2,000 USDT)
    res = sizer.calculate_position(
        allocated_capital=1000.0,
        risk_per_trade_pct=2.0,
        entry_price=60000.0,
        stop_loss=59990.0,
        take_profit=60030.0,
        product=btc_spec,
        max_leverage_ceiling=2.0
    )
    assert res.is_valid is True
    # Notional must not exceed 1000 * 2.0 = 2,000
    assert res.notional_exposure <= 2000.0
    assert res.effective_leverage <= 2.0
