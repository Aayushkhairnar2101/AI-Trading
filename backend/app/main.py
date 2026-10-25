"""
RiskPilot AI — Personalized, Explainable Algorithmic Trading System
Main FastAPI Application Entrypoint.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.api.routes_status import router as status_router
from app.api.routes_market import router as market_router
from app.api.routes_passport import router as passport_router
from app.api.routes_strategy import router as strategy_router
from app.api.routes_bot import router as bot_router
from app.api.routes_analytics import router as analytics_router
from app.services.execution.bot_engine import bot

# ── Logging Configuration ─────────────────────────────────────────────────────
# Use INFO level by default to avoid accidentally exposing HTTP headers,
# signatures, or account data via httpx's DEBUG output.
# Set DEBUG=false in .env for production-like logging.
_log_level = logging.INFO  # Safe default — does NOT expose auth headers
if settings.DEBUG:
    # Even in DEBUG mode, suppress httpx's verbose header/body logging
    # so that api-key, signature, and account data are never emitted.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    _log_level = logging.DEBUG

logging.basicConfig(
    level=_log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("riskpilot.main")


async def _background_connection_check() -> None:
    """
    Performs the Testnet connectivity check in the background AFTER uvicorn
    is fully bound and serving requests.

    Running check_connection() inside the blocking lifespan startup step caused
    uvicorn to appear hung because the live HTTP call (timeout=6s) blocked the
    event loop before the server could accept requests — including health probes.

    This background task runs 1 second after startup so the server is fully
    ready to serve traffic before the outbound request is attempted.
    No orders are placed. This is strictly read-only.
    """
    await asyncio.sleep(1)
    try:
        conn = await bot.exchange.check_connection()
        mode = conn.get("mode", "UNKNOWN")
        msg = conn.get("message", "")
        if conn.get("authenticated"):
            logger.info(f"[TESTNET] Authenticated connection established — {mode}")
        elif conn.get("connected"):
            logger.warning(f"[TESTNET] Connected but NOT authenticated — {mode}: {msg}")
        else:
            logger.info(f"[TESTNET] {mode}: {msg}")
    except Exception as exc:
        logger.warning(f"[TESTNET] Background connection check error: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("RiskPilot AI Backend — Starting")
    logger.info(f"  Environment   : {settings.DELTA_ENV}")
    logger.info(f"  REST Endpoint : {settings.DELTA_REST_BASE_URL}")
    logger.info(f"  Credentials   : {'CONFIGURED' if settings.has_credentials else 'NOT CONFIGURED (Demo Mode)'}")
    logger.info("=" * 60)

    # Hard safety check — refuse to start if URL is not testnet
    if "testnet" not in settings.DELTA_REST_BASE_URL.lower():
        raise RuntimeError(
            "FATAL: DELTA_REST_BASE_URL does not contain 'testnet'. "
            "RiskPilot AI refuses to start without an approved testnet endpoint."
        )

    # Launch the connectivity check in the background so it does NOT block
    # uvicorn from binding and serving requests.
    asyncio.create_task(_background_connection_check())

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("RiskPilot AI Backend — Shutting down")
    if bot.is_running:
        await bot.stop_session()
    await bot.exchange.close_client()


app = FastAPI(
    title="RiskPilot AI Backend",
    description=(
        "Personalized, Explainable Algorithmic Trading System "
        "connecting to Delta Exchange India Testnet."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(status_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(passport_router, prefix="/api")
app.include_router(strategy_router, prefix="/api")
app.include_router(bot_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "app": "RiskPilot AI",
        "tagline": (
            "The user defines the risk. AI evaluates the opportunity. "
            "The risk engine decides whether the trade is allowed."
        ),
        "status": "online",
        "docs_url": "/docs",
        "environment": settings.DELTA_ENV,
        "credentials_configured": settings.has_credentials,
        "mode": "LIVE_TESTNET_READY" if settings.has_credentials else "DEMO_SAFE_SIMULATION",
    }
