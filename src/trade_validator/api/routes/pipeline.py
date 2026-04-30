"""Pipeline execution API."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from langgraph.checkpoint.memory import MemorySaver
from sqlmodel import Session

from trade_validator.agents.extractor import sniff_mime_type
from trade_validator.config import DEFAULT_CUSTOMER_ID
from trade_validator.db.session import get_db
from trade_validator.graph.pipeline import build_compiled_pipeline
from trade_validator.graph.state import GraphState
from trade_validator.services.storage import persist_document_run

router = APIRouter(tags=["pipeline"])


@router.post("/pipeline/run")
async def run_pipeline(
    file: UploadFile = File(...),
    customer_id: str = DEFAULT_CUSTOMER_ID,
    use_pro_extraction: bool = False,
    session: Session = Depends(get_db),
) -> dict:
    """
    Upload a PDF or image; run extract → validate → route; persist to SQLite.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    suffix = Path(file.filename).suffix or ".pdf"
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"read failed: {e}") from e
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file larger than 20MB")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(content)
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()

    mime = file.content_type or sniff_mime_type(tmp_path)
    job_id = str(uuid.uuid4())

    try:
        graph = build_compiled_pipeline(checkpointer=MemorySaver())
        cfg = {"configurable": {"thread_id": job_id}}
        initial: GraphState = {
            "job_id": job_id,
            "customer_id": customer_id,
            "document_path": tmp_path,
            "document_mime_type": mime,
            "use_pro_extraction": use_pro_extraction,
            "llm_calls": 0,
            "errors": [],
        }
        final: GraphState = graph.invoke(initial, config=cfg)  # type: ignore[assignment]
        persist_document_run(
            session,
            run_id=job_id,
            customer_id=customer_id,
            original_filename=file.filename,
            mime_type=mime,
            final_state=final,
        )
        return _state_to_response(final)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _state_to_response(state: GraphState) -> dict:
    """JSON-serializable view for UI."""
    return {
        "job_id": state.get("job_id"),
        "customer_id": state.get("customer_id"),
        "llm_calls": state.get("llm_calls", 0),
        "errors": state.get("errors") or [],
        "extraction": state.get("extraction"),
        "validation": state.get("validation"),
        "router_decision": state.get("router_decision"),
    }
