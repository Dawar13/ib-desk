"""Parsing unit tests. No database required.

Exercises the PDF, DOCX, pasted-text, and scanned-detection paths against
deterministically generated fixtures.
"""

from __future__ import annotations

from app.normalization import assemble_raw_text
from app.parsing import looks_scanned, parse_docx, parse_pdf, parse_text
from tests.fixtures_gen import (
    DOCX_PARAGRAPH_MARKER,
    DOCX_TABLE_MARKER,
    born_digital_pdf,
    sample_docx,
    scanned_pdf,
)

SCANNED_THRESHOLD = 50


def test_born_digital_pdf_yields_text() -> None:
    result = parse_pdf(born_digital_pdf())
    assert result.page_count == 1
    assert result.extractable_chars > 0
    assert not looks_scanned(result, SCANNED_THRESHOLD)
    raw_text, _offsets = assemble_raw_text(result.segments)
    assert "born-digital PDF" in raw_text


def test_docx_yields_paragraph_and_table_text() -> None:
    result = parse_docx(sample_docx())
    raw_text, _offsets = assemble_raw_text(result.segments)
    assert DOCX_PARAGRAPH_MARKER in raw_text
    assert DOCX_TABLE_MARKER in raw_text
    assert not looks_scanned(result, SCANNED_THRESHOLD)


def test_scanned_pdf_is_detected() -> None:
    result = parse_pdf(scanned_pdf())
    assert result.page_count == 1
    assert result.extractable_chars == 0
    assert looks_scanned(result, SCANNED_THRESHOLD)


def test_pasted_text_is_not_scanned() -> None:
    text = "This is a longer pasted sample note with well over fifty non whitespace characters."
    result = parse_text(text)
    assert result.page_count == 1
    assert not looks_scanned(result, SCANNED_THRESHOLD)
