"""In-process rate limiting and a usage backstop for the public endpoints.

The link is public even though each visitor's documents are private, so the
upload and extract endpoints need a guard against being hammered into a large
bill or a denial of service. A small fixed-window counter keyed by a caller key
(workspace id plus client address) throttles bursts, and a separate, longer
window caps how many extractions a single workspace can start, as a second line
of defense behind the OpenAI spend cap.

State is in process, which is the right scope for a single-instance demo: it
resets on restart and is not shared across instances. A clock can be injected for
deterministic tests. Expired buckets are pruned opportunistically so the table
does not grow without bound.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Window:
    count: int
    reset_at: float


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Window] = {}

    def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: float,
        now: float | None = None,
    ) -> bool:
        """Record a request and return whether it is within the limit.

        Returns True and counts the request when it is allowed; returns False
        without counting it when the key has already reached max_requests in the
        current window. A new or expired window starts fresh.
        """
        current = time.monotonic() if now is None else now
        self._prune(current)
        window = self._buckets.get(key)
        if window is None or current >= window.reset_at:
            self._buckets[key] = _Window(count=1, reset_at=current + window_seconds)
            return True
        if window.count >= max_requests:
            return False
        window.count += 1
        return True

    def _prune(self, current: float) -> None:
        # Drop windows that have already expired, to bound memory. Cheap while the
        # number of distinct callers is small, which it is for a demo.
        if len(self._buckets) > 1024:
            expired = [key for key, window in self._buckets.items() if current >= window.reset_at]
            for key in expired:
                del self._buckets[key]

    def reset(self) -> None:
        self._buckets.clear()
