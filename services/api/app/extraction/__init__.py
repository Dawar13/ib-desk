"""The schema-agnostic extraction engine (Phase 2).

Subpackages and modules:
  - grounding: locate a model-quoted sentence in the canonical text and compute
    its character span (service-computed offsets, never model-reported).
  - valuenorm: deterministic value normalization (value_norm).
  - schemas: pydantic models for the discovery, extraction, and verification
    structured outputs.
"""
