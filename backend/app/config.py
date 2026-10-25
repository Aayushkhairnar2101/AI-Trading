"""
Application Configuration and Environment-Level Safety Controls.
Enforces that ONLY Delta Exchange Testnet endpoints can be connected to.
Strictly forbids production endpoints.
"""

from typing import List, Tuple
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import logging

logger = logging.getLogger("riskpilot.config")

# Hard system safety limits that NO profile or setting can exceed
ABSOLUTE_MAX_RISK_PER_TRADE_PCT: float = 2.0  # Max 2% capital per trade
ABSOLUTE_MAX_DAILY_LOSS_PCT: float = 5.0      # Max 5% daily loss limit
ABSOLUTE_MAX_LEVERAGE: float = 10.0           # Max 10x leverage ceiling

ALLOWED_TESTNET_HOST_PATTERNS: List[str] = [
    "cdn-ind.testnet.deltaex.org",
    "testnet.deltaex.org",
    "socket-ind-pub.testnet.deltaex.org",
    "socket-ind.testnet.deltaex.org",
    "socket.testnet.deltaex.org"
]

FORBIDDEN_PROD_PATTERNS: List[str] = [
    "cdn.delta.exchange",
    "api.delta.exchange",
    "socket.delta.exchange",
    "cdn.india.delta.exchange",
    "india.delta.exchange",
    "delta.exchange"
]


class Settings(BaseSettings):
    DELTA_ENV: str = Field(default="india_testnet", description="Must be approved testnet environment")
    DELTA_REST_BASE_URL: str = Field(
        default="https://cdn-ind.testnet.deltaex.org",
        description="Official Delta Exchange India Testnet REST base URL"
    )
    DELTA_WS_PUBLIC_URL: str = Field(
        default="wss://socket-ind-pub.testnet.deltaex.org",
        description="Official Delta Exchange Testnet Public WebSocket URL"
    )
    DELTA_WS_PRIVATE_URL: str = Field(
        default="wss://socket-ind.testnet.deltaex.org",
        description="Official Delta Exchange Testnet Private WebSocket URL"
    )
    DELTA_API_KEY: str = Field(default="", description="Delta Testnet API Key")
    DELTA_API_SECRET: str = Field(default="", description="Delta Testnet API Secret")

    HOST: str = Field(default="127.0.0.1")
    PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=True)
    DB_PATH: str = Field(default="riskpilot.db", description="SQLite local database filename")

    # Safety validator for DELTA_ENV
    @field_validator("DELTA_ENV")
    @classmethod
    def validate_testnet_env(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean in ["production", "prod", "mainnet", "india_prod", "global_prod"]:
            raise ValueError(
                f"CRITICAL SAFETY VIOLATION: Production environment '{v}' is strictly prohibited. "
                f"RiskPilot AI runs solely in Delta Exchange Testnet mode."
            )
        if "testnet" not in clean:
            raise ValueError(
                f"Invalid DELTA_ENV '{v}'. DELTA_ENV must be 'india_testnet'."
            )
        return clean

    # Safety validator for REST URL
    @field_validator("DELTA_REST_BASE_URL")
    @classmethod
    def validate_testnet_rest_url(cls, v: str) -> str:
        clean_url = v.strip().lower()
        for forbidden in FORBIDDEN_PROD_PATTERNS:
            if forbidden in clean_url:
                raise ValueError(
                    f"CRITICAL SAFETY VIOLATION: Production endpoint '{v}' is strictly prohibited. "
                    f"RiskPilot AI runs solely in Delta Exchange Testnet mode."
                )
        if "testnet" not in clean_url:
            raise ValueError(
                f"Endpoint '{v}' does not contain 'testnet'. Only Delta Testnet endpoints are permitted."
            )
        return v.rstrip("/")

    # Safety validator for WS URL
    @field_validator("DELTA_WS_PUBLIC_URL", "DELTA_WS_PRIVATE_URL")
    @classmethod
    def validate_testnet_ws_url(cls, v: str) -> str:
        clean_url = v.strip().lower()
        for forbidden in FORBIDDEN_PROD_PATTERNS:
            if forbidden in clean_url:
                raise ValueError(
                    f"CRITICAL SAFETY VIOLATION: Production WS endpoint '{v}' is strictly prohibited."
                )
        if "testnet" not in clean_url:
            raise ValueError(
                f"WebSocket endpoint '{v}' does not contain 'testnet'. Only Delta Testnet is permitted."
            )
        return v

    @property
    def has_credentials(self) -> bool:
        return bool(self.DELTA_API_KEY.strip() and self.DELTA_API_SECRET.strip())

    @property
    def redacted_api_key(self) -> str:
        key = self.DELTA_API_KEY.strip()
        if not key:
            return "NOT_CONFIGURED"
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

    @property
    def redacted_api_secret(self) -> str:
        secret = self.DELTA_API_SECRET.strip()
        if not secret:
            return "NOT_CONFIGURED"
        return "[CONFIGURED_SECRET]"

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
