"""Validator agent — compare extraction to customer JSON rules."""

from __future__ import annotations

import re
from typing import Any

from trade_validator.config import EXTRACTION_UNCERTAIN_THRESHOLD
from trade_validator.schemas.extraction import ExtractionResult, FieldExtraction
from trade_validator.schemas.validation import (
    FieldValidation,
    FieldValidationVerdict,
    ValidationReport,
)
from trade_validator.services.rules_loader import load_rules
from trade_validator.services.textnorm import (
    normalize_hs_for_regex,
    normalize_port,
    normalize_spaces_upper,
    primary_port_city,
)

_FIELD_ORDER = (
    "consignee_name",
    "hs_code",
    "port_of_loading",
    "port_of_discharge",
    "incoterms",
    "description_of_goods",
    "gross_weight",
    "invoice_number",
)


def _field_extraction(er: ExtractionResult, name: str) -> FieldExtraction:
    return getattr(er, name)


def _validate_one(
    field_name: str,
    fe: FieldExtraction,
    rule: dict[str, Any] | None,
) -> FieldValidation:
    if rule is None:
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.uncertain,
            found=fe.value,
            expected=None,
            reason="No rule defined for this field in customer profile.",
        )

    desc = rule.get("description", "")
    required = bool(rule.get("required", False))

    if fe.confidence < EXTRACTION_UNCERTAIN_THRESHOLD:
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.uncertain,
            found=fe.value,
            expected=desc or "See customer rule set",
            reason=(
                f"Extraction confidence {fe.confidence:.2f} is below threshold "
                f"{EXTRACTION_UNCERTAIN_THRESHOLD}; cannot treat as validated."
            ),
        )

    val = fe.value
    if val is None or (isinstance(val, str) and not val.strip()):
        if required:
            return FieldValidation(
                field_name=field_name,
                verdict=FieldValidationVerdict.mismatch,
                found=val,
                expected=desc or "Required field present on document",
                reason="Required field missing or empty in extraction.",
            )
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.uncertain,
            found=val,
            expected=desc,
            reason="Optional field empty; marked uncertain for operator awareness.",
        )

    val_s = val.strip() if isinstance(val, str) else str(val)

    if "normalized_equals" in rule:
        exp = rule["normalized_equals"]
        if normalize_spaces_upper(val_s) == normalize_spaces_upper(str(exp)):
            return FieldValidation(
                field_name=field_name,
                verdict=FieldValidationVerdict.match,
                found=val_s,
                expected=str(exp),
                reason="Consignee matches customer master data (normalized).",
            )
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.mismatch,
            found=val_s,
            expected=str(exp),
            reason="Consignee does not match required legal name.",
        )

    if "regex" in rule:
        pattern = rule["regex"]
        hs_norm = normalize_hs_for_regex(val_s)
        if re.match(pattern, hs_norm):
            return FieldValidation(
                field_name=field_name,
                verdict=FieldValidationVerdict.match,
                found=val_s,
                expected=rule.get("human_readable") or pattern,
                reason="HS code matches required pattern.",
            )
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.mismatch,
            found=val_s,
            expected=rule.get("human_readable") or pattern,
            reason="HS code outside allowed chapter / format.",
        )

    if "allowed_normalized" in rule:
        allowed = {normalize_port(x) for x in rule["allowed_normalized"]}
        if field_name == "incoterms":
            raw = normalize_spaces_upper(val_s)
            m = re.match(r"^([A-Z]{2,4})\b", raw)
            got = m.group(1) if m else raw
        elif field_name in ("port_of_loading", "port_of_discharge"):
            got = primary_port_city(val_s)
        else:
            got = normalize_port(val_s)
        if got in allowed:
            return FieldValidation(
                field_name=field_name,
                verdict=FieldValidationVerdict.match,
                found=val_s,
                expected=", ".join(rule["allowed_normalized"]),
                reason="Value is on the approved list.",
            )
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.mismatch,
            found=val_s,
            expected=", ".join(rule["allowed_normalized"]),
            reason="Value not in customer's approved list.",
        )

    if "min_chars" in rule:
        mc = int(rule["min_chars"])
        if len(val_s) >= mc:
            return FieldValidation(
                field_name=field_name,
                verdict=FieldValidationVerdict.match,
                found=val_s,
                expected=f"At least {mc} characters",
                reason="Text length satisfies minimum.",
            )
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.mismatch,
            found=val_s,
            expected=f"At least {mc} characters",
            reason="Text too short.",
        )

    if rule.get("must_contain_kg"):
        if re.search(r"\bKG(S)?\b", val_s.upper()) or re.search(
            r"KILO", val_s.upper()
        ):
            return FieldValidation(
                field_name=field_name,
                verdict=FieldValidationVerdict.match,
                found=val_s,
                expected="Weight line including KG",
                reason="Gross weight line includes kilogram unit.",
            )
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.mismatch,
            found=val_s,
            expected="Must include KG (or KGS) unit",
            reason="Gross weight missing explicit KG unit.",
        )

    if "min_length" in rule:
        ml = int(rule["min_length"])
        if len(val_s) >= ml:
            return FieldValidation(
                field_name=field_name,
                verdict=FieldValidationVerdict.match,
                found=val_s,
                expected=f"Min length {ml}",
                reason="Invoice number length OK.",
            )
        return FieldValidation(
            field_name=field_name,
            verdict=FieldValidationVerdict.mismatch,
            found=val_s,
            expected=f"Min length {ml}",
            reason="Invoice number too short.",
        )

    return FieldValidation(
        field_name=field_name,
        verdict=FieldValidationVerdict.uncertain,
        found=val_s,
        expected=desc,
        reason="Rule shape not handled; manual review.",
    )


def run_validator(
    *,
    extraction: ExtractionResult,
    customer_id: str = "acme_retail_eu",
) -> ValidationReport:
    rules = load_rules(customer_id)
    fields: list[FieldValidation] = []
    for fname in _FIELD_ORDER:
        fe = _field_extraction(extraction, fname)
        rule = rules.get(fname)
        if isinstance(rule, dict) and "required" not in rule and fname != "customer_id":
            pass
        fields.append(_validate_one(fname, fe, rule if isinstance(rule, dict) else None))

    display = str(rules.get("display_name", customer_id))
    return ValidationReport(
        customer_id=customer_id,
        fields=fields,
        summary=f"Validation against {display} rules ({len(fields)} fields).",
    )
