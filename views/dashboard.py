"""Executive dashboard — a port of src/pages/Dashboard.tsx."""
from __future__ import annotations

import streamlit as st

from app import store
from app.charts import portfolio_matrix, QUADRANTS, LIFECYCLE_SLOT
from app.data.catalogs import CATEGORY_META
from app.engine.insights import portfolio_insights
from app.format import money, months, pct, ratio_pct
from app.theme import tokens
from app.ui import (badge, band_tone, card, category_row, esc, h2, kpi, kpi_grid,
                    meter, rule, swatch, write)
from .common import chart, open_product

FILTERS = ["All", "Revenue", "Cost Savings", "Risk", "Customer", "Productivity",
           "AI", "Data Platform", "Regulatory"]


def matches_filter(f: str, row) -> bool:
    if f == "All":
        return True
    v, p = row["valuation"], row["product"]
    dominant = max(v["byCategory"].items(), key=lambda kv: kv[1])[0] if v["byCategory"] else ""
    if f == "Revenue":
        return dominant == "revenue"
    if f == "Cost Savings":
        return dominant in ("costSavings", "costAvoidance")
    if f == "Risk":
        return dominant == "risk"
    if f == "Productivity":
        return dominant == "productivity"
    if f == "Customer":
        return p["domain"] == "Customer"
    if f == "AI":
        return p["type"] in ("AI / ML Product", "GenAI Application", "Decision Engine")
    if f == "Data Platform":
        return p["type"] in ("Data Platform Capability", "Data Product", "Data Service / API")
    if f == "Regulatory":
        return p["type"] == "Regulatory / Compliance Product" or p["domain"] == "Regulatory"
    return True


