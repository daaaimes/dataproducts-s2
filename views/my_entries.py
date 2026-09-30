"""My Entries — the current user's own submissions, across every status.

Dashboard and Portfolio only ever show Published work (store.rows()), so
this page is the one place a user can find, continue, publish or duplicate
their own Drafts and Archived entries. Anyone with Archive access also sees
a queue here of their direct reports' Published entries waiting to be
archived — archiving is scoped to the manager relationship, not the tier
alone (see app.auth.can_archive_entry).
"""
from __future__ import annotations

import streamlit as st

from app import auth, store
from app.format import money, relative_date
from app.ui import badge, empty_state, esc, rule, write
from .common import goto, page_header

STATUS_TONE = {"draft": "warn", "published": "good", "archived": "neutral"}


def render() -> None:
    page_header("My Entries", "Every valuation you've submitted, and its current status.")

    user = auth.current_user()
    if not user:
        st.info("You're not yet set up with submission access — ask an admin to add your "
                "LAN ID before you can create or track valuations.")
        return

    c = store.currency()
    write(f'<p style="margin:-6px 0 16px;font-size:12.5px;color:var(--text-muted)">'
          f'{esc(user["department"])} · {esc(user["subDepartment"])} · '
          f'{esc(user["access"].capitalize())} access</p>')

    entries = store.my_entries()
    if not entries:
        write(f'<div class="dpv-card">'
              f'{empty_state("No submissions yet", "Value a data product to see it here.")}</div>')
    else:
        for r in entries:
            _entry_row(r, c)

    queue = store.archive_queue()
    if queue:
        write(rule() + '<h3 class="dpv-h3" style="margin-top:8px">Awaiting archive — your team</h3>'
              '<p class="dpv-sub">Published entries from people who report to you. Archive one '
              "once the owner has asked you to, so they can duplicate it and start the next "
              "version.</p>")
        for r in queue:
            _queue_row(r, c)


def _entry_row(r, c: str) -> None:
    p, v = r["product"], r["valuation"]
    status = p.get("recordStatus", "published")
    write(rule())
    head, val, actions = st.columns([2.3, 1.2, 2.3], vertical_alignment="center")
    with head:
        write(f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
              f'<span style="font-size:14px;font-weight:600;color:var(--text-primary)">'
              f'{esc(p["name"] or "Untitled")}</span>'
              f'{badge(status.capitalize(), STATUS_TONE.get(status, "neutral"))}</div>'
              f'<div style="margin-top:2px;font-size:11.5px;color:var(--text-muted)">'
              f'Updated {relative_date(p["updatedAt"])}</div>')
    with val:
        write(f'<div class="tnum" style="text-align:right;font-size:14px;font-weight:600;'
              f'color:var(--text-primary)">{money(v["threeYearValue"], c)}</div>'
              f'<div style="text-align:right;font-size:10.5px;color:var(--text-muted)">'
              "3-year value</div>")
    with actions:
        b1, b2, b3 = st.columns(3)
        if status == "draft":
            if b1.button("Continue", key=f"cont_{p['id']}", use_container_width=True):
                st.session_state.edit_product = p["id"]
                goto("value")
            if b2.button("Publish", key=f"pub_{p['id']}", type="primary",
                        use_container_width=True):
                if store.publish_product(p["id"]):
                    st.rerun()
        else:
            if b1.button("View", key=f"view_{p['id']}", use_container_width=True):
                goto("product", selected_product=p["id"])
        if b3.button("Duplicate", key=f"dup_{p['id']}", use_container_width=True):
            new_id = store.duplicate_product(p["id"])
            if new_id:
                st.session_state.edit_product = new_id
                goto("value")


def _queue_row(r, c: str) -> None:
    p, v = r["product"], r["valuation"]
    write(rule())
    head, val, action = st.columns([2.3, 1.2, 1], vertical_alignment="center")
    with head:
        write(f'<span style="font-size:13.5px;font-weight:600;color:var(--text-primary)">'
              f'{esc(p["name"])}</span>'
              f'<div style="margin-top:2px;font-size:11.5px;color:var(--text-muted)">'
              f'{esc(p.get("ownerLanId", ""))} · {esc(p.get("department", ""))} · '
              f'{esc(p.get("subDepartment", ""))}</div>')
    with val:
        write(f'<div class="tnum" style="text-align:right;font-size:13px;font-weight:600;'
              f'color:var(--text-primary)">{money(v["threeYearValue"], c)}</div>')
    with action:
        if st.button("Archive", key=f"arc_{p['id']}", use_container_width=True):
            if store.archive_product(p["id"]):
                st.rerun()
