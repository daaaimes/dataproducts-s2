"""Settings — a port of src/pages/SettingsPage.tsx."""
from __future__ import annotations

import copy

import streamlit as st

from app import store
from app.data.catalogs import CURRENCIES
from app.domain import DEFAULT_SETTINGS, WEIGHT_META
from app.format import num, pct
from app.ui import badge, card, esc, h3, rule, write
from .common import page_header


def render() -> None:
    s = store.settings()
    rows = store.rows()

    page_header("Settings",
                "Organisation-wide financial parameters and prioritisation weights. Changes apply "
                "immediately across every valuation.")

    # ── Organisation ────────────────────────────────────────────────────────
    write(h3("Organisation"))
    a, b = st.columns(2)
    org = a.text_input("Organisation name", s["organisationName"], key="set_org")
    codes = list(CURRENCIES)
    cur = b.selectbox("Reporting currency", codes, codes.index(s["currency"]), key="set_cur",
                      format_func=lambda k: f"{k} — {CURRENCIES[k]['label']}",
                      help="Applied to every value shown across the application.")
    dark = st.toggle("Dark interface", value=s["theme"] == "dark", key="set_theme",
                     help="Boardroom Mode always presents on the same surface as the rest of the app.")
    patch = {}
    if org != s["organisationName"]:
        patch["organisationName"] = org
    if cur != s["currency"]:
        patch["currency"] = cur
    if ("dark" if dark else "light") != s["theme"]:
        patch["theme"] = "dark" if dark else "light"
    if patch:
        store.set_settings(patch)
        st.rerun()

    # ── Financial parameters ────────────────────────────────────────────────
    write(rule() + h3("Financial parameters",
                      "These should match the rates Finance uses for capital appraisal. A product "
                      "can override them individually in advanced assumptions."))
    f1, f2 = st.columns(2)
    with f1:
        rate = st.slider("Discount rate", 0.0, 0.25, float(s["discountRate"]), 0.005,
                         key="set_rate", format="%.3f")
        write('<p style="margin:-6px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
              "Used for NPV. A rate materially below the organisation's cost of capital will "
              "flatter every case in the portfolio.</p>")
    with f2:
        horizon = st.slider("Projection period (years)", 3, 10, int(s["horizonYears"]), 1,
                            key="set_horizon")
        write('<p style="margin:-6px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
              "ROI, NPV and IRR are calculated over this horizon. Three-year and five-year "
              "economic value are always reported.</p>")
    g1, g2 = st.columns(2)
    hours = g1.number_input("Annual working hours per FTE", 1000, 2400,
                            int(s["annualWorkingHours"]), 20, key="set_hours",
                            help="Used to convert a fully-loaded annual salary into an hourly rate, "
                                 "and hours released into FTE equivalents.")
    guardrails = g2.toggle(
        "Assumption guardrails", value=s["guardrailsEnabled"], key="set_guard",
        help="Automatic benchmark checks that flag assumptions outside observed ranges. Turning "
             "these off removes the anti-gaming controls.")

    patch = {}
    if rate != s["discountRate"]:
        patch["discountRate"] = rate
    if horizon != s["horizonYears"]:
        patch["horizonYears"] = horizon
    if hours != s["annualWorkingHours"]:
        patch["annualWorkingHours"] = hours
    if guardrails != s["guardrailsEnabled"]:
        patch["guardrailsEnabled"] = guardrails
    if patch:
        store.set_settings(patch)
        st.rerun()

    # ── Priority weights ────────────────────────────────────────────────────
    total = sum(s["priorityWeights"].values())
    write(rule())
    head, tot = st.columns([4, 1])
    with head:
        write(h3("Priority score weighting",
                 "How the portfolio priority score is composed. Weights are normalised, so they "
                 "need not sum to 100."))
    with tot:
        write(f'<div style="text-align:right;padding-top:8px">'
              f'{badge(f"Total {total}", "good" if total == 100 else "neutral")}</div>')

    weights = dict(s["priorityWeights"])
    cols = st.columns(2)
    for i, w in enumerate(WEIGHT_META):
        with cols[i % 2]:
            weights[w["key"]] = st.slider(w["label"], 0, 50, int(weights[w["key"]]), 1,
                                          key=f"set_w_{w['key']}")
            write(f'<p style="margin:-6px 0 6px;font-size:11px;line-height:1.6;'
                  f'color:var(--text-muted)">{esc(w["help"])}</p>')
    if weights != s["priorityWeights"]:
        store.set_settings({"priorityWeights": weights})
        st.rerun()

    r1, r2 = st.columns([3, 1])
    r1.markdown('<p style="padding-top:8px;font-size:12px;color:var(--text-muted)">'
                "Bands: 90–100 Invest Now · 75–89 Accelerate · 60–74 Validate · below 60 Reassess</p>",
                unsafe_allow_html=True)
    if r2.button("↺  Reset weights", use_container_width=True, key="set_reset_w"):
        store.set_settings({"priorityWeights": copy.deepcopy(DEFAULT_SETTINGS["priorityWeights"])})
        st.rerun()

    # ── Data ────────────────────────────────────────────────────────────────
    write(rule() + h3("Data"))
    write(f'<p class="dpv-sub" style="max-width:70em">This deployment keeps everything in the '
          f"Streamlit session. {num(len(rows))} products are currently loaded. The same entities — "
          "DataProduct, Benefit, Investment, Valuation, Evidence, PriorityScore and "
          "ValueRealisation — map cleanly onto REST resources, so this interface can be connected "
          "to enterprise identity, Finance systems, Jira, the data catalogue and the data product "
          "registry.</p>")
    st.write("")
    if st.button("↺  Restore banking catalogue", key="set_reset_demo"):
        store.reset_demo()
        st.toast("Banking catalogue restored")
        st.rerun()
    st.caption("This replaces every product in this session with the 200-product banking data "
               "catalogue, valued on conservative SGD benchmarks. Settings are preserved.")
