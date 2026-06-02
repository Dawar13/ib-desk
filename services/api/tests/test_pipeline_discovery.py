"""Discovery contract test on a recorded cassette. No database or model needed.

Replays a recorded discovery response and checks the engine parses it into a valid
schema with a primary subject and proposed sections.
"""

from __future__ import annotations

import os

from app.extraction.llm import LLMClient
from app.extraction.schemas import DiscoveryResult

_BASIC = os.path.join(os.path.dirname(__file__), "cassettes", "basic")


def test_discovery_cassette_parses_into_schema() -> None:
    client = LLMClient(mode="replay", api_key=None, cassette_dir=_BASIC)
    result, usage = client.complete("discovery", "unused-in-replay", [], DiscoveryResult)
    assert result.doc_type == "company_profile"
    assert result.primary_subject.label == "Acme Robotics"
    assert [section.key for section in result.sections] == ["investors_capital", "overview"]
    assert usage.prompt_tokens == 1200
