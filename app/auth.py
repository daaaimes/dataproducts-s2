"""Identity and role-based access.

Access tiers are hierarchical: Publish < Archive < Portfolio. A user's single
`access` value is a ceiling, not an exact match — Archive also grants
everything Publish can do, Portfolio also grants everything Archive can do.

Who the user is comes from, in order of preference:
  1. A sign-in page checked against the company LDAP / Active Directory server,
     when DPV_LDAP_SERVER is set (see app/ldap_auth.py). The app then shows nothing
     until the person has signed in with their LAN ID and password, and the
     manual override and any proxy header are ignored.
  2. A header a fronting proxy/CML injects (see `_HEADER_CANDIDATES`), when no
     LDAP server is configured.
  3. For a local run only, the sidebar's manual override (see `override_allowed`).

"Create user" is a separate, hardcoded admin list — intentionally outside
the users table and the three business tiers, per the spec this was built
against.
"""
from __future__ import annotations

import os
import time

import streamlit as st

from . import db, ldap_auth

ADMIN_LAN_IDS = {"GMTRUN", "FCDTUN", "FCDAKG", "GMTBRL"}

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


def signin_required() -> bool:
    """True when the app asks for a LAN ID and password (an LDAP server is configured)."""
    return ldap_auth.configured()


def is_header_detected() -> bool:
    return bool(_detect_lan_id())


def override_allowed() -> bool:
    """Whether the manual "set LAN ID" box may be used.

    It lets whoever types claim any identity, so it must never be reachable on a
    deployed CML Application, where the identity has to come from CML's sign-in.
    It is on for a local run (no CML environment), or when DPV_ALLOW_LAN_OVERRIDE=1
    is set on the Application as a deliberate, admin-controlled break-glass switch.
    """
    if signin_required():
        return False  # the password sign-in is the only way in; typing a name is never an identity
    if os.environ.get("DPV_ALLOW_LAN_OVERRIDE") == "1":
        return True
    return not os.environ.get("CDSW_APP_PORT")


def current_lan_id() -> str:
    """The signed-in LAN ID for this session, or "" if none is known.

    A header from CML's sign-in always wins. Otherwise a manual override is only
    honoured where override_allowed(), so a missing header can't be papered over
    by typing a name on a deployed app."""
    ss = st.session_state
    if signin_required():
        ss.lan_id = ss.get("_signed_in_lan_id", "")
        return ss.lan_id
    detected = _detect_lan_id()
    if detected:
        ss.lan_id = detected
    elif "lan_id" not in ss or not override_allowed():
        ss.lan_id = ""
    return ss.lan_id


def set_lan_id_override(lan_id: str) -> None:
    if not override_allowed():
        return
    st.session_state.lan_id = lan_id.strip().upper()
    st.session_state.pop("_user_cache", None)


_MAX_FAILURES = 5
_LOCKOUT_SECONDS = 60


def sign_in(username: str, password: str) -> str:
    """Try to sign this session in. Returns "" on success, else a message to show.

    After a few wrong passwords in a row the session is locked out briefly. That
    only slows a person down; the directory's own lockout policy is the real
    protection against someone guessing a password."""
    ss = st.session_state
    now = time.time()
    if ss.get("_signin_locked_until", 0) > now:
        wait = int(ss["_signin_locked_until"] - now) + 1
        return f"Too many attempts. Please wait {wait} seconds and try again."
    lan_id, message = ldap_auth.authenticate(username, password)
    if lan_id:
        ss.pop("_signin_failures", None)
        ss.pop("_signin_locked_until", None)
        ss["_signed_in_lan_id"] = lan_id
        ss.pop("_user_cache", None)
        return ""
    ss["_signin_failures"] = ss.get("_signin_failures", 0) + 1
    if ss["_signin_failures"] >= _MAX_FAILURES:
        ss["_signin_locked_until"] = now + _LOCKOUT_SECONDS
        ss["_signin_failures"] = 0
    return message


def sign_out() -> None:
    for key in ("_signed_in_lan_id", "lan_id", "_user_cache", "_signin_failures",
                "_signin_locked_until"):
        st.session_state.pop(key, None)


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
