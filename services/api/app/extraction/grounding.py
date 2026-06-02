"""Grounding by search.

Models count characters unreliably, so the extraction model returns each value
together with the verbatim sentence that supports it, copied from the document.
The service locates that sentence in the canonical text here and computes the
character span itself. A value whose sentence cannot be located is ungrounded and
is dropped, which doubles as a fabrication check: a quote the model invented will
not be found.

Matching is exact first, then whitespace-insensitive (collapsing runs of
whitespace), which tolerates the spacing differences that survive parsing and
normalization. It is intentionally conservative: it never matches on paraphrase
or case changes, so an unsupported value is dropped rather than falsely grounded.
The span is returned as offsets into the canonical text, so later phases can
highlight the supporting sentence. Deterministic.
"""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def _normalized_with_map(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace runs to a single space and return the collapsed text
    plus a map from each collapsed-text index to its index in the original text.
    """
    chars: list[str] = []
    index_map: list[int] = []
    i = 0
    length = len(text)
    while i < length:
        if text[i].isspace():
            chars.append(" ")
            index_map.append(i)
            i += 1
            while i < length and text[i].isspace():
                i += 1
        else:
            chars.append(text[i])
            index_map.append(i)
            i += 1
    return "".join(chars), index_map


def find_span(canonical_text: str, snippet: str) -> tuple[int, int] | None:
    """Return (char_start, char_end) for snippet within canonical_text, as offsets
    into canonical_text, or None when the snippet cannot be located by an exact or
    whitespace-insensitive match. char_end is exclusive.
    """
    if not snippet:
        return None

    exact = canonical_text.find(snippet)
    if exact != -1:
        return exact, exact + len(snippet)

    normalized_text, index_map = _normalized_with_map(canonical_text)
    normalized_snippet = _WHITESPACE.sub(" ", snippet).strip()
    if not normalized_snippet:
        return None

    found = normalized_text.find(normalized_snippet)
    if found == -1:
        return None

    start = index_map[found]
    last = found + len(normalized_snippet) - 1
    end = index_map[last] + 1
    return start, end


def is_grounded(canonical_text: str, snippet: str) -> bool:
    """True when the snippet can be located in the canonical text."""
    return find_span(canonical_text, snippet) is not None
