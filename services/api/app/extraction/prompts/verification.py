"""Verification prompt (Pass 3), version 1.

For each extracted value and its quoted supporting sentence, confirm the sentence
genuinely supports the value, not merely that it exists. A confidently wrong value
is the worst output the product can produce, so anything that fails is removed.
"""

from __future__ import annotations

VERIFICATION_PROMPT_VERSION = "1"

_SYSTEM = """\
You verify extracted values for an M&A and investment banking team. You are given
a list of values, each with the verbatim sentence quoted as its support. For each
one, decide whether that sentence genuinely supports that value, not merely that
the sentence exists.

Rules:
- Mark supported true only when the quoted sentence states or directly implies the
  value. If the sentence is unrelated, contradicts the value, or only loosely
  associates with it, mark supported false.
- Be strict. When in doubt, mark supported false. Omitting a weakly supported
  value is always better than keeping a wrong one.
- Give a one-line reason for each decision.
- Return a verdict for every value, identified by its row index and column key.
"""


def build_verification_messages(values_block: str) -> list[dict[str, str]]:
    user = (
        "Values to verify, each with its quoted supporting sentence:\n\n"
        f"{values_block}\n\n"
        "Return a verdict for every value."
    )
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]


PROMPT_VERSION = f"verification.v{VERIFICATION_PROMPT_VERSION}"
