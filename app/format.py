"""Formatting helpers — a faithful port of src/lib/format.ts.

JavaScript's Number.prototype.toFixed rounds half away from zero on the exact
binary value of the double; Python's format() uses banker's rounding. The two
disagree on values like 2.5, so every fixed-point conversion here goes through
_to_fixed, which reproduces the JavaScript behaviour exactly.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

CurrencyCode = str


def js_round(v: float) -> float:
    """Math.round: half rounds toward +Infinity (not away from zero)."""
    if not math.isfinite(v):
        return v
    return math.floor(v + 0.5)


def _to_fixed(v: float, decimals: int) -> str:
    """Number.prototype.toFixed, including its half-away-from-zero rounding."""
    if not math.isfinite(v):
        return "NaN" if math.isnan(v) else ("Infinity" if v > 0 else "-Infinity")
    quant = Decimal(1).scaleb(-decimals)
    return str(Decimal(v).quantize(quant, rounding=ROUND_HALF_UP))


def _trim(n: float, decimals: int) -> str:
    s = _to_fixed(n, decimals)
    s = re.sub(r"\.0+$", "", s)
    s = re.sub(r"(\.\d*?)0+$", r"\1", s)
    return s


def _group(n: float, decimals: int = 0) -> str:
    """Intl.NumberFormat('en-SG') — comma thousands separators."""
    return f"{Decimal(_to_fixed(n, decimals)):,.{decimals}f}"


def compact_number(v: float, decimals: int = 1) -> str:
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    if abs_v >= 1e12:
        return f"{sign}{_trim(abs_v / 1e12, decimals)}T"
    if abs_v >= 1e9:
        return f"{sign}{_trim(abs_v / 1e9, decimals)}B"
    if abs_v >= 1e6:
        return f"{sign}{_trim(abs_v / 1e6, decimals)}M"
    if abs_v >= 1e3:
        return f"{sign}{_trim(abs_v / 1e3, 0 if abs_v >= 1e5 else decimals)}K"
    return f"{sign}{_trim(abs_v, 1 if abs_v < 10 and abs_v % 1 != 0 else 0)}"


def money(v: float, currency: CurrencyCode = "SGD", decimals: int = 1) -> str:
    """Executive money format: "SGD 18.7M"."""
    if not math.isfinite(v):
        return "—"
    neg = v < 0
    return f"{'−' if neg else ''}{currency} {compact_number(abs(v), decimals)}"


def money_full(v: float, currency: CurrencyCode = "SGD") -> str:
    """Full precision money: "SGD 18,700,000"."""
    if not math.isfinite(v):
        return "—"
    return f"{currency} {_group(js_round(v))}"


def num(v: float, decimals: int = 0) -> str:
    if not math.isfinite(v):
        return "—"
    return _group(v, decimals)


def pct(v: float, decimals: int = 0) -> str:
    """pct(0.824) -> "82%"; pct(0.824, 1) -> "82.4%"."""
    if not math.isfinite(v):
        return "—"
    return f"{_to_fixed(v * 100, decimals)}%"


def ratio_pct(v: float, decimals: int = 0) -> str:
    """For ratios already expressed as a multiple."""
    if not math.isfinite(v):
        return "—"
    if v > 100:
        return ">10,000%"
    return f"{_to_fixed(v * 100, decimals)}%"


def months(v: float) -> str:
    if not math.isfinite(v) or v <= 0:
        return "Not recovered"
    if v >= 120:
        return "10+ years"
    r = int(js_round(v))
    return "1 month" if r == 1 else f"{r} months"


def months_short(v: float) -> str:
    if not math.isfinite(v) or v <= 0:
        return "—"
    if v >= 120:
        return "120+ mo"
    return f"{int(js_round(v))} mo"


def signed(v: float, fmt) -> str:
    return f"{'+' if v > 0 else ''}{fmt(v)}"


def initials(name: str) -> str:
    return "".join(w[0].upper() for w in re.split(r"\s+", name) if w)[:2]


def relative_date(iso: str) -> str:
    """en-SG medium date: "29 Aug 2026"."""
    text = iso.replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(text)
    except ValueError:
        d = datetime.fromisoformat(text[:10])
    return f"{d.day:02d} {d.strftime('%b')} {d.year}"


def clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))
