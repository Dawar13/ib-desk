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
    # col_key is null for scalar and longtext sections. value is the value exactly
    # as written; source_snippet is the verbatim supporting sentence. The service
    # computes value_norm and the char span; the model never reports them.
    col_key: str | None
    value: str
    source_snippet: str
    unit: str | None
    period: str | None
    confidence: float


class ExtractionRow(BaseModel):
    row_idx: int
    cells: list[ExtractionCell]


class ExtractionResult(BaseModel):
    section_key: str
    rows: list[ExtractionRow]


class VerificationVerdict(BaseModel):
    row_idx: int
    col_key: str | None
    supported: bool
    reason: str


class VerificationResult(BaseModel):
    verdicts: list[VerificationVerdict]
