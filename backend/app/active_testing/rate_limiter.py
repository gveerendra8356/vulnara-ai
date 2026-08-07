"""
active_testing/rate_limiter.py

Two independent controls, both required, layered on top of each other:

1. ThrottleLimiter -- caps requests-per-second AND adds randomized jitter
   between requests, so this module never fires a burst at the target
   and doesn't produce a suspiciously mechanical, perfectly-periodic
   request pattern.

2. ScanRequestBudget -- a hard ceiling on TOTAL requests for one scan,
   independent of rate. Throttling alone doesn't prevent a large scan
   (many forms x many params x many payloads) from eventually sending
   thousands of requests over a long enough window -- the budget caps
   total volume outright, regardless of how patient the throttle is.

Both are intentionally conservative defaults for a student/thesis
project testing against systems you or your client own. Tune via env
vars, but don't remove the caps entirely.
"""

from __future__ import annotations

import asyncio
import os
import random
import time


class ScanBudgetExceededError(RuntimeError):
    """Raised when a scan hits its hard total-request cap for active testing."""


class ThrottleLimiter:
    """Simple per-second rate limiter with jitter, shared across one scan's active-testing run."""

    def __init__(self, max_requests_per_second: float = 1.0, jitter_seconds: float = 0.3):
        self.min_interval = 1.0 / max_requests_per_second
        self.jitter_seconds = jitter_seconds
        self._last_request_at: float | None = None
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if self._last_request_at is not None:
                elapsed = now - self._last_request_at
                remaining = self.min_interval - elapsed
                if remaining > 0:
                    await asyncio.sleep(remaining)
            # Jitter AFTER the minimum-interval wait, not instead of it --
            # jitter alone could still average out to a fast, regular rate.
            await asyncio.sleep(random.uniform(0, self.jitter_seconds))
            self._last_request_at = time.monotonic()


class ScanRequestBudget:
    """
    Hard cap on total active-testing requests for a single scan.
    Default is deliberately low -- appropriate for testing a handful of
    forms with the minimal payload set above, not for crawling and
    fuzzing a large application.
    """

    def __init__(self, max_total_requests: int | None = None):
        self.max_total_requests = max_total_requests or int(
            os.environ.get("ACTIVE_TEST_MAX_REQUESTS_PER_SCAN", "150")
        )
        self._used = 0
        self._lock = asyncio.Lock()

    async def consume(self, count: int = 1) -> None:
        async with self._lock:
            if self._used + count > self.max_total_requests:
                raise ScanBudgetExceededError(
                    f"Active-testing request budget exhausted "
                    f"({self._used}/{self.max_total_requests}) -- stopping "
                    f"active testing for this scan. Remaining forms/params "
                    f"were not tested."
                )
            self._used += count

    @property
    def used(self) -> int:
        return self._used
