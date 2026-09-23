"""Value realisation — a port of src/pages/Realisation.tsx."""
from __future__ import annotations

import copy

import streamlit as st

from app import store
from app.charts import realisation_chart
from app.format import money, num, pct
from app.theme import tokens
from app.ui import (badge, card, empty_state, esc, h3, kpi, kpi_grid, meter, rule,
                    table, write)
from .common import chart, page_header, product_picker


def totals_for(periods):
    t = dict(forecast=0.0, actual=0.0, fRev=0.0, aRev=0.0, fSav=0.0, aSav=0.0,
             fPro=0.0, aPro=0.0, fRisk=0.0, aRisk=0.0)
    for p in periods:
        t["forecast"] += (p["forecastRevenue"] + p["forecastSavings"]
                          + p["forecastProductivity"] + p["forecastRisk"])
        t["actual"] += (p["actualRevenue"] + p["actualSavings"]
                        + p["actualProductivity"] + p["actualRisk"])
        t["fRev"] += p["forecastRevenue"]; t["aRev"] += p["actualRevenue"]
        t["fSav"] += p["forecastSavings"]; t["aSav"] += p["actualSavings"]
        t["fPro"] += p["forecastProductivity"]; t["aPro"] += p["actualProductivity"]
        t["fRisk"] += p["forecastRisk"]; t["aRisk"] += p["actualRisk"]
    return t