def render() -> None:
    rows = store.rows()
    totals = store.totals()
    settings = store.settings()
    c = settings["currency"]
    th = store.theme()
    t = tokens(th)

    # ── Hero ────────────────────────────────────────────────────────────────
    write(f"""<div class="dpv-hero">
      <p style="margin:0;font-size:11.5px;font-weight:600;text-transform:uppercase;
         letter-spacing:.14em;color:{t['s1']}">
        Data Product Value · Turn Data Into Business Value</p>
      <h1 style="margin:14px 0 0;font-size:42px;font-weight:600;line-height:1.08;
         letter-spacing:-0.03em;color:var(--text-primary);max-width:16em">
        How much is your data product worth?</h1>
      <p style="margin:16px 0 0;max-width:44em;font-size:15px;line-height:1.65;
         color:var(--text-secondary)">
        Quantify the revenue, savings, productivity and risk value of your data and AI investments.
        <strong style="color:var(--text-primary)">Quantify. Prioritise. Track.</strong></p>
    </div>""")

    hero_a, hero_b, hero_c = st.columns([1.1, 1, 3.4])
    with hero_a:
        if st.button("＋  Value a Data Product", type="primary", use_container_width=True):
            from .common import goto
            goto("value")
    with hero_b:
        if st.button("View Portfolio  →", use_container_width=True):
            from .common import goto
            goto("portfolio")
    with hero_c:
        st.markdown('<div style="padding-top:9px;font-size:12px;color:var(--text-muted)">'
                    "Simple mode takes about 45 seconds.</div>", unsafe_allow_html=True)

    # ── Portfolio KPIs ──────────────────────────────────────────────────────
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    write(f"""<div style="display:flex;align-items:baseline;justify-content:space-between;
        gap:16px;margin-bottom:10px">
      <h2 class="dpv-eyebrow" style="font-size:13px;letter-spacing:.08em">Your data portfolio</h2>
      <span style="font-size:11.5px;color:var(--text-muted)">{len(rows)} products ·
        {esc(settings['organisationName'])}</span></div>""")

    write(kpi_grid(
        kpi("Total Portfolio Value", money(totals["fiveYear"], c), "5-year economic value")
        + kpi("Annual Value", money(totals["annualNet"], c),
              f"Gross {money(totals['annualGross'], c)} less run cost")
        + kpi("Portfolio ROI", ratio_pct(totals["roi"]), f"Over {settings['horizonYears']} years")
        + kpi("Average Payback", months(totals["avgPayback"]), "From first spend")))
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    write(kpi_grid(
        kpi("Revenue Impact", money(totals["revenue"], c), "Annual, incl. revenue protected", small=True)
        + kpi("Cost Savings", money(totals["costSavings"], c), "Annual run-rate reduction", small=True)
        + kpi("Cost Avoidance", money(totals["costAvoidance"], c), "Probability-weighted", small=True)
        + kpi("Total Investment", money(totals["investment"], c),
              f"Plus {money(totals['annualRunCost'], c)} a year to run", small=True)))

    # ── Value mix + maturity ────────────────────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    mix_col, mat_col = st.columns([2, 1], gap="medium")

    mix = [("revenue", "Revenue", totals["revenue"]), ("costSavings", "Cost savings", totals["costSavings"]),
           ("costAvoidance", "Cost avoidance", totals["costAvoidance"]),
           ("productivity", "Productivity", totals["productivity"]),
           ("risk", "Risk reduction", totals["risk"])]
    mix_max = max([1.0] + [m[2] for m in mix])

    with mix_col:
        body = "".join(
            category_row(label, value, mix_max, t[CATEGORY_META[key]["series"]], c,
                         CATEGORY_META[key]["blurb"], value / max(1, totals["annualGross"]))
            for key, label, value in mix)
        write(card(
            '<h3 class="dpv-h3">Where portfolio value comes from</h3>'
            '<p class="dpv-sub" style="margin-bottom:18px">Annual gross value by category. '
            "Economic value and strategic value are held separately — strategic contribution is "
            "scored, never added to the financials.</p>" + body))

    with mat_col:
        bars = [("Proven value", totals["proven"], t["good"], "Backed by measured actuals"),
                ("Expected value", totals["expected"], t["s1"], "Pilot results or benchmarks"),
                ("Potential value", totals["potential"], t["warn"],
                 "Estimates and management assumptions")]
        body = "".join(
            f'<div style="margin-bottom:15px">'
            f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
            f'gap:8px;margin-bottom:6px"><span style="font-size:12.5px;color:var(--text-secondary)">'
            f'{esc(label)}</span><span class="tnum" style="font-size:12.5px;font-weight:600;'
            f'color:var(--text-primary)">{money(value, c)}</span></div>'
            f'{meter(value, max(1, totals["annualGross"]), colour)}'
            f'<p style="margin:5px 0 0;font-size:11px;color:var(--text-muted)">{esc(note_text)}</p></div>'
            for label, value, colour, note_text in bars)
        write(card('<h3 class="dpv-h3">Value maturity</h3>'
                   '<p class="dpv-sub" style="margin-bottom:18px">How much of the portfolio is '
                   "evidenced rather than estimated.</p>" + body))

    # ── Matrix ──────────────────────────────────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    write(f"""<div class="dpv-card" style="padding-bottom:6px">
      {h2("Which data products should we invest in next?",
          "Business value against implementation complexity and investment. Bubble size is "
          "five-year economic value. Hover a bubble for its numbers, or open it from the list below.")}
    </div>""")

    f = st.radio("Filter the matrix", FILTERS, horizontal=True, key="dash_filter",
                 label_visibility="collapsed")
    filtered = [r for r in rows if matches_filter(f, r)]

    if not filtered:
        st.info(f"No products match the “{f}” filter.")
    else:
        chart(portfolio_matrix(filtered, c, th), key="matrix")
        quad = "".join(
            f'<div class="dpv-tile" style="padding:11px 13px">'
            f'<div style="font-size:11.5px;font-weight:600;color:var(--text-primary)">'
            f'<span style="color:{t[q["slot"]]};margin-right:6px">{q["icon"]}</span>{esc(q["title"])}</div>'
            f'<div style="margin-top:2px;font-size:11px;line-height:1.45;color:var(--text-muted)">'
            f'{esc(q["blurb"])}</div></div>'
            for q in QUADRANTS)
        legend = "".join(
            f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:11.5px;'
            f'color:var(--text-secondary);margin-right:16px">{swatch(t[slot])}{esc(stage)}</span>'
            for stage, slot in list(LIFECYCLE_SLOT.items())[:6])
        write(f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));'
              f'gap:9px;margin-bottom:14px">{quad}</div>'
              f'<div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;'
              f'gap:10px">{legend}<span style="font-size:11px;color:var(--text-muted)">'
              f"Bubble size = 5-year economic value</span></div>")

    # ── Insights + highest priority ─────────────────────────────────────────
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    ins_col, top_col = st.columns([3, 2], gap="medium")

    with ins_col:
        insights = portfolio_insights(rows, settings)
        icon = {"warn": ("⚠", t["warn"]), "good": ("↗", t["good"]), "neutral": ("✦", t["text-muted"])}
        body = "".join(
            f'<div class="dpv-note" style="margin-bottom:10px">'
            f'<span style="color:{icon[i["tone"]][1]};flex:none">{icon[i["tone"]][0]}</span>'
            f'<div><span class="tnum" style="font-weight:600;color:var(--text-primary);'
            f'margin-right:7px">{esc(i["metric"])}</span>'
            f'<span style="color:var(--text-secondary)">{esc(i["text"])}</span></div></div>'
            for i in insights)
        write(card(f'<h3 class="dpv-h3" style="margin-bottom:14px">'
                   f'<span style="color:{t["s4"]};margin-right:7px">💡</span>Executive insights</h3>'
                   + body))

    with top_col:
        top = sorted(rows, key=lambda r: r["priority"]["score"], reverse=True)[:7]
        write('<div class="dpv-card flush" style="padding:18px 20px 4px">'
              '<h3 class="dpv-h3">Highest priority</h3></div>')
        for r in top:
            p, v, pr = r["product"], r["valuation"], r["priority"]
            col_a, col_b = st.columns([3, 2], vertical_alignment="center")
            with col_a:
                if st.button(p["name"], key=f"top_{p['id']}", use_container_width=True):
                    open_product(p["id"])
                st.markdown(f'<div style="margin:-8px 0 6px;font-size:11.5px;'
                            f'color:var(--text-muted)">{esc(p["businessUnit"])} · '
                            f'{esc(p["lifecycle"])}</div>', unsafe_allow_html=True)
            with col_b:
                write(f'<div style="text-align:right;padding-top:4px">'
                      f'<div class="tnum" style="font-size:13px;font-weight:600;'
                      f'color:var(--text-primary)">{money(v["threeYearValue"], c)}</div>'
                      f'<div style="margin-top:3px">{badge(pr["score"], band_tone(pr["band"]))}</div>'
                      f"</div>")
        write('<p style="margin:12px 0 0;font-size:11.5px;line-height:1.65;color:var(--text-muted)">'
              "Priority weighs economic value, strategic alignment, time to value, confidence, "
              "customer impact, risk reduction and reusability. Weights are configurable in Settings.</p>")
