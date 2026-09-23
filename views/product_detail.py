"""Product valuation — a port of src/pages/ProductDetail.tsx."""
from __future__ import annotations

import math

import streamlit as st

from app import store
from app.charts import cashflow_chart, scenario_chart, tornado_chart, value_waterfall
from app.data.catalogs import CATEGORY_META, DRIVER_BY_ID
from app.domain import LIFECYCLE_ORDER
from app.engine.models import MODELS
from app.engine.recommendations import recommendations_for
from app.engine.scenarios import LEVER_META, run_scenarios
from app.engine.sensitivity import tornado
from app.engine.valuation import value_product
from app.format import (money, money_full, months, num, pct, ratio_pct, relative_date)
from app.theme import tokens
from app.ui import (badge, band_tone, card, esc, evidence_tone, gauge, h3, key_value,
                    lifecycle_tone, meter, rule, stars, swatch, table, write)
from .common import chart, goto, selected_product_id


@st.dialog("How was this calculated?", width="large")
def explain_dialog(result, settings):
    """The Explain modal — formula, source inputs, evidence and timing."""
    model = MODELS[result["benefit"]["kind"]]
    ex = model["explain"](result["benefit"]["inputs"],
                          {"annualWorkingHours": settings["annualWorkingHours"],
                           "currency": settings["currency"]},
                          result["benefit"]["attribution"])
    c = settings["currency"]
    b = result["benefit"]
    driver = DRIVER_BY_ID.get(b["driverId"])

    write(f'<div style="font-size:19px;font-weight:600;letter-spacing:-0.02em;'
          f'color:var(--text-primary)">{money(result["annualValue"], c)} — {esc(b["label"])}</div>'
          f'<p class="dpv-sub" style="margin-top:4px">{esc(model["name"])} · '
          f'{esc(CATEGORY_META[result["category"]]["label"])} · '
          f'{"Direct value" if result["valueClass"] == "direct" else "Indirect value"}</p>')

    write(f'<div class="dpv-tile" style="margin-top:14px">'
          f'<div class="dpv-eyebrow">Formula</div>'
          f'<p style="margin:6px 0 0;font-size:13px;font-weight:500;line-height:1.6;'
          f'color:var(--text-primary)">{esc(ex["formula"])}</p></div>')

    terms = "".join(
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:16px;'
        f'padding:8px 0;border-bottom:1px solid var(--hairline)">'
        f'<span style="font-size:12.5px;color:{"var(--text-muted)" if t.get("muted") else "var(--text-secondary)"};'
        f'{"font-style:italic" if t.get("muted") else ""}">{esc(t["label"])}</span>'
        f'<span class="tnum" style="font-size:12.5px;font-weight:500;text-align:right;'
        f'color:{"var(--text-muted)" if t.get("muted") else "var(--text-primary)"}">{esc(t["value"])}</span>'
        f"</div>" for t in ex["terms"])
    write(f'<div style="margin-top:18px"><div class="dpv-eyebrow">Source inputs</div>{terms}'
          f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:16px;'
          f'padding-top:12px;border-top:2px solid var(--hairline-strong)">'
          f'<span style="font-size:13px;font-weight:600;color:var(--text-primary)">Annual value</span>'
          f'<span class="tnum" style="font-size:16px;font-weight:600;color:var(--text-primary)">'
          f'{money(result["annualValue"], c)}</span></div></div>')

    if ex.get("note"):
        write(f'<div class="dpv-note warn" style="margin-top:16px">{esc(ex["note"])}</div>')

    write(rule())
    left, right = st.columns(2)
    with left:
        write(f'<div class="dpv-eyebrow">Evidence</div>'
              f'<div style="margin-top:6px;display:flex;align-items:center;gap:8px">'
              f'{badge(b["evidence"], evidence_tone(b["evidence"]), dot=True)}'
              f'{stars(b["evidenceStrength"], 14)}</div>'
              + (f'<p style="margin:8px 0 0;font-size:12px;line-height:1.6;color:var(--text-muted)">'
                 f'{esc(b["evidenceNote"])}</p>' if b.get("evidenceNote") else ""))
    with right:
        start = ("at go-live" if b["startMonth"] == 0
                 else f"{b['startMonth']} months after go-live")
        write(f'<div class="dpv-eyebrow">Timing</div>'
              f'<p style="margin:6px 0 0;font-size:12.5px;line-height:1.6;color:var(--text-secondary)">'
              f'Starts {start}, reaching full run-rate over {b["rampMonths"]} months.</p>'
              + (f'<p style="margin:8px 0 0;font-size:11.5px;line-height:1.6;'
                 f'color:var(--text-muted)">{esc(driver["hint"])}</p>' if driver else ""))

    write(f'<p style="margin:18px 0 0;font-size:11px;line-height:1.7;color:var(--text-muted)">'
          f'Classified as <strong style="color:var(--text-secondary)">{result["maturity"]} value</strong>. '
          f'Attribution of {pct(b["attribution"])} means {pct(1 - b["attribution"])} of the modelled '
          f"outcome is credited to factors outside this data product.</p>")


