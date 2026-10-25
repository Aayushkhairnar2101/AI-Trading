"""
Unit Tests for Live Market Data Pipeline, Ticker & Candle Synchronization,
UDF Parsing, Timestamp Integrity, Stale Feed Detection, and Safety Guardrails.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import pandas as pd
import numpy as np

from app.services.exchange.delta_client import DeltaExchangeClient
from app.services.execution.bot_engine import BotEngine
from app.schemas.decision import TradeDirection, MarketRegime, PreTradeDecisionCard, DecisionStatus
from app.schemas.strategy import StrategyConfig
from app.schemas.order import AccountBalance
from app.services.strategy.signal_engine import StrategySignal
from app.services.risk.position_sizer import ProductSpecification
from app.services.storage.database import db


@pytest.fixture
def testnet_client():
    return DeltaExchangeClient(
        api_key="xtst_key_live_testnet",
        api_secret="xtst_secret_live_testnet",
        base_url="https://cdn-ind.testnet.deltaex.org"
    )


# =====================================================================
# 1. Symbol and Resolution Mapping Tests
# =====================================================================

def test_symbol_mapping_to_exchange_contract():
    """BTCUSDT and BTC_USDT must map to Delta Exchange contract symbol BTCUSD."""
    assert DeltaExchangeClient.map_exchange_symbol("BTCUSDT") == "BTCUSD"
    assert DeltaExchangeClient.map_exchange_symbol("BTC_USDT") == "BTCUSD"
    assert DeltaExchangeClient.map_exchange_symbol("btcusdt") == "BTCUSD"
    assert DeltaExchangeClient.map_exchange_symbol("BTCUSD") == "BTCUSD"
    assert DeltaExchangeClient.map_exchange_symbol("ETHUSDT") == "ETHUSD"
    assert DeltaExchangeClient.map_exchange_symbol("SOLUSDT") == "SOLUSD"


def test_resolution_mapping_for_delta_exchange():
    """Delta Exchange requires numeric string format for resolutions ('5', '1', '15', '60', 'D')."""
    assert DeltaExchangeClient.map_resolution("5m") == "5"
    assert DeltaExchangeClient.map_resolution("1m") == "1"
    assert DeltaExchangeClient.map_resolution("15m") == "15"
    assert DeltaExchangeClient.map_resolution("30m") == "30"
    assert DeltaExchangeClient.map_resolution("1h") == "60"
    assert DeltaExchangeClient.map_resolution("60m") == "60"
    assert DeltaExchangeClient.map_resolution("1d") == "D"
    assert DeltaExchangeClient.map_resolution("5") == "5"

    assert DeltaExchangeClient.get_resolution_seconds("5m") == 300
    assert DeltaExchangeClient.get_resolution_seconds("1m") == 60
    assert DeltaExchangeClient.get_resolution_seconds("15m") == 900
    assert DeltaExchangeClient.get_resolution_seconds("1h") == 3600


# =====================================================================
# 2. Fresh Ticker Parsing Tests
# =====================================================================

def test_fresh_ticker_parsing_from_exchange_response(testnet_client):
    """Ticker parser must extract mark_price, quotes (best_bid, best_ask), and report live testnet source."""
    fake_payload = {
        "success": True,
        "result": {
            "symbol": "BTCUSD",
            "mark_price": "80384.50",
            "close": 80384.0,
            "volume": 3412.5,
            "quotes": {
                "best_bid": "80381.0",
                "best_ask": "80385.0"
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_payload

    testnet_client.client.get = AsyncMock(return_value=mock_resp)

    ticker = asyncio.run(testnet_client.get_ticker("BTCUSDT"))

    assert ticker["symbol"] == "BTCUSDT"
    assert ticker["exchange_symbol"] == "BTCUSD"
    assert ticker["mark_price"] == 80384.50
    assert ticker["bid"] == 80381.0
    assert ticker["ask"] == 80385.0
    assert ticker["is_mock"] is False
    assert ticker["data_source"] == "DELTA_TESTNET_LIVE"
    assert ticker["spread_pct"] > 0
    assert testnet_client.is_feed_live is True
    assert testnet_client.last_ticker_time is not None


# =====================================================================
# 3. UDF Candle Parsing, Ordering, and Timestamps Tests
# =====================================================================

def test_udf_candle_parsing_and_strictly_ascending_timestamps(testnet_client):
    """TradingView UDF dictionary {t, o, h, l, c, v} must be parsed into strictly ascending integer seconds."""
    base_ts = 1792920000
    times = [base_ts + (i * 300) for i in range(40)]
    # Intentionally insert one duplicate and unsorted entry to test deduplication & sorting
    unsorted_times = list(reversed(times)) + [times[5]]

    fake_udf = {
        "success": True,
        "result": {
            "s": "ok",
            "t": unsorted_times,
            "o": [80000.0 + i for i in range(len(unsorted_times))],
            "h": [80100.0 + i for i in range(len(unsorted_times))],
            "l": [79900.0 + i for i in range(len(unsorted_times))],
            "c": [80050.0 + i for i in range(len(unsorted_times))],
            "v": [10.0 + i for i in range(len(unsorted_times))]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_udf
    testnet_client.client.get = AsyncMock(return_value=mock_resp)

    df = asyncio.run(testnet_client.get_candles("BTCUSDT", resolution="5m", limit=35))

    assert len(df) == 35
    t_list = list(df["time"])
    # Must be strictly ascending
    assert all(t_list[i] < t_list[i + 1] for i in range(len(t_list) - 1))
    # Must be integer seconds
    assert all(isinstance(x, (int, np.integer)) for x in t_list)
    # No duplicates
    assert len(t_list) == len(set(t_list))


def test_current_candle_update_without_duplicating_timestamp(testnet_client):
    """Within a 5m interval, updating current candle with live ticker must update existing bar without duplicate timestamp."""
    step = 300
    now_ts = int(time.time())
    current_bar_ts = now_ts - (now_ts % step)

    # 35 historical candles ending at current_bar_ts
    times = [current_bar_ts - ((34 - i) * step) for i in range(35)]
    fake_udf = {
        "success": True,
        "result": {
            "s": "ok",
            "t": times,
            "o": [80000.0] * 35,
            "h": [80050.0] * 35,
            "l": [79950.0] * 35,
            "c": [80020.0] * 35,
            "v": [100.0] * 35
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_udf
    testnet_client.client.get = AsyncMock(return_value=mock_resp)

    # Ticker with a new high price in current bar
    testnet_client._cached_ticker = {
        "mark_price": 80120.0,
        "symbol": "BTCUSDT"
    }

    df = asyncio.run(testnet_client.get_candles("BTCUSDT", resolution="5m", limit=35))

    # Bar count remains 35 (no duplicate)
    assert len(df) == 35
    # Timestamp of last bar equals current_bar_ts
    assert df.iloc[-1]["time"] == current_bar_ts
    # High is updated with ticker_mark
    assert df.iloc[-1]["high"] == 80120.0
    # Close is updated with ticker_mark
    assert df.iloc[-1]["close"] == 80120.0


# =====================================================================
# 4. Stale Feed Detection & Order Approval Blocking Tests
# =====================================================================

def test_stale_feed_status_detection(testnet_client):
    """When last update is > 120s old, feed status must report STALE_OR_DISCONNECTED."""
    # Never updated
    status = testnet_client.get_feed_status()
    assert status["status"] == "STALE_OR_DISCONNECTED"
    assert status["is_live"] is False

    # Fresh update 5s ago
    testnet_client.last_ticker_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    testnet_client.last_candle_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    status_fresh = testnet_client.get_feed_status()
    assert status_fresh["status"] == "LIVE_HEALTHY"
    assert status_fresh["is_live"] is True

    # Stale update 150s ago
    testnet_client.last_ticker_time = datetime.now(timezone.utc) - timedelta(seconds=150)
    testnet_client.last_candle_time = datetime.now(timezone.utc) - timedelta(seconds=150)
    status_stale = testnet_client.get_feed_status()
    assert status_stale["status"] == "STALE_OR_DISCONNECTED"
    assert status_stale["is_live"] is False


def test_blocking_order_approval_when_feed_is_stale():
    """bot.approve_trade must strictly block execution if live market data feed is stale."""
    bot = BotEngine()
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
    mock_bal = AccountBalance(asset="USDT", available_balance=2000.0, total_balance=2000.0, is_mock=True)
    card = bot.risk_manager.evaluate_opportunity(
        signal=signal,
        product_spec=spec,
        account_balance=mock_bal,
        open_positions=[],
        data_timestamp=datetime.now(timezone.utc)
    )
    db.save_decision(card)

    # Force client to appear authenticated with stale market data feed
    bot.exchange.is_authenticated = True
    bot.exchange.last_ticker_time = datetime.now(timezone.utc) - timedelta(seconds=200)
    bot.exchange.last_candle_time = datetime.now(timezone.utc) - timedelta(seconds=200)

    async def fake_get_balance(asset="USDT"):
        return AccountBalance(asset="USDT", available_balance=5000.0, total_balance=5000.0, is_mock=False)
    bot.exchange.get_balance = fake_get_balance

    result = asyncio.run(bot.approve_trade(card.id))
    assert result["success"] is False
    assert "ORDER BLOCKED" in result["message"]
    assert "Stale Market Data Feed" in result["message"]
