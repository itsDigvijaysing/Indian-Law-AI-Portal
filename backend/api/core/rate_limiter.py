"""
Global daily rate limiter.

Protects the (unpaid) LLM budget by capping the TOTAL number of answer
generations across ALL visitors per calendar day (UTC). This is a GLOBAL
ceiling, not per-visitor: once the day's quota is spent, every visitor gets
a 429 until the next UTC midnight.

In-memory and process-local. A single-worker deployment is assumed (the
free-tier norm); with N gunicorn/uvicorn workers the effective cap is
limit * N. The counter also resets if the process restarts — acceptable for
a hobby deploy. Swap in a shared store (Redis / SQLite) if either matters.
"""

import asyncio
from datetime import datetime, timezone, timedelta


class DailyRateLimiter:
    """A single global counter that rolls over at UTC midnight."""

    def __init__(self, limit: int):
        self.limit = max(0, int(limit))
        self._date = None
        self._count = 0
        self._lock = asyncio.Lock()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    @staticmethod
    def _next_reset_iso() -> str:
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return tomorrow.isoformat()

    def _roll(self) -> None:
        """Reset the counter when the UTC day changes."""
        today = self._today()
        if self._date != today:
            self._date = today
            self._count = 0

    async def consume(self) -> dict:
        """Increment the counter if under the cap.

        Returns a status dict with an 'allowed' flag. When False, nothing was
        consumed and the caller should reject the request (429).
        """
        async with self._lock:
            self._roll()
            if self._count >= self.limit:
                return self._status(False)
            self._count += 1
            return self._status(True)

    async def status(self) -> dict:
        """Read-only snapshot (does not consume quota)."""
        async with self._lock:
            self._roll()
            return self._status(self._count < self.limit)

    def _status(self, allowed: bool) -> dict:
        return {
            "allowed": allowed,
            "limit": self.limit,
            "used": self._count,
            "remaining": max(0, self.limit - self._count),
            "reset_at": self._next_reset_iso(),
        }


_limiter: DailyRateLimiter | None = None


def get_rate_limiter() -> DailyRateLimiter:
    """Module-level singleton, sized from settings on first use."""
    global _limiter
    if _limiter is None:
        try:
            from .config import get_settings
        except ImportError:
            from api.core.config import get_settings
        _limiter = DailyRateLimiter(get_settings().DAILY_QUERY_LIMIT)
    return _limiter
