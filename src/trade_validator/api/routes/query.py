"""Grounded NL → SQL API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter

from trade_validator.services.nl_query import answer_natural_language_question

router = APIRouter(tags=["query"])


class NlQueryRequest(BaseModel):
    question: str = Field(..., min_length=3)


@router.post("/query")
def nl_query(body: NlQueryRequest) -> dict:
    return answer_natural_language_question(body.question)
