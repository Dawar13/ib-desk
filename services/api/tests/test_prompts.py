"""Extraction prompt structure gate. Secret-free.

Locks the cost-saving property: the document is placed before the per-section
instruction, so the stable prefix (the system rules plus the document) is
identical across a run's section calls and OpenAI prompt caching can bill the
repeated document at the cached rate. A failure means the document slipped after
the varying section and the caching saving was lost.
"""

from __future__ import annotations

from app.extraction.prompts.extraction import build_extraction_messages


def test_document_precedes_section_so_the_prefix_is_cacheable() -> None:
    messages = build_extraction_messages("SECTION_MARKER", "DOCUMENT_MARKER")
    user = next(m["content"] for m in messages if m["role"] == "user")
    assert "DOCUMENT_MARKER" in user
    assert "SECTION_MARKER" in user
    # The document comes first; only the small section instruction varies at the end.
    assert user.index("DOCUMENT_MARKER") < user.index("SECTION_MARKER")


def test_system_message_does_not_vary_between_sections() -> None:
    a = build_extraction_messages("section A", "doc")
    b = build_extraction_messages("section B", "doc")
    system_a = next(m["content"] for m in a if m["role"] == "system")
    system_b = next(m["content"] for m in b if m["role"] == "system")
    # The system rules are part of the cacheable prefix, so they are stable.
    assert system_a == system_b
