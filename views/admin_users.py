"""Create User — admin-only management of the Publish/Archive/Portfolio users table.

Gated on app.auth.is_admin(), a hardcoded list separate from the three
business access tiers this table grants — see app/auth.py.
"""
from __future__ import annotations

import streamlit as st

from app import auth, db
from app.ui import badge, esc, rule, write
from .common import page_header

ACCESS_CHOICES = ["publish", "archive", "portfolio"]
ACCESS_TONE = {"publish": "neutral", "archive": "info", "portfolio": "good"}


def render() -> None:
    page_header("Create User", "Manage who can submit, archive and see the full portfolio.")

    if not auth.is_admin():
        st.error("You don't have access to this page.")
        return

    users = db.fetch_users()
    lan_ids = [u["lanId"] for u in users]

    with st.form("new_user_form", clear_on_submit=True):
        a, b = st.columns(2)
        lan_id = a.text_input("Lan ID", placeholder="e.g. GMTRUN").strip().upper()
        access = b.selectbox("Access required", ACCESS_CHOICES,
                             format_func=lambda a: a.capitalize())
        c, d = st.columns(2)
        department = c.text_input("Department", placeholder="e.g. IG")
        sub_department = d.text_input("Sub-department", placeholder="e.g. Data")
        manager = st.selectbox("Manager", ["(none)"] + lan_ids)
        submitted = st.form_submit_button("Save user", type="primary")

    if submitted:
        if not lan_id or not department.strip() or not sub_department.strip():
            st.error("Lan ID, Department and Sub-department are all required.")
        else:
            db.upsert_user({
                "lanId": lan_id, "department": department.strip(),
                "subDepartment": sub_department.strip(),
                "manager": None if manager == "(none)" else manager,
                "access": access,
            })
            st.success(f"Saved {lan_id}.")
            st.rerun()

    write(rule())
    write('<h3 class="dpv-h3">Existing users</h3>')
    if not users:
        st.caption("No users yet.")
        return

    for u in users:
        cols = st.columns([1.3, 1.3, 1.3, 1.3, 1.2, 0.8], vertical_alignment="center")
        cols[0].markdown(f"**{esc(u['lanId'])}**", unsafe_allow_html=True)
        cols[1].write(u["department"])
        cols[2].write(u["subDepartment"])
        cols[3].write(u["manager"] or "—")
        with cols[4]:
            write(badge(u["access"].capitalize(), ACCESS_TONE.get(u["access"], "neutral")))
        if cols[5].button("Delete", key=f"del_{u['lanId']}", use_container_width=True):
            db.delete_user(u["lanId"])
            st.rerun()
