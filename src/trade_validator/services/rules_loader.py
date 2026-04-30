"""Load customer JSON rules from the package."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any


def load_rules(customer_id: str) -> dict[str, Any]:
    """Return rule dict for ``customer_id`` (e.g. ``acme_retail_eu``)."""
    filename = f"{customer_id}.json"
    try:
        pkg = resources.files("trade_validator.rules").joinpath(filename)
        text = pkg.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as e:
        raise FileNotFoundError(f"No rule set for customer_id={customer_id!r}") from e
    data = json.loads(text)
    if data.get("customer_id") != customer_id:
        raise ValueError(
            f"Rule file customer_id mismatch: expected {customer_id!r}, "
            f"got {data.get('customer_id')!r}"
        )
    return data
