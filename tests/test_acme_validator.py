"""Validator + router behavior against bundled Acme rules (no LLM)."""

from trade_validator.agents.router import run_router
from trade_validator.agents.validator import run_validator
from trade_validator.schemas.extraction import ExtractionResult, FieldExtraction
from trade_validator.schemas.routing import RouterAction
from trade_validator.schemas.validation import FieldValidationVerdict


def _fe(v: str | None, c: float) -> FieldExtraction:
    return FieldExtraction(value=v, confidence=c, source_snippet="x" if v else None)


def test_acme_all_match_auto_approve():
    ext = ExtractionResult(
        consignee_name=_fe("Acme Retail EU BV", 0.9),
        hs_code=_fe("8471.30", 0.9),
        port_of_loading=_fe("Shanghai", 0.9),
        port_of_discharge=_fe("Rotterdam", 0.9),
        incoterms=_fe("FOB Shanghai", 0.9),
        description_of_goods=_fe("Laptop computers batch 42", 0.9),
        gross_weight=_fe("1250 KG", 0.9),
        invoice_number=_fe("INV-2025-0099", 0.9),
    )
    report = run_validator(extraction=ext, customer_id="acme_retail_eu")
    assert all(f.verdict == FieldValidationVerdict.match for f in report.fields)
    decision, delta = run_router(validation=report, llm_calls_used=0)
    assert decision.action == RouterAction.auto_approve
    assert delta == 0


def test_acme_mismatch_triggers_amendment_or_template():
    ext = ExtractionResult(
        consignee_name=_fe("Wrong Co", 0.9),
        hs_code=_fe("9999.00", 0.9),
        port_of_loading=_fe("Shanghai", 0.9),
        port_of_discharge=_fe("Rotterdam", 0.9),
        incoterms=_fe("FOB", 0.9),
        description_of_goods=_fe("Goods description here long enough", 0.9),
        gross_weight=_fe("100 KG", 0.9),
        invoice_number=_fe("INV-9999", 0.9),
    )
    report = run_validator(extraction=ext, customer_id="acme_retail_eu")
    has_mismatch = any(
        f.verdict == FieldValidationVerdict.mismatch for f in report.fields
    )
    assert has_mismatch
    decision, _ = run_router(validation=report, llm_calls_used=99)
    assert decision.action == RouterAction.draft_amendment_request
    assert decision.draft_amendment_email
    assert (
        "Wrong Co" in decision.draft_amendment_email
        or "consignee_name" in decision.draft_amendment_email.lower()
    )


def test_port_city_country_still_matches_allowed_list():
    """Documents often include 'City, Country' — compare city to approved ports."""
    ext = ExtractionResult(
        consignee_name=_fe("Acme Retail EU BV", 0.9),
        hs_code=_fe("8471.30", 0.9),
        port_of_loading=_fe("Shanghai, China", 0.9),
        port_of_discharge=_fe("Rotterdam, Netherlands", 0.9),
        incoterms=_fe("FOB Shanghai", 0.9),
        description_of_goods=_fe("Laptop computers batch 42", 0.9),
        gross_weight=_fe("1250 KG", 0.9),
        invoice_number=_fe("INV-2025-0099", 0.9),
    )
    report = run_validator(extraction=ext, customer_id="acme_retail_eu")
    pl = next(f for f in report.fields if f.field_name == "port_of_loading")
    pd = next(f for f in report.fields if f.field_name == "port_of_discharge")
    assert pl.verdict == FieldValidationVerdict.match
    assert pd.verdict == FieldValidationVerdict.match


def test_low_confidence_forces_human_review():
    ext = ExtractionResult(
        consignee_name=_fe("Acme Retail EU BV", 0.9),
        hs_code=_fe("8471.30", 0.9),
        port_of_loading=_fe("Shanghai", 0.9),
        port_of_discharge=_fe("Rotterdam", 0.9),
        incoterms=_fe("FOB", 0.9),
        description_of_goods=_fe("Some goods text here", 0.9),
        gross_weight=_fe("1250 KG", 0.9),
        invoice_number=_fe("INV-2025-0099", 0.2),
    )
    report = run_validator(extraction=ext, customer_id="acme_retail_eu")
    uncertain = [f for f in report.fields if f.verdict == FieldValidationVerdict.uncertain]
    assert uncertain
    decision, _ = run_router(validation=report, llm_calls_used=0)
    assert decision.action == RouterAction.human_review
