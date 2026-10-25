"""
Unit Tests for Circuit Breaker and Production Safety Blockers.
"""

import pytest
from app.services.risk.circuit_breaker import CircuitBreaker
from app.config import Settings, ABSOLUTE_MAX_RISK_PER_TRADE_PCT, ABSOLUTE_MAX_DAILY_LOSS_PCT


def test_circuit_breaker_daily_drawdown_trip():
    cb = CircuitBreaker(session_start_equity=1000.0, max_daily_loss_pct=2.0, max_consecutive_losses=3)
    assert cb.is_tripped is False

    # Small loss 10 USDT (1%) -> Should remain normal
    allowed, _ = cb.update_equity(current_equity=990.0)
    assert allowed is True
    assert cb.is_tripped is False

    # Loss reaches 25 USDT (2.5% > 2.0% threshold) -> Must trip!
    allowed, reason = cb.update_equity(current_equity=975.0)
    assert allowed is False
    assert cb.is_tripped is True
    assert "Daily drawdown limit breached" in reason


def test_circuit_breaker_consecutive_losses_trip():
    cb = CircuitBreaker(session_start_equity=1000.0, max_daily_loss_pct=5.0, max_consecutive_losses=3)

    # 1st loss
    cb.record_trade_result(-2.0)
    assert cb.consecutive_losses == 1
    assert cb.is_tripped is False

    # 2nd loss
    cb.record_trade_result(-2.0)
    assert cb.consecutive_losses == 2
    assert cb.is_tripped is False

    # 3rd loss -> Reaches threshold 3 -> Trips!
    cb.record_trade_result(-2.0)
    assert cb.consecutive_losses == 3
    assert cb.is_tripped is True
    assert "Consecutive loss streak" in cb.trip_reason


def test_circuit_breaker_reset():
    cb = CircuitBreaker(session_start_equity=1000.0, max_daily_loss_pct=2.0, max_consecutive_losses=3)
    cb.record_trade_result(-5.0)
    cb.record_trade_result(-5.0)
    cb.record_trade_result(-5.0)
    assert cb.is_tripped is True

    # Reset
    cb.reset(new_start_equity=985.0)
    assert cb.is_tripped is False
    assert cb.consecutive_losses == 0
    assert cb.session_start_equity == 985.0


def test_environment_safety_blocks_production_endpoints():
    """Confirms production URLs are strictly rejected at startup."""
    with pytest.raises(ValueError, match="Production endpoint .* is strictly prohibited"):
        Settings(
            DELTA_REST_BASE_URL="https://cdn.delta.exchange",
            DELTA_API_KEY="",
            DELTA_API_SECRET=""
        )

    with pytest.raises(ValueError, match="Production endpoint .* is strictly prohibited"):
        Settings(
            DELTA_REST_BASE_URL="https://api.delta.exchange",
            DELTA_API_KEY="",
            DELTA_API_SECRET=""
        )

    with pytest.raises(ValueError, match="CRITICAL SAFETY VIOLATION"):
        Settings(
            DELTA_WS_PUBLIC_URL="wss://socket.delta.exchange",
            DELTA_API_KEY="",
            DELTA_API_SECRET=""
        )


def test_environment_safety_allows_official_testnet():
    s = Settings(
        DELTA_REST_BASE_URL="https://cdn-ind.testnet.deltaex.org",
        DELTA_WS_PUBLIC_URL="wss://socket-ind-pub.testnet.deltaex.org",
        DELTA_WS_PRIVATE_URL="wss://socket-ind.testnet.deltaex.org"
    )
    assert "testnet" in s.DELTA_REST_BASE_URL
