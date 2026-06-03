"""Rate limiter unit test. Secret-free and database-free: an always-on gate for
the limiter that backs the public-endpoint throttle and the usage backstop.

A pass means the limiter allows up to the limit within a window, throttles beyond
it, resets when the window rolls over, and keeps distinct callers independent. A
failure means the abuse guard is wrong, which is direct cost exposure.
"""

from __future__ import annotations

from app.ratelimit import RateLimiter


def test_allows_up_to_the_limit_then_throttles() -> None:
    limiter = RateLimiter()
    now = 1000.0  # a fixed clock so the window does not roll over mid-test
    assert limiter.check("k", 3, 60, now=now) is True
    assert limiter.check("k", 3, 60, now=now) is True
    assert limiter.check("k", 3, 60, now=now) is True
    assert limiter.check("k", 3, 60, now=now) is False


def test_window_resets_after_it_expires() -> None:
    limiter = RateLimiter()
    assert limiter.check("k", 1, 60, now=0.0) is True
    assert limiter.check("k", 1, 60, now=10.0) is False  # still inside the window
    assert limiter.check("k", 1, 60, now=61.0) is True  # window rolled over


def test_keys_are_independent() -> None:
    limiter = RateLimiter()
    assert limiter.check("a", 1, 60, now=0.0) is True
    assert limiter.check("b", 1, 60, now=0.0) is True  # different caller, own window
    assert limiter.check("a", 1, 60, now=0.0) is False
