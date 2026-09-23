"""Side-by-side comparison — a port of src/pages/Compare.tsx."""
from __future__ import annotations

import math

import streamlit as st

from app import store
from app.data.catalogs import CATEGORY_META
from app.format import money, months, num, pct, ratio_pct
from app.theme import tokens
from app.ui import badge, band_tone, card, empty_state, esc, h3, meter, table, write
from .common import page_header

METRICS = [
    ("3-year economic value", lambda r: r["valuation"]["threeYearValue"], "money", "high"),
    ("5-year economic value", lambda r: r["valuation"]["fiveYearValue"], "money", "high"),
    ("Net annual value", lambda r: r["valuation"]["netAnnualValue"], "money", "high"),
    ("Initial investment", lambda r: r["valuation"]["costs"]["initialInvestment"], "money", "low"),
    ("Annual run cost", lambda r: r["valuation"]["annualOperatingCost"], "money", "low"),
    ("ROI", lambda r: r["valuation"]["roi"], "ratio", "high"),
    ("Payback", lambda r: (r["valuation"]["paybackMonths"]
                           if math.isfinite(r["valuation"]["paybackMonths"]) else 999),
     "months", "low"),
    ("NPV", lambda r: r["valuation"]["npv"], "money", "high"),
    ("IRR", lambda r: (r["valuation"]["irr"] if math.isfinite(r["valuation"]["irr"]) else 0),
     "ratio_or_dash", "high"),
    ("Strategic value score", lambda r: r["valuation"]["strategicScore"], "score", "high"),
    ("Delivery complexity", lambda r: r["product"]["complexity"], "ten", "low"),
    ("Time to value", lambda r: r["product"]["timeToValueMonths"], "months_plain", "low"),
    ("Hard-dollar share", lambda r: (r["valuation"]["hardDollarValue"] / r["valuation"]["annualGrossValue"]
                                     if r["valuation"]["annualGrossValue"] > 0 else 0), "pct", "high"),
    ("Priority score", lambda r: r["priority"]["score"], "score", "high"),
]


def _fmt(kind: str, v: float, c: str) -> str:
    if kind == "money":
        return money(v, c)
    if kind == "ratio":
        return ratio_pct(v)
    if kind == "ratio_or_dash":
        return ratio_pct(v) if v else "—"
    if kind == "months":
        return months(v)
    if kind == "months_plain":
        return f"{int(v)} months"
    if kind == "score":
        return f"{round(v)}/100"
    if kind == "ten":
        return f"{v}/10"
    return pct(v)


def _recommendation(rows, c):
    if len(rows) < 2:
        return None
    scored = []
    for r in rows:
        v = r["valuation"]
        pb = v["paybackMonths"] if math.isfinite(v["paybackMonths"]) else 120
        score = (min(1, max(0, v["roi"] / 6)) * 30
                 + (v["confidence"]["score"] / 100) * 30
                 + max(0, 1 - pb / 36) * 20
                 + (r["priority"]["score"] / 100) * 20)
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    win, runner_up = scored[0][1], scored[1][1]
    best_roi = max(rows, key=lambda r: r["valuation"]["roi"])
    estimate_heavy = [r for r in rows
                      if r["valuation"]["byMaturity"]["Potential"]
                      / (r["valuation"]["annualGrossValue"] or 1) > 0.5]

    text = (f"{win['product']['name']} is the strongest near-term investment. It combines "
            f"{money(win['valuation']['threeYearValue'], c)} of three-year economic value and a "
            f"{ratio_pct(win['valuation']['roi'])} return, paying back in "
            f"{months(win['valuation']['paybackMonths'])}.")
    if best_roi["product"]["id"] != win["product"]["id"]:
        n = len(best_roi["valuation"]["guardrails"])
        extra = (f" and {n} assumption{'s fall' if n > 1 else ' falls'} outside benchmark ranges"
                 if n else "")
        text += (f" {best_roi['product']['name']} shows a higher headline return at "
                 f"{ratio_pct(best_roi['valuation']['roi'])}, but that number carries materially "
                 f"more estimation risk{extra}.")
    if estimate_heavy:
        names = " and ".join(r["product"]["name"] for r in estimate_heavy)
        text += (f" Before committing, {names} would each benefit from a short validation period — "
                 "most of their value still rests on estimates, so the ranking could change once "
                 "the baselines are measured.")
    text += f" {runner_up['product']['name']} is the natural second call if funding allows both."
    return text


