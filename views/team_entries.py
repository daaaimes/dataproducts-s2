"""Team Entries — the Published and Archived entries of the people who report to you.

Shown to Archive-tier users. Archiving is scoped to the manager relationship, not the
tier alone (see app.auth.can_archive_entry): a manager can archive an entry only for a
person whose `manager` is them. Drafts stay private to their owner and are not listed.
"""
from __future__ import annotations

import streamlit as st

from app import auth, store
from app.format import money, relative_date
from app.ui import badge, empty_state, esc, rule, write
from .common import goto, page_header

STATUS_TONE = {"published": "good", "archived": "neutral"}


def render() -> None:
    page_header("Team Entries", "Valuations submitted by the people who report to you.")

    user = auth.current_user()
    if not auth.has_level(user, "archive"):
        st.info("This page is for users with Archive access.")
        return

    c = store.currency()
    reports = store.direct_reports()
    entries = store.team_entries()

    if not reports:
        write(f'<div class="dpv-card">{empty_state("No one reports to you yet", "Ask an admin to set you as the manager of your team on the Create User page.")}</div>')
        return

    write(f'<p style="margin:-6px 0 16px;font-size:12.5px;color:var(--text-muted)">'
          f'Your team: {esc(", ".join(reports))}</p>')
    if not entries:
        write(f'<div class="dpv-card">{empty_state("No team entries yet", "Published and archived entries from your team appear here. Drafts stay private to their owner.")}</div>')
        return

    for r in entries:
        _row(r, c)


def _row(r, c: str) -> None:
    p, v = r["product"], r["valuation"]
    status = p.get("recordStatus", "published")
    write(rule())
    head, val, actions = st.columns([2.3, 1.2, 1.6], vertical_alignment="center")
    with head:
        write(f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">'
              f'<span style="font-size:14px;font-weight:600;color:var(--text-primary)">'
              f'{esc(p["name"] or "Untitled")}</span>'
              f'{badge(status.capitalize(), STATUS_TONE.get(status, "neutral"))}</div>'
              f'<div style="margin-top:2px;font-size:11.5px;color:var(--text-muted)">'
              f'{esc(p.get("ownerLanId", ""))} · {esc(p.get("department", ""))} · '
              f'{esc(p.get("subDepartment", ""))} · Updated {relative_date(p["updatedAt"])}</div>')
    with val:
        write(f'<div class="tnum" style="text-align:right;font-size:14px;font-weight:600;'
              f'color:var(--text-primary)">{money(v["threeYearValue"], c)}</div>'
              f'<div style="text-align:right;font-size:10.5px;color:var(--text-muted)">'
              "3-year value</div>")
    with actions:
        b1, b2 = st.columns(2)
        if b1.button("View", key=f"tview_{p['id']}", use_container_width=True):
            goto("product", selected_product=p["id"])
        if status == "published" and auth.can_archive_entry(p.get("ownerLanId", "")):
            if b2.button("Archive", key=f"tarc_{p['id']}", use_container_width=True):
                if store.archive_product(p["id"]):
                    st.rerun()
