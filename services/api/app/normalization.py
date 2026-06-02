"""Deterministic normalization to the canonical raw_text form.

The output of normalize_text is the canonical document text that downstream
phases index into with character spans, so it is produced once at ingestion and
never re-derived. It must be deterministic: the same input always yields the same
output. There is no randomness anywhere in this module.
"""

from __future__ import annotations

import re
import unicodedata

# Matches runs of whitespace except the newline, so paragraph structure (newlines)
# is preserved while spaces, tabs, and Unicode spaces inside a line collapse.
_INTRALINE_WHITESPACE = re.compile(r"[^\S\n]+")


def _is_control(ch: str) -> bool:
    # Unicode general categories beginning with C are control or format characters.
    return unicodedata.category(ch).startswith("C")


def normalize_text(text: str) -> str:
    """Return the canonical clean form of the given text.

    Steps, in order: NFC Unicode normalization, line-ending standardization to
    newline, tab to space, removal of control and format characters (keeping the
    newline), collapse of intra-line whitespace runs to a single space, collapse
    of blank-line runs to a single paragraph break, and trimming of leading and
    trailing blank lines. Deterministic.
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", " ")
    text = "".join(ch for ch in text if ch == "\n" or not _is_control(ch))

    lines = [_INTRALINE_WHITESPACE.sub(" ", line).strip() for line in text.split("\n")]

    result: list[str] = []
    prev_blank = True  # start True so leading blank lines are dropped
    for line in lines:
        if line == "":
            if not prev_blank:
                result.append("")
            prev_blank = True
        else:
            result.append(line)
            prev_blank = False
    while result and result[-1] == "":
        result.pop()
    return "\n".join(result)


def assemble_raw_text(segments: list[str]) -> tuple[str, list[int]]:
    """Normalize each segment and join with a blank line.

    A segment is one PDF page, or the whole document for DOCX and pasted text.
    Returns the canonical raw_text and the list of character offsets at which each
    segment begins in raw_text, so a later phase can map a character span back to
    its page. Offsets stay aligned with the input segments even when a segment
    normalizes to empty. Deterministic.
    """
    normalized = [normalize_text(segment) for segment in segments]
    separator = "\n\n"
    offsets: list[int] = []
    parts: list[str] = []
    cursor = 0
    for index, segment_text in enumerate(normalized):
        if index > 0:
            parts.append(separator)
            cursor += len(separator)
        offsets.append(cursor)
        parts.append(segment_text)
        cursor += len(segment_text)
    return "".join(parts), offsets
