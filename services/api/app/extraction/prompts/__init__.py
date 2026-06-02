"""Versioned extraction prompts and the soft section taxonomy.

Every prompt records a version so prompt changes are gated by the eval harness.
"""

from app.extraction.prompts.discovery import (
    DISCOVERY_PROMPT_VERSION,
    build_discovery_messages,
)
from app.extraction.prompts.extraction import (
    EXTRACTION_PROMPT_VERSION,
    build_extraction_messages,
)
from app.extraction.prompts.taxonomy import (
    SECTION_TAXONOMY,
    TAXONOMY_VERSION,
    taxonomy_text,
)
from app.extraction.prompts.verification import (
    VERIFICATION_PROMPT_VERSION,
    build_verification_messages,
)

__all__ = [
    "DISCOVERY_PROMPT_VERSION",
    "EXTRACTION_PROMPT_VERSION",
    "VERIFICATION_PROMPT_VERSION",
    "TAXONOMY_VERSION",
    "SECTION_TAXONOMY",
    "taxonomy_text",
    "build_discovery_messages",
    "build_extraction_messages",
    "build_verification_messages",
]
