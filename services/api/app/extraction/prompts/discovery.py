"""Discovery prompt (Pass 1), version 1.

Encodes the rules from CLAUDE.md Section 7: discover the topic first, never assume
the document is about a company, propose the structure that fits this document,
map to stable taxonomy keys where they apply, include qualitative insight
sections and not only numeric ones, and do not extract values yet. The structured
output enforces the discovery schema, so the prompt describes the task and the
rules rather than the JSON shape.
"""

from __future__ import annotations

from app.extraction.prompts.taxonomy import TAXONOMY_VERSION, taxonomy_text

DISCOVERY_PROMPT_VERSION = "1"

_SYSTEM = """\
You are analyzing a research document for an M&A and investment banking team. Your
job is to discover the structure that best organizes the useful information in
THIS specific document. You do not extract values in this step.

Rules:
- First identify the single primary subject and what the document is fundamentally
  about. The subject may be a company, a market, a person or team, a technology,
  or a deal. Never assume it is a company.
- Then propose the sections that best organize the useful information in this
  document. Prefer the taxonomy keys below when a section matches one of them, so
  the same concept maps to the same key across runs. Add a new section only when
  the document genuinely needs one the taxonomy does not cover.
- Include qualitative insight sections, not only numeric ones. A clear statement
  of who the buyers might be, why a founder may be ready to sell, or what makes a
  market attractive is often worth more than a number.
- Optimize for what helps a banker assess a target, a buyer, a market, or a deal.
- For each section give a machine key, a human label, the kind (scalar, list,
  table, timeseries, or longtext), a render hint, a soft category for grouping,
  the ordered columns when the section is tabular, and a one-line rationale.
- Identify the primary subject's identity fields (for example founded, location)
  with a short supporting source quote for each.
- Do not invent sections the document does not support. Do not extract row values.
"""


def build_discovery_messages(canonical_text: str) -> list[dict[str, str]]:
    user = (
        "Soft section taxonomy (a guide, not a constraint):\n"
        f"{taxonomy_text()}\n\n"
        "Document text follows. Discover the primary subject and propose the "
        "fitting sections.\n\n"
        "=== DOCUMENT START ===\n"
        f"{canonical_text}\n"
        "=== DOCUMENT END ==="
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]


# Combined version tag recorded with each run for prompt-change gating.
PROMPT_VERSION = f"discovery.v{DISCOVERY_PROMPT_VERSION}+taxonomy.v{TAXONOMY_VERSION}"
