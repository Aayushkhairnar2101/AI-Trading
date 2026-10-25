"""
Status, Health, and Connectivity Diagnostic Endpoints.
All responses are sanitized — credentials and signatures are never returned.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from app.config import settings
from app.services.execution.bot_engine import bot

router = APIRouter(prefix="/status", tags=["Status & Health"])


@router.get("/health")
async def get_health():
    """Basic health check — always responds instantly, never makes external calls."""
    return {
        "status": "healthy",
        "system": "RiskPilot AI",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.DELTA_ENV,
        "is_testnet": "testnet" in settings.DELTA_REST_BASE_URL.lower(),
        "credentials_configured": settings.has_credentials,
        "bot_running": bot.is_running,
        "bot_paused": bot.is_paused,
        "analysis_running": bot.is_running and not bot.is_paused,
        "analysis_status": "ACTIVE" if (bot.is_running and not bot.is_paused) else ("PAUSED" if bot.is_paused else "IDLE"),
        "execution_mode": bot.passport.execution_mode.value,
        "orders_execution_mode": bot.passport.execution_mode.value,
        "circuit_breaker_tripped": bot.circuit_breaker.is_tripped,
        "last_evaluation_time": bot.last_evaluation_time.isoformat() if bot.last_evaluation_time else None,
    }


@router.get("/connectivity")
async def get_connectivity():
    """
    Live Testnet connectivity verification — read-only, never places orders.

    Returns a sanitized status report including:
    - Whether credentials are configured (configured/not_configured, no values)
    - Which environment and endpoint are targeted
    - Whether authentication with Delta Testnet succeeded
    - Actionable advice if authentication fails
    - USDT balance (real if authenticated, absent if not)

    Never returns API keys, secrets, signatures, or raw auth headers.
    """
    result = await bot.exchange.check_connection()
    # Ensure no raw credential fields leak through
    result.pop("api_key", None)
    result.pop("api_secret", None)
    result.pop("signature", None)
    return result


@router.get("/account")
async def get_account_status():
    """
    Account funding status — separate from API connection status.

    Returns:
    - api_connected: whether authentication with Delta Testnet succeeded
    - account_funded: whether the testnet account has positive USDT balance
    - balance: verified real balance from exchange (or mock in demo mode)
    - funding_warning: human-readable warning when balance is zero
    - mode: LIVE_TESTNET | DEMO_SAFE_SIMULATION | AUTHENTICATION_FAILED

    This endpoint explicitly distinguishes between:
    - A successfully authenticated API connection (api_connected=True)
    - A funded trading account (account_funded=True)

    Both must be True before order submission is enabled.
    Never returns API keys or secrets.
    """
    conn = await bot.exchange.check_connection()
    conn.pop("api_key", None)
    conn.pop("api_secret", None)
    conn.pop("signature", None)

    api_connected = conn.get("authenticated", False)
    mode = conn.get("mode", "UNKNOWN")
    conn_balance = conn.get("balance", {})
    balance_obj = await bot.exchange.get_balance(asset=bot.passport.settlement_asset)

    available = balance_obj.available_balance if balance_obj else 0.0
    is_mock = balance_obj.is_mock if balance_obj else True
    account_funded = available > 0.0

    # Determine funding warning message
    if not api_connected:
        funding_warning = None  # Cannot determine funding without connection
    elif is_mock:
        funding_warning = "DEMO_SIMULATION_MODE: Balance is simulated. No real funds or testnet funds are active."
        account_funded = False
    elif not account_funded:
        funding_warning = (
            "Testnet account connected but balance is zero USDT. "
            "Order submission is disabled. "
            "Fund your testnet account at https://demo.delta.exchange to enable trading."
        )
    else:
        funding_warning = None

    return {
        "api_connected": api_connected,
        "account_funded": account_funded,
        "orders_enabled": api_connected and account_funded and not is_mock,
        "environment": settings.DELTA_ENV,
        "base_url": settings.DELTA_REST_BASE_URL,
        "mode": mode,
        "balance": {
            "asset": balance_obj.asset if balance_obj else "USDT",
            "available_balance": available,
            "total_balance": balance_obj.total_balance if balance_obj else 0.0,
            "is_mock": is_mock,
        },
        "funding_warning": funding_warning,
        "key_status": conn.get("key_status", "UNKNOWN"),
        "check_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/diagnostic")
async def get_diagnostic():
    """
    Safe credential-loading and configuration diagnostic.
    Reports configuration status WITHOUT revealing credential values.
    Use this to verify that backend/.env is loaded correctly.
    """
    key_configured = settings.has_credentials
    key_len = len(settings.DELTA_API_KEY.strip())
    secret_len = len(settings.DELTA_API_SECRET.strip())

    # Classify credential state
    if key_len == 0 and secret_len == 0:
        credential_status = "BOTH_EMPTY — Demo/Simulation Mode active"
    elif key_len == 0:
        credential_status = "API_KEY_EMPTY — Secret is set but key is missing"
    elif secret_len == 0:
        credential_status = "API_SECRET_EMPTY — Key is set but secret is missing"
    elif key_len < 20:
        credential_status = "API_KEY_SUSPICIOUSLY_SHORT — May be truncated or incorrect"
    elif secret_len < 40:
        credential_status = "API_SECRET_SUSPICIOUSLY_SHORT — May be truncated or incorrect"
    else:
        credential_status = "BOTH_CONFIGURED"

    return {
        "diagnostic": "RiskPilot AI Configuration Check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "DELTA_ENV": settings.DELTA_ENV,
            "DELTA_REST_BASE_URL": settings.DELTA_REST_BASE_URL,
            "DELTA_WS_PUBLIC_URL": settings.DELTA_WS_PUBLIC_URL,
            "DELTA_WS_PRIVATE_URL": settings.DELTA_WS_PRIVATE_URL,
            "is_testnet_rest": "testnet" in settings.DELTA_REST_BASE_URL.lower(),
            "is_testnet_ws_pub": "testnet" in settings.DELTA_WS_PUBLIC_URL.lower(),
            "is_testnet_ws_priv": "testnet" in settings.DELTA_WS_PRIVATE_URL.lower(),
        },
        "credentials": {
            "status": credential_status,
            "api_key_configured": key_len > 0,
            "api_key_length": key_len,
            "api_secret_configured": secret_len > 0,
            "api_secret_length": secret_len,
            "source": "backend/.env (read via Pydantic BaseSettings)",
        },
        "authentication_advisory": (
            "Credentials are present — call GET /api/status/connectivity to test authentication."
            if key_configured else
            "No credentials configured. Running in Demo/Simulation Mode. "
            "To enable live testnet: create fresh India Testnet API keys at "
            "https://cdn-ind.testnet.deltaex.org and add them to backend/.env. "
            "NEVER paste credentials into AI chat, screenshots, or source code."
        ),
        "common_401_causes": [
            "API key was created in Global Testnet or Production instead of India Testnet",
            "API key was revoked, expired, or regenerated",
            "API key or secret contains leading/trailing whitespace in .env",
            "Credentials were previously exposed and have been revoked for security",
            "API key lacks Read permission",
            "System clock drift (timestamp must be within ±30s of exchange server time)",
        ],
        "invalid_api_key_note": (
            "HTTP 401 invalid_api_key from Delta means the key does not exist in the "
            "India Testnet account database — not a signing algorithm error. "
            "The signing implementation (HMAC-SHA256) is correct. "
            "The key itself is unknown to the exchange."
        ),
    }
