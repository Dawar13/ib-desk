"""Structured-output schemas for the extraction passes.

These pydantic models define the JSON the model is constrained to return for the
discovery, extraction, and verification passes. They mirror the discovery and
extraction contracts in BUILD_PLAN.md, refined so the model never reports
character offsets or value_norm: it returns each value exactly as written and the
verbatim supporting sentence, and the service computes the span (grounding) and
value_norm (normalization) itself.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.models import DocType, RenderHint, SectionKind


class DiscoveryColumn(BaseModel):
    key: str
    label: str


class DiscoveryIdentityField(BaseModel):
    key: str
    label: str
    value: str
    source: str
    confidence: float


class DiscoveryPrimarySubject(BaseModel):
    label: str
    identity_fields: list[DiscoveryIdentityField]


class DiscoverySection(BaseModel):
    key: str
    label: str
    kind: SectionKind
    render_hint: RenderHint
    category: str | None
    columns: list[DiscoveryColumn] | None
    rationale: str


class DiscoveryResult(BaseModel):
    doc_type: DocType
    primary_topic: str
    primary_subject: DiscoveryPrimarySubject
    sections: list[DiscoverySection]


class ExtractionCell(BaseModel):
    # col_key is the column key for tabular sections, a short field label for
    # scalar sections (so each fact carries the name of what it is, not a
    # positional placeholder), and null for longtext sections. value is the value
    # exactly as written; source_snippet is the verbatim supporting sentence. The
    # service computes value_norm and the char span; the model never reports them.
    col_key: str | None
    value: str
    source_snippet: str
    unit: str | None
    period: str | None
    confidence: float


class ExtractionRow(BaseModel):
    row_idx: int
    cells: list[ExtractionCell]


class SectionExtraction(BaseModel):
    # One discovered section's extracted rows. section_key ties the rows back to
    # the section the discovery pass proposed.
    section_key: str
    rows: list[ExtractionRow]


class ExtractionResult(BaseModel):
    # Every section extracted in a single call. The document is sent to the model
    # once per chunk and all sections come back together, instead of re-sending the
    # whole document once per section, which was the dominant extraction cost.
    sections: list[SectionExtraction]


class VerificationVerdict(BaseModel):
    # section_key identifies which section the value belongs to, so one
    # verification call can return a verdict for every value across all sections.
    section_key: str
    row_idx: int
    col_key: str | None
    supported: bool
    reason: str


class VerificationResult(BaseModel):
    verdicts: list[VerificationVerdict]
