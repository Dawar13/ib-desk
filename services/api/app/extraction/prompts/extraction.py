"""Extraction prompt (Pass 2).

Run once per proposed section. Encodes the cardinal rule: never include a value
that is not supported by a sentence that can be quoted verbatim from the document.
The model returns each value exactly as written and the verbatim supporting
sentence copied exactly; the service locates that sentence and computes the span,
so the prompt forbids reporting character offsets.

Cost note (v3): the full document is placed BEFORE the per-section instruction, so
the stable prefix (the system rules plus the document) is byte-identical across
every section's extraction call in a run. OpenAI prompt caching then bills the
repeated document at the cached rate after the first call, instead of charging the
full document once per section, which is the dominant cost. Only the order
changes; the content the model sees and the output it produces are the same.
"""

from __future__ import annotations

EXTRACTION_PROMPT_VERSION = "3"

_SYSTEM = """\
You extract structured data from a research document for an M&A and investment
banking team. You are given one section definition and the full document. Extract
every instance that belongs to this section.

Rules:
- For each value, return the value exactly as written in the document, and the
  verbatim sentence from the document that supports it, copied exactly so it can
  be found in the source. Do not paraphrase the supporting sentence.
- Do not report character positions or offsets. Do not compute a normalized form.
  Return only the value as written and the supporting sentence.
- Be exhaustive: extract every instance present. Do not summarize away rows in a
  table or list.
- If the section is narrative insight, write a faithful, concise summary as one or
  more longtext values, each grounded in a specific quoted sentence. Do not drop
  qualitative value because it is not a number.
- Never include anything not present in the document. If a value is not supported
  by a sentence you can quote verbatim from the document, do not include it.
  Omission is always better than a guess.
- For tabular sections, use the section's columns as col_key.
- For a scalar section (a set of distinct single facts, for example an identity
  or basics block), set col_key on every value to a short, human-readable field
  label that names what the value is, drawn from how the document presents it
  (for example "Roll number", "Date of birth", "Degree", "Institution"). The
  label organizes the value and must stay faithful to the document; do not
  invent one. Use the same label for the same fact on every run, and put each
  distinct fact in its own row.
- For a longtext section, leave col_key null.
- Set unit and period only when the document states them.
- Prioritize what helps a banker assess a target, a buyer, a market, or a deal.
"""


def build_extraction_messages(section_definition: str, canonical_text: str) -> list[dict[str, str]]:
    # Document first (the stable, cacheable prefix), then the small per-section
    # instruction last (the part that varies between the section calls of a run).
    user = (
        "=== DOCUMENT START ===\n"
        f"{canonical_text}\n"
        "=== DOCUMENT END ===\n\n"
        "Extract the following section from the document above. Extract every "
        "supported value for this section, each with its verbatim supporting "
        "sentence.\n\n"
        "Section to extract:\n"
        f"{section_definition}"
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]


PROMPT_VERSION = f"extraction.v{EXTRACTION_PROMPT_VERSION}"
