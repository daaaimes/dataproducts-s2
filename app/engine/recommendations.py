"""Smart recommendations — a port of src/engine/recommendations.ts."""
from __future__ import annotations

import copy

from ..format import money, pct, js_round
from .valuation import value_product


def recommendations_for(p, settings, v):
    out = []
    cur = v["threeYearValue"]
    c = settings["currency"]

    # 1 — Adoption headroom
    adoption_benefits = [b for b in p["benefits"] if isinstance(b["inputs"].get("adoption"), (int, float))]
    if adoption_benefits:
        avg_adoption = sum(b["inputs"]["adoption"] for b in adoption_benefits) / len(adoption_benefits)
        if avg_adoption < 0.85:
            target = min(0.9, avg_adoption + 0.15)
            d = copy.deepcopy(p)
            for b in d["benefits"]:
                if isinstance(b["inputs"].get("adoption"), (int, float)):
                    b["inputs"]["adoption"] = min(0.9, b["inputs"]["adoption"] + 0.15)
            uplift = value_product(d, settings)["threeYearValue"] - cur
            if uplift > 0:
                out.append({
                    "id": "adoption", "tone": "opportunity", "title": "Increase adoption",
                    "body": (f"Adoption is currently modelled at {pct(avg_adoption)}. A focused enablement "
                             "programme for the target user base is usually the single cheapest way to raise "
                             "value on a product that is already built."),
                    "impact": (f"Raising adoption to {pct(target)} would increase 3-year value by approximately "
                               f"{money(uplift, c)}."),
                })

    # 2 — Attribution validation
    heavy = sorted([r for r in v["benefits"] if r["benefit"]["attribution"] > 0.7],
                   key=lambda r: r["annualValue"], reverse=True)
    if heavy:
        h = heavy[0]
        share = h["annualValue"] / v["annualGrossValue"] if v["annualGrossValue"] > 0 else 0
        out.append({
            "id": "attribution", "tone": "validate", "title": "Validate attribution with Finance",
            "body": (f"\"{h['benefit']['label']}\" claims {pct(h['benefit']['attribution'])} attribution and carries "
                     f"{pct(share)} of total annual value. An agreed attribution rule — ideally supported by a "
                     "hold-out group — removes the most common objection in an investment committee."),
            "impact": (f"Reducing attribution to 60% would lower annual value by "
                       f"{money(h['annualValue'] * (1 - 0.6 / h['benefit']['attribution']), c)}."),
        })

    # 3 — Pilot first when the evidence base is weak
    if v["confidence"]["score"] < 65:
        out.append({
            "id": "pilot", "tone": "caution", "title": "Pilot before requesting full investment",
            "body": (f"The evidence base is thin, held back mainly by {_weakest_dim(v)}. A 90-day pilot on a single "
                     "segment would convert the largest assumptions from estimates into measured baselines."),
            "impact": (f"Stage-gating the investment protects {money(v['costs']['initialInvestment'] * 0.7, c)} of "
                       "build spend until the value hypothesis is tested."),
        })

    # 4 — Cost base completeness
    change_total = sum(p["investment"]["change"].values())
    build_total = sum(p["investment"]["build"].values())
    if build_total > 0 and change_total / build_total < 0.1:
        out.append({
            "id": "change", "tone": "caution", "title": "Strengthen the change and adoption budget",
            "body": (f"Change spend is {pct(change_total / build_total)} of build cost. For products that depend on "
                     "frontline behaviour, under-funding adoption is the most common cause of value leakage."),
            "impact": (f"Adding {money(build_total * 0.12 - change_total, c)} of change investment typically protects "
                       "the adoption assumption this case depends on."),
        })

    # 5 — Ramp acceleration
    slow = [b for b in p["benefits"] if b["rampMonths"] >= 12]
    if slow:
        d = copy.deepcopy(p)
        for b in d["benefits"]:
            if b["rampMonths"] >= 12:
                b["rampMonths"] = max(6, js_round(b["rampMonths"] * 0.6))
        uplift = value_product(d, settings)["threeYearValue"] - cur
        if uplift > 0:
            out.append({
                "id": "ramp", "tone": "opportunity", "title": "Compress the benefit ramp",
                "body": (f"{len(slow)} benefit line{'s take' if len(slow) > 1 else ' takes'} a year or more to reach "
                         "full run-rate. Sequencing the highest-value user segment first pulls value into the "
                         "payback window."),
                "impact": (f"A 40% faster ramp is worth approximately {money(uplift, c)} over three years and "
                           "shortens payback."),
            })

    # 6 — Evidence upgrade
    weak = sorted([r for r in v["benefits"]
                   if r["benefit"]["evidence"] in ("Estimate", "Management Assumption")],
                  key=lambda r: r["annualValue"], reverse=True)
    if weak:
        w = weak[0]
        out.append({
            "id": "evidence", "tone": "validate",
            "title": "Upgrade the evidence behind the largest assumption",
            "body": (f"\"{w['benefit']['label']}\" is worth {money(w['annualValue'], c)} a year but rests on "
                     f"{w['benefit']['evidence'].lower()}. Replacing it with an operational baseline or a benchmark "
                     "from a comparable product is normally a few days of work."),
            "impact": ("Moving this line to measured evidence is the single highest-leverage way to strengthen "
                       "the case."),
        })

    # 7 — Risk concentration
    risk_share = v["byCategory"]["risk"] / v["annualGrossValue"] if v["annualGrossValue"] > 0 else 0
    if risk_share > 0.5:
        out.append({
            "id": "risk", "tone": "caution", "title": "Present risk value separately",
            "body": (f"{pct(risk_share)} of annual value is risk-adjusted expected loss reduction. CFOs will not "
                     "accept this as a budget saving. Present it as risk-adjusted economic value alongside — not "
                     "inside — the hard-dollar case."),
            "impact": None,
        })

    return out[:6]


def _weakest_dim(v) -> str:
    dims = sorted(v["confidence"]["dimensions"], key=lambda d: d["value"])
    return dims[0]["label"].lower() if dims else "assumption quality"
