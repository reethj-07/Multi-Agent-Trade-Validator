"""Normalize strings for rule comparison."""

from __future__ import annotations

import re
import unicodedata


def normalize_spaces_upper(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_hs_for_regex(s: str) -> str:
    """Keep digits and single dot for HS pattern matching."""
    s = unicodedata.normalize("NFKC", s).strip().upper()
    s = re.sub(r"\s+", "", s)
    return s


def normalize_port(s: str) -> str:
    return normalize_spaces_upper(s)


def primary_port_city(s: str) -> str:
    """
    Trade docs often print ``Port of Loading: Shanghai, China``.
    Compare the **city** token to the approved list, not ``CITY, COUNTRY``.

    Handles ASCII comma, fullwidth comma (U+FF0C), and ideographic comma (U+3001)
    before splitting.
    """
    raw = unicodedata.normalize("NFKC", str(s)).strip()
    raw = re.sub(r"[\uFF0C\u3001]", ",", raw)
    head = raw.split(",")[0].strip()
    return normalize_spaces_upper(head)
