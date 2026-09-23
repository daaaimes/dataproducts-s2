"""Portfolio table — a port of src/pages/Portfolio.tsx."""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import streamlit as st

from app import store
from app.data.catalogs import BUSINESS_UNITS
from app.domain import LIFECYCLE_STAGES, PRODUCT_TYPES
from app.format import money, months_short, ratio_pct
from app.ui import esc, write
from .common import open_product, page_header

BANDS = ["All", "Invest Now", "Accelerate", "Validate", "Reassess"]


def _csv(rows, c: str) -> str:
    out = []
    for r in rows:
        v, p = r["valuation"], r["product"]
        out.append({
            "Product": p["name"], "Code": p["code"], "Owner": p["owner"], "Sponsor": p["sponsor"],
            "Business Unit": p["businessUnit"], "Type": p["type"], "Lifecycle": p["lifecycle"],
            "Tags": "|".join(p["tags"]),
            f"Annual Gross ({c})": round(v["annualGrossValue"]),
            f"Annual Run Cost ({c})": round(v["annualOperatingCost"]),
            f"Net Annual ({c})": round(v["netAnnualValue"]),
            f"3-Year ({c})": round(v["threeYearValue"]),
            f"5-Year ({c})": round(v["fiveYearValue"]),
            f"Investment ({c})": round(v["costs"]["initialInvestment"]),
            f"NPV ({c})": round(v["npv"]),
            "ROI %": f"{v['roi'] * 100:.1f}",
            "Payback (months)": (f"{v['paybackMonths']:.1f}"
                                 if math.isfinite(v["paybackMonths"]) else ""),
            "IRR %": f"{v['irr'] * 100:.1f}" if math.isfinite(v["irr"]) else "",
            "Priority": r["priority"]["score"], "Band": r["priority"]["band"],
            "Strategic Score": v["strategicScore"],
        })
    return pd.DataFrame(out).to_csv(index=False).encode("utf-8")


