"""Boardroom mode — a port of src/pages/Boardroom.tsx.

Six slides for presenting a single valuation, driven by the same numbers as the
rest of the app.
"""
from __future__ import annotations

import math

import streamlit as st

from app import store
from app.charts import value_waterfall
from app.data.catalogs import CATEGORY_META
from app.engine.scenarios import run_scenarios
from app.format import money, months, num, pct, ratio_pct
from app.theme import tokens
from app.ui import esc, swatch, write
from .common import chart, product_picker

SLIDES = 6


def render() -> None:
    rows = store.rows()
    settings = store.settings()
    c = settings["currency"]
    th = store.theme()
    t = tokens(th)

    if not rows:
        st.info("No products to present.")
        return

    st.session_state.setdefault("board_slide", 0)

    head, pick = st.columns([2, 1.4], vertical_alignment="center")
    with head:
        write(f'<div style="display:flex;align-items:center;gap:10px;padding-top:6px">'
              f'<svg width="20" height="20" viewBox="0 0 64 64" aria-hidden="true">'
              f'<rect x="10" y="34" width="10" height="18" rx="3.5" fill="{t["s1"]}"/>'
              f'<rect x="27" y="23" width="10" height="29" rx="3.5" fill="{t["s3"]}"/>'
              f'<rect x="44" y="12" width="10" height="40" rx="3.5" fill="{t["s4"]}"/></svg>'
              f'<span style="font-size:13px;font-weight:500;color:var(--text-secondary)">'
              f"Data Product Value</span>"
              f'<span style="color:var(--text-muted)">·</span>'
              f'<span style="font-size:13px;color:var(--text-muted)">'
              f'{esc(settings["organisationName"])}</span></div>')
    with pick:
        default = st.session_state.get("boardroom_product")
        pid = product_picker("Presented product", rows, "board_pick",
                             default if default and any(r["product"]["id"] == default for r in rows)
                             else None, help="Choose the valuation to present")

    row = next(r for r in rows if r["product"]["id"] == pid)
    p, v, priority = row["product"], row["valuation"], row["priority"]
    scenarios = run_scenarios(p, settings)
    decision = {"Invest Now": "Invest", "Accelerate": "Accelerate",
                "Validate": "Validate first"}.get(priority["band"], "Reassess")
    slide = st.session_state.board_slide

    st.write("")
    if slide == 0:
        write(f"""<div class="dpv-stage">
          <div class="eyebrow">{esc(p['businessUnit'])} · {esc(p['type'])}</div>
          <h1>{esc(p['name'])}</h1>
          <p class="lede">This data product can generate
            <span style="font-weight:600;color:var(--text-primary)">
            {money(v['threeYearValue'], c)}</span> of economic value over three years.</p>
        </div>""")
    elif slide == 1:
        cells = "".join(
            f'<div><div class="dpv-eyebrow" style="letter-spacing:.1em">{k}</div>'
            f'<div class="tnum" style="margin-top:6px;font-size:36px;font-weight:600;'
            f'letter-spacing:-0.03em;line-height:1;color:var(--text-primary)">{val}</div></div>'
            for k, val in [("Net annual value", money(v["netAnnualValue"], c)),
                           ("Return on investment", ratio_pct(v["roi"])),
                           ("Payback", months(v["paybackMonths"])),
                           ("IRR", ratio_pct(v["irr"]) if math.isfinite(v["irr"]) else "—")])
        write(f"""<div class="dpv-stage">
          <div class="dpv-eyebrow" style="letter-spacing:.2em;font-size:13px">
            3-year economic value</div>
          <div class="huge">{money(v['threeYearValue'], c)}</div>
          <div style="margin-top:48px;display:grid;
               grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:32px">{cells}</div>
        </div>""")
    elif slide == 2:
        cells = "".join(
            f'<div><div style="display:flex;align-items:center;gap:8px">'
            f'{swatch(t[meta["series"]])}'
            f'<span style="font-size:12.5px;font-weight:500;color:var(--text-muted)">'
            f'{esc(meta["short"])}</span></div>'
            f'<div class="tnum" style="margin-top:8px;font-size:28px;font-weight:600;'
            f'letter-spacing:-0.025em;line-height:1;color:var(--text-primary)">'
            f'{money(v["byCategory"][key], c)}</div>'
            f'<div style="margin-top:6px;font-size:12px;color:var(--text-muted)">'
            f'{pct(v["byCategory"][key] / max(1, v["annualGrossValue"]))} of annual value</div></div>'
            for key, meta in CATEGORY_META.items() if v["byCategory"][key] > 0)
        write(f"""<div class="dpv-stage" style="min-height:0">
          <h2 style="margin:0;font-size:40px;font-weight:600;line-height:1.15;
              letter-spacing:-0.03em;color:var(--text-primary)">Where the value comes from</h2>
          <div style="margin-top:26px;display:grid;
               grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:28px">{cells}</div>
        </div>""")
        chart(value_waterfall(v, c, th, height=300, show_investment=False), key="board_wf")
    elif slide == 3:
        cards = "".join(
            f'<div style="border-radius:18px;padding:26px;background:var(--surface-1);'
            f'box-shadow:inset 0 0 0 {"2px var(--s1)" if s["key"] == "base" else "1px var(--hairline)"}">'
            f'<div style="font-size:12.5px;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:.1em;color:{t["s1"] if s["key"] == "base" else t["text-muted"]}">'
            f'{esc(s["label"])}</div>'
            f'<div class="tnum" style="margin-top:12px;font-size:36px;font-weight:600;'
            f'letter-spacing:-0.03em;line-height:1;color:var(--text-primary)">'
            f'{money(s["valuation"]["threeYearValue"], c)}</div>'
            f'<div style="margin-top:18px;font-size:13.5px">'
            f'{_kv("ROI", ratio_pct(s["valuation"]["roi"]))}'
            f'{_kv("NPV", money(s["valuation"]["npv"], c))}'
            f'{_kv("Payback", months(s["valuation"]["paybackMonths"]))}</div></div>'
            for s in scenarios)
        write(f"""<div class="dpv-stage">
          <h2 style="margin:0;font-size:40px;font-weight:600;line-height:1.15;
              letter-spacing:-0.03em;color:var(--text-primary)">What if we are wrong?</h2>
          <p class="lede" style="font-size:19px;margin-top:14px">Three-year economic value under
            conservative, base and upside assumptions.</p>
          <div style="margin-top:36px;display:grid;
               grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px">{cards}</div>
        </div>""")
    elif slide == 4:
        evidenced = (round(100 * (v["byMaturity"]["Proven"] + v["byMaturity"]["Expected"])
                           / v["annualGrossValue"]) if v["annualGrossValue"] > 0 else 0)
        right = "".join(
            f'<div style="border-bottom:1px solid var(--hairline);padding-bottom:14px;'
            f'margin-bottom:14px">'
            f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:16px">'
            f'<span style="font-size:15px;color:var(--text-secondary)">{esc(label)}</span>'
            f'<span class="tnum" style="font-size:24px;font-weight:600;letter-spacing:-0.02em;'
            f'color:var(--text-primary)">{val}</span></div>'
            f'<div style="margin-top:4px;font-size:12.5px;color:var(--text-muted)">{esc(note)}</div>'
            f"</div>"
            for label, val, note in [
                ("Hard-dollar value", money(v["hardDollarValue"], c), "Reaches the P&L directly"),
                ("Indirect value", money(v["softValue"], c), "Capacity, risk and avoided cost"),
                ("Capacity released", f"{num(v['fteEquivalent'], 1)} FTE",
                 "Redeployed, not removed, unless agreed"),
                ("Strategic value score", f"{v['strategicScore']}/100",
                 "Scored separately — never added to the financials")])
        write(f"""<div class="dpv-stage">
          <h2 style="margin:0;font-size:40px;font-weight:600;line-height:1.15;
              letter-spacing:-0.03em;color:var(--text-primary)">How much can we rely on this?</h2>
          <div style="margin-top:34px;display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
               gap:44px">
            <div>
              <div class="dpv-eyebrow" style="letter-spacing:.14em;font-size:13px">Evidence maturity</div>
              <div style="margin-top:12px;display:flex;align-items:baseline;gap:14px">
                <span class="tnum" style="font-size:76px;font-weight:600;line-height:1;
                      letter-spacing:-0.04em;color:var(--text-primary)">{evidenced}</span>
                <span style="font-size:24px;font-weight:300;color:var(--text-muted)">% evidenced</span>
              </div>
              <div style="margin-top:10px;font-size:19px;font-weight:500;color:var(--text-secondary)">
                Measured actuals + pilots &amp; benchmarks</div>
              <p style="margin-top:20px;max-width:30em;font-size:15px;line-height:1.7;
                 color:var(--text-muted)">
                {money(v['byMaturity']['Proven'], c)} of annual value is evidenced by measured actuals,
                {money(v['byMaturity']['Expected'], c)} by pilots and benchmarks, and
                {money(v['byMaturity']['Potential'], c)} by estimate.</p>
            </div>
            <div>{right}</div>
          </div>
        </div>""")
    else:
        stats = "".join(
            f'<div><div class="dpv-eyebrow" style="letter-spacing:.1em">{k}</div>'
            f'<div class="tnum" style="margin-top:6px;font-size:26px;font-weight:600;'
            f'letter-spacing:-0.025em;color:var(--text-primary)">{val}</div></div>'
            for k, val in [("Priority score", f"{priority['score']}/100"),
                           ("Portfolio position", priority["band"]),
                           ("Portfolio 3-year value", money(store.totals()["threeYear"], c))])
        write(f"""<div class="dpv-stage">
          <div class="eyebrow">Recommendation</div>
          <h1 style="font-size:70px">{esc(decision)}</h1>
          <p class="lede" style="font-size:22px">
            {money(v['costs']['initialInvestment'], c)} of investment and
            {money(v['annualOperatingCost'], c)} a year to run, returning
            <span style="font-weight:600;color:var(--text-primary)">
            {money(v['netAnnualValue'], c)}</span> of net annual economic value — a
            <span style="font-weight:600;color:var(--text-primary)">{ratio_pct(v['roi'])}</span>
            return with payback in {months(v['paybackMonths'])}.</p>
          <div style="margin-top:40px;display:flex;flex-wrap:wrap;gap:24px 56px">{stats}</div>
          <p style="margin-top:44px;max-width:60em;font-size:12.5px;line-height:1.7;
             color:var(--text-muted)">
            Values shown are estimates based on user-provided assumptions and should be validated
            with Finance and business owners before formal investment approval.</p>
        </div>""")

    # ── Navigation ──────────────────────────────────────────────────────────
    st.write("")
    dots = "".join(
        f'<span style="display:inline-block;height:6px;border-radius:999px;margin-right:6px;'
        f'width:{30 if i == slide else 8}px;'
        f'background:{t["s1"] if i == slide else t["hairline-strong"]}"></span>'
        for i in range(SLIDES))
    nav_a, nav_b, nav_c = st.columns([4, 1, 1])
    nav_a.markdown(f'<div style="padding-top:12px">{dots}</div>', unsafe_allow_html=True)
    if nav_b.button("←  Previous", disabled=slide == 0, use_container_width=True, key="board_prev"):
        st.session_state.board_slide = max(0, slide - 1)
        st.rerun()
    if nav_c.button("Next  →", type="primary", disabled=slide == SLIDES - 1,
                    use_container_width=True, key="board_next"):
        st.session_state.board_slide = min(SLIDES - 1, slide + 1)
        st.rerun()


def _kv(label: str, value: str) -> str:
    return (f'<div style="display:flex;justify-content:space-between;margin-top:8px">'
            f'<span style="color:var(--text-muted)">{esc(label)}</span>'
            f'<span class="tnum" style="font-weight:600;color:var(--text-primary)">'
            f"{esc(value)}</span></div>")
