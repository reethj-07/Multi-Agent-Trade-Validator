"""Per-agent implementations (Gemini-backed where applicable)."""

from __future__ import annotations

__all__ = ["run_extractor", "run_router", "run_validator", "sniff_mime_type"]


def __getattr__(name: str):
    if name == "run_extractor":
        from trade_validator.agents.extractor import run_extractor

        return run_extractor
    if name == "sniff_mime_type":
        from trade_validator.agents.extractor import sniff_mime_type

        return sniff_mime_type
    if name == "run_router":
        from trade_validator.agents.router import run_router

        return run_router
    if name == "run_validator":
        from trade_validator.agents.validator import run_validator

        return run_validator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
