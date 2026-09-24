"""Assumption register — a port of src/pages/Assumptions.tsx."""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from app import store
from app.data.factory import make_assumption
from app.domain import EVIDENCE_TYPES
from app.format import money, num, pct
from app.theme import tokens
from app.ui import badge, card, empty_state, esc, evidence_tone, kpi, kpi_grid, meter, table, write
from .common import page_header


def render() -> None:
    rows = store.rows()
    c = store.currency()
    t = tokens(store.theme())

    page_header("Assumption Register",
                "Every material assumption, with its source, owner and evidence grade. A named "
                "owner beside each number is what turns a business case into something a committee "
                "will sign.")

    entries = [(a, r["product"]) for r in rows for a in r["product"]["assumptions"]]

    by_evidence = {}
    for a, _ in entries:
        by_evidence[a["evidence"]] = by_evidence.get(a["evidence"], 0) + 1
    avg_conf = round(sum(a["confidence"] for a, _ in entries) / len(entries)) if entries else 0
    stale = 0
    for a, _ in entries:
        try:
            d = datetime.fromisoformat(a["lastUpdated"]).date()
            stale += (date.today() - d).days > 180
        except ValueError:
            pass

    actual = by_evidence.get("Actual", 0)
    write(kpi_grid(
        kpi("Registered assumptions", num(len(entries)), f"across {len(rows)} products", small=True)
        + kpi("Backed by actuals", str(actual),
              f"{pct(actual / max(1, len(entries)))} of the register", small=True)
        + kpi("Average confidence", str(avg_conf), "weighted equally across records", small=True)
        + kpi("Not reviewed in 6 months", str(stale),
              "due for refresh" if stale else "register is current", small=True)))
    st.write("")

    f1, f2, f3 = st.columns([2, 2, 2.4])
    q = f1.text_input("Search", key="as_q", placeholder="Search assumptions, sources, owners…",
                      label_visibility="collapsed")
    product_ids = ["All"] + [r["product"]["id"] for r in rows]
    names = {r["product"]["id"]: r["product"]["name"] for r in rows}
    pf = f2.selectbox("Product", product_ids, key="as_pf", label_visibility="collapsed",
                      format_func=lambda i: "All products" if i == "All" else names[i])
    with f3:
        ev = st.radio("Evidence", ["All"] + EVIDENCE_TYPES, horizontal=True, key="as_ev",
                      label_visibility="collapsed")

    needle = q.strip().lower()
    filtered = []
    for a, p in entries:
        if needle and needle not in " ".join([a["assumption"], a["source"], a["owner"],
                                              p["name"]]).lower():
            continue
        if ev != "All" and a["evidence"] != ev:
            continue
        if pf != "All" and p["id"] != pf:
            continue
        filtered.append((a, p))

    st.download_button(
        "⤓  Export CSV",
        pd.DataFrame([{
            "Product": p["name"], "Assumption": a["assumption"], "Value": a["value"],
            "Unit": a["unit"], "Source": a["source"], "Owner": a["owner"],
            "Evidence": a["evidence"], "Confidence": a["confidence"],
            "Last updated": a["lastUpdated"], "Evidence reference": a.get("evidenceRef") or "",
        } for a, p in filtered]).to_csv(index=False).encode("utf-8"),
        "assumption-register.csv", "text/csv")

    st.write("")
    if not filtered:
        write(card(empty_state("No assumptions match", "Try widening the filters.", "☰")))
        return

    body = ""
    prev_product_id = None
    shade = False
    for a, p in filtered[:400]:
        if p["id"] != prev_product_id:
            shade = not shade
            prev_product_id = p["id"]
        row_style = ' style="background:var(--hairline-strong)"' if shade else ""
        if a["unit"] == "%":
            val = pct(a["value"], 2 if a["value"] < 0.01 else 1)
        elif a["value"] >= 10000:
            val = money(a["value"], c)
        else:
            val = num(a["value"], 3 if a["value"] % 1 else 0)
        conf_colour = (t["good"] if a["confidence"] >= 80
                       else t["s1"] if a["confidence"] >= 60 else t["warn"])
        body += (f'<tr{row_style}><td class="strong">{esc(a["assumption"])}</td>'
                 f'<td>{esc(p["name"])}</td>'
                 f'<td class="num strong">{esc(val)}</td>'
                 f'<td>{esc(a["unit"])}</td>'
                 f'<td>{esc(a["source"])}</td>'
                 f'<td>{esc(a["owner"])}</td>'
                 f'<td>{badge(a["evidence"], evidence_tone(a["evidence"]))}</td>'
                 f'<td class="num"><span style="display:inline-flex;align-items:center;gap:8px;'
                 f'justify-content:flex-end"><span style="width:42px">'
                 f'{meter(a["confidence"], 100, conf_colour, 5)}</span>'
                 f'<span class="tnum">{a["confidence"]}</span></span></td>'
                 f'<td class="num">{esc(a["lastUpdated"])}</td></tr>')

    write(card(table([("Assumption", False), ("Product", False), ("Value", True), ("Unit", False),
                      ("Source", False), ("Owner", False), ("Evidence", False),
                      ("Confidence", True), ("Last updated", True)], body, min_width=1180),
               flush=True))
    if len(filtered) > 400:
        st.caption(f"Showing the first 400 of {len(filtered)} matching records — narrow the "
                   "filters to see the rest.")

    write('<p style="margin:14px 0 0;max-width:70em;font-size:11.5px;line-height:1.7;'
          'color:var(--text-muted)">'
          "Evidence grades in ascending order of strength: Management Assumption, Estimate, "
          "Benchmark, Pilot, Actual. A register with a high proportion of estimates is not a "
          "failure — it is an accurate statement of where the organisation is, and a work list.</p>")

    # ── Add or edit a record ────────────────────────────────────────────────
    st.write("")
    with st.expander("Add an assumption"):
        st.caption("Source, owner and evidence grade are what make an assumption defensible.")
        a1, a2 = st.columns(2)
        target = a1.selectbox("Product", [r["product"]["id"] for r in rows],
                              format_func=lambda i: names[i], key="as_new_p")
        text = a2.text_input("Assumption", key="as_new_t",
                             placeholder="Hours saved per RM per month")
        b1, b2, b3 = st.columns(3)
        value = b1.number_input("Value", value=0.0, step=1.0, key="as_new_v")
        unit = b2.text_input("Unit", "%", key="as_new_u", placeholder="hours, %, SGD")
        evidence = b3.selectbox("Evidence grade", EVIDENCE_TYPES, 3, key="as_new_e")
        d1, d2, d3 = st.columns(3)
        source = d1.text_input("Source", key="as_new_s",
                               placeholder="Time-and-motion study, 48 RMs")
        owner = d2.text_input("Owner", key="as_new_o", placeholder="Wealth COO")
        ref = d3.text_input("Evidence reference", key="as_new_r", placeholder="WM-TMS-2026-03")
        confidence = st.slider("Confidence in this assumption", 0, 100, 60, 5, key="as_new_c")
        if st.button("Save assumption", type="primary", key="as_save", disabled=not text.strip()):
            product = next(r["product"] for r in rows if r["product"]["id"] == target)
            record = make_assumption(target, text.strip(), value, unit, source=source or None,
                                     owner=owner or None, evidence=evidence,
                                     confidence=confidence, evidence_ref=ref or None)
            store.save_product({**product, "assumptions": product["assumptions"] + [record]})
            st.toast("Assumption added")
            st.rerun()
