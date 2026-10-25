"""
Unit Tests for Delta Exchange Testnet Integration.
Covers:
- Request signing correctness (HMAC-SHA256 verification)
- Environment and production URL validation
- Demo-Safe fallback when credentials are not configured
- Redaction of credentials in status and log outputs
- Mocked authentication success and 401/429 failure handling
- Network timeout and connectivity failure handling
- Verification that connection checks are strictly read-only and never place orders
"""

import pytest
import hmac
import hashlib
import time
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.config import Settings
from app.services.exchange.delta_client import DeltaExchangeClient
from app.schemas.order import OrderSide, OrderType


@pytest.fixture
def dummy_client():
    return DeltaExchangeClient(
        api_key="test_dummy_key_12345",
        api_secret="test_dummy_secret_67890",
        base_url="https://cdn-ind.testnet.deltaex.org"
    )


@pytest.fixture
def unauthenticated_client():
    return DeltaExchangeClient(
        api_key="",
        api_secret="",
        base_url="https://cdn-ind.testnet.deltaex.org"
    )


def test_missing_credentials_enters_demo_mode(unauthenticated_client):
    assert unauthenticated_client.is_authenticated is False
    assert unauthenticated_client.redacted_api_key == "NOT_CONFIGURED"


@pytest.mark.anyio
async def test_connection_check_in_demo_mode(unauthenticated_client):
    status = await unauthenticated_client.check_connection()
    assert status["connected"] is False
    assert status["authenticated"] is False
    assert status["mode"] == "DEMO_SAFE_SIMULATION"
    assert "backend/.env" in status["actionable_advice"]
    # Secrets must never appear in response
    assert "test_dummy" not in str(status)


def test_request_signing_correctness(dummy_client):
    """
    Verifies that generate_signature strictly produces HMAC-SHA256 of:
    method.upper() + timestamp + path + query_string + payload
    """
    method = "GET"
    path = "/v2/wallet/balances"
    query = ""
    payload = ""
    timestamp = "1729850000"

    expected_message = f"GET1729850000/v2/wallet/balances"
    expected_sig = hmac.new(
        b"test_dummy_secret_67890",
        expected_message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    signature, ts = dummy_client.generate_signature(
        method=method,
        path=path,
        query_string=query,
        payload=payload,
        timestamp=timestamp
    )

    assert ts == timestamp
    assert signature == expected_sig


def test_request_signing_with_query_and_payload(dummy_client):
    method = "POST"
    path = "/v2/orders"
    query = "?symbol=BTCUSDT"
    payload = '{"size":1}'
    timestamp = "1729851111"

    expected_message = f"POST1729851111/v2/orders?symbol=BTCUSDT" + '{"size":1}'
    expected_sig = hmac.new(
        b"test_dummy_secret_67890",
        expected_message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    signature, ts = dummy_client.generate_signature(
        method=method,
        path=path,
        query_string=query,
        payload=payload,
        timestamp=timestamp
    )

    assert signature == expected_sig


def test_credential_redaction(dummy_client):
    redacted = dummy_client.redacted_api_key
    assert redacted.startswith("test")
    assert redacted.endswith("2345")
    assert "dummy_key" not in redacted
    # Secret must never be accessible through redaction property
    assert dummy_client.api_secret not in redacted


@pytest.mark.anyio
async def test_connection_verification_auth_success(dummy_client):
    mock_products = httpx.Response(
        status_code=200,
        json={"result": [{"id": 1, "symbol": "BTCUSDT"}]},
        request=httpx.Request("GET", "https://cdn-ind.testnet.deltaex.org/v2/products")
    )
    mock_balances = httpx.Response(
        status_code=200,
        json={"result": [{"asset_symbol": "USDT", "available_balance": "5000.0", "balance": "5000.0"}]},
        request=httpx.Request("GET", "https://cdn-ind.testnet.deltaex.org/v2/wallet/balances")
    )

    with patch.object(dummy_client.client, "get", side_effect=[mock_products, mock_balances]) as mock_get:
        status = await dummy_client.check_connection()
        assert status["connected"] is True
        assert status["authenticated"] is True
        assert status["mode"] == "LIVE_TESTNET"
        assert status["instruments_count"] == 1
        assert status["balance"]["available_balance"] == 5000.0
        assert mock_get.call_count == 2


@pytest.mark.anyio
async def test_connection_verification_auth_failure_401(dummy_client):
    mock_products = httpx.Response(
        status_code=200,
        json={"result": [{"id": 1, "symbol": "BTCUSDT"}]},
        request=httpx.Request("GET", "https://cdn-ind.testnet.deltaex.org/v2/products")
    )
    mock_auth_fail = httpx.Response(
        status_code=401,
        text='{"error":{"code":"invalid_api_key","message":"Invalid API key or signature"}}',
        request=httpx.Request("GET", "https://cdn-ind.testnet.deltaex.org/v2/wallet/balances")
    )

    with patch.object(dummy_client.client, "get", side_effect=[mock_products, mock_auth_fail]):
        status = await dummy_client.check_connection()
        assert status["connected"] is True
        assert status["authenticated"] is False
        assert status["mode"] == "AUTHENTICATION_FAILED"
        assert "Authentication rejected by Delta Testnet" in status["actionable_advice"]


@pytest.mark.anyio
async def test_connection_verification_rate_limited_429(dummy_client):
    mock_products = httpx.Response(
        status_code=200,
        json={"result": []},
        request=httpx.Request("GET", "https://cdn-ind.testnet.deltaex.org/v2/products")
    )
    mock_rate_limit = httpx.Response(
        status_code=429,
        text="Rate limit exceeded",
        request=httpx.Request("GET", "https://cdn-ind.testnet.deltaex.org/v2/wallet/balances")
    )

    with patch.object(dummy_client.client, "get", side_effect=[mock_products, mock_rate_limit]):
        status = await dummy_client.check_connection()
        assert status["mode"] == "RATE_LIMITED"


@pytest.mark.anyio
async def test_connection_timeout_handling(dummy_client):
    with patch.object(dummy_client.client, "get", side_effect=httpx.TimeoutException("Read timed out")):
        status = await dummy_client.check_connection()
        assert status["connected"] is False
        assert status["authenticated"] is False
        assert status["mode"] == "CONNECTIVITY_FAILED"


@pytest.mark.anyio
async def test_connection_check_never_submits_trades(dummy_client):
    """Guarantees that check_connection() never invokes order placement."""
    with patch.object(dummy_client, "place_order") as mock_place_order:
        with patch.object(dummy_client.client, "post") as mock_post:
            await dummy_client.check_connection()
            assert mock_place_order.call_count == 0
            assert mock_post.call_count == 0


def test_environment_validation_rejects_production():
    with pytest.raises(ValueError, match="Production environment .* is strictly prohibited"):
        Settings(DELTA_ENV="production")

    with pytest.raises(ValueError, match="Invalid DELTA_ENV"):
        Settings(DELTA_ENV="arbitrary_env")
