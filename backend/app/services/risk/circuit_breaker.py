"""
Circuit Breaker System.
Guards the account against catastrophic drawdown streaks and daily loss breaches.
Automatically halts trade generation when limits are tripped.
"""

from typing import Tuple, Optional
from datetime import datetime, timezone
from app.config import ABSOLUTE_MAX_DAILY_LOSS_PCT
from app.schemas.analytics import CircuitBreakerStatus
import logging

logger = logging.getLogger("riskpilot.circuit_breaker")


class CircuitBreaker:
    def __init__(
        self,
        session_start_equity: float = 1000.0,
        max_daily_loss_pct: float = 2.0,
        max_consecutive_losses: int = 3
    ):
        self.session_start_equity = max(session_start_equity, 1.0)
        # Never allow configuration to exceed absolute safety limit
        self.max_daily_loss_pct = min(max_daily_loss_pct, ABSOLUTE_MAX_DAILY_LOSS_PCT)
        self.max_consecutive_losses = max(1, max_consecutive_losses)

        self.current_equity = self.session_start_equity
        self.consecutive_losses: int = 0
        self.total_losses: int = 0
        self.is_tripped: bool = False
        self.trip_reason: Optional[str] = None
        self.tripped_at: Optional[datetime] = None

    def update_equity(self, current_equity: float) -> Tuple[bool, Optional[str]]:
        """
        Updates equity and evaluates daily drawdown.
        Returns (is_allowed, optional_breach_reason).
        """
        self.current_equity = current_equity
        if self.session_start_equity <= 0:
            return True, None

        drawdown_pct = ((self.session_start_equity - current_equity) / self.session_start_equity) * 100.0

        if drawdown_pct >= self.max_daily_loss_pct and not self.is_tripped:
            self._trip(
                f"Daily drawdown limit breached: {drawdown_pct:.2f}% loss from session start equity "
                f"({self.session_start_equity:.2f} -> {current_equity:.2f}), exceeding threshold {self.max_daily_loss_pct:.2f}%."
            )
            return False, self.trip_reason

        return not self.is_tripped, self.trip_reason

    def record_trade_result(self, realized_pnl: float) -> None:
        """
        Updates streak metrics when a trade closes.
        """
        self.current_equity += realized_pnl
        if realized_pnl < 0:
            self.consecutive_losses += 1
            self.total_losses += 1
            logger.warning(
                f"Loss recorded: {realized_pnl:.2f}. Consecutive losses count: {self.consecutive_losses}/{self.max_consecutive_losses}"
            )
            if self.consecutive_losses >= self.max_consecutive_losses and not self.is_tripped:
                self._trip(
                    f"Consecutive loss streak triggered: {self.consecutive_losses} losses in a row "
                    f"(limit: {self.max_consecutive_losses}). Circuit breaker engaged."
                )
        else:
            # Winning trade or breakeven resets the consecutive streak
            self.consecutive_losses = 0

        # Also check updated equity drawdown
        self.update_equity(self.current_equity)

    def _trip(self, reason: str) -> None:
        self.is_tripped = True
        self.trip_reason = reason
        self.tripped_at = datetime.now(timezone.utc)
        logger.critical(f"CIRCUIT BREAKER TRIPPED: {reason}")

    def reset(self, new_start_equity: Optional[float] = None) -> None:
        """Explicit manual reset by user after reviewing risk state."""
        self.is_tripped = False
        self.trip_reason = None
        self.tripped_at = None
        self.consecutive_losses = 0
        if new_start_equity is not None and new_start_equity > 0:
            self.session_start_equity = new_start_equity
            self.current_equity = new_start_equity
        logger.info("Circuit breaker manually reset by user.")

    def get_status(self) -> CircuitBreakerStatus:
        drawdown_pct = 0.0
        if self.session_start_equity > 0 and self.current_equity < self.session_start_equity:
            drawdown_pct = ((self.session_start_equity - self.current_equity) / self.session_start_equity) * 100.0

        return CircuitBreakerStatus(
            is_tripped=self.is_tripped,
            trip_reason=self.trip_reason,
            tripped_at=self.tripped_at,
            consecutive_losses=self.consecutive_losses,
            max_consecutive_losses=self.max_consecutive_losses,
            current_daily_drawdown_pct=round(drawdown_pct, 2),
            max_daily_loss_pct=self.max_daily_loss_pct,
            paused_trades=self.is_tripped,
            message="Circuit breaker TRIPPED. New entries paused." if self.is_tripped else "Circuit breaker normal."
        )
