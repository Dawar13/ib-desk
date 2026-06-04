"""Extraction prompt (Pass 2).

Run once over the whole document (once per chunk for a document too large for one
pass), returning every proposed section at once. Encodes the cardinal rule: never
include a value that is not supported by a sentence that can be quoted verbatim
from the document. The model returns each value exactly as written and the
verbatim supporting sentence copied exactly; the service locates that sentence and
computes the span, so the prompt forbids reporting character offsets.

Cost note (v5): the previous design sent the full document once per section, so a
document with a dozen sections was sent to the model a dozen times. This version
extracts every section in a single call, so the document is sent once. That is the
dominant cost saving and it also cuts the number of calls and the latency. The
document is still placed before the section list so the system rules plus document
remain a stable cacheable prefix, which helps when a document is re-extracted or
spans more than one chunk. Seeing all sections together also lets the model avoid
restating the same fact across sections, which the service-side de-duplication then
backs up.
"""

from __future__ import annotations

EXTRACTION_PROMPT_VERSION = "5"

_SYSTEM = """\
You extract structured data from a research document for an M&A and investment
banking team. You are given the full document and a list of section definitions.
Extract the important facts for every section, and return each section's values
under its section key.

Rules:
- For each value, return the value exactly as written in the document, and the
  verbatim sentence from the document that supports it, copied exactly so it can
  be found in the source. Do not paraphrase the supporting sentence.
- Do not report character positions or offsets. Do not compute a normalized form.
  Return only the value as written and the supporting sentence.
- Curate, do not dump. Extract the facts a banker would actually use to assess the
  subject, and stop there. Prefer a small set of distinct, high-value facts over
  capturing every phrase. Do not turn every sentence into a value, and do not
  restate the same fact in more than one value, in more than one form, or in more
  than one section. Leave out filler, restated marketing language, and low-signal
  detail.
- Put each fact in the single section it fits best. Do not repeat the same fact
  across sections.
- If a section is narrative insight, write one concise, faithful summary as a
  longtext value, or a few at most, grounded in specific quoted sentences. Do not
  list every sentence; capture the point.
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
- Return a section entry for every section key listed, using an empty row list for
  a section the document does not support.
"""


def build_extraction_messages(sections_block: str, canonical_text: str) -> list[dict[str, str]]:
    # Document first (the stable, cacheable prefix), then the section list. Every
    # section is extracted in this one call, so the document is sent once.
    user = (
        "=== DOCUMENT START ===\n"
        f"{canonical_text}\n"
        "=== DOCUMENT END ===\n\n"
        "Extract every section listed below from the document above. For each "
        "section, return its section_key and every supported value, each with its "
        "verbatim supporting sentence. Do not repeat the same fact across "
        "sections.\n\n"
        "Sections to extract:\n"
        f"{sections_block}"
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]


PROMPT_VERSION = f"extraction.v{EXTRACTION_PROMPT_VERSION}"
