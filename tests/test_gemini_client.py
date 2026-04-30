"""Gemini client configuration (no live API calls)."""

import pytest

from trade_validator.clients.gemini_client import (
    GEMINI_MODEL_FLASH,
    GEMINI_MODEL_PRO,
    get_gemini_client,
)


def test_model_constants():
    assert GEMINI_MODEL_FLASH == "gemini-2.5-flash"
    assert GEMINI_MODEL_PRO == "gemini-2.5-pro"


def test_get_gemini_client_requires_key(monkeypatch: pytest.MonkeyPatch, tmp_path):
    # Avoid picking up keys from a developer `.env` in the repo root.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_gemini_client()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = get_gemini_client()
    assert client is not None


def test_get_gemini_client_explicit_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = get_gemini_client(api_key=" explicit ")
    assert client is not None
