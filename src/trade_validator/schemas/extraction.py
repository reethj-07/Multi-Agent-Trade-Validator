"""Extractor agent output contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Canonical field names aligned with the assignment brief.
EXTRACTION_FIELD_NAMES: tuple[str, ...] = (
    "consignee_name",
    "hs_code",
    "port_of_loading",
    "port_of_discharge",
    "incoterms",
    "description_of_goods",
    "gross_weight",
    "invoice_number",
)


class FieldExtraction(BaseModel):
    """One extracted field with provenance and confidence."""

    value: str | None = Field(
        default=None,
        description="Literal text from the document, or null if not visibly present.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence that value is grounded in the document.",
    )
    source_snippet: str | None = Field(
        default=None,
        description="Short verbatim snippet from the document supporting the value, if any.",
    )

    @field_validator("source_snippet")
    @classmethod
    def empty_snippet_to_none(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v


class ExtractionResult(BaseModel):
    """Full structured extraction for a single trade document."""

    consignee_name: FieldExtraction
    hs_code: FieldExtraction
    port_of_loading: FieldExtraction
    port_of_discharge: FieldExtraction
    incoterms: FieldExtraction
    description_of_goods: FieldExtraction
    gross_weight: FieldExtraction
    invoice_number: FieldExtraction

    document_type_hint: str | None = Field(
        default=None,
        description="Optional classifier label e.g. commercial_invoice, bill_of_lading.",
    )
    extraction_notes: str | None = Field(
        default=None,
        description="Non-field notes: illegible regions, multi-page caveats, etc.",
    )
