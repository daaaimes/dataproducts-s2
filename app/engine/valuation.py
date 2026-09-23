"""The valuation engine — a port of src/engine/valuation.ts.

value_product() turns a product plus a set of scenario levers into every number
the interface shows: monthly benefit and cost streams, NPV, IRR, payback,
confidence, guardrail flags and the strategic score.
"""
from __future__ import annotations

import math

from ..data.catalogs import DRIVER_BY_ID
from ..format import _to_fixed, clamp, js_round
from .finance import INF, cumulative, irr as _irr, npv as _npv, payback_months, ramp_factor, sum_range
from .models import MODELS

NEUTRAL_LEVERS = {
    "adoption": 1.0, "revenueUplift": 1.0, "costSavings": 1.0,
    "attribution": 1.0, "implementationCost": 1.0, "runCost": 1.0,
}

CONFIDENCE_DIMS = [
    {"key": "baselineQuality", "label": "Quality of baseline", "weight": 0.16},
    {"key": "dataAvailability", "label": "Availability of actual data", "weight": 0.14},
    {"key": "assumptionStrength", "label": "Strength of business assumptions", "weight": 0.14},
    {"key": "historicalEvidence", "label": "Historical evidence", "weight": 0.12},
    {"key": "attributionConfidence", "label": "Attribution confidence", "weight": 0.14},
    {"key": "adoptionConfidence", "label": "Adoption confidence", "weight": 0.12},
    {"key": "financialValidation", "label": "Financial validation", "weight": 0.10},
    {"key": "measurementMaturity", "label": "Measurement maturity", "weight": 0.08},
]

EVIDENCE_WEIGHT = {
    "Actual": 100, "Pilot": 82, "Benchmark": 68,
    "Estimate": 48, "Management Assumption": 34,
}


def ctx_of(settings):
    return {"annualWorkingHours": settings["annualWorkingHours"], "currency": settings["currency"]}


def benefit_value_class(b) -> str:
    if b.get("valueClassOverride"):
        return b["valueClassOverride"]
    if b["kind"] == "fteSaving":
        return "direct" if b["inputs"].get("hardReduction", 0) >= 0.5 else "indirect"
    return MODELS[b["kind"]]["valueClass"]


def benefit_maturity(b) -> str:
    if b["evidence"] == "Actual":
        return "Proven"
    if b["evidence"] in ("Pilot", "Benchmark"):
        return "Expected"
    return "Potential"


def _lever_for(category, levers):
    return levers["revenueUplift"] if category == "revenue" else levers["costSavings"]


def _apply_adoption_lever(b, levers):
    if levers["adoption"] == 1:
        return b["inputs"]
    out = dict(b["inputs"])
    if isinstance(out.get("adoption"), (int, float)):
        out["adoption"] = clamp(out["adoption"] * levers["adoption"], 0, 1)
    elif isinstance(out.get("conversionRate"), (int, float)):
        out["conversionRate"] = clamp(out["conversionRate"] * levers["adoption"], 0, 1)
    elif isinstance(out.get("realisation"), (int, float)):
        out["realisation"] = clamp(out["realisation"] * levers["adoption"], 0, 1)
    return out


def benefit_annual_value(b, settings, levers) -> float:
    model = MODELS[b["kind"]]
    inputs = _apply_adoption_lever(b, levers)
    gross = model["compute"](inputs, ctx_of(settings))
    attr = clamp(b["attribution"] * levers["attribution"], 0, 1)
    return max(0.0, gross * attr * _lever_for(model["category"], levers))


def cost_breakdown(inv, levers):
    def s(o):
        return sum(v or 0 for v in o.values())
    build_total = s(inv["build"]) * levers["implementationCost"]
    change_total = s(inv["change"]) * levers["implementationCost"]
    technology_annual = s(inv["technology"]) * levers["runCost"]
    run_annual = s(inv["run"]) * levers["runCost"]
    return {
        "buildTotal": build_total,
        "changeTotal": change_total,
        "technologyAnnual": technology_annual,
        "runAnnual": run_annual,
        "initialInvestment": build_total + change_total,
        "annualOperatingCost": technology_annual + run_annual,
    }


