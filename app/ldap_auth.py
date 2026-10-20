"""Checks a LAN ID and password against the company LDAP / Active Directory server.

Nothing here stores or logs a password: it is sent to the directory server to
sign in as that person, and discarded. It is turned on by setting
DPV_LDAP_SERVER on the CML Application; the other settings are optional.

Settings (environment variables):
  DPV_LDAP_SERVER        ldaps://dc.example.com:636  (or ldap://host:389 with STARTTLS)
                         (LDAP_SERVER works too)
  DPV_LDAP_BASE_DN       DC=corp,DC=example,DC=com or simply corp.example.com (used to
                         find the user, and to work out the domain for "user@corp.example.com")
                         (LDAP_BASE_DN works too)
  DPV_LDAP_USER_ATTR     attribute holding the LAN ID (default sAMAccountName)
  DPV_LDAP_BIND_TEMPLATE how to turn a LAN ID into a sign-in name, e.g. "CORP\\{user}"
                         or "{user}@corp.example.com". Default: the domain taken from
                         the base DN, i.e. "{user}@<domain>"
  DPV_LDAP_STARTTLS      1 = upgrade a plain ldap:// connection with STARTTLS
  DPV_LDAP_CA_FILE       path to the CA certificate that signed the server's certificate
  DPV_LDAP_ALLOW_PLAINTEXT  1 = allow an unencrypted connection (passwords in clear
                         text on the network). Off by default; the sign-in is refused.
  DPV_LDAP_TIMEOUT       seconds to wait for the server (default 8)

ldap3 is imported only when a sign-in is attempted, so the app still runs on a
machine that does not have it, as long as DPV_LDAP_SERVER is not set.
"""
from __future__ import annotations

import os
import re
import ssl
import sys

# A LAN ID is letters, digits and . _ - only. Anything else is rejected before it
# can reach a directory filter or a sign-in name.
_LAN_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

BAD_CREDENTIALS = "Incorrect LAN ID or password."
UNAVAILABLE = "We could not reach the sign-in server. Please try again, or contact an admin."


def _setting(name: str, default: str = "") -> str:
    """DPV_LDAP_<name>, falling back to the unprefixed LDAP_<name> some projects already use."""
    value = os.environ.get(f"DPV_LDAP_{name}") or os.environ.get(f"LDAP_{name}") or default
    return value.strip().strip('"').strip("'")


def configured() -> bool:
    return bool(_setting("SERVER"))


def valid_lan_id(value: str) -> bool:
    return bool(_LAN_ID.match(value or ""))


def domain_from_base_dn(base_dn: str) -> str:
    """DC=corp,DC=example,DC=com  ->  corp.example.com   (a plain DNS name is kept as is)"""
    base_dn = (base_dn or "").strip()
    if base_dn and "=" not in base_dn:
        return base_dn.lower()
    parts = [p.split("=", 1)[1].strip() for p in base_dn.split(",")
             if p.strip().upper().startswith("DC=") and "=" in p]
    return ".".join(parts).lower()


def search_base(base_dn: str) -> str:
    """The base to search under, as a real DN: corp.example.com -> DC=corp,DC=example,DC=com"""
    base_dn = (base_dn or "").strip()
    if base_dn and "=" not in base_dn:
        return ",".join(f"DC={label}" for label in base_dn.split(".") if label)
    return base_dn


def bind_name(lan_id: str) -> str:
    """The name to sign in to the directory with."""
    template = _setting("BIND_TEMPLATE")
    if template:
        return template.replace("{user}", lan_id)
    domain = domain_from_base_dn(_setting("BASE_DN"))
    return f"{lan_id}@{domain}" if domain else lan_id


def _log(message: str) -> None:
    print(f"[ldap] {message}", file=sys.stderr, flush=True)


def authenticate(username: str, password: str) -> tuple[str | None, str]:
    """Returns (LAN ID, "") when the password is right, else (None, message to show)."""
    username = (username or "").strip()
    if not valid_lan_id(username) or not password:
        # An empty password must never reach the server: many directories treat a
        # bind with a name and no password as a successful anonymous bind.
        return None, BAD_CREDENTIALS

    server_url = _setting("SERVER")
    use_ssl = server_url.lower().startswith("ldaps://")
    starttls = _setting("STARTTLS") == "1"
    if not use_ssl and not starttls and _setting("ALLOW_PLAINTEXT") != "1":
        _log("refusing an unencrypted sign-in: use ldaps://, set DPV_LDAP_STARTTLS=1, "
             "or set DPV_LDAP_ALLOW_PLAINTEXT=1 to accept the risk")
        return None, UNAVAILABLE

    try:
        from ldap3 import SIMPLE, SUBTREE, Connection, Server, Tls
        from ldap3.core.exceptions import LDAPException
        from ldap3.utils.conv import escape_filter_chars
    except ImportError:
        _log("the ldap3 package is not installed")
        return None, UNAVAILABLE

    timeout = int(_setting("TIMEOUT", "8") or 8)
    ca_file = _setting("CA_FILE") or None
    attr = _setting("USER_ATTR", "sAMAccountName") or "sAMAccountName"
    base_dn = search_base(_setting("BASE_DN"))

    conn = None
    try:
        tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=ca_file) if (use_ssl or starttls) else None
        server = Server(server_url, use_ssl=use_ssl, tls=tls, connect_timeout=timeout)
        conn = Connection(server, user=bind_name(username), password=password,
                          authentication=SIMPLE, receive_timeout=timeout)
        conn.open()
        if starttls and not use_ssl:
            conn.start_tls()
        if not conn.bind():
            return None, BAD_CREDENTIALS

        # Signed in. Prefer the directory's own spelling of the LAN ID.
        lan_id = username.upper()
        if base_dn:
            try:
                conn.search(search_base=base_dn, search_scope=SUBTREE,
                            search_filter=f"({attr}={escape_filter_chars(username)})",
                            attributes=[attr], size_limit=2)
                if len(conn.entries) == 1:
                    found = str(conn.entries[0][attr].value or "").strip()
                    if found and valid_lan_id(found):
                        lan_id = found.upper()
            except Exception as exc:  # the password was already accepted
                _log(f"user lookup skipped: {type(exc).__name__}: {exc}")
        return lan_id, ""
    except LDAPException as exc:
        _log(f"{type(exc).__name__}: {exc}")
        return None, UNAVAILABLE
    except OSError as exc:  # DNS, refused, TLS handshake and similar
        _log(f"{type(exc).__name__}: {exc}")
        return None, UNAVAILABLE
    finally:
        try:
            if conn is not None:
                conn.unbind()
        except Exception:
            pass
