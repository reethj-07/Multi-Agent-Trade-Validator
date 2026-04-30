"""LangGraph StateGraph: extract → validate → route."""

from __future__ import annotations

import logging
import traceback
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from trade_validator.agents.extractor import run_extractor, sniff_mime_type
from trade_validator.agents.router import run_router
from trade_validator.agents.validator import run_validator
from trade_validator.config import DEFAULT_CUSTOMER_ID
from trade_validator.graph.state import GraphState
from trade_validator.schemas.extraction import ExtractionResult
from trade_validator.schemas.validation import ValidationReport

logger = logging.getLogger(__name__)


def _node_extract(state: GraphState) -> dict:
    try:
        path = state.get("document_path")
        doc_bytes = None
        mime = state.get("document_mime_type")
        if path:
            with open(path, "rb") as f:
                doc_bytes = f.read()
            if not mime:
                mime = sniff_mime_type(path)
        used = int(state.get("llm_calls", 0))
        result, delta = run_extractor(
            document_label=state.get("document_label", "dummy"),
            document_bytes=doc_bytes,
            mime_type=mime,
            use_pro_model=bool(state.get("use_pro_extraction")),
            llm_calls_used=used,
        )
        return {"extraction": result.model_dump(mode="json"), "llm_calls": delta}
    except Exception:
        logger.exception("extract_node")
        fb = _fallback_extraction()
        return {
            "extraction": fb.model_dump(mode="json"),
            "errors": [traceback.format_exc()],
            "llm_calls": 0,
        }


def _fallback_extraction() -> ExtractionResult:
    """Minimal valid extraction when vision fails (all empty / zero confidence)."""
    from trade_validator.schemas.extraction import FieldExtraction

    z = FieldExtraction(value=None, confidence=0.0, source_snippet=None)
    return ExtractionResult(
        consignee_name=z,
        hs_code=z,
        port_of_loading=z,
        port_of_discharge=z,
        incoterms=z,
        description_of_goods=z,
        gross_weight=z,
        invoice_number=z,
        document_type_hint="error",
        extraction_notes="Extraction failed; operator review required.",
    )


def _node_validate(state: GraphState) -> dict:
    ext = ExtractionResult.model_validate(state["extraction"])
    customer_id = state.get("customer_id", DEFAULT_CUSTOMER_ID)
    report = run_validator(extraction=ext, customer_id=customer_id)
    return {"validation": report.model_dump(mode="json")}


def _node_route(state: GraphState) -> dict:
    report = ValidationReport.model_validate(state["validation"])
    used = int(state.get("llm_calls", 0))
    decision, delta = run_router(validation=report, llm_calls_used=used)
    return {"router_decision": decision.model_dump(mode="json"), "llm_calls": delta}


def build_compiled_pipeline(*, checkpointer: MemorySaver | None = None):
    """
    Linear StateGraph with MemorySaver checkpoints after each node.

    Resume: invoke with the same `thread_id` in configurable; LangGraph reloads
    state from the last successful checkpoint.
    """
    g: StateGraph = StateGraph(GraphState)
    g.add_node("extract", _node_extract)
    g.add_node("validate", _node_validate)
    g.add_node("route", _node_route)
    g.add_edge(START, "extract")
    g.add_edge("extract", "validate")
    g.add_edge("validate", "route")
    g.add_edge("route", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())


def run_pipeline_once(
    *,
    thread_id: str = "local-test",
    job_id: str | None = None,
    customer_id: str = DEFAULT_CUSTOMER_ID,
    document_label: str = "dummy",
    document_path: str | None = None,
    document_mime_type: str | None = None,
) -> GraphState:
    """Run full linear pipeline once (smoke test / demo helper)."""
    graph = build_compiled_pipeline()
    jid = job_id or str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": thread_id}}
    initial: GraphState = {
        "job_id": jid,
        "customer_id": customer_id,
        "document_label": document_label,
        "llm_calls": 0,
        "errors": [],
    }
    if document_path:
        initial["document_path"] = document_path
    if document_mime_type:
        initial["document_mime_type"] = document_mime_type
    out = graph.invoke(initial, config=cfg)
    return out  # type: ignore[return-value]