def _compute_confidence(p, results, guardrails):
    dims = [dict(d, value=clamp(p["confidence"].get(d["key"], 50), 0, 100)) for d in CONFIDENCE_DIMS]
    weighted = sum(d["value"] * d["weight"] for d in dims)

    total_value = sum(r["annualValue"] for r in results)
    if total_value > 0:
        evidence_score = 0.0
        for r in results:
            base = EVIDENCE_WEIGHT[r["benefit"]["evidence"]]
            star_adj = (clamp(r["benefit"]["evidenceStrength"], 1, 5) - 3) * 4
            evidence_score += (r["annualValue"] / total_value) * clamp(base + star_adj, 0, 100)
    else:
        evidence_score = 50.0

    penalty = sum(6 if gr["severity"] == "severe" else 2.5 if gr["severity"] == "warn" else 0
                  for gr in guardrails)
    score = clamp(js_round(weighted * 0.72 + evidence_score * 0.28 - penalty), 5, 98)
    band = ("High" if score >= 80 else "Moderate" if score >= 65
            else "Developing" if score >= 50 else "Low")
    return {
        "score": int(score), "band": band, "dimensions": dims,
        "evidenceScore": int(js_round(evidence_score)),
        "guardrailPenalty": int(js_round(penalty)),
    }


