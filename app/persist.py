"""Keep user settings across a browser refresh.

Streamlit's session_state lives only as long as the websocket, so a reload
would otherwise throw away the theme, currency and financial parameters the
user chose — state the original app kept in localStorage. The settings that
change what is on screen are mirrored into the query string instead, which
also makes a configured view shareable by URL.

Only values that differ from the defaults are written, so the URL stays clean
for anyone using the app as it ships.
"""
from __future__ import annotations

import streamlit as st

from .domain import DEFAULT_SETTINGS

# query-param key -> (settings key, parser)
FIELDS = {
    "t": ("theme", lambda v: v if v in ("light", "dark") else None),
    "cur": ("currency", lambda v: v if v in
            ("SGD", "USD", "EUR", "GBP", "AUD", "HKD", "INR") else None),
    "dr": ("discountRate", lambda v: _num(v, 0.0, 0.25)),
    "hy": ("horizonYears", lambda v: _int(v, 3, 10)),
    "wh": ("annualWorkingHours", lambda v: _int(v, 1000, 2400)),
    "gr": ("guardrailsEnabled", lambda v: v == "1"),
    "org": ("organisationName", lambda v: v[:80] or None),
}

ENCODERS = {
    "theme": str,
    "currency": str,
    "discountRate": lambda v: f"{v:g}",
    "horizonYears": lambda v: str(int(v)),
    "annualWorkingHours": lambda v: str(int(v)),
    "guardrailsEnabled": lambda v: "1" if v else "0",
    "organisationName": str,
}


def _num(v, lo, hi):
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def _int(v, lo, hi):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return n if lo <= n <= hi else None


def load_into(settings: dict) -> None:
    """Apply any settings present in the query string. Invalid values are ignored."""
    params = st.query_params
    for param, (key, parse) in FIELDS.items():
        if param not in params:
            continue
        value = parse(params[param])
        if value is not None:
            settings[key] = value


def save(settings: dict) -> None:
    """Mirror the non-default settings back into the query string."""
    wanted = {}
    for param, (key, _parse) in FIELDS.items():
        value = settings.get(key)
        if value != DEFAULT_SETTINGS[key]:
            wanted[param] = ENCODERS[key](value)

    current = {p: st.query_params[p] for p in FIELDS if p in st.query_params}
    if current == wanted:
        return
    for param in FIELDS:
        if param in st.query_params and param not in wanted:
            del st.query_params[param]
    for param, value in wanted.items():
        st.query_params[param] = value
