"""Executive business case — a port of src/pages/Reports.tsx."""
from __future__ import annotations

import math
from datetime import datetime, timezone

import streamlit as st

from app import store
from app.charts import value_waterfall
from app.data.catalogs import CATEGORY_META
from app.engine.models import MODELS
from app.engine.recommendations import recommendations_for
from app.engine.scenarios import run_scenarios
from app.engine.sensitivity import tornado
from app.format import (money, money_full, months, num, pct, ratio_pct, relative_date)
from app.ui import badge, esc, evidence_tone, table, write
from .common import chart, page_header, product_picker


def _today_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_markdown(p, v, priority, scenarios, settings, decision) -> str:
    c = settings["currency"]
    lines = [
        f"# {p['name']} — Executive Business Case",
        f"{settings['organisationName']} · {p['businessUnit']} · {relative_date(_today_iso())}",
        "",
        "## Executive summary",
        (f"{p['name']} is estimated to create **{money(v['threeYearValue'], c)}** of economic value "
         f"over three years, on an initial investment of {money(v['costs']['initialInvestment'], c)} "
         f"and {money(v['annualOperatingCost'], c)} of annual operating cost. Return on investment "
         f"is {ratio_pct(v['roi'])} over {settings['horizonYears']} years, with payback in "
         f"{months(v['paybackMonths'])} and an NPV of {money(v['npv'], c)} at a "
         f"{pct(v['discountRate'])} discount rate."),
        "",
        "## Recommendation",
        f"**{decision}.** Priority score {priority['score']}/100 ({priority['band']}).",
        "",
        "## Financial summary",
        "| Metric | Value |", "| --- | ---: |",
        f"| Annual gross value | {money(v['annualGrossValue'], c)} |",
        f"| Annual operating cost | {money(v['annualOperatingCost'], c)} |",
        f"| Net annual value | {money(v['netAnnualValue'], c)} |",
        f"| Initial investment | {money(v['costs']['initialInvestment'], c)} |",
        f"| 3-year economic value | {money(v['threeYearValue'], c)} |",
        f"| 5-year economic value | {money(v['fiveYearValue'], c)} |",
        f"| ROI | {ratio_pct(v['roi'])} |",
        f"| Payback | {months(v['paybackMonths'])} |",
        f"| NPV | {money(v['npv'], c)} |",
        f"| IRR | {ratio_pct(v['irr']) if math.isfinite(v['irr']) else '—'} |",
        "",
        "## Value drivers",
    ]
    lines += [f"- **{b['benefit']['label']}** — {money(b['annualValue'], c)} p.a. "
              f"({MODELS[b['benefit']['kind']]['name']}, {b['benefit']['evidence']}, "
              f"{pct(b['benefit']['attribution'])} attribution)" for b in v["benefits"]]
    lines += ["", "## Key assumptions"]
    lines += [f"- {a['assumption']}: {a['value']} {a['unit']} — {a['source']} "
              f"({a['evidence']}, confidence {a['confidence']})" for a in p["assumptions"]]
    lines += ["", "## Risks and challenges"]
    lines += ([f"- **{g['title']}** — {g['detail']}" for g in v["guardrails"]]
              or ["- No assumptions fall outside benchmark ranges."])
    lines += ["", "---",
              "Values shown are estimates based on user-provided assumptions and should be "
              "validated with Finance and business owners before formal investment approval."]
    return "\n".join(lines)


def _section(n: int, title: str, body: str) -> str:
    return (f'<h2><span class="n">{n:02d}</span>{esc(title)}</h2>{body}')


