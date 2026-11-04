"""Small helpers shared by the pipeline and eval scripts."""
from __future__ import annotations

import re


def canon(symbol: str) -> str:
    """UN house style: upper-case series, title-case Rev./Add./Corr. suffixes."""
    s = re.sub(r"\s+", "", symbol).upper()
    for part in ("REV", "ADD", "CORR"):
        s = s.replace(f"/{part}.", f"/{part.title()}.")
    return s


def safe_name(symbol: str) -> str:
    """File-system-safe form of a symbol: E/CN.4/SR.60 -> E_CN.4_SR.60."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol).strip("_")