def evaluate_guardrails(p, settings, results, roi, payback):
    """Automatic benchmark checks — the questions an investment committee will ask."""
    if not settings.get("guardrailsEnabled"):
        return []
    out = []

    for r in results:
        b = r["benefit"]
        i = b["inputs"]
        label = b["label"]

        if b["attribution"] >= 0.95:
            out.append({
                "id": f"{b['id']}-attr", "severity": "severe", "benefitId": b["id"],
                "title": "100% attribution may overstate contribution",
                "detail": (f"\"{label}\" attributes {int(js_round(b['attribution'] * 100))}% of the outcome to this "
                           "data product. Business outcomes are usually shaped by pricing, campaigns and frontline "
                           "execution as well. Benchmark for a single data product is 30–70%."),
            })
        elif b["attribution"] > 0.8:
            out.append({
                "id": f"{b['id']}-attr", "severity": "warn", "benefitId": b["id"],
                "title": "High attribution assumption",
                "detail": (f"\"{label}\" claims {int(js_round(b['attribution'] * 100))}% attribution. Above 80% "
                           "normally needs a controlled test or a Finance-agreed attribution rule."),
            })

        if isinstance(i.get("adoption"), (int, float)) and i["adoption"] > 0.9:
            out.append({
                "id": f"{b['id']}-adopt", "severity": "warn", "benefitId": b["id"],
                "title": f"Adoption assumption of {int(js_round(i['adoption'] * 100))}% is unusually high",
                "detail": ("Enterprise data products typically stabilise at 45–75% active adoption in year one. "
                           "Consider validating with pilot data before committing to this level."),
            })

        if (isinstance(i.get("currentConversion"), (int, float))
                and isinstance(i.get("expectedConversion"), (int, float))
                and i["currentConversion"] > 0):
            mult = i["expectedConversion"] / i["currentConversion"]
            if mult > 2.5:
                out.append({
                    "id": f"{b['id']}-conv", "severity": "severe", "benefitId": b["id"],
                    "title": "Conversion uplift far above historical performance",
                    "detail": (f"\"{label}\" assumes conversion rises {_to_fixed(mult, 1)}× versus baseline. Analytics-led "
                               "targeting typically delivers 1.2–1.8×. Evidence from a pilot or hold-out test is "
                               "recommended."),
                })
            elif mult > 1.8:
                out.append({
                    "id": f"{b['id']}-conv", "severity": "warn", "benefitId": b["id"],
                    "title": "Ambitious conversion uplift",
                    "detail": (f"Assumed uplift is {_to_fixed(mult, 1)}× baseline, above the 1.2–1.8× benchmark range for "
                               "targeting models."),
                })

        if (isinstance(i.get("currentChurn"), (int, float))
                and isinstance(i.get("expectedChurn"), (int, float))
                and i["currentChurn"] > 0):
            rel = (i["currentChurn"] - i["expectedChurn"]) / i["currentChurn"]
            if rel > 0.4:
                out.append({
                    "id": f"{b['id']}-churn", "severity": "warn", "benefitId": b["id"],
                    "title": "Large churn reduction assumed",
                    "detail": (f"\"{label}\" assumes churn falls by {int(js_round(rel * 100))}% relative to baseline. "
                               "Retention models typically move churn by 8–25% relative in the first year."),
                })

        if isinstance(i.get("hoursSaved"), (int, float)) and i["hoursSaved"] > 20:
            out.append({
                "id": f"{b['id']}-hours", "severity": "warn", "benefitId": b["id"],
                "title": "Very high time saving per user",
                "detail": (f"{_jsnum(i['hoursSaved'])} hours/user/month is more than 12% of a working month. "
                           "Time-and-motion evidence is recommended above 20 hours."),
            })
        if isinstance(i.get("hoursSavedPerMonth"), (int, float)) and i["hoursSavedPerMonth"] > 24:
            out.append({
                "id": f"{b['id']}-hours2", "severity": "warn", "benefitId": b["id"],
                "title": "Very high effort reduction assumption",
                "detail": (f"{_jsnum(i['hoursSavedPerMonth'])} hours/person/month removed. Validate with an observed "
                           "process baseline."),
            })

        if (b["kind"] == "fteSaving" and i.get("hardReduction", 0) >= 0.5
                and p["lifecycle"] not in ("Production", "Scale", "Optimise")):
            out.append({
                "id": f"{b['id']}-hardfte", "severity": "warn", "benefitId": b["id"],
                "title": "Hard FTE reduction claimed pre-production",
                "detail": ("Headcount reduction should be agreed with the business unit and reflected in the "
                           "workforce plan before it is booked as a hard saving."),
            })

        if b["kind"] == "riskReduction":
            base_p = i.get("baselineProbability", 0)
            rel = ((base_p - i.get("expectedProbability", 0)) / base_p) if base_p > 0 else 0
            if rel > 0.7:
                out.append({
                    "id": f"{b['id']}-risk", "severity": "warn", "benefitId": b["id"],
                    "title": "Risk probability reduction above benchmark",
                    "detail": (f"A {int(js_round(rel * 100))}% relative reduction in event probability is at the top "
                               "of the observed range for detection-led controls (typically 25–60%). Second-line "
                               "validation is recommended."),
                })

        if b["evidence"] == "Management Assumption" and r["annualValue"] > 3_000_000:
            out.append({
                "id": f"{b['id']}-eviq", "severity": "severe", "benefitId": b["id"],
                "title": "Large benefit resting on a management assumption",
                "detail": (f"\"{label}\" contributes a material annual value but is only supported by a management "
                           "assumption. Obtain a baseline measurement or pilot result before approval."),
            })
        if b["rampMonths"] <= 1 and r["annualValue"] > 1_000_000:
            out.append({
                "id": f"{b['id']}-ramp", "severity": "warn", "benefitId": b["id"],
                "title": "Immediate full-value realisation assumed",
                "detail": (f"\"{label}\" reaches full run-rate almost immediately. Most data products need 6–18 "
                           "months to reach steady-state adoption."),
            })

    if roi > 10 and math.isfinite(roi):
        out.append({
            "id": "roi-outlier", "severity": "warn", "title": "ROI is an outlier versus the portfolio",
            "detail": (f"A {int(js_round(roi * 100))}% return is well above the 150–400% range typical of approved "
                       "data investments. Confirm that operating costs and change costs are complete."),
        })
    if 0 < payback < 3:
        out.append({
            "id": "payback-fast", "severity": "info", "title": "Payback under three months",
            "detail": ("Very fast payback usually indicates either an unusually strong case or an understated cost "
                       "base. Confirm build, change and run costs are fully loaded."),
        })

    change_total = sum(p["investment"]["change"].values())
    build_total = sum(p["investment"]["build"].values())
    if build_total > 0 and change_total / build_total < 0.05:
        out.append({
            "id": "change-thin", "severity": "warn", "title": "Change and adoption cost looks understated",
            "detail": (f"Change spend is {int(js_round((change_total / build_total) * 100))}% of build cost. Products "
                       "that depend on frontline behaviour change typically need 10–20%."),
        })

    productivity_share = sum(r["annualValue"] for r in results if r["category"] == "productivity")
    total = sum(r["annualValue"] for r in results)
    if total > 0 and productivity_share / total > 0.7:
        out.append({
            "id": "prod-heavy", "severity": "info", "title": "Value is concentrated in released capacity",
            "detail": (f"{int(js_round((productivity_share / total) * 100))}% of value is productivity. This is "
                       "legitimate economic value but does not reduce the cost base unless capacity is redeployed or "
                       "removed. Agree the treatment with Finance."),
        })

    return out


def _jsnum(v):
    """Render a number the way JS string interpolation does (no trailing .0)."""
    return int(v) if float(v).is_integer() else v