def render() -> None:
    rows = store.rows()
    c = store.currency()
    th = store.theme()
    t = tokens(th)
    tracked = [r for r in rows if r["product"]["realisation"]]

    page_header("Value Realisation",
                "Forecast versus actual, by period. The point of tracking is not scorekeeping — "
                "it is calibrating the assumptions used on the products still in business case.")

    if not tracked:
        write(card(empty_state(
            "No products are tracking realised value yet",
            "Once a data product reaches production, record actuals against the forecast here. "
            "The variance is the single best input to improving future business cases.", "↗")))
        return

    portfolio_f = sum(totals_for(r["product"]["realisation"])["forecast"] for r in tracked)
    portfolio_a = sum(totals_for(r["product"]["realisation"])["actual"] for r in tracked)

    write(kpi_grid(
        kpi("Portfolio forecast to date", money(portfolio_f, c),
            f"{len(tracked)} products in production", small=True)
        + kpi("Realised to date", money(portfolio_a, c),
              f"{money(portfolio_f - portfolio_a, c)} still to land", small=True)
        + kpi("Portfolio value realisation", pct(portfolio_a / max(1, portfolio_f)),
              "Across every tracked product", small=True)))
    st.write("")

    default = st.session_state.get("realisation_product")
    pid = product_picker("Product", tracked, "real_pick",
                         default if default and any(r["product"]["id"] == default for r in tracked)
                         else None)
    row = next(r for r in tracked if r["product"]["id"] == pid)
    p, v = row["product"], row["valuation"]
    tt = totals_for(p["realisation"])
    realisation_pct = tt["actual"] / tt["forecast"] if tt["forecast"] > 0 else 0

    st.write("")
    left, right = st.columns([1.55, 1], gap="medium")
    with left:
        write(f'<div style="display:flex;flex-wrap:wrap;align-items:start;justify-content:space-between;gap:12px">'
              f'<div><h3 class="dpv-h3">{esc(p["name"])}</h3>'
              f'<p class="dpv-sub">Forecast 3-year value {money(v["threeYearValue"], c)} · '
              f'Realised to date {money(tt["actual"], c)}</p></div>'
              f'{badge("Value realisation " + pct(realisation_pct), "good" if realisation_pct >= 0.95 else "info" if realisation_pct >= 0.8 else "warn", dot=True)}</div>')
        chart(realisation_chart(p["realisation"], c, th), key="real_chart")

    with right:
        write(h3("Realisation by value type", "Where the forecast held and where it did not."))
        bands = [("Revenue", tt["fRev"], tt["aRev"], t["s1"]),
                 ("Cost savings", tt["fSav"], tt["aSav"], t["s3"]),
                 ("Productivity", tt["fPro"], tt["aPro"], t["s7"]),
                 ("Risk reduction", tt["fRisk"], tt["aRisk"], t["s2"])]
        body = ""
        for label, f, a, colour in bands:
            if f <= 0:
                continue
            tail = ""
            if a < f * 0.85:
                tail = " — below plan, worth understanding before the next case reuses this assumption"
            elif a > f * 1.05:
                tail = " — ahead of plan, this assumption was conservative"
            body += (f'<div style="margin-bottom:14px">'
                     f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
                     f'gap:8px;margin-bottom:6px">'
                     f'<span style="font-size:12.5px;color:var(--text-secondary)">{esc(label)}</span>'
                     f'<span class="tnum" style="font-size:12.5px;font-weight:600;'
                     f'color:var(--text-primary)">{money(a, c)} '
                     f'<span style="font-weight:400;color:var(--text-muted)">of {money(f, c)}</span>'
                     f"</span></div>{meter(a, max(1, f), colour)}"
                     f'<p style="margin:5px 0 0;font-size:11px;color:var(--text-muted)">'
                     f"{pct(a / max(1, f))} realised{tail}</p></div>")
        last = p["realisation"][-1]
        body += (f'{rule()}<div style="display:flex;align-items:baseline;justify-content:space-between;'
                 f'gap:8px;margin-bottom:6px"><span style="font-size:12.5px;'
                 f'color:var(--text-secondary)">Adoption</span>'
                 f'<span class="tnum" style="font-size:12.5px;font-weight:600;'
                 f'color:var(--text-primary)">{pct(last["actualAdoption"])}'
                 f'<span style="font-weight:400;color:var(--text-muted)"> vs '
                 f'{pct(last["forecastAdoption"])} forecast</span></span></div>'
                 f'{meter(last["actualAdoption"], 1, t["s4"])}')
        write(body)

    # ── Period detail ───────────────────────────────────────────────────────
    st.write("")
    write(h3("Period detail", "F = forecast, A = actual."))
    body = ""
    for per in p["realisation"]:
        f = (per["forecastRevenue"] + per["forecastSavings"]
             + per["forecastProductivity"] + per["forecastRisk"])
        a = (per["actualRevenue"] + per["actualSavings"]
             + per["actualProductivity"] + per["actualRisk"])
        r = a / f if f > 0 else 0
        body += (f'<tr><td class="strong">{esc(per["period"])}</td>'
                 f'<td class="num">{money(per["forecastRevenue"], c)}</td>'
                 f'<td class="num strong">{money(per["actualRevenue"], c)}</td>'
                 f'<td class="num">{money(per["forecastSavings"], c)}</td>'
                 f'<td class="num strong">{money(per["actualSavings"], c)}</td>'
                 f'<td class="num">{money(per["forecastProductivity"], c)}</td>'
                 f'<td class="num strong">{money(per["actualProductivity"], c)}</td>'
                 f'<td class="num">{pct(per["forecastAdoption"])} / {pct(per["actualAdoption"])}</td>'
                 f'<td class="num">{badge(pct(r), "good" if r >= 0.95 else "info" if r >= 0.8 else "warn")}</td></tr>')
    write(card(table([("Period", False), ("Revenue F", True), ("Revenue A", True),
                      ("Savings F", True), ("Savings A", True), ("Productivity F", True),
                      ("Productivity A", True), ("Adoption F / A", True), ("Realisation", True)],
                     body, min_width=940), flush=True))

    # ── Calibration notes ───────────────────────────────────────────────────
    st.write("")
    notes = [
        (f"Productivity assumptions on {p['name']} were conservative — actuals are running "
         f"{pct(tt['aPro'] / max(1, tt['fPro']) - 1)} ahead. Similar products can carry a slightly "
         "higher hours-saved assumption, provided the same time-and-motion evidence exists."
         if tt["aPro"] > tt["fPro"] else
         f"Productivity realisation is {pct(tt['aPro'] / max(1, tt['fPro']))} of forecast. The gap "
         "is usually adoption depth rather than the per-user saving — worth checking utilisation "
         "before reusing this assumption."),
        (f"Revenue is landing at {pct(tt['aRev'] / max(1, tt['fRev']))} of forecast. Attribution "
         "and conversion ramp are the usual causes; a hold-out group would settle which."
         if tt["aRev"] < tt["fRev"] else
         f"Revenue is at or ahead of forecast at {pct(tt['aRev'] / max(1, tt['fRev']))}, which "
         "supports the attribution assumption used here."),
        (f"Adoption reached {pct(last['actualAdoption'])} against a "
         f"{pct(last['forecastAdoption'])} forecast — use this as the benchmark for comparable "
         "products rather than an aspirational number."),
    ]
    items = "".join(
        f'<li style="display:flex;gap:10px;margin-top:10px;font-size:13px;line-height:1.7;'
        f'color:var(--text-secondary)">'
        f'<span style="margin-top:7px;width:6px;height:6px;flex:none;border-radius:999px;'
        f'background:{t["s1"]}"></span><span>{esc(n)}</span></li>' for n in notes)
    write(card(f'<h3 class="dpv-h3">What this tells us about future business cases</h3>'
               f'<ul style="margin:0;padding:0;list-style:none">{items}</ul>'))

    # ── Record actuals ──────────────────────────────────────────────────────
    st.write("")
    with st.expander("Record actuals"):
        st.caption("Enter realised value by period. These figures feed the realisation percentage "
                   "and portfolio calibration.")
        draft = copy.deepcopy(p["realisation"])
        for i, per in enumerate(draft):
            st.markdown(f"**{per['period']}**")
            cols = st.columns(5)
            for col, (k, label) in zip(cols, [("actualRevenue", "Actual revenue"),
                                              ("actualSavings", "Actual savings"),
                                              ("actualProductivity", "Actual productivity"),
                                              ("actualRisk", "Actual risk value")]):
                per[k] = col.number_input(label, 0.0, None, float(per[k]), 10_000.0,
                                          key=f"ra_{pid}_{i}_{k}", label_visibility="visible")
            per["actualAdoption"] = cols[4].slider("Actual adoption", 0.0, 1.0,
                                                   float(per["actualAdoption"]), 0.01,
                                                   key=f"ra_{pid}_{i}_ad", format="%.2f")
        if st.button("Save actuals", type="primary", key="ra_save"):
            store.save_product({**p, "realisation": draft})
            st.toast("Actuals saved")
            st.rerun()
