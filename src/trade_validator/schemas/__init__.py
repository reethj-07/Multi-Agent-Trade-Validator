"""Pydantic contracts shared between agents."""

from trade_validator.schemas.extraction import (
    EXTRACTION_FIELD_NAMES,
    ExtractionResult,
    FieldExtraction,
)
from trade_validator.schemas.routing import (
    DiscrepancyItem,
    RouterAction,
    RouterDecision,
)
from trade_validator.schemas.validation import (
    FieldValidation,
    FieldValidationVerdict,
    ValidationReport,
)

__all__ = [
    "EXTRACTION_FIELD_NAMES",
    "DiscrepancyItem",
    "ExtractionResult",
    "FieldExtraction",
    "FieldValidation",
    "FieldValidationVerdict",
    "RouterAction",
    "RouterDecision",
    "ValidationReport",
]
