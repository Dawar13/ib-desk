"""Normalization unit tests. No database required.

These guard the canonical raw_text contract that later phases index into with
character spans, so determinism and the exact canonical form matter. Unicode
inputs are built with chr() so the source stays ASCII and unambiguous.
"""

from __future__ import annotations

from app.normalization import assemble_raw_text, normalize_text
from tests.fixtures_gen import messy_text


def test_messy_input_canonical_form() -> None:
    # Irregular spaces, CRLF runs, a tab, a null control char, trailing space.
    assert normalize_text(messy_text()) == "Hello world\n\nSecond paragraph here"


def test_unicode_is_nfc_normalized() -> None:
    # "e" + U+0301 combining acute accent normalizes to U+00E9 (composed e-acute).
    decomposed = "e" + chr(0x0301)
    composed = chr(0x00E9)
    assert decomposed != composed
    assert normalize_text(decomposed) == composed


def test_nonbreaking_space_collapses() -> None:
    # Two U+00A0 non-breaking spaces collapse to a single ordinary space.
    nbsp = chr(0x00A0)
    assert normalize_text("a" + nbsp + nbsp + "b") == "a b"


def test_is_deterministic_and_idempotent() -> None:
    sample = messy_text()
    first = normalize_text(sample)
    second = normalize_text(sample)
    assert first == second
    # Normalizing an already-canonical string returns it unchanged.
    assert normalize_text(first) == first


def test_assemble_raw_text_offsets() -> None:
    raw_text, offsets = assemble_raw_text(["Page one.", "Page two."])
    assert raw_text == "Page one.\n\nPage two."
    assert offsets == [0, 11]
    assert raw_text[offsets[1] :] == "Page two."
