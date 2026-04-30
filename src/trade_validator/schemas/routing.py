"""Router / decision agent output contracts."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RouterAction(str, Enum):
    """High-level routing outcome."""

    auto_approve = "auto_approve"
    human_review = "human_review"
    draft_amendment_request = "draft_amendment_request"


class DiscrepancyItem(BaseModel):
    """Structured discrepancy for amendment drafts and UI."""

    field_name: str
    found: str | None = None
    expected: str | None = None


class RouterDecision(BaseModel):
    """Final decision with plain-language reasoning and optional amendment email."""

    action: RouterAction
    reasoning: str = Field(
        ...,
        description="Plain-language explanation for CG operators.",
    )
    discrepancies: list[DiscrepancyItem] = Field(default_factory=list)
    draft_amendment_email: str | None = Field(
        default=None,
        description="Draft email body listing discrepancies; null unless action is draft_amendment_request.",
    )
