"""Router / decision agent — policy + optional Gemini amendment draft."""

from __future__ import annotations

import logging
from pydantic import BaseModel, Field

from trade_validator.config import MAX_LLM_CALLS_PER_PIPELINE
from trade_validator.schemas.routing import (
    DiscrepancyItem,
    RouterAction,
    RouterDecision,
)
from trade_validator.schemas.validation import FieldValidationVerdict, ValidationReport

logger = logging.getLogger(__name__)


def _discrepancies_from_report(validation: ValidationReport) -> list[DiscrepancyItem]:
    out: list[DiscrepancyItem] = []
    for fv in validation.fields:
        if fv.verdict == FieldValidationVerdict.match:
            continue
        out.append(
            DiscrepancyItem(
                field_name=fv.field_name,
                found=fv.found,
                expected=fv.expected,
            )
        )
    return out


def _template_amendment_email(
    *,
    customer_label: str,
    discrepancies: list[DiscrepancyItem],
) -> str:
    lines = [
        "Dear Supplier,",
        "",
        f"We reviewed the trade documents for {customer_label}. "
        "Please amend and resubmit with the corrections below.",
        "",
    ]
    for i, d in enumerate(discrepancies, 1):
        exp = d.expected or "(see customer policy)"
        found = d.found if d.found is not None else "(missing / not extracted)"
        lines.append(f"{i}. {d.field_name}: found \"{found}\" — expected: {exp}.")
    lines.extend(
        [
            "",
            "Thank you,",
            "Cargo Control Group (automated draft — please review before sending)",
        ]
    )
    return "\n".join(lines)


class _AmendmentEmailBody(BaseModel):
    body: str = Field(..., description="Full email body plain text, professional tone.")


def _maybe_polish_amendment_email(
    *,
    template_body: str,
    validation_summary: str,
    llm_calls_used: int,
) -> tuple[str, int]:
    if llm_calls_used >= MAX_LLM_CALLS_PER_PIPELINE:
        return template_body, 0
    try:
        from trade_validator.clients.gemini_client import (
            GEMINI_MODEL_FLASH,
            get_gemini_client,
        )

        client = get_gemini_client()
    except ValueError:
        return template_body, 0

    from google.genai import types

    prompt = (
        "Rewrite this amendment request email to be concise and professional. "
        "Keep every field discrepancy and the found vs expected facts exactly; "
        "do not invent new issues.\n\n---\n"
        f"{template_body}\n---\nContext: {validation_summary}"
    )
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_FLASH,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=_AmendmentEmailBody,
                max_output_tokens=2048,
            ),
        )
        parsed = response.parsed
        if isinstance(parsed, _AmendmentEmailBody):
            return parsed.body.strip(), 1
        if isinstance(parsed, BaseModel):
            return _AmendmentEmailBody.model_validate(parsed.model_dump()).body.strip(), 1
        if parsed is not None:
            return _AmendmentEmailBody.model_validate(parsed).body.strip(), 1
    except Exception:
        logger.exception("Amendment email polish failed; using template.")
    return template_body, 0


def run_router(
    *,
    validation: ValidationReport,
    llm_calls_used: int = 0,
) -> tuple[RouterDecision, int]:
    """
    Routing policy:
    - Any ``uncertain`` field → ``human_review`` (never auto-approve).
    - All ``match`` → ``auto_approve``.
    - Any ``mismatch`` and no ``uncertain`` → ``draft_amendment_request`` with email.
    """
    fields = validation.fields
    has_uncertain = any(fv.verdict == FieldValidationVerdict.uncertain for fv in fields)
    has_mismatch = any(fv.verdict == FieldValidationVerdict.mismatch for fv in fields)
    all_match = all(fv.verdict == FieldValidationVerdict.match for fv in fields)
    discrepancies = _discrepancies_from_report(validation)

    customer_label = validation.customer_id

    if all_match and not has_uncertain and not has_mismatch:
        return (
            RouterDecision(
                action=RouterAction.auto_approve,
                reasoning=(
                    "All fields matched the customer rule set with no uncertain items. "
                    "Eligible for automated approval path (subject to CG policy)."
                ),
                discrepancies=[],
                draft_amendment_email=None,
            ),
            0,
        )

    if has_uncertain:
        return (
            RouterDecision(
                action=RouterAction.human_review,
                reasoning=(
                    "One or more fields are uncertain (low extraction confidence or "
                    "unhandled rule). A CG operator must review before approval or "
                    "supplier outreach."
                ),
                discrepancies=discrepancies,
                draft_amendment_email=None,
            ),
            0,
        )

    if has_mismatch:
        template = _template_amendment_email(
            customer_label=customer_label,
            discrepancies=discrepancies,
        )
        summary = validation.summary or ""
        body, delta = _maybe_polish_amendment_email(
            template_body=template,
            validation_summary=summary,
            llm_calls_used=llm_calls_used,
        )
        return (
            RouterDecision(
                action=RouterAction.draft_amendment_request,
                reasoning=(
                    "Clear mismatches were found against customer rules with no uncertain "
                    "fields. Draft amendment email prepared listing each discrepancy."
                ),
                discrepancies=discrepancies,
                draft_amendment_email=body,
            ),
            delta,
        )

    return (
        RouterDecision(
            action=RouterAction.human_review,
            reasoning="Unexpected validation state; defaulting to human review.",
            discrepancies=discrepancies,
            draft_amendment_email=None,
        ),
        0,
    )
