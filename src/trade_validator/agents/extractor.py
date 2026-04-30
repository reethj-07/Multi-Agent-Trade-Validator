"""Extractor agent — Gemini vision over PDF or images."""

from __future__ import annotations

import logging
from pathlib import Path

from trade_validator.clients.gemini_client import (
    GEMINI_MODEL_FLASH,
    GEMINI_MODEL_PRO,
    generate_structured,
    get_gemini_client,
)
from trade_validator.config import MAX_LLM_CALLS_PER_PIPELINE
from trade_validator.schemas.extraction import ExtractionResult, FieldExtraction

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = """You extract structured data from trade documents (commercial invoices, packing lists, B/L, etc.).

Rules:
- Output ONLY JSON matching the response schema. No markdown.
- Use ONLY text visibly printed or clearly handwritten in the document. Do not guess from context or typical trade practice.
- If a field is absent, illegible, or ambiguous, set value to null, confidence to 0.0–0.25, source_snippet to null.
- confidence guidance: 0.0 not visible; 0.3–0.55 partially visible or noisy scan; 0.65–0.85 clearly readable; above 0.85 only when verbatim and unambiguous.
- source_snippet: a short verbatim quote from the document (max ~120 characters) supporting the value, or null if value is null.
- Never invent invoice numbers, HS codes, ports, weights, or consignee names not on the page.
- Map “Notify Party”, “Buyer”, or “Consignee” lines to consignee_name when that is the consigned party.
- HS code: return as printed (digits with optional dot), no commentary.
- Gross weight: include unit if shown (e.g. \"1,250.00 KGS\").
"""


def _stub_extraction(document_label: str) -> ExtractionResult:
    low = FieldExtraction(value=None, confidence=0.0, source_snippet=None)
    mid = FieldExtraction(
        value="STUB VALUE",
        confidence=0.5,
        source_snippet="[stub snippet]",
    )
    return ExtractionResult(
        consignee_name=mid,
        hs_code=mid,
        port_of_loading=mid,
        port_of_discharge=mid,
        incoterms=mid,
        description_of_goods=mid,
        gross_weight=mid,
        invoice_number=low,
        document_type_hint="stub",
        extraction_notes=f"Stub run (document_label={document_label}).",
    )


def run_extractor(
    *,
    document_label: str = "dummy",
    document_bytes: bytes | None = None,
    mime_type: str | None = None,
    use_pro_model: bool = False,
    llm_calls_used: int = 0,
) -> tuple[ExtractionResult, int]:
    """
    Extract fields. If ``document_bytes`` is None, returns deterministic stub (tests / offline).

    Returns:
        (ExtractionResult, new_llm_calls_delta) where delta is 0 for stub or 1 for API.
    """
    if document_bytes is None or mime_type is None:
        return _stub_extraction(document_label), 0

    from google.genai import types

    if llm_calls_used >= MAX_LLM_CALLS_PER_PIPELINE:
        raise RuntimeError(
            f"LLM call budget exhausted ({MAX_LLM_CALLS_PER_PIPELINE}) before extraction."
        )

    client = get_gemini_client()
    model = GEMINI_MODEL_PRO if use_pro_model else GEMINI_MODEL_FLASH
    media = types.Part.from_bytes(data=document_bytes, mime_type=mime_type)
    user_text = types.Part.from_text(
        text=(
            "Extract all trade fields from this document into the schema. "
            "If the file has multiple pages, consider every page."
        )
    )
    try:
        result = generate_structured(
            client,
            model,
            contents=[media, user_text],
            response_model=ExtractionResult,
            system_instruction=_EXTRACTION_SYSTEM,
            temperature=0.0,
            max_output_tokens=8192,
        )
    except Exception:
        logger.exception("Primary extraction failed; retrying with Pro model once.")
        if use_pro_model:
            raise
        if llm_calls_used + 1 >= MAX_LLM_CALLS_PER_PIPELINE:
            raise
        result = generate_structured(
            client,
            GEMINI_MODEL_PRO,
            contents=[media, user_text],
            response_model=ExtractionResult,
            system_instruction=_EXTRACTION_SYSTEM,
            temperature=0.0,
            max_output_tokens=8192,
        )
        return result, 2

    return result, 1


def sniff_mime_type(path: str | Path) -> str:
    """Guess mime from file suffix for Gemini."""
    p = Path(path)
    ext = p.suffix.lower()
    mapping = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mapping.get(ext, "application/octet-stream")