def compute_strategic_score(p) -> int:
    s = p["strategic"]
    score = (s["strategicAlignment"] * 0.28 + s["customerImpact"] * 0.18
             + s["reusability"] * 0.16 + s["riskReduction"] * 0.14
             + s["dataDemocratisation"] * 0.12 + s["aiReadiness"] * 0.12)
    return int(clamp(js_round(score), 0, 100))


def compute_priority(v, p, weights, portfolio_max_value):
    value_norm = (clamp(100 * math.log10(1 + 9 * max(0.0, v["threeYearValue"]) / portfolio_max_value), 0, 100)
                  if portfolio_max_value > 0 else 0)
    ttv = clamp(100 - (p["timeToValueMonths"] - 3) * 4.3, 0, 100)
    risk_share = v["byCategory"]["risk"] / v["annualGrossValue"] if v["annualGrossValue"] > 0 else 0
    risk_score = clamp(p["strategic"]["riskReduction"] * 0.7 + risk_share * 100 * 0.3, 0, 100)

    comps = [
        {"key": "economicValue", "label": "Economic Value", "raw": value_norm, "weight": weights["economicValue"]},
        {"key": "strategicAlignment", "label": "Strategic Alignment",
         "raw": p["strategic"]["strategicAlignment"], "weight": weights["strategicAlignment"]},
        {"key": "timeToValue", "label": "Time to Value", "raw": ttv, "weight": weights["timeToValue"]},
        {"key": "confidence", "label": "Confidence", "raw": v["confidence"]["score"], "weight": weights["confidence"]},
        {"key": "customerImpact", "label": "Customer Impact",
         "raw": p["strategic"]["customerImpact"], "weight": weights["customerImpact"]},
        {"key": "riskReduction", "label": "Risk Reduction", "raw": risk_score, "weight": weights["riskReduction"]},
        {"key": "reusability", "label": "Reusability",
         "raw": p["strategic"]["reusability"], "weight": weights["reusability"]},
    ]
    wsum = sum(c["weight"] for c in comps) or 1
    score = int(clamp(js_round(sum(c["raw"] * (c["weight"] / wsum) for c in comps)), 0, 100))
    band = ("Invest Now" if score >= 90 else "Accelerate" if score >= 75
            else "Validate" if score >= 60 else "Reassess")
    return {
        "score": score, "band": band,
        "components": [dict(c, contribution=c["raw"] * (c["weight"] / wsum)) for c in comps],
    }


