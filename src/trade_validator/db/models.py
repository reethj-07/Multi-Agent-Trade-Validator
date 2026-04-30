"""SQLModel tables — portable naming for future Postgres."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentRun(SQLModel, table=True):
    """
    One completed pipeline execution (all documents stored for NL query / audit).

    Table name stays generic for ORM portability to Postgres.
    """

    __tablename__ = "document_run"

    id: str = Field(primary_key=True, max_length=36)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    customer_id: str = Field(index=True, max_length=128)
    original_filename: str = Field(max_length=512)
    mime_type: str | None = Field(default=None, max_length=128)
    final_action: str = Field(index=True, max_length=64)
    mismatch_count: int = Field(default=0, index=True)
    uncertain_count: int = Field(default=0, index=True)
    llm_calls_used: int = Field(default=0)
    extraction_json: str | None = Field(default=None, sa_column=Column(Text))
    validation_json: str | None = Field(default=None, sa_column=Column(Text))
    router_json: str | None = Field(default=None, sa_column=Column(Text))
    pipeline_errors_json: str | None = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON list of error strings, if any.",
    )
