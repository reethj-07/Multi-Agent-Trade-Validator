"""Contract tests for Pydantic schemas."""

from trade_validator.schemas import (
    DiscrepancyItem,
    ExtractionResult,
    FieldExtraction,
    FieldValidation,
    FieldValidationVerdict,
    RouterAction,
    RouterDecision,
    ValidationReport,
)


def test_extraction_roundtrip():
    fe = FieldExtraction(value="ACME", confidence=0.9, source_snippet="Consignee: ACME")
    m = ExtractionResult(
        consignee_name=fe,
        hs_code=fe,
        port_of_loading=fe,
        port_of_discharge=fe,
        incoterms=fe,
        description_of_goods=fe,
        gross_weight=fe,
        invoice_number=FieldExtraction(value=None, confidence=0.0),
    )
    d = m.model_dump(mode="json")
    m2 = ExtractionResult.model_validate(d)
    assert m2.consignee_name.value == "ACME"


def test_validation_and_router_roundtrip():
    fv = FieldValidation(
        field_name="hs_code",
        verdict=FieldValidationVerdict.mismatch,
        found="1234",
        expected="8471",
        reason="Prefix mismatch",
    )
    vr = ValidationReport(customer_id="c1", fields=[fv])
    rd = RouterDecision(
        action=RouterAction.draft_amendment_request,
        reasoning="Fix HS code",
        discrepancies=[
            DiscrepancyItem(field_name="hs_code", found="1234", expected="8471")
        ],
        draft_amendment_email="Please amend HS code...",
    )
    ValidationReport.model_validate(vr.model_dump(mode="json"))
    RouterDecision.model_validate(rd.model_dump(mode="json"))
