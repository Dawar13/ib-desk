"""Cost estimate gate. Secret-free and pure.

Confirms the token-cost estimate bills cached input tokens at the cheaper cached
rate, so the prompt-caching saving shows up in sheets.cost_usd, and that zero
prices yield zero (no fabricated cost until prices are configured).
"""

from __future__ import annotations

from app.extraction.cost import estimate_cost_usd
from app.extraction.llm import Usage


def test_zero_prices_yield_zero_cost() -> None:
    usages = [Usage(prompt_tokens=1000, completion_tokens=500, cached_prompt_tokens=800)]
    assert estimate_cost_usd(usages, 0.0, 0.0, 0.0) == 0.0


def test_cached_input_billed_at_the_cached_rate() -> None:
    # 1000 input tokens, 800 cached; 500 output. Fresh input = 200.
    usages = [Usage(prompt_tokens=1000, completion_tokens=500, cached_prompt_tokens=800)]
    actual = estimate_cost_usd(usages, 10.0, 5.0, 30.0)
    expected = (200 * 10.0 + 800 * 5.0 + 500 * 30.0) / 1_000_000
    assert abs(actual - expected) < 1e-12


def test_caching_lowers_cost_versus_no_caching() -> None:
    no_cache = [Usage(prompt_tokens=1000, completion_tokens=100, cached_prompt_tokens=0)]
    with_cache = [Usage(prompt_tokens=1000, completion_tokens=100, cached_prompt_tokens=900)]
    assert estimate_cost_usd(with_cache, 10.0, 5.0, 30.0) < estimate_cost_usd(
        no_cache, 10.0, 5.0, 30.0
    )
