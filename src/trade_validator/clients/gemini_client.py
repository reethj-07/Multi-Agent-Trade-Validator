"""Google Gemini Developer API client (2.5 Flash / 2.5 Pro)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

if TYPE_CHECKING:
    from google.genai import Client as GenaiClient

# Stable model IDs for the Gemini API (see https://ai.google.dev/gemini-api/docs/models).
GEMINI_MODEL_FLASH = "gemini-2.5-flash"
GEMINI_MODEL_PRO = "gemini-2.5-pro"

T = TypeVar("T", bound=BaseModel)


def _ensure_dotenv() -> None:
    """
    Load ``.env`` from the current working directory only (no upward search).

    This avoids accidentally loading a developer key when tests ``chdir`` to an
    isolated temp folder, and matches “run from repo root” workflows.
    """
    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


def get_gemini_client(*, api_key: str | None = None) -> GenaiClient:
    """
    Build a Gemini API client.

    Uses ``GEMINI_API_KEY`` (preferred) or ``GOOGLE_API_KEY`` after loading ``.env``,
    matching the ``google-genai`` SDK.
    """
    from google.genai import Client

    _ensure_dotenv()
    key = (
        api_key
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    if not key or not str(key).strip():
        raise ValueError(
            "Gemini API key missing. Set GEMINI_API_KEY (preferred) or GOOGLE_API_KEY "
            "in your environment or in a .env file."
        )
    return Client(api_key=key.strip())


def generate_structured(
    client: GenaiClient,
    model: str,
    contents: Any,
    response_model: type[T],
    *,
    system_instruction: str | None = None,
    temperature: float = 0.0,
    max_output_tokens: int | None = None,
) -> T:
    """
    Call ``generate_content`` with JSON constrained to ``response_model`` (Pydantic).

    Use ``GEMINI_MODEL_FLASH`` for fast / cheap multimodal extraction; ``GEMINI_MODEL_PRO``
    for harder reasoning or ambiguous documents.
    """
    from google.genai import types

    config_kw: dict[str, Any] = {
        "temperature": temperature,
        "response_mime_type": "application/json",
        "response_schema": response_model,
    }
    if system_instruction is not None:
        config_kw["system_instruction"] = system_instruction
    if max_output_tokens is not None:
        config_kw["max_output_tokens"] = max_output_tokens

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(**config_kw),
    )
    parsed = response.parsed
    if parsed is None:
        text = getattr(response, "text", None)
        raise RuntimeError(
            "Gemini returned no parsed structured output. "
            f"response.text={text!r}"
        )
    if isinstance(parsed, response_model):
        return parsed
    if isinstance(parsed, BaseModel):
        return response_model.model_validate(parsed.model_dump())
    return response_model.model_validate(parsed)
