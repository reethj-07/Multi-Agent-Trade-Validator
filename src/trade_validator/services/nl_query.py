"""Natural language → read-only SQL → grounded answer (Gemini)."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from trade_validator.clients.gemini_client import GEMINI_MODEL_PRO
from trade_validator.config import DATABASE_URL

_SCHEMA_PROMPT = """
You are a read-only analytics assistant over a SQLite database.

Table: document_run
  id TEXT PRIMARY KEY
  created_at TEXT (ISO-8601 UTC timestamp)
  customer_id TEXT
  original_filename TEXT
  mime_type TEXT
  final_action TEXT — one of: auto_approve, human_review, draft_amendment_request
  mismatch_count INTEGER
  uncertain_count INTEGER
  llm_calls_used INTEGER
  extraction_json TEXT (JSON string, avoid parsing in SQL unless necessary)
  validation_json TEXT
  router_json TEXT
  pipeline_errors_json TEXT (JSON array string or null)

Rules:
- Output a SINGLE SQLite SELECT statement only.
- No INSERT/UPDATE/DELETE/DDL/PRAGMA/ATTACH/DETACH.
- Prefer aggregates (COUNT, SUM) and filters on created_at, customer_id, final_action, mismatch_count, uncertain_count.
- For "this week" use datetime('now', '-7 days') comparisons against created_at where helpful.
- Limit large scans: add LIMIT 100 when listing rows.

User question:
"""


class SqlAnswer(BaseModel):
    sql: str = Field(description="Single SELECT only.")
    explanation: str = Field(
        default="",
        description="One sentence on what the query returns.",
    )


class _GroundedSummary(BaseModel):
    answer: str = Field(
        description="Direct answer using ONLY the provided query result JSON. If empty, say no rows."
    )


_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|PRAGMA|ATTACH|DETACH|VACUUM|ANALYZE)\b",
    re.I,
)


def _sqlite_engine_from_url(url: str) -> Engine:
    if not url.startswith("sqlite:///"):
        raise ValueError("NL query layer currently supports sqlite:/// URLs only.")
    return create_engine(url, connect_args={"check_same_thread": False})


def _validate_select_only(sql: str) -> None:
    s = sql.strip().rstrip(";")
    if not s.upper().startswith("SELECT"):
        raise ValueError("Generated SQL must be a single SELECT statement.")
    if ";" in s:
        raise ValueError("Multiple statements are not allowed.")
    if _FORBIDDEN_SQL.search(s):
        raise ValueError("Forbidden keyword in generated SQL.")


def generate_sql(question: str) -> SqlAnswer:
    from google.genai import types

    from trade_validator.clients.gemini_client import get_gemini_client

    client = get_gemini_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL_PRO,
        contents=[types.Part.from_text(text=_SCHEMA_PROMPT + question)],
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=SqlAnswer,
            max_output_tokens=1024,
        ),
    )
    parsed = response.parsed
    if parsed is None:
        raise RuntimeError("Gemini returned no SQL payload.")
    if isinstance(parsed, SqlAnswer):
        return parsed
    return SqlAnswer.model_validate(parsed)


def run_select(engine: Engine, sql: str) -> list[dict[str, Any]]:
    _validate_select_only(sql)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        cols = list(result.keys())
        rows = [dict(zip(cols, row)) for row in result.fetchall()]
    return rows


def summarize_rows(question: str, rows: list[dict[str, Any]]) -> str:
    from google.genai import types

    from trade_validator.clients.gemini_client import get_gemini_client

    client = get_gemini_client()
    payload = json.dumps(rows, default=str)[:120000]
    prompt = (
        "Answer the user's question using ONLY the data in the JSON array. "
        "If the array is empty, say there were no matching rows. "
        "Do not invent counts or shipment IDs.\n\n"
        f"Question: {question}\n\nRows JSON:\n{payload}"
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL_PRO,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=_GroundedSummary,
            max_output_tokens=512,
        ),
    )
    parsed = response.parsed
    if isinstance(parsed, _GroundedSummary):
        return parsed.answer
    if parsed is not None:
        return _GroundedSummary.model_validate(parsed).answer
    return str(response.text or "No summary available.")


def answer_natural_language_question(question: str) -> dict[str, Any]:
    """
    Returns dict with keys: answer, sql, rows (truncated), error (optional).
    """
    engine = _sqlite_engine_from_url(DATABASE_URL)
    try:
        gen = generate_sql(question)
        rows = run_select(engine, gen.sql)
        answer = summarize_rows(question, rows)
        return {
            "answer": answer,
            "sql": gen.sql,
            "row_count": len(rows),
            "rows": rows[:50],
            "explanation": gen.explanation,
        }
    except Exception as e:
        return {"answer": "", "sql": None, "rows": [], "error": str(e)}
