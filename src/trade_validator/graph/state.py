"""Typed graph state (checkpoint-friendly dict payloads)."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


def _merge_errors(
    left: list[str] | None, right: list[str] | None
) -> list[str]:
    """Reducer: concatenate error lists for parallel-safe updates (unused in linear graph)."""
    a = left or []
    b = right or []
    return [*a, *b]


class GraphState(TypedDict, total=False):
    """
    LangGraph state. Nested agent outputs are stored as JSON-serializable dicts
    (from Pydantic `model_dump`) so MemorySaver checkpoints round-trip cleanly.
    """

    job_id: str
    customer_id: str
    document_label: str
    document_path: str
    document_mime_type: str
    use_pro_extraction: bool

    extraction: dict
    validation: dict
    router_decision: dict

    llm_calls: Annotated[int, operator.add]
    errors: Annotated[list[str], _merge_errors]
