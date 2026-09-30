"""Identity and role-based access.

Access tiers are hierarchical: Publish < Archive < Portfolio. A user's single
`access` value is a ceiling, not an exact match — Archive also grants
everything Publish can do, Portfolio also grants everything Archive can do.

The LAN ID is meant to come from a header a fronting proxy/CML injects once
that is confirmed to be in place (see `_HEADER_CANDIDATES`). Until then,
`_detect_lan_id` finds nothing and the sidebar's manual override lets you
test the app as any listed user locally.

"Create user" is a separate, hardcoded admin list — intentionally outside
the users table and the three business tiers, per the spec this was built
against.
"""
from __future__ import annotations

import streamlit as st

from . import db

ADMIN_LAN_IDS = {"GMTRUN"}

ACCESS_LEVELS = {"publish": 1, "archive": 2, "portfolio": 3}
ACCESS_ORDER = ["publish", "archive", "portfolio"]

_HEADER_CANDIDATES = ("Remote-User", "Remote-User-Perm", "X-Forwarded-User")


def _detect_lan_id() -> str | None:
    try:
        headers = st.context.headers
    except Exception:
        return None
    for key in _HEADER_CANDIDATES:
        value = headers.get(key)
        if value:
            return value.strip().upper()
    return None


def is_header_detected() -> bool:
    return bool(_detect_lan_id())


def current_lan_id() -> str:
    """The signed-in LAN ID for this session, or "" if none is known yet."""
    ss = st.session_state
    if "lan_id" not in ss:
        ss.lan_id = _detect_lan_id() or ""
    return ss.lan_id


def set_lan_id_override(lan_id: str) -> None:
    st.session_state.lan_id = lan_id.strip().upper()
    st.session_state.pop("_user_cache", None)


def current_user() -> dict | None:
    """The users-table row for the signed-in LAN ID, or None if unlisted."""
    lan_id = current_lan_id()
    if not lan_id:
        return None
    ss = st.session_state
    cache = ss.get("_user_cache")
    if cache is not None and cache[0] == lan_id:
        return cache[1]
    user = db.get_user(lan_id)
    ss._user_cache = (lan_id, user)
    return user


def is_admin() -> bool:
    return current_lan_id() in ADMIN_LAN_IDS


def has_level(user: dict | None, level: str) -> bool:
    if not user:
        return False
    return ACCESS_LEVELS.get(user.get("access"), 0) >= ACCESS_LEVELS[level]


def is_portfolio() -> bool:
    return has_level(current_user(), "portfolio")


def can_submit() -> bool:
    """Any listed user, of any tier, can create/publish their own drafts."""
    return current_user() is not None


def can_archive_entry(owner_lan_id: str) -> bool:
    """Only the entry owner's own manager, with at least Archive access, may archive it."""
    user = current_user()
    if not has_level(user, "archive") or not owner_lan_id:
        return False
    owner = db.get_user(owner_lan_id)
    return bool(owner) and owner.get("manager") == user["lanId"]


def can_view(product: dict) -> bool:
    """Portfolio tier sees everything; everyone else only their own submissions
    (plus legacy/demo data that predates ownership, which stays shared)."""
    owner = product.get("ownerLanId") or ""
    if not owner:
        return True
    return is_portfolio() or owner == current_lan_id()


def is_manager_of_anyone() -> bool:
    lan_id = current_lan_id()
    if not lan_id:
        return False
    return any(u.get("manager") == lan_id for u in db.fetch_users())