def value_product(p, settings, levers=None):
    levers = levers or NEUTRAL_LEVERS
    discount_rate = p.get("discountRate") if p.get("discountRate") is not None else settings["discountRate"]
    horizon_years = p.get("horizonYears") if p.get("horizonYears") is not None else settings["horizonYears"]
    horizon_months = max(36, int(js_round(horizon_years * 12)))
    go_live = max(0, int(js_round(p["investment"]["buildMonths"])))
    costs = cost_breakdown(p["investment"], levers)

    results = []
    for b in p["benefits"]:
        model = MODELS[b["kind"]]
        inputs = _apply_adoption_lever(b, levers)
        gross = model["compute"](inputs, ctx_of(settings))
        attr = clamp(b["attribution"] * levers["attribution"], 0, 1)
        annual = max(0.0, gross * attr * _lever_for(model["category"], levers))
        growth = b["inputs"].get("annualGrowth", 0) or 0
        start = go_live + max(0, b["startMonth"])

        monthly = [0.0] * horizon_months
        for m in range(horizon_months):
            ramp = ramp_factor(m, start, b["rampMonths"])
            if ramp <= 0:
                continue
            years_in = max(0.0, (m - start) / 12)
            monthly[m] = (annual / 12) * ramp * math.pow(1 + growth, years_in)

        results.append({
            "benefit": b,
            "category": model["category"],
            "valueClass": benefit_value_class(b),
            "maturity": benefit_maturity(b),
            "annualValue": annual,
            "grossBeforeAttribution": gross,
            "monthly": monthly,
        })

    monthly_benefits = [sum(r["monthly"][m] for r in results) for m in range(horizon_months)]

    monthly_costs = []
    for m in range(horizon_months):
        if go_live > 0:
            capex = costs["initialInvestment"] / go_live if m < go_live else 0.0
        else:
            capex = costs["initialInvestment"] if m == 0 else 0.0
        opex = costs["annualOperatingCost"] / 12 if m >= go_live else 0.0
        monthly_costs.append(capex + opex)

    monthly_net = [b - monthly_costs[m] for m, b in enumerate(monthly_benefits)]
    cum_net = cumulative(monthly_net)

    by_category = {"revenue": 0.0, "costSavings": 0.0, "costAvoidance": 0.0, "productivity": 0.0, "risk": 0.0}
    by_class = {"direct": 0.0, "indirect": 0.0}
    by_maturity = {"Proven": 0.0, "Expected": 0.0, "Potential": 0.0}
    for r in results:
        by_category[r["category"]] += r["annualValue"]
        by_class[r["valueClass"]] += r["annualValue"]
        by_maturity[r["maturity"]] += r["annualValue"]

    annual_gross_value = sum(r["annualValue"] for r in results)
    net_annual_value = annual_gross_value - costs["annualOperatingCost"]

    opex_only = [(costs["annualOperatingCost"] / 12 if m >= go_live else 0.0) for m in range(horizon_months)]
    net_operating = [b - opex_only[m] for m, b in enumerate(monthly_benefits)]
    three_year_value = sum_range(net_operating, 0, 36)
    five_year_value = sum_range(net_operating, 0, 60)
    horizon_value = sum_range(net_operating, 0, horizon_months)

    total_benefits = sum_range(monthly_benefits, 0, horizon_months)
    total_costs = sum_range(monthly_costs, 0, horizon_months)
    roi = (total_benefits - total_costs) / total_costs if total_costs > 0 else 0.0

    pb = payback_months(monthly_net)
    npv_value = _npv(monthly_net, discount_rate)
    irr_value = _irr(monthly_net)

    guardrails = evaluate_guardrails(p, settings, results, roi, pb)
    confidence = _compute_confidence(p, results, guardrails)

    hard_dollar_value = sum(
        r["annualValue"] for r in results
        if r["valueClass"] == "direct" and r["category"] not in ("costAvoidance", "risk"))

    capacity_hours = 0.0
    for r in results:
        i = r["benefit"]["inputs"]
        if r["benefit"]["kind"] == "productivity":
            capacity_hours += (i.get("users", 0) * i.get("hoursSaved", 0) * 12
                               * i.get("adoption", 1) * i.get("utilisation", 1))
        if r["benefit"]["kind"] == "fteSaving":
            capacity_hours += i.get("affectedEmployees", 0) * i.get("hoursSavedPerMonth", 0) * 12
        # revenueProductivity hours are monetised in the revenue line, so they are deliberately
        # excluded here — counting them again would double-count the same released time.

    strategic_drivers = list(dict.fromkeys(
        b["driverId"] for b in p["benefits"]
        if (DRIVER_BY_ID.get(b["driverId"]) or {}).get("category") == "strategic"))

    return {
        "productId": p["id"],
        "currency": settings["currency"],
        "discountRate": discount_rate,
        "horizonMonths": horizon_months,
        "goLiveMonth": go_live,
        "benefits": results,
        "byCategory": by_category,
        "byClass": by_class,
        "byMaturity": by_maturity,
        "costs": costs,
        "annualGrossValue": annual_gross_value,
        "annualOperatingCost": costs["annualOperatingCost"],
        "netAnnualValue": net_annual_value,
        "monthlyBenefits": monthly_benefits,
        "monthlyCosts": monthly_costs,
        "monthlyNet": monthly_net,
        "cumulativeNet": cum_net,
        "threeYearValue": three_year_value,
        "fiveYearValue": five_year_value,
        "horizonValue": horizon_value,
        "totalBenefits": total_benefits,
        "totalCosts": total_costs,
        "roi": roi,
        "paybackMonths": pb,
        "paybackFromGoLive": max(0.0, pb - go_live) if math.isfinite(pb) else INF,
        "npv": npv_value,
        "irr": irr_value,
        "valuePerDollar": total_benefits / total_costs if total_costs > 0 else 0.0,
        "confidence": confidence,
        "strategicScore": compute_strategic_score(p),
        "strategicDrivers": strategic_drivers,
        "guardrails": guardrails,
        "hardDollarValue": hard_dollar_value,
        "softValue": annual_gross_value - hard_dollar_value,
        "fteEquivalent": capacity_hours / max(1, settings["annualWorkingHours"]),
        "capacityReleaseHours": capacity_hours,
    }