def render() -> None:
    rows = store.rows()
    c = store.currency()
    t = tokens(store.theme())

    page_header("Which product should we fund?",
                "Compare up to four data products side by side across value, cost and risk.")

    all_ids = [r["product"]["id"] for r in rows]
    names = {r["product"]["id"]: r["product"]["name"] for r in rows}
    default = [i for i in st.session_state.compare_ids if i in all_ids]
    picked = st.multiselect("Choose products to compare (up to four)", all_ids, default,
                            format_func=lambda i: names[i], max_selections=4, key="cmp_pick")
    if picked != st.session_state.compare_ids:
        store.set_compare(picked)

    selected = [r for r in rows if r["product"]["id"] in picked]
    selected.sort(key=lambda r: picked.index(r["product"]["id"]))

    if len(selected) < 2:
        write(card(empty_state(
            "Select at least two products",
            "Comparison is most useful when the products are competing for the same investment "
            "envelope.", "⇄")))
        return

    rec = _recommendation(selected, c)
    if rec:
        write(card(f'<div style="display:flex;gap:12px">'
                   f'<span style="width:32px;height:32px;flex:none;border-radius:10px;display:flex;'
                   f'align-items:center;justify-content:center;color:{t["good"]};'
                   f'background:color-mix(in srgb, {t["good"]} 14%, transparent)">🏆</span>'
                   f'<div><h3 class="dpv-h3">Recommendation</h3>'
                   f'<p style="margin:6px 0 0;max-width:70em;font-size:13.5px;line-height:1.7;'
                   f'color:var(--text-secondary)">{esc(rec)}</p></div></div>'))

    # ── Metric table with per-row winner highlighting ────────────────────────
    headers = [("Metric", False)] + [(r["product"]["name"], True) for r in selected]
    body = ""
    for label, getter, kind, direction in METRICS:
        values = [(r["product"]["id"], getter(r)) for r in selected]
        ordered = sorted(values, key=lambda kv: kv[1], reverse=(direction == "high"))
        winner = None if ordered[0][1] == ordered[-1][1] else ordered[0][0]
        cells = ""
        for pid, val in values:
            win = pid == winner
            style = (f'background:color-mix(in srgb, {t["good"]} 14%, transparent);'
                     "padding:3px 7px;border-radius:6px;font-weight:600;color:var(--text-primary)"
                     if win else "")
            cells += f'<td class="num"><span style="{style}">{_fmt(kind, val, c)}</span></td>'
        body += f'<tr><td>{esc(label)}</td>{cells}</tr>'

    body += ("<tr><td>Priority band</td>"
             + "".join(f'<td class="num">{badge(r["priority"]["band"], band_tone(r["priority"]["band"]))}</td>'
                       for r in selected) + "</tr>")
    body += ("<tr><td>Assumption flags</td>"
             + "".join(
                 f'<td class="num">'
                 + ("<span>None</span>" if not r["valuation"]["guardrails"]
                    else badge(len(r["valuation"]["guardrails"]),
                               "critical" if any(g["severity"] == "severe"
                                                 for g in r["valuation"]["guardrails"]) else "warn"))
                 + "</td>" for r in selected) + "</tr>")
    write(card(f'<div class="dpv-cmp">{table(headers, body, min_width=210 + 190 * len(selected))}</div>',
               flush=True))

    # ── Per-product value mix ────────────────────────────────────────────────
    st.write("")
    cols = st.columns(len(selected), gap="medium")
    for col, r in zip(cols, selected):
        v = r["valuation"]
        bars = "".join(
            f'<div style="margin-bottom:9px">'
            f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:8px;'
            f'margin-bottom:4px"><span style="font-size:11.5px;color:var(--text-muted)">'
            f'{esc(meta["short"])}</span><span class="tnum" style="font-size:11.5px;font-weight:500;'
            f'color:var(--text-secondary)">{money(v["byCategory"][key], c)}</span></div>'
            f'{meter(v["byCategory"][key], max(1, v["annualGrossValue"]), t[meta["series"]], 5)}</div>'
            for key, meta in CATEGORY_META.items())
        with col:
            write(card(
                f'<h4 style="margin:0;font-size:14px;font-weight:600;color:var(--text-primary)">'
                f'{esc(r["product"]["name"])}</h4>'
                f'<p style="margin:3px 0 12px;font-size:11.5px;color:var(--text-muted)">'
                f'{esc(r["product"]["type"])}</p>{bars}'
                f'<p style="margin:10px 0 0;font-size:11.5px;line-height:1.65;'
                f'color:var(--text-muted)">Capacity released ≈ {num(v["fteEquivalent"], 1)} FTE · '
                f'{pct(v["hardDollarValue"] / max(1, v["annualGrossValue"]))} hard-dollar</p>'))
