"""Create User — admin-only management of the Publish/Archive/Portfolio users table.

Gated on app.auth.is_admin(), a hardcoded list separate from the three
business access tiers this table grants — see app/auth.py.
"""
from __future__ import annotations

import streamlit as st

from app import auth, db, user_import
from app.ui import badge, esc, rule, write
from .common import page_header

ACCESS_CHOICES = ["publish", "archive", "portfolio"]
ACCESS_TONE = {"publish": "neutral", "archive": "info", "portfolio": "good"}


def render() -> None:
    page_header("Create User", "Manage who can submit, archive and see the full portfolio.")

    if not auth.is_admin():
        st.error("You don't have access to this page.")
        return

    if st.session_state.get("_bulk_done"):
        st.success(st.session_state.pop("_bulk_done"))

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

    _bulk_import(users)

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


def _bulk_import(users: list[dict]) -> None:
    """Add or update many users from a CSV file. Nothing is deleted, and a file with
    any problem is refused whole, so an import is never half done."""
    write(rule())
    write('<h3 class="dpv-h3">Bulk import from CSV</h3>')
    st.caption("Columns: lan_id, department, sub_department, manager, access (publish, archive or "
               "portfolio). Manager can be blank. People already listed are updated; nobody is "
               "removed. Edit your current users in Excel by downloading them below, changing "
               "rows, and uploading the file again.")
    d1, d2, _ = st.columns([1, 1, 2])
    d1.download_button("Download blank template", user_import.template_csv(),
                       file_name="users_template.csv", mime="text/csv", use_container_width=True)
    d2.download_button("Download current users", user_import.users_to_csv(users),
                       file_name="users_current.csv", mime="text/csv",
                       disabled=not users, use_container_width=True)

    round_no = st.session_state.get("_bulk_round", 0)
    upload = st.file_uploader("Choose a CSV file", type=["csv"], key=f"bulk_users_file_{round_no}")
    if upload is None:
        return

    rows, file_problems = user_import.parse_users_csv(upload.getvalue(), users)
    if file_problems:
        for p in file_problems:
            st.error(p)
        return

    bad = [r for r in rows if r["problems"]]
    counts = {s: sum(1 for r in rows if r["status"] == s and not r["problems"])
              for s in ("New", "Update", "No change")}
    st.dataframe(
        [{"Line": r["line"], "LAN ID": r["lanId"], "Department": r["department"],
          "Sub-department": r["subDepartment"], "Manager": r["manager"] or "—",
          "Access": r["access"].capitalize() if r["access"] in user_import.ACCESS_CHOICES else r["access"],
          "Result": ("Problem: " + "; ".join(r["problems"])) if r["problems"] else r["status"]}
         for r in rows],
        hide_index=True, use_container_width=True,
        column_config={"Result": st.column_config.TextColumn("Result", width="large")})
    if bad:
        for r in bad:
            write(f'<div style="font-size:13px;line-height:1.6;margin-bottom:4px"><strong>Line '
                  f'{r["line"]}</strong> {esc(r["lanId"] or "(blank)")} — '
                  f'{esc("; ".join(r["problems"]))}</div>')
        many = len(bad) > 1
        st.error(f"{len(bad)} row{'s' if many else ''} {'need' if many else 'needs'} fixing before "
                 "anything can be imported. Correct the file and upload it again; nothing has "
                 "been saved.")
        return

    st.info(f"{counts['New']} new, {counts['Update']} to update, {counts['No change']} unchanged.")
    to_save = [r for r in rows if r["status"] != "No change"]
    if not to_save:
        st.caption("Everyone in this file is already set up exactly like this.")
        return
    if st.button(f"Import {len(to_save)} user{'s' if len(to_save) > 1 else ''}", type="primary",
                 key=f"bulk_users_go_{round_no}"):
        saved = db.upsert_users(to_save)
        st.session_state["_bulk_round"] = round_no + 1  # clears the uploader
        st.session_state["_bulk_done"] = f"Imported {saved} user{'s' if saved > 1 else ''}."
        st.rerun()