def render() -> None:
    rows = store.rows()
    settings = store.settings()
    c = settings["currency"]
    th = store.theme()
    t = tokens(th)

    if not rows:
        st.info("No products in this workspace yet.")
        return

    pid = selected_product_id(rows)
    row = next((r for r in rows if r["product"]["id"] == pid), None)
    if row is None:
        st.warning("Product not found. It may have been deleted.")
        return

    p, v, priority = row["product"], row["valuation"], row["priority"]

    # ── Header ──────────────────────────────────────────────────────────────
    head, actions = st.columns([3, 2], vertical_alignment="bottom")
    with head:
        write(f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px">'
              f'<h1 style="margin:0;font-size:27px;font-weight:600;letter-spacing:-0.028em;'
              f'color:var(--text-primary)">{esc(p["name"])}</h1>'
              f'{badge(p["code"])}'
              f'{badge(p["lifecycle"], lifecycle_tone(p["lifecycle"]), dot=True)}'
              f'{badge(p["strategicPriority"] + " priority", "critical" if p["strategicPriority"] == "Critical" else "info" if p["strategicPriority"] == "High" else "neutral")}'
              f"</div>"
              f'<p class="dpv-sub">{esc(p["type"])} · {esc(p["businessUnit"])} · Owner '
              f'{esc(p["owner"])} · Sponsor {esc(p["sponsor"])} · Updated '
              f'{relative_date(p["updatedAt"])}</p>')
    with actions:
        b1, b2, b3 = st.columns(3)
        if b1.button("Business case", use_container_width=True):
            goto("reports", report_product=p["id"])
        if b2.button("Boardroom", use_container_width=True):
            goto("boardroom", boardroom_product=p["id"])
        if b3.button("Advisor", use_container_width=True):
            goto("advisor", selected_product=p["id"])

    scenarios = run_scenarios(p, settings)
    sensitivity = tornado(p, settings)
    recs = recommendations_for(p, settings, v)

    severe = [g for g in v["guardrails"] if g["severity"] == "severe"]
    warn = [g for g in v["guardrails"] if g["severity"] == "warn"]
    info = [g for g in v["guardrails"] if g["severity"] == "info"]
    recommendation = {"Invest Now": "Invest", "Accelerate": "Accelerate",
                      "Validate": "Validate"}.get(priority["band"], "Reassess")

    # ── Executive valuation card ────────────────────────────────────────────
    st.write("")
    hero_l, hero_r = st.columns([1.05, 1], gap="medium")
    with hero_l:
        flags = (badge(f"{len(severe)} assumption{'s' if len(severe) > 1 else ''} to challenge",
                       "critical", dot=True) if severe else "")
        write(f"""<div class="dpv-hero" style="padding:30px 32px">
          <div class="dpv-eyebrow" style="font-size:12px;letter-spacing:.09em">
            Estimated 3-year economic value</div>
          <div class="tnum" style="margin-top:8px;font-size:46px;font-weight:600;line-height:1;
               letter-spacing:-0.035em;color:var(--text-primary)">
            {money(v['threeYearValue'], c)}</div>
          <p style="margin:14px 0 0;max-width:34em;font-size:13.5px;line-height:1.65;
             color:var(--text-secondary)">
            {esc(p['name'])} generates <strong style="color:var(--text-primary)">
            {money(v['netAnnualValue'], c)}</strong> of net annual economic value. At the current
            investment level it pays back in approximately
            <strong style="color:var(--text-primary)">{months(v['paybackMonths'])}</strong> from first
            spend ({months(v['paybackFromGoLive'])} from go-live), making it a
            <strong style="color:var(--text-primary)">{esc(priority['band'].lower())}</strong> candidate.</p>
          <div style="margin-top:18px;display:flex;flex-wrap:wrap;gap:8px">
            {badge("Recommendation: " + recommendation,
                   "good" if recommendation in ("Invest", "Accelerate")
                   else "warn" if recommendation == "Validate" else "critical", dot=True)}
            {flags}
          </div>
        </div>""")
    with hero_r:
        metrics = [
            ("Annual value", money(v["annualGrossValue"], c)),
            ("Investment", money(v["costs"]["initialInvestment"], c)),
            ("Annual run cost", money(v["annualOperatingCost"], c)),
            ("Net annual value", money(v["netAnnualValue"], c)),
            ("ROI", ratio_pct(v["roi"])),
            ("Payback", months(v["paybackMonths"])),
            ("NPV", money(v["npv"], c)),
            ("IRR", ratio_pct(v["irr"]) if math.isfinite(v["irr"]) else "—"),
        ]
        cells = "".join(
            f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px;'
            f'padding:9px 0;{"border-bottom:1px solid var(--hairline)" if i < 6 else ""}">'
            f'<span style="font-size:12px;color:var(--text-muted)">{esc(k)}</span>'
            f'<span class="tnum" style="font-size:14px;font-weight:600;color:var(--text-primary)">'
            f"{esc(val)}</span></div>" for i, (k, val) in enumerate(metrics))
        write(card(f'<div style="display:grid;grid-template-columns:1fr 1fr;column-gap:26px">{cells}</div>'))

    # Category strip
    strip = "".join(
        kpi_cell(CATEGORY_META[cat], v["byCategory"][cat], v["annualGrossValue"], c, t)
        for cat in CATEGORY_META)
    write(f'<div class="dpv-kpi-grid" style="margin-top:6px">{strip}</div>')

    # Governance banner
    write(f'<div class="dpv-note" style="margin-top:10px;flex-wrap:wrap;gap:6px 22px">'
          f'<span>ⓘ <strong style="color:var(--text-primary)">Economic value</strong> '
          f'{money(v["annualGrossValue"], c)} p.a.</span>'
          f'<span><strong style="color:var(--text-primary)">Strategic value score</strong> '
          f'{v["strategicScore"]}/100 — scored, never added to the financials</span>'
          f'<span><strong style="color:var(--text-primary)">Hard-dollar</strong> '
          f'{money(v["hardDollarValue"], c)} · <strong style="color:var(--text-primary)">Indirect</strong> '
          f'{money(v["softValue"], c)}</span>'
          f'<span>Capacity released ≈ {num(v["fteEquivalent"], 1)} FTE</span></div>')

    # ── Waterfall + evidence maturity ───────────────────────────────────────
    st.write("")
    wf, ev = st.columns([1.7, 1], gap="medium")
    with wf:
        write(h3("Value waterfall",
                 "How gross annual value builds and what operating cost takes back. Investment is "
                 "marked as a reference line — it is capital, not a run-rate deduction."))
        chart(value_waterfall(v, c, th, height=330), key="pd_waterfall")
    with ev:
        write(h3("Evidence maturity", "How much of this number is measured versus estimated."))
        tiles = "".join(
            f'<div class="dpv-tile" style="text-align:center;padding:10px">'
            f'<div class="dpv-eyebrow" style="font-size:10.5px">{label}</div>'
            f'<div class="tnum" style="margin-top:4px;font-size:13px;font-weight:600;'
            f'color:var(--text-primary)">{money(val, c)}</div></div>'
            for label, val in [("Proven", v["byMaturity"]["Proven"]),
                               ("Expected", v["byMaturity"]["Expected"]),
                               ("Potential", v["byMaturity"]["Potential"])])
        write(f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;'
              f'margin-top:10px">{tiles}</div>'
              f'<p style="margin:12px 0 0;font-size:11px;line-height:1.65;color:var(--text-muted)">'
              "Proven value is backed by measured actuals, Expected by pilots and benchmarks, and "
              "Potential by estimates and management assumptions.</p>")
        weak = sorted([b for b in v["benefits"]
                       if b["annualValue"] > 0
                       and b["benefit"]["evidence"] in ("Estimate", "Management Assumption")],
                      key=lambda b: b["annualValue"], reverse=True)[:3]
        if weak:
            items = "".join(
                f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
                f'gap:12px;margin-top:7px"><span style="font-size:12px;color:var(--text-secondary)">'
                f'{esc(b["benefit"]["label"])}</span><span class="tnum" style="font-size:11.5px;'
                f'color:var(--text-muted)">{money(b["annualValue"], c)}</span></div>'
                for b in weak)
            write(f'<div style="margin-top:14px;padding-top:14px;border-top:1px solid var(--hairline)">'
                  f'<div class="dpv-eyebrow">Firm up first</div>{items}</div>')

    # ── Benefit lines ───────────────────────────────────────────────────────
    st.write("")
    write(h3("Benefit lines",
             "Every number here is explainable. Open any line to see the formula, the source "
             "inputs and the evidence behind it."))
    ordered = sorted(v["benefits"], key=lambda b: b["annualValue"], reverse=True)
    body = "".join(
        f"<tr><td><span style='display:flex;align-items:center;gap:8px'>"
        f"{swatch(t[CATEGORY_META[b['category']]['series']])}"
        f"<span class='strong'>{esc(b['benefit']['label'])}</span></span></td>"
        f"<td>{esc(MODELS[b['benefit']['kind']]['name'])}</td>"
        f"<td>{badge('Direct' if b['valueClass'] == 'direct' else 'Indirect', 'info' if b['valueClass'] == 'direct' else 'neutral')}</td>"
        f"<td>{badge(b['benefit']['evidence'], evidence_tone(b['benefit']['evidence']))} "
        f"{stars(b['benefit']['evidenceStrength'])}</td>"
        f"<td class='num'>{pct(b['benefit']['attribution'])}</td>"
        f"<td class='num'>{b['benefit']['rampMonths']} mo</td>"
        f"<td class='num strong'>{money(b['annualValue'], c)}</td>"
        f"<td class='num'>{pct(b['annualValue'] / max(1, v['annualGrossValue']))}</td></tr>"
        for b in ordered)
    write(card(table([("Benefit", False), ("Model", False), ("Class", False), ("Evidence", False),
                      ("Attribution", True), ("Ramp", True), ("Annual value", True), ("Share", True)],
                     body, min_width=880), flush=True))

    cols = st.columns(min(4, max(1, len(ordered))))
    for i, b in enumerate(ordered):
        if cols[i % len(cols)].button(f"Explain · {b['benefit']['label'][:26]}",
                                      key=f"explain_{b['benefit']['id']}",
                                      use_container_width=True):
            explain_dialog(b, settings)

    # ── Guardrails ──────────────────────────────────────────────────────────
    if v["guardrails"]:
        st.write("")
        n_flags = len(v["guardrails"])
        flag_badge = badge(f"{n_flags} flag" + ("s" if n_flags > 1 else ""),
                           "critical" if severe else "warn")
        write(f'<div style="display:flex;align-items:center;gap:9px">'
              f'<h3 class="dpv-h3">Assumption guardrails</h3>{flag_badge}</div>'
              '<p class="dpv-sub">Automatic benchmark checks. These are not errors — they are '
              'the questions an investment committee will ask.</p>')
        for g in severe + warn + info:
            icon_colour = (t["critical"] if g["severity"] == "severe"
                           else t["warn"] if g["severity"] == "warn" else t["text-muted"])
            write(f'<div class="dpv-note {g["severity"] if g["severity"] != "info" else ""}" '
                  f'style="margin-top:9px">'
                  f'<span style="color:{icon_colour};flex:none">⚠</span>'
                  f'<div><div style="font-size:13px;font-weight:500;color:var(--text-primary)">'
                  f'{esc(g["title"])}</div>'
                  f'<p style="margin:3px 0 0;font-size:12.5px;line-height:1.6">{esc(g["detail"])}</p>'
                  f"</div></div>")

    # ── Scenarios + what-if ─────────────────────────────────────────────────
    st.write("")
    sc, wi = st.columns([1.35, 1], gap="medium")
    with sc:
        write(h3("Scenario analysis",
                 "Three-year economic value under conservative, base and upside assumptions."))
        tab_chart, tab_table = st.tabs(["Chart", "Table"])
        with tab_chart:
            chart(scenario_chart(scenarios, c, th), key="pd_scen")
        with tab_table:
            body = "".join(
                f"<tr><td class='strong'>{esc(s['label'])}</td>"
                f"<td class='num strong'>{money(s['valuation']['threeYearValue'], c)}</td>"
                f"<td class='num'>{ratio_pct(s['valuation']['roi'])}</td>"
                f"<td class='num'>{money(s['valuation']['npv'], c)}</td>"
                f"<td class='num'>{months(s['valuation']['paybackMonths'])}</td></tr>"
                for s in scenarios)
            write(table([("Scenario", False), ("3-Year Value", True), ("ROI", True),
                         ("NPV", True), ("Payback", True)], body))
        lev = "".join(
            f'<div class="dpv-tile"><div style="font-size:12px;font-weight:600;'
            f'color:var(--text-primary)">{esc(s["label"])}</div>'
            f'<div style="margin-top:4px;font-size:11.5px;line-height:1.6;color:var(--text-muted)">'
            f'Adoption {pct(s["levers"]["adoption"])} · Revenue {pct(s["levers"]["revenueUplift"])} · '
            f'Cost benefits {pct(s["levers"]["costSavings"])} · '
            f'Attribution {pct(s["levers"]["attribution"])} · '
            f'Build cost {pct(s["levers"]["implementationCost"])}</div></div>'
            for s in scenarios)
        write(f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));'
              f'gap:9px;margin-top:12px">{lev}</div>')

    with wi:
        write(h3("What if…", "Move a lever and watch the case move. Nothing here is saved."))
        levers = {}
        for lm in LEVER_META:
            levers[lm["key"]] = st.slider(lm["label"], 0.4, 1.6,
                                          st.session_state.get(f"wi_{lm['key']}", 1.0), 0.05,
                                          key=f"wi_{lm['key']}", help=lm["help"],
                                          format="%.2f×")
        wv = value_product(p, settings, levers) if any(x != 1.0 for x in levers.values()) else v
        write(rule() + key_value([
            ("3-year value", money(wv["threeYearValue"], c)),
            ("Change vs base", money(wv["threeYearValue"] - v["threeYearValue"], c)),
            ("ROI", ratio_pct(wv["roi"])),
            ("Payback", months(wv["paybackMonths"])),
            ("NPV", money(wv["npv"], c)),
        ]))
        if any(x != 1.0 for x in levers.values()):
            if st.button("Reset to base case", use_container_width=True):
                for lm in LEVER_META:
                    st.session_state[f"wi_{lm['key']}"] = 1.0
                st.rerun()

    # ── Sensitivity + cashflow ──────────────────────────────────────────────
    st.write("")
    sens, cash = st.columns(2, gap="medium")
    with sens:
        write(h3("Sensitivity analysis",
                 "Which assumptions actually move the valuation. Validate from the top down."))
        if sensitivity:
            chart(tornado_chart(sensitivity, c, th), key="pd_tornado")
            write('<p style="margin:6px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
                  "Each assumption is moved through its own plausible range in isolation and the "
                  "3-year economic value recalculated. Ranges differ by assumption type — adoption "
                  "moves in percentage points, unit costs in percent — so the widest bars are "
                  "genuinely the assumptions worth validating first.</p>")
        else:
            st.caption("Not enough variable assumptions to run a sensitivity analysis.")
    with cash:
        write(h3("Cashflow and payback",
                 "Cumulative net cashflow. The line crosses zero at payback."))
        chart(cashflow_chart(v, c, th), key="pd_cash")
        write('<p style="margin:6px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
              "Cumulative benefits less cumulative cost, month by month. Monthly benefit and cost "
              "figures are shown on hover — plotting them on this axis would make the scale "
              "unreadable.</p>")

    # ── Priority + recommendations ──────────────────────────────────────────
    st.write("")
    pr_col, rec_col = st.columns([1, 1.55], gap="medium")
    with pr_col:
        write(h3("Priority score",
                 "Weighted across seven dimensions. Weights are configurable in Settings."))
        colour = (t["good"] if priority["score"] >= 90 else t["s1"] if priority["score"] >= 75
                  else t["warn"] if priority["score"] >= 60 else t["critical"])
        write(gauge(priority["score"], priority["band"], "Priority score", colour))
        comps = "".join(
            f'<div style="display:flex;align-items:center;gap:11px;margin-top:8px">'
            f'<span style="width:126px;flex:none;font-size:11.5px;color:var(--text-muted)">'
            f'{esc(comp["label"])}</span>'
            f'<span style="flex:1">{meter(comp["raw"], 100, t["s1"], 5)}</span>'
            f'<span class="tnum" style="width:58px;text-align:right;font-size:11px;'
            f'color:var(--text-muted)">{round(comp["raw"])} · {comp["weight"]}%</span></div>'
            for comp in priority["components"])
        write(f'<div style="margin-top:14px">{comps}</div>')
    with rec_col:
        write(h3("Smart recommendations"))
        for r in recs:
            tone = {"opportunity": "good", "validate": "info"}.get(r["tone"], "warn")
            label = {"opportunity": "Opportunity", "validate": "Validate"}.get(r["tone"], "Caution")
            impact = (f'<p style="margin:6px 0 0;font-size:12.5px;font-weight:500;line-height:1.65;'
                      f'color:var(--text-primary)">{esc(r["impact"])}</p>' if r.get("impact") else "")
            write(f'<div class="dpv-tile" style="margin-top:10px">'
                  f'<div style="display:flex;align-items:center;gap:9px">{badge(label, tone)}'
                  f'<span style="font-size:13px;font-weight:600;color:var(--text-primary)">'
                  f'{esc(r["title"])}</span></div>'
                  f'<p style="margin:7px 0 0;font-size:12.5px;line-height:1.65;'
                  f'color:var(--text-secondary)">{esc(r["body"])}</p>{impact}</div>')

    # ── Investment + profile + lifecycle ────────────────────────────────────
    st.write("")
    a, b_, c_ = st.columns(3, gap="medium")
    with a:
        write(h3("Total cost of ownership") + key_value([
            ("Build cost", money(v["costs"]["buildTotal"], c)),
            ("Change & adoption", money(v["costs"]["changeTotal"], c)),
            ("Initial investment", money_full(v["costs"]["initialInvestment"], c)),
            ("Technology (annual)", money(v["costs"]["technologyAnnual"], c), True),
            ("Run (annual)", money(v["costs"]["runAnnual"], c), True),
            ("Annual operating cost", money(v["annualOperatingCost"], c)),
            (f"{settings['horizonYears']}-year total cost", money(v["totalCosts"], c)),
        ]))
    with b_:
        write(h3("Product profile") + key_value([
            ("Business unit", p["businessUnit"]),
            ("Domain", p["domain"]),
            ("Target users", f"{num(p['userCount'])} · {p['targetUsers'].split(',')[0]}"),
            ("Usage frequency", p["usageFrequency"]),
            ("Geographic scope", p["geographicScope"]),
            ("Delivery complexity", f"{p['complexity']}/10"),
            ("Time to value", f"{p['timeToValueMonths']} months"),
            ("Strategic value score", f"{v['strategicScore']}/100"),
        ]))
    with c_:
        write(h3("Lifecycle",
                 "Expected value becomes actual value as the product moves through the stages."))
        stage_index = LIFECYCLE_ORDER.index(p["lifecycle"])
        items = ""
        for i, stage in enumerate(LIFECYCLE_ORDER):
            done, current = i < stage_index, i == stage_index
            current_badge = ('<span style="margin-left:auto">' + badge("Current", "info") + "</span>"
                             if current else "")
            bg = (t["s1"] if current
                  else f"color-mix(in srgb, {t['s1']} 24%, transparent)" if done
                  else "var(--surface-3)")
            fg = "#fff" if current else "var(--text-muted)"
            items += (f'<li style="display:flex;align-items:center;gap:11px;padding:4px 0">'
                      f'<span style="width:17px;height:17px;border-radius:999px;flex:none;'
                      f'display:flex;align-items:center;justify-content:center;font-size:9px;'
                      f'font-weight:700;background:{bg};color:{fg}">{"✓" if done else i + 1}</span>'
                      f'<span style="font-size:12.5px;color:{"var(--text-primary)" if current else "var(--text-secondary)" if done else "var(--text-muted)"};'
                      f'{"font-weight:600" if current else ""}">{stage}</span>'
                      f'{current_badge}</li>')
        write(f'<ol style="margin:10px 0 0;padding:0;list-style:none">{items}</ol>')
        if p["realisation"]:
            if st.button("View value realisation  →", key="pd_real", use_container_width=True):
                goto("realisation", realisation_product=p["id"])

    # ── Description + assumptions ───────────────────────────────────────────
    st.write("")
    d1, d2 = st.columns(2, gap="medium")
    with d1:
        tags = " ".join(badge(tag) for tag in p["tags"])
        write(card(f'<h3 class="dpv-h3">Business problem</h3>'
                   f'<p style="margin:8px 0 0;font-size:13px;line-height:1.7;'
                   f'color:var(--text-secondary)">{esc(p["problemStatement"])}</p>'
                   f'<h3 class="dpv-h3" style="margin-top:20px">What the product does</h3>'
                   f'<p style="margin:8px 0 0;font-size:13px;line-height:1.7;'
                   f'color:var(--text-secondary)">{esc(p["description"])}</p>'
                   f'<div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:6px">{tags}</div>'))
    with d2:
        items = ""
        for asm in p["assumptions"]:
            if asm["unit"] == "%":
                val = pct(asm["value"], 1)
            elif "SGD" in asm["unit"] or asm["value"] > 10000:
                val = money_full(asm["value"], c)
            else:
                val = f"{num(asm['value'], 3 if asm['value'] % 1 else 0)} {asm['unit']}"
            items += (f'<div class="dpv-tile" style="margin-top:9px">'
                      f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px">'
                      f'<span style="font-size:12.5px;font-weight:500;color:var(--text-primary)">'
                      f'{esc(asm["assumption"])}</span>'
                      f'<span class="tnum" style="flex:none;font-size:12.5px;font-weight:600;'
                      f'color:var(--text-primary)">{esc(val)}</span></div>'
                      f'<div style="margin-top:6px;display:flex;flex-wrap:wrap;align-items:center;'
                      f'gap:4px 11px;font-size:11px;color:var(--text-muted)">'
                      f'{badge(asm["evidence"], evidence_tone(asm["evidence"]))}'
                      f'<span>{esc(asm["source"])}</span><span>· {esc(asm["owner"])}</span>'
                      f'<span>· confidence {asm["confidence"]}</span>'
                      f'<span>· {esc(asm["lastUpdated"])}</span></div></div>')
        write(card(f'<h3 class="dpv-h3">Key assumptions</h3>{items}'))

    write('<p style="margin:22px 0 0;max-width:60em;font-size:11.5px;line-height:1.7;'
          'color:var(--text-muted)">'
          "Forecast and estimated values. Risk value is risk-adjusted expected loss reduction, not "
          "a guaranteed saving. Cost avoidance is probability-weighted and does not reduce "
          "current-year budget. Validate with Finance and the business owner before formal "
          "investment approval.</p>")

    st.write("")
    with st.expander("Delete this valuation"):
        st.write(f"This removes **{p['name']}**, its assumptions and its realisation history from "
                 "this workspace. You can restore the full banking catalogue at any time from Settings.")
        if st.button("Delete product", type="primary", key="pd_delete"):
            store.delete_product(p["id"])
            st.session_state.pop("selected_product", None)
            goto("portfolio")


def kpi_cell(meta, value, gross, currency, t) -> str:
    share = (f"{pct(value / max(1, gross))} of annual value" if value > 0
             else "Not a value driver here")
    colour = "var(--text-primary)" if value > 0 else "var(--text-muted)"
    return (f'<div class="dpv-kpi" style="padding:14px 18px">'
            f'<div style="display:flex;align-items:center;gap:8px">'
            f'{swatch(t[meta["series"]])}'
            f'<span style="font-size:11.5px;font-weight:500;color:var(--text-muted)">'
            f'{esc(meta["short"])}</span></div>'
            f'<div class="tnum" style="margin-top:6px;font-size:19px;font-weight:600;'
            f'line-height:1;color:{colour}">{money(value, currency)}</div>'
            f'<div style="margin-top:4px;font-size:11px;color:var(--text-muted)">{share}</div></div>')
