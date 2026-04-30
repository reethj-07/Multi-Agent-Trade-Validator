"""Validator agent output contracts."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FieldValidationVerdict(str, Enum):
    """Per-field validation outcome; uncertain must never be treated as match."""

    match = "match"
    mismatch = "mismatch"
    uncertain = "uncertain"


class FieldValidation(BaseModel):
    """Comparison of one extracted field to customer rules."""

    field_name: str = Field(..., description="Canonical extraction field name.")
    verdict: FieldValidationVerdict
    found: str | None = Field(
        default=None,
        description="Value from extraction (or null if extraction was empty).",
    )
    expected: str | None = Field(
        default=None,
        description="Rule expectation: required value, pattern, or human-readable requirement.",
    )
    reason: str | None = Field(
        default=None,
        description="Why this verdict was assigned.",
    )


class ValidationReport(BaseModel):
    """Complete validator output for one pipeline run."""

    customer_id: str = Field(..., description="Rule set / customer identifier.")
    fields: list[FieldValidation] = Field(default_factory=list)
    summary: str | None = Field(
        default=None,
        description="Optional short summary for operators.",
    )
