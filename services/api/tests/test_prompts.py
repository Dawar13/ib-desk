"""Extraction prompt structure gate. Secret-free.

Locks the cost-saving structure: the document is placed before the section list, so
the stable prefix (the system rules plus the document) stays a cacheable prefix,
and the system rules do not vary across calls. The dominant saving in v5 is that
the section list is extracted in one call, so the document is sent once rather than
once per section; this gate guards the prefix ordering that keeps caching effective
when a document is re-extracted or spans more than one chunk. A failure means the
document slipped after the varying section list and the caching property was lost.
"""

from __future__ import annotations

from app.extraction.prompts.extraction import build_extraction_messages


def test_document_precedes_sections_so_the_prefix_is_cacheable() -> None:
    messages = build_extraction_messages("SECTIONS_MARKER", "DOCUMENT_MARKER")
    user = next(m["content"] for m in messages if m["role"] == "user")
    assert "DOCUMENT_MARKER" in user
    assert "SECTIONS_MARKER" in user
    # The document comes first; only the section list varies at the end.
    assert user.index("DOCUMENT_MARKER") < user.index("SECTIONS_MARKER")


def test_system_message_is_stable_across_calls() -> None:
    a = build_extraction_messages("sections A", "doc")
    b = build_extraction_messages("sections B", "doc")
    system_a = next(m["content"] for m in a if m["role"] == "system")
    system_b = next(m["content"] for m in b if m["role"] == "system")
    # The system rules are part of the cacheable prefix, so they are stable.
    assert system_a == system_b
