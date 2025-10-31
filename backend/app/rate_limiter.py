"""In-memory async rate limiter."""
from __future__ import annotations

import asyncio
import time
from collections import deque


class RateLimiter:
    """A cooperative rate limiter suitable for FastAPI endpoints."""

    def __init__(self, max_calls: int, period_seconds: int) -> None:
        self._max_calls = max_calls
        self._period = period_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until the caller is allowed to proceed."""

        if self._max_calls <= 0:
            return

        while True:
            async with self._lock:
                now = time.monotonic()
                # Drop timestamps that are outside of the current window.
                while self._timestamps and now - self._timestamps[0] > self._period:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._max_calls:
                    self._timestamps.append(now)
                    return

                wait_time = self._period - (now - self._timestamps[0])

            await asyncio.sleep(max(wait_time, 0.01))