def render() -> None:
    rows = store.rows()
    c = store.currency()

    q = st.session_state.get("pf_q", "")
    bu = st.session_state.get("pf_bu", "All")
    ptype = st.session_state.get("pf_type", "All")
    life = st.session_state.get("pf_life", "All")
    band = st.session_state.get("pf_band", "All")
    sort_key = st.session_state.get("pf_sort", "Priority")
    sort_dir = st.session_state.get("pf_dir", "Highest first")

    needle = q.strip().lower()
    filtered = []
    for r in rows:
        p = r["product"]
        if needle and needle not in " ".join(
                [p["name"], p["owner"], p["sponsor"], p["businessUnit"], p["code"],
                 p["description"], *p["tags"]]).lower():
            continue
        if bu != "All" and p["businessUnit"] != bu:
            continue
        if ptype != "All" and p["type"] != ptype:
            continue
        if life != "All" and p["lifecycle"] != life:
            continue
        if band != "All" and r["priority"]["band"] != band:
            continue
        filtered.append(r)

    sorters = {
        "Product": lambda r: r["product"]["name"].lower(),
        "Annual Value": lambda r: r["valuation"]["netAnnualValue"],
        "3-Year Value": lambda r: r["valuation"]["threeYearValue"],
        "Investment": lambda r: r["valuation"]["costs"]["initialInvestment"],
        "ROI": lambda r: r["valuation"]["roi"],
        "Payback": lambda r: (r["valuation"]["paybackMonths"]
                              if math.isfinite(r["valuation"]["paybackMonths"]) else 9999),
        "Priority": lambda r: r["priority"]["score"],
    }
    filtered.sort(key=sorters[sort_key], reverse=(sort_dir == "Highest first"))

    three_year = sum(r["valuation"]["threeYearValue"] for r in filtered)
    page_header("Data Product Portfolio",
                f"{len(filtered)} of {len(rows)} products · {money(three_year, c)} three-year value")

    # ── Filters ─────────────────────────────────────────────────────────────
    with st.container():
        f1, f2, f3, f4 = st.columns([2, 1.5, 1.5, 1.2])
        f1.text_input("Search", key="pf_q", placeholder="Search products, owners, tags…",
                      label_visibility="collapsed")
        f2.selectbox("Business unit", ["All"] + BUSINESS_UNITS, key="pf_bu",
                     label_visibility="collapsed")
        f3.selectbox("Product type", ["All"] + PRODUCT_TYPES, key="pf_type",
                     label_visibility="collapsed")
        f4.selectbox("Lifecycle", ["All"] + LIFECYCLE_STAGES, key="pf_life",
                     label_visibility="collapsed")
        g1, g2, g3 = st.columns([2.4, 1.5, 1.3])
        with g1:
            st.radio("Priority band", BANDS, horizontal=True, key="pf_band",
                     label_visibility="collapsed")
        g2.selectbox("Sort by", list(sorters), index=list(sorters).index("Priority"),
                     key="pf_sort", label_visibility="collapsed")
        g3.selectbox("Direction", ["Highest first", "Lowest first"], key="pf_dir",
                     label_visibility="collapsed")

    a1, a2, a3 = st.columns([1.2, 1.4, 4])
    a1.download_button("⤓  Export CSV", _csv(filtered, c),
                       f"data-product-portfolio-{date.today().isoformat()}.csv",
                       "text/csv", use_container_width=True)
    with a2:
        if st.button("⇄  Compare selected", use_container_width=True):
            from .common import goto
            goto("compare")

    st.write("")

    if not filtered:
        from app.ui import empty_state
        write(f'<div class="dpv-card">{empty_state("No products match these filters", "Try clearing the search box or widening the business unit and lifecycle filters.")}</div>')
        return

    # ── Table ───────────────────────────────────────────────────────────────
    compare_ids = st.session_state.compare_ids
    df = pd.DataFrame([{
        "Compare": r["product"]["id"] in compare_ids,
        "Product": r["product"]["name"],
        "Code": r["product"]["code"],
        "Owner": r["product"]["owner"],
        "Business Unit": r["product"]["businessUnit"],
        "Type": r["product"]["type"],
        "Lifecycle": r["product"]["lifecycle"],
        "Annual Value": r["valuation"]["netAnnualValue"],
        "3-Year Value": r["valuation"]["threeYearValue"],
        "Investment": r["valuation"]["costs"]["initialInvestment"],
        "ROI": r["valuation"]["roi"],
        "Payback": (r["valuation"]["paybackMonths"]
                    if math.isfinite(r["valuation"]["paybackMonths"]) else None),
        "Priority": r["priority"]["score"],
        "Status": r["priority"]["band"],
        "_id": r["product"]["id"],
    } for r in filtered])

    edited = st.data_editor(
        df, hide_index=True, use_container_width=True, height=560,
        key="pf_table", disabled=[c_ for c_ in df.columns if c_ != "Compare"],
        column_order=["Compare", "Product", "Code", "Owner", "Business Unit", "Type", "Lifecycle",
                      "Annual Value", "3-Year Value", "Investment", "ROI", "Payback",
                      "Priority", "Status"],
        column_config={
            "Compare": st.column_config.CheckboxColumn("⇄", width="small",
                                                       help="Add to the comparison"),
            "Product": st.column_config.TextColumn(width="large"),
            "Code": st.column_config.TextColumn(width="small"),
            "Annual Value": st.column_config.NumberColumn(format="localized", width="small",
                                                          help="Net of operating cost"),
            "3-Year Value": st.column_config.NumberColumn(format="localized", width="small"),
            "Investment": st.column_config.NumberColumn(format="localized", width="small"),
            "ROI": st.column_config.NumberColumn(format="percent", width="small"),
            "Payback": st.column_config.NumberColumn(format="%.0f mo", width="small"),
            "Priority": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=100,
                                                        width="small"),
            "Status": st.column_config.TextColumn(width="small"),
            "_id": None,
        })

    picked = [r["_id"] for _, r in edited.iterrows() if r["Compare"]]
    if set(picked) != set(compare_ids):
        store.set_compare(picked[-4:])
        st.rerun()

    st.write("")
    o1, o2 = st.columns([2, 4])
    with o1:
        pid = st.selectbox("Open a valuation", [r["product"]["id"] for r in filtered],
                           format_func=lambda i: next(r["product"]["name"] for r in filtered
                                                      if r["product"]["id"] == i),
                           key="pf_open")
    with o2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Open valuation  →", type="primary"):
            open_product(pid)

    write('<p style="margin:14px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
          "Annual Value is net of operating cost. 3-Year Value is cumulative benefits less "
          "operating cost over 36 months, before capital investment; NPV and ROI include "
          "investment.</p>")