def render() -> None:
    rows = store.rows()
    settings = store.settings()
    c = settings["currency"]
    th = store.theme()

    if not rows:
        st.info("No products to report on.")
        return

    page_header("Executive Business Case",
                "A complete, board-ready investment paper generated from the valuation.")

    default = st.session_state.get("report_product")
    pick_col, dl_col = st.columns([2, 1.2], vertical_alignment="bottom")
    with pick_col:
        pid = product_picker("Product", rows, "rep_pick",
                             default if default and any(r["product"]["id"] == default for r in rows)
                             else None)
    row = next(r for r in rows if r["product"]["id"] == pid)
    p, v, priority = row["product"], row["valuation"], row["priority"]

    scenarios = run_scenarios(p, settings)
    sens = tornado(p, settings, None, 6)
    recs = recommendations_for(p, settings, v)
    decision = {"Invest Now": "Invest", "Accelerate": "Accelerate",
                "Validate": "Validate"}.get(priority["band"], "Reassess")
    weakest = sorted(v["confidence"]["dimensions"], key=lambda d: d["value"])[0]["label"].lower()

    with dl_col:
        st.download_button("⤓  Download Markdown",
                           build_markdown(p, v, priority, scenarios, settings, decision),
                           f"{p['name'].replace(' ', '-').lower()}-business-case.md",
                           "text/markdown", use_container_width=True)

    st.write("")
    write(f"""<div class="dpv-paper">
      <div style="border-bottom:1px solid var(--hairline);padding-bottom:22px">
        <div style="font-size:11.5px;font-weight:600;text-transform:uppercase;letter-spacing:.12em;
             color:var(--s1)">{esc(settings['organisationName'])} · Data &amp; AI investment paper</div>
        <h1 style="margin:12px 0 0;font-size:32px;font-weight:600;line-height:1.15;
             letter-spacing:-0.03em;color:var(--text-primary)">{esc(p['name'])}</h1>
        <p style="margin:8px 0 0;font-size:14px;color:var(--text-secondary)">
          {esc(p['type'])} · {esc(p['businessUnit'])} · {esc(p['lifecycle'])}</p>
        <div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:8px 32px;font-size:12.5px;
             color:var(--text-muted)">
          <span>Product owner: <strong style="color:var(--text-secondary)">{esc(p['owner'])}</strong></span>
          <span>Business sponsor: <strong style="color:var(--text-secondary)">{esc(p['sponsor'])}</strong></span>
          <span>Prepared: <strong style="color:var(--text-secondary)">{relative_date(_today_iso())}</strong></span>
        </div>
      </div>

      <div style="margin-top:26px;border-radius:16px;padding:24px 26px;background:var(--surface-3)">
        <div class="dpv-eyebrow" style="letter-spacing:.09em">Estimated 3-year economic value</div>
        <div class="tnum" style="margin-top:6px;font-size:42px;font-weight:600;line-height:1;
             letter-spacing:-0.035em;color:var(--text-primary)">{money(v['threeYearValue'], c)}</div>
        <div style="margin-top:18px;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
             gap:12px 32px">
          {"".join(f'<div><div class="dpv-eyebrow">{k}</div><div class="tnum" style="margin-top:2px;font-size:18px;font-weight:600;color:var(--text-primary)">{val}</div></div>'
                   for k, val in [("Net annual value", money(v["netAnnualValue"], c)),
                                  ("ROI", ratio_pct(v["roi"])),
                                  ("Payback", months(v["paybackMonths"])),
                                  ("IRR", ratio_pct(v["irr"]) if math.isfinite(v["irr"]) else "—")])}
        </div>
      </div>

      {_section(1, "Executive summary", f'''
        <p>{esc(p['name'])} is estimated to create <strong>{money(v['threeYearValue'], c)}</strong> of
        economic value over three years, on an initial investment of
        {money(v['costs']['initialInvestment'], c)} and {money(v['annualOperatingCost'], c)} of annual
        operating cost. The case returns <strong>{ratio_pct(v['roi'])}</strong> over
        {settings['horizonYears']} years, pays back in <strong>{months(v['paybackMonths'])}</strong>
        from first spend ({months(v['paybackFromGoLive'])} from go-live) and carries an NPV of
        {money(v['npv'], c)} at a {pct(v['discountRate'])} discount rate.</p>
        <p style="margin-top:12px">Of the {money(v['annualGrossValue'], c)} annual gross value,
        {money(v['hardDollarValue'], c)} is hard-dollar
        ({pct(v['hardDollarValue'] / max(1, v['annualGrossValue']))}) and {money(v['softValue'], c)}
        is indirect — productivity, risk-adjusted and probability-weighted value.
        {money(v['byMaturity']['Proven'], c)} of annual value is evidenced by measured actuals, with
        the remainder resting on pilots, benchmarks and estimates.</p>''')}

      {_section(2, "Business problem", f"<p>{esc(p['problemStatement'])}</p>")}

      {_section(3, "Data product description", f'''
        <p>{esc(p['description'])}</p>
        <p style="margin-top:12px">Target population is {num(p['userCount'])}
        {esc(p['targetUsers'].lower())}, using the product {esc(p['usageFrequency'].lower())}, across a
        {esc(p['geographicScope'].lower())} footprint. Delivery complexity is assessed at
        {p['complexity']}/10 with first measurable value expected {p['timeToValueMonths']} months
        after start.</p>''')}
    </div>""")

    # Value drivers (table + waterfall)
    body = "".join(
        f"<tr><td class='strong'>{esc(b['benefit']['label'])}</td>"
        f"<td>{esc(CATEGORY_META[b['category']]['short'])}</td>"
        f"<td>{esc(b['benefit']['evidence'])}</td>"
        f"<td class='num'>{pct(b['benefit']['attribution'])}</td>"
        f"<td class='num strong'>{money(b['annualValue'], c)}</td></tr>"
        for b in sorted(v["benefits"], key=lambda b: b["annualValue"], reverse=True))
    write(f'<div class="dpv-paper" style="margin-top:8px">'
          + _section(4, "Value drivers",
                     table([("Value driver", False), ("Type", False), ("Evidence", False),
                            ("Attribution", True), ("Annual value", True)], body))
          + "</div>")
    chart(value_waterfall(v, c, th, height=290), key="rep_wf")

    # Financial benefits
    body = "".join(
        f"<tr><td class='strong'>{esc(meta['label'])}</td>"
        f"<td class='num strong'>{money(v['byCategory'][k], c)}</td>"
        f"<td class='num'>{pct(v['byCategory'][k] / max(1, v['annualGrossValue']))}</td>"
        f"<td>{esc(meta['blurb'])}</td></tr>"
        for k, meta in CATEGORY_META.items() if v["byCategory"][k] > 0)
    inv = [("Build", money_full(v["costs"]["buildTotal"], c),
            f"One-off, over {p['investment']['buildMonths']} months"),
           ("Change &amp; adoption", money_full(v["costs"]["changeTotal"], c), "One-off"),
           ("<strong>Initial investment</strong>", money_full(v["costs"]["initialInvestment"], c),
            "Capital request"),
           ("Technology", money_full(v["costs"]["technologyAnnual"], c), "Annual run-rate"),
           ("Run &amp; support", money_full(v["costs"]["runAnnual"], c), "Annual run-rate"),
           ("<strong>Annual operating cost</strong>", money_full(v["annualOperatingCost"], c),
            "Recurring"),
           (f"{settings['horizonYears']}-year total cost of ownership",
            money_full(v["totalCosts"], c), "Investment plus operating cost")]
    inv_body = "".join(f"<tr><td class='strong'>{label}</td><td class='num strong'>{amount}</td>"
                       f"<td>{basis}</td></tr>" for label, amount, basis in inv)

    scen_body = "".join(
        f"<tr><td class='strong'>{esc(s['label'])}</td>"
        f"<td class='num strong'>{money(s['valuation']['threeYearValue'], c)}</td>"
        f"<td class='num'>{ratio_pct(s['valuation']['roi'])}</td>"
        f"<td class='num'>{money(s['valuation']['npv'], c)}</td>"
        f"<td class='num'>{months(s['valuation']['paybackMonths'])}</td></tr>" for s in scenarios)

    def _assumption_value(a) -> str:
        if a["unit"] == "%":
            return pct(a["value"], 1)
        decimals = 3 if a["value"] % 1 else 0
        return f'{num(a["value"], decimals)} {esc(a["unit"])}'

    asm_body = "".join(
        f"<tr><td class='strong'>{esc(a['assumption'])}</td>"
        f"<td class='num'>{_assumption_value(a)}</td>"
        f"<td>{esc(a['source'])}</td><td>{esc(a['owner'])}</td>"
        f"<td>{badge(a['evidence'], evidence_tone(a['evidence']))}</td></tr>"
        for a in p["assumptions"])

    dims_body = "".join(f"<tr><td class='strong'>{esc(d['label'])}</td>"
                        f"<td class='num'>{round(d['weight'] * 100)}%</td></tr>"
                        for d in v["confidence"]["dimensions"])

    conservative_line = ("remains value-accretive" if scenarios[0]["valuation"]["npv"] > 0
                         else "does not clear the hurdle rate, which is the key risk to weigh")
    npv_line = (" The case is value-accretive at the organisation-wide hurdle rate."
                if v["npv"] > 0 else
                " The case does not clear the hurdle rate on current assumptions.")
    irr_line = (f" and an internal rate of return of <strong>{ratio_pct(v['irr'])}</strong>"
                if math.isfinite(v["irr"]) else "")

    risks = ("<p>No assumption in this case falls outside the benchmark ranges applied by the "
             "valuation guardrails. The principal residual risk is delivery execution rather than "
             "value estimation.</p>" if not v["guardrails"] else
             "<ul style='margin:6px 0 0;padding-left:18px'>"
             + "".join(f"<li style='margin-top:8px'><strong>{esc(g['title'])}.</strong> "
                       f"{esc(g['detail'])}</li>" for g in v["guardrails"]) + "</ul>")
    actions = ("<p style='margin-top:16px'>Actions that would strengthen the case before approval:</p>"
               "<ul style='margin:6px 0 0;padding-left:18px'>"
               + "".join(f"<li style='margin-top:8px'><strong>{esc(r['title'])}.</strong> "
                         f"{esc(r['body'])} {esc(r.get('impact') or '')}</li>"
                         for r in recs[:4]) + "</ul>")

    decision_copy = {
        "Invest": (f"{p['name']} scores {priority['score']}/100 on portfolio priority. It combines "
                   "material economic value, credible evidence and a short payback. Fund at the full "
                   "requested amount and hold the product to the value realisation plan."),
        "Accelerate": (f"{p['name']} scores {priority['score']}/100 on portfolio priority. The case is "
                       "strong and the evidence base is sound. Fund it, and consider bringing delivery "
                       f"forward — {money(v['netAnnualValue'] / 12, c)} of net value accrues for every "
                       "month it ships earlier."),
        "Validate": (f"{p['name']} scores {priority['score']}/100 on portfolio priority. The economics "
                     "are attractive but the evidence base is still thin. Approve a funded validation "
                     "stage rather than the full investment, with a decision gate once the largest "
                     "assumptions have been measured."),
        "Reassess": (f"{p['name']} scores {priority['score']}/100 on portfolio priority. On current "
                     "assumptions the case does not compete with the rest of the portfolio. Either "
                     "re-scope to a materially smaller investment, strengthen the value hypothesis "
                     "with evidence, or release the capacity to higher-scoring products."),
    }[decision]

    write(f"""<div class="dpv-paper" style="margin-top:8px">
      {_section(5, "Financial benefits", table([("Category", False), ("Annual value", True), ("Share", True), ("Treatment", False)], body))}
      {_section(6, "Investment", table([("Cost element", False), ("Amount", True), ("Basis", False)], inv_body))}
      {_section(7, "Return on investment", f'''
        <p>Over the {settings['horizonYears']}-year horizon the product generates
        {money(v['totalBenefits'], c)} of gross benefit against {money(v['totalCosts'], c)} of total
        cost, a return of <strong>{ratio_pct(v['roi'])}</strong>. Every {c} 1 invested returns
        {c} {v['valuePerDollar']:.2f} of gross economic value.</p>''')}
      {_section(8, "Payback", f'''
        <p>Cumulative net cashflow turns positive at <strong>{months(v['paybackMonths'])}</strong> from
        the start of investment, equivalent to {months(v['paybackFromGoLive'])} from go-live. Business
        sponsors typically reference payback from go-live; Finance references it from first spend. Both
        are stated here to avoid ambiguity in review.</p>''')}
      {_section(9, "Net present value", f'''
        <p>Discounting monthly net cashflows at {pct(v['discountRate'])} over {settings['horizonYears']}
        years gives an NPV of <strong>{money(v['npv'], c)}</strong>{irr_line}.{npv_line}</p>''')}
      {_section(10, "Scenario analysis",
                table([("Scenario", False), ("3-year value", True), ("ROI", True), ("NPV", True), ("Payback", True)], scen_body)
                + f'''<p style="margin-top:12px">The conservative case reflects lower adoption, reduced
                attribution and a 25% cost overrun. Even under those conditions the product
                {conservative_line}.</p>
                <p style="margin-top:12px">Sensitivity testing identifies the assumptions with the
                greatest influence on the valuation, in order:
                {esc(', '.join(s['label'].lower() for s in sens))}.</p>''')}
      {_section(11, "Key assumptions",
                table([("Assumption", False), ("Value", True), ("Source", False), ("Owner", False), ("Evidence", False)], asm_body)
                if p["assumptions"] else "<p>No assumptions have been formally registered for this product.</p>")}
      {_section(12, "Evidence assessment", f'''
        <p>This valuation is assessed against baseline quality, data availability, assumption strength,
        historical evidence, attribution, adoption, financial validation and measurement maturity,
        blended with the evidence grade of each benefit line. The weakest area today is
        <strong>{esc(weakest)}</strong> — strengthening it first would do the most to firm up the
        case.</p>''' + table([("Dimension assessed", False), ("Weight", True)], dims_body)
        + f'''<p style="margin-top:12px">Value maturity split: {money(v['byMaturity']['Proven'], c)}
        proven, {money(v['byMaturity']['Expected'], c)} expected,
        {money(v['byMaturity']['Potential'], c)} potential.</p>''')}
      {_section(13, "Risks and challenges", risks + actions)}
      {_section(14, "Recommendation", f'''
        <div style="border-radius:14px;padding:20px 22px;
             background:color-mix(in srgb, var(--s1) 8%, transparent)">
          <div style="font-size:19px;font-weight:600;letter-spacing:-0.02em;color:var(--text-primary)">
            Recommendation: {decision}</div>
          <p style="margin-top:10px">{esc(decision_copy)}</p>
          <p style="margin-top:12px;font-size:12.5px;color:var(--text-muted)">
            Requested: {money_full(v['costs']['initialInvestment'], c)} initial investment plus
            {money_full(v['annualOperatingCost'], c)} annual operating cost.</p>
        </div>''')}
      <p style="margin-top:30px;padding-top:20px;border-top:1px solid var(--hairline);
         font-size:11.5px;line-height:1.7;color:var(--text-muted)">
        Values shown are estimates based on user-provided assumptions and should be validated with
        Finance and business owners before formal investment approval. Risk value is risk-adjusted
        expected loss reduction, not a guaranteed saving. Cost avoidance is probability-weighted and
        does not reduce current-year budget. Productivity value represents capacity released at
        fully-loaded cost and reaches the P&amp;L only where capacity is formally removed or
        redeployed.</p>
    </div>""")
