"""Runtime limits and defaults."""

from __future__ import annotations

import os

# Hard cap on LLM round-trips per pipeline run (prevents runaway cost).
MAX_LLM_CALLS_PER_PIPELINE = int(os.environ.get("TRADE_VALIDATOR_MAX_LLM_CALLS", "8"))

DEFAULT_CUSTOMER_ID = "acme_retail_eu"

# SQLite file under cwd unless overridden
DATABASE_URL = os.environ.get(
    "TRADE_VALIDATOR_DATABASE_URL",
    "sqlite:///./trade_validator.db",
)

API_HOST = os.environ.get("TRADE_VALIDATOR_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TRADE_VALIDATOR_API_PORT", "8000"))

# Extraction: very low confidence fields are treated as uncertain downstream
EXTRACTION_UNCERTAIN_THRESHOLD = float(
    os.environ.get("TRADE_VALIDATOR_EXTRACTION_UNCERTAIN_THRESHOLD", "0.35")
)
