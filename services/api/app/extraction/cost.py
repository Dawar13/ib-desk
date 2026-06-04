"""Token-cost estimate for the extraction pipeline (Phase 5 cost tracking).

Turns the tracked token usage into a dollar estimate, accounting for the cheaper
cached-input rate that the extraction prompt's caching produces. Prices come from
settings and default to zero, so no cost is fabricated until they are configured.
The figure is an estimate of model spend per sheet, recorded in sheets.cost_usd
and emitted on the done event so the caching saving is visible.
"""

from __future__ import annotations

from app.extraction.llm import Usage


def estimate_cost_usd(
    usages: list[Usage],
    input_price_per_1m: float,
    cached_input_price_per_1m: float,
    output_price_per_1m: float,
) -> float:
    """Estimate model spend, billing cached input tokens at the cached rate.

    prompt_tokens already includes the cached ones, so the fresh (full-price)
    input is prompt minus cached. Prices are per 1,000,000 tokens.
    """
    prompt = sum(usage.prompt_tokens for usage in usages)
    cached = sum(usage.cached_prompt_tokens for usage in usages)
    completion = sum(usage.completion_tokens for usage in usages)
    fresh_input = max(0, prompt - cached)
    total = (
        fresh_input * input_price_per_1m
        + cached * cached_input_price_per_1m
        + completion * output_price_per_1m
    )
    return total / 1_000_000
