"""Persist pipeline results to SQLite."""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session

from trade_validator.db.models import DocumentRun
from trade_validator.graph.state import GraphState
from trade_validator.schemas.routing import RouterDecision
from trade_validator.schemas.validation import FieldValidationVerdict, ValidationReport


def _counts_from_validation(report: ValidationReport) -> tuple[int, int]:
    mismatch = sum(
        1 for f in report.fields if f.verdict == FieldValidationVerdict.mismatch
    )
    uncertain = sum(
        1 for f in report.fields if f.verdict == FieldValidationVerdict.uncertain
    )
    return mismatch, uncertain


def persist_document_run(
    session: Session,
    *,
    run_id: str,
    customer_id: str,
    original_filename: str,
    mime_type: str | None,
    final_state: GraphState,
) -> DocumentRun:
    """Insert a row from terminal graph state."""
    ext = final_state.get("extraction")
    val = final_state.get("validation")
    router = final_state.get("router_decision")
    errors = final_state.get("errors") or []

    decision = RouterDecision.model_validate(router)
    validation = ValidationReport.model_validate(val)
    mismatch_count, uncertain_count = _counts_from_validation(validation)

    row = DocumentRun(
        id=run_id,
        customer_id=customer_id,
        original_filename=original_filename,
        mime_type=mime_type,
        final_action=decision.action.value,
        mismatch_count=mismatch_count,
        uncertain_count=uncertain_count,
        llm_calls_used=int(final_state.get("llm_calls", 0)),
        extraction_json=json.dumps(ext, ensure_ascii=False) if ext else None,
        validation_json=json.dumps(val, ensure_ascii=False) if val else None,
        router_json=json.dumps(router, ensure_ascii=False) if router else None,
        pipeline_errors_json=json.dumps(errors) if errors else None,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def fetch_run(session: Session, run_id: str) -> DocumentRun | None:
    return session.get(DocumentRun, run_id)


def list_recent_runs(session: Session, *, limit: int = 50) -> list[DocumentRun]:
    from sqlmodel import select

    stmt = select(DocumentRun).order_by(DocumentRun.created_at.desc()).limit(limit)
    return list(session.exec(stmt).all())
