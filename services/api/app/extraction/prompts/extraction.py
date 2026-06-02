"""Extraction prompt (Pass 2), version 1.

Run once per proposed section. Encodes the cardinal rule: never include a value
that is not supported by a sentence that can be quoted verbatim from the document.
The model returns each value exactly as written and the verbatim supporting
sentence copied exactly; the service locates that sentence and computes the span,
so the prompt forbids reporting character offsets.
"""

from __future__ import annotations

EXTRACTION_PROMPT_VERSION = "1"

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
- For tabular sections, use the section's columns as col_key. For scalar and
  longtext sections, leave col_key null. Set unit and period only when the
  document states them.
- Prioritize what helps a banker assess a target, a buyer, a market, or a deal.
"""


def build_extraction_messages(section_definition: str, canonical_text: str) -> list[dict[str, str]]:
    user = (
        "Section to extract:\n"
        f"{section_definition}\n\n"
        "Document text follows. Extract every supported value for this section, "
        "each with its verbatim supporting sentence.\n\n"
        "=== DOCUMENT START ===\n"
        f"{canonical_text}\n"
        "=== DOCUMENT END ==="
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]


PROMPT_VERSION = f"extraction.v{EXTRACTION_PROMPT_VERSION}"
