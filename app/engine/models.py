"""Benefit models — a port of src/engine/models.ts.

Each model owns its own input fields, its steady-state annual computation
(before attribution and scenario levers) and the explanation shown in the
"how was this calculated?" panel.
"""
from __future__ import annotations

import math

from ..format import money, money_full, num, pct


def _field(key, label, unit, default, minimum=None, maximum=None, step=None,
           help=None, sensitive=False):
    return {"key": key, "label": label, "unit": unit, "def": default, "min": minimum,
            "max": maximum, "step": step, "help": help, "sensitive": sensitive}


def g(i, k, d=0.0):
    v = i.get(k, d)
    return v if isinstance(v, (int, float)) and math.isfinite(v) else d


def _non_neg(v):
    return v if v > 0 else 0


def _ctx_hours(ctx):
    return max(1, ctx["annualWorkingHours"])


# ── REVENUE ──────────────────────────────────────────────────────────────────

def _cross_sell_compute(i, ctx):
    return (g(i, "addressableCustomers") * g(i, "eligiblePct")
            * _non_neg(g(i, "expectedConversion") - g(i, "currentConversion"))
            * g(i, "revenuePerCustomer"))


def _cross_sell_explain(i, ctx, attr):
    c = ctx["currency"]
    eligible = g(i, "addressableCustomers") * g(i, "eligiblePct")
    uplift = _non_neg(g(i, "expectedConversion") - g(i, "currentConversion"))
    return {
        "formula": "Eligible population × Incremental conversion × Revenue per customer × Attribution",
        "terms": [
            {"label": "Addressable customers", "value": num(g(i, "addressableCustomers"))},
            {"label": "× Eligible", "value": pct(g(i, "eligiblePct"))},
            {"label": "= Eligible population", "value": num(eligible), "muted": True},
            {"label": "× Incremental conversion",
             "value": f"{pct(g(i, 'expectedConversion'), 1)} − {pct(g(i, 'currentConversion'), 1)} = {pct(uplift, 1)}"},
            {"label": "= Incremental customers", "value": num(eligible * uplift), "muted": True},
            {"label": "× Revenue per customer", "value": money_full(g(i, "revenuePerCustomer"), c)},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": None,
    }


def _balance_compute(i, ctx):
    return (g(i, "targetCustomers") * g(i, "conversionRate")
            * g(i, "incrementalBalance") * g(i, "netRevenueMargin"))


def _balance_explain(i, ctx, attr):
    c = ctx["currency"]
    bal = g(i, "targetCustomers") * g(i, "conversionRate") * g(i, "incrementalBalance")
    return {
        "formula": "Converted customers × Incremental balance × Net revenue margin × Attribution",
        "terms": [
            {"label": "Target customers", "value": num(g(i, "targetCustomers"))},
            {"label": "× Conversion rate", "value": pct(g(i, "conversionRate"))},
            {"label": "× Incremental balance", "value": money_full(g(i, "incrementalBalance"), c)},
            {"label": "= Incremental balances", "value": money(bal, c), "muted": True},
            {"label": "× Net revenue margin", "value": pct(g(i, "netRevenueMargin"), 2)},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": None,
    }


def _churn_compute(i, ctx):
    return (g(i, "customersAtRisk")
            * _non_neg(g(i, "currentChurn") - g(i, "expectedChurn"))
            * g(i, "avgAnnualRevenue"))


def _churn_explain(i, ctx, attr):
    c = ctx["currency"]
    delta = _non_neg(g(i, "currentChurn") - g(i, "expectedChurn"))
    return {
        "formula": "Customers at risk × Churn reduction × Annual revenue per customer × Attribution",
        "terms": [
            {"label": "Customers at risk", "value": num(g(i, "customersAtRisk"))},
            {"label": "× Churn reduction",
             "value": f"{pct(g(i, 'currentChurn'), 1)} − {pct(g(i, 'expectedChurn'), 1)} = {pct(delta, 1)}"},
            {"label": "= Customers retained", "value": num(g(i, "customersAtRisk") * delta), "muted": True},
            {"label": "× Annual revenue / customer", "value": money_full(g(i, "avgAnnualRevenue"), c)},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": "Classified as revenue protected. Present separately from revenue growth when discussing top-line impact.",
    }


def _rev_prod_compute(i, ctx):
    return (g(i, "employees") * g(i, "hoursSavedPerMonth") * 12
            * g(i, "pctRedeployed") * g(i, "revenuePerProductiveHour"))


def _rev_prod_explain(i, ctx, attr):
    c = ctx["currency"]
    return {
        "formula": "Employees × Hours saved / month × 12 × % redeployed × Revenue per productive hour × Attribution",
        "terms": [
            {"label": "Employees", "value": num(g(i, "employees"))},
            {"label": "× Hours saved / month", "value": f"{num(g(i, 'hoursSavedPerMonth'), 1)} h"},
            {"label": "× 12 months",
             "value": f"{num(g(i, 'employees') * g(i, 'hoursSavedPerMonth') * 12)} h / year", "muted": True},
            {"label": "× % redeployed to revenue", "value": pct(g(i, "pctRedeployed"))},
            {"label": "× Revenue per productive hour", "value": money_full(g(i, "revenuePerProductiveHour"), c)},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": "Indirect value — depends on management redeploying released capacity into revenue activity.",
    }


def _simple_rev_compute(i, ctx):
    return g(i, "annualRevenue") * g(i, "probability")


def _simple_rev_explain(i, ctx, attr):
    c = ctx["currency"]
    return {
        "formula": "Annual incremental revenue × Probability × Attribution",
        "terms": [
            {"label": "Annual incremental revenue", "value": money_full(g(i, "annualRevenue"), c)},
            {"label": "× Probability", "value": pct(g(i, "probability"))},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": None,
    }


# ── COST ─────────────────────────────────────────────────────────────────────

def _fte_compute(i, ctx):
    hourly = g(i, "fullyLoadedAnnualCost") / _ctx_hours(ctx)
    return (g(i, "affectedEmployees") * g(i, "hoursSavedPerMonth") * 12
            * hourly * g(i, "realisation"))


def _fte_explain(i, ctx, attr):
    c = ctx["currency"]
    hours_year = _ctx_hours(ctx)
    hourly = g(i, "fullyLoadedAnnualCost") / hours_year
    hours = g(i, "affectedEmployees") * g(i, "hoursSavedPerMonth") * 12
    fte = hours / hours_year
    return {
        "formula": "Employees × Hours saved / month × 12 × Fully-loaded hourly cost × Realisation × Attribution",
        "terms": [
            {"label": "Affected employees", "value": num(g(i, "affectedEmployees"))},
            {"label": "× Hours saved / month", "value": f"{num(g(i, 'hoursSavedPerMonth'), 1)} h"},
            {"label": "= Hours released / year",
             "value": f"{num(hours)} h  (≈ {num(fte, 1)} FTE)", "muted": True},
            {"label": "× Fully-loaded hourly cost",
             "value": f"{money_full(g(i, 'fullyLoadedAnnualCost'), c)} ÷ {num(ctx['annualWorkingHours'])} h = {money_full(hourly, c)}/h"},
            {"label": "× Realisation", "value": pct(g(i, "realisation"))},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": (
            "Recorded as a hard FTE reduction — headcount is removed from the plan and the saving reaches the P&L."
            if g(i, "hardReduction") >= 0.5 else
            "Recorded as capacity release, not headcount reduction. The economic value of time released is real, "
            "but it does not reduce the cost base unless management redeploys or removes the capacity."
        ),
    }


def _run_rate_compute(i, ctx):
    return g(i, "baselineAnnualCost") * g(i, "reductionPct") * g(i, "realisation")


def _run_rate_explain(i, ctx, attr):
    c = ctx["currency"]
    return {
        "formula": "Baseline annual cost × Expected reduction × Realisation × Attribution",
        "terms": [
            {"label": "Baseline annual cost", "value": money_full(g(i, "baselineAnnualCost"), c)},
            {"label": "× Expected reduction", "value": pct(g(i, "reductionPct"))},
            {"label": "× Realisation", "value": pct(g(i, "realisation"))},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": "Hard-dollar saving: requires an identified budget line to be reduced.",
    }


def _avoid_compute(i, ctx):
    return g(i, "avoidedCost") * g(i, "probability")


def _avoid_explain(i, ctx, attr):
    c = ctx["currency"]
    return {
        "formula": "Avoided cost × Probability × Attribution",
        "terms": [
            {"label": "Baseline planned cost", "value": money_full(g(i, "baselineCost"), c), "muted": True},
            {"label": "Expected avoided cost", "value": money_full(g(i, "avoidedCost"), c)},
            {"label": "× Probability", "value": pct(g(i, "probability"))},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": "Cost avoidance does not reduce current-year budget. Present separately from hard savings when speaking to Finance.",
    }


# ── RISK ─────────────────────────────────────────────────────────────────────

def _risk_compute(i, ctx):
    return (g(i, "financialImpact")
            * _non_neg(g(i, "baselineProbability") - g(i, "expectedProbability"))
            * g(i, "controlEffectiveness"))


def _risk_explain(i, ctx, attr):
    c = ctx["currency"]
    before = g(i, "financialImpact") * g(i, "baselineProbability")
    after = g(i, "financialImpact") * g(i, "expectedProbability")
    return {
        "formula": "Expected loss (before) − Expected loss (after), × Control effectiveness × Attribution",
        "terms": [
            {"label": "Expected loss before",
             "value": f"{money_full(g(i, 'financialImpact'), c)} × {pct(g(i, 'baselineProbability'), 1)} = {money(before, c)}"},
            {"label": "Expected loss after",
             "value": f"{money_full(g(i, 'financialImpact'), c)} × {pct(g(i, 'expectedProbability'), 1)} = {money(after, c)}"},
            {"label": "= Gross loss reduction", "value": money(before - after, c), "muted": True},
            {"label": "× Control effectiveness", "value": pct(g(i, "controlEffectiveness"))},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": "Risk-adjusted economic value, not a guaranteed saving. In any single year the realised loss will be either zero or the full event.",
    }


# ── PRODUCTIVITY ─────────────────────────────────────────────────────────────

def _prod_compute(i, ctx):
    return (g(i, "users") * g(i, "hoursSaved") * 12 * g(i, "hourlyCost")
            * g(i, "adoption") * g(i, "utilisation") * g(i, "realisation"))


def _prod_explain(i, ctx, attr):
    c = ctx["currency"]
    return {
        "formula": "Users × Hours saved / month × 12 × Hourly cost × Adoption × Utilisation × Realisation × Attribution",
        "terms": [
            {"label": "Users", "value": num(g(i, "users"))},
            {"label": "× Hours saved / user / month", "value": f"{num(g(i, 'hoursSaved'), 1)} h"},
            {"label": "× 12 months", "value": f"{num(g(i, 'users') * g(i, 'hoursSaved') * 12)} h / year", "muted": True},
            {"label": "× Fully-loaded hourly cost", "value": f"{money_full(g(i, 'hourlyCost'), c)}/h"},
            {"label": "× Adoption", "value": pct(g(i, "adoption"))},
            {"label": "× Utilisation", "value": pct(g(i, "utilisation"))},
            {"label": "× Realisation", "value": pct(g(i, "realisation"))},
            {"label": "× Attribution", "value": pct(attr)},
        ],
        "note": "Capacity released, valued at fully-loaded cost. This is not a budget reduction unless headcount is removed.",
    }


MODELS = {
    "crossSell": {
        "kind": "crossSell", "name": "Conversion uplift", "category": "revenue",
        "valueClass": "direct",
        "summary": "Eligible population × incremental conversion × revenue per customer × attribution.",
        "fields": [
            _field("addressableCustomers", "Addressable customers", "count", 250_000, 0, None, 1000,
                   "Total customers the product can reach.", True),
            _field("eligiblePct", "Eligible customers", "percent", 0.35, 0, 1, 0.01,
                   "Share that passes product, risk and consent eligibility.", True),
            _field("currentConversion", "Current conversion", "percent", 0.024, 0, 1, 0.001,
                   "Observed baseline conversion — should come from actuals.", True),
            _field("expectedConversion", "Expected conversion", "percent", 0.038, 0, 1, 0.001,
                   "Post-implementation conversion. Validate against pilot data.", True),
            _field("revenuePerCustomer", "Incremental revenue / customer", "currency", 640, 0, None, 10,
                   "Annual net revenue per converted customer.", True),
            _field("annualGrowth", "Annual growth", "percent", 0.03, -0.2, 0.5, 0.01,
                   "Year-on-year growth applied to this benefit line."),
        ],
        "compute": _cross_sell_compute, "explain": _cross_sell_explain,
    },
    "balanceGrowth": {
        "kind": "balanceGrowth", "name": "Balance growth (AUM / deposits / lending)",
        "category": "revenue", "valueClass": "direct",
        "summary": "Incremental balances × net revenue margin × attribution.",
        "fields": [
            _field("targetCustomers", "Target customers", "count", 12_000, 0, None, 100, None, True),
            _field("conversionRate", "Conversion rate", "percent", 0.11, 0, 1, 0.01,
                   "Share of targeted customers who increase balances.", True),
            _field("incrementalBalance", "Incremental balance / customer", "currency", 85_000, 0, None, 1000, None, True),
            _field("netRevenueMargin", "Net revenue margin", "percent", 0.0085, 0, 0.2, 0.0005,
                   "Net interest or fee margin earned on the balance.", True),
            _field("annualGrowth", "Annual growth", "percent", 0.04, -0.2, 0.5, 0.01),
        ],
        "compute": _balance_compute, "explain": _balance_explain,
    },
    "churnReduction": {
        "kind": "churnReduction", "name": "Churn reduction (revenue protected)",
        "category": "revenue", "valueClass": "direct",
        "summary": "Customers retained × annual revenue per customer × attribution. Revenue protected, not created.",
        "fields": [
            _field("customersAtRisk", "Customers at risk", "count", 42_000, 0, None, 100, None, True),
            _field("currentChurn", "Current churn rate", "percent", 0.089, 0, 1, 0.001, None, True),
            _field("expectedChurn", "Expected churn rate", "percent", 0.071, 0, 1, 0.001, None, True),
            _field("avgAnnualRevenue", "Average annual revenue / customer", "currency", 1_150, 0, None, 10, None, True),
            _field("annualGrowth", "Annual growth", "percent", 0.02, -0.2, 0.5, 0.01),
        ],
        "compute": _churn_compute, "explain": _churn_explain,
    },
    "revenueProductivity": {
        "kind": "revenueProductivity", "name": "Productivity-driven revenue",
        "category": "revenue", "valueClass": "indirect",
        "summary": "Released capacity redeployed into revenue-generating activity.",
        "fields": [
            _field("employees", "Number of employees", "count", 380, 0, None, 5, None, True),
            _field("hoursSavedPerMonth", "Hours saved / person / month", "hours", 6, 0, 80, 0.5, None, True),
            _field("pctRedeployed", "Time redeployed to revenue activity", "percent", 0.4, 0, 1, 0.05,
                   "Not all released time converts into selling time.", True),
            _field("revenuePerProductiveHour", "Revenue per productive hour", "currency", 210, 0, None, 10, None, True),
        ],
        "compute": _rev_prod_compute, "explain": _rev_prod_explain,
    },
    "simpleRevenue": {
        "kind": "simpleRevenue", "name": "Direct revenue estimate",
        "category": "revenue", "valueClass": "direct",
        "summary": "A stated annual revenue effect, probability-weighted.",
        "fields": [
            _field("annualRevenue", "Annual incremental revenue", "currency", 1_800_000, 0, None, 10_000, None, True),
            _field("probability", "Probability of achievement", "percent", 0.7, 0, 1, 0.05, None, True),
            _field("annualGrowth", "Annual growth", "percent", 0.03, -0.2, 0.5, 0.01),
        ],
        "compute": _simple_rev_compute, "explain": _simple_rev_explain,
    },
    "fteSaving": {
        "kind": "fteSaving", "name": "Effort reduction", "category": "costSavings",
        "valueClass": "indirect",
        "summary": "Hours removed × fully-loaded hourly cost × realisation. Hard reduction only when headcount actually leaves the plan.",
        "fields": [
            _field("affectedEmployees", "Affected employees", "count", 120, 0, None, 1, None, True),
            _field("hoursSavedPerMonth", "Hours saved / person / month", "hours", 9, 0, 160, 0.5, None, True),
            _field("fullyLoadedAnnualCost", "Fully-loaded annual cost / employee", "currency", 135_000, 0, None, 1000, None, True),
            _field("realisation", "Realisation", "percent", 0.7, 0, 1, 0.05,
                   "Share of theoretical saving that lands in the cost base.", True),
            _field("hardReduction", "Hard FTE reduction (headcount removed)", "toggle", 0, None, None, None,
                   "Off = capacity release. On = budgeted headcount genuinely removed."),
        ],
        "compute": _fte_compute, "explain": _fte_explain,
    },
    "runRateReduction": {
        "kind": "runRateReduction", "name": "Run-rate cost reduction",
        "category": "costSavings", "valueClass": "direct",
        "summary": "Baseline annual cost × reduction × realisation.",
        "fields": [
            _field("baselineAnnualCost", "Baseline annual cost", "currency", 2_400_000, 0, None, 10_000, None, True),
            _field("reductionPct", "Expected reduction", "percent", 0.25, 0, 1, 0.01, None, True),
            _field("realisation", "Realisation", "percent", 0.85, 0, 1, 0.05, None, True),
        ],
        "compute": _run_rate_compute, "explain": _run_rate_explain,
    },
    "costAvoidance": {
        "kind": "costAvoidance", "name": "Cost avoidance", "category": "costAvoidance",
        "valueClass": "indirect",
        "summary": "Avoided cost × probability × attribution.",
        "fields": [
            _field("baselineCost", "Baseline planned cost", "currency", 1_600_000, 0, None, 10_000,
                   "What the organisation would otherwise spend."),
            _field("avoidedCost", "Expected avoided cost (annual)", "currency", 1_200_000, 0, None, 10_000, None, True),
            _field("probability", "Probability the cost is avoided", "percent", 0.7, 0, 1, 0.05, None, True),
        ],
        "compute": _avoid_compute, "explain": _avoid_explain,
    },
    "riskReduction": {
        "kind": "riskReduction", "name": "Expected loss reduction", "category": "risk",
        "valueClass": "indirect",
        "summary": "Baseline expected loss − future expected loss, scaled by control effectiveness.",
        "fields": [
            _field("financialImpact", "Financial impact of the risk event", "currency", 10_000_000, 0, None, 100_000, None, True),
            _field("baselineProbability", "Current annual probability", "percent", 0.08, 0, 1, 0.005, None, True),
            _field("expectedProbability", "Probability after the product", "percent", 0.04, 0, 1, 0.005, None, True),
            _field("controlEffectiveness", "Control effectiveness", "percent", 0.85, 0, 1, 0.05,
                   "How reliably the control operates in practice.", True),
        ],
        "compute": _risk_compute, "explain": _risk_explain,
    },
    "productivity": {
        "kind": "productivity", "name": "Productivity value", "category": "productivity",
        "valueClass": "indirect",
        "summary": "Users × hours saved × hourly cost × adoption × utilisation × realisation.",
        "fields": [
            _field("users", "Number of users", "count", 420, 0, None, 5, None, True),
            _field("hoursSaved", "Hours saved / user / month", "hours", 6.5, 0, 160, 0.5, None, True),
            _field("hourlyCost", "Fully-loaded hourly cost", "currency", 75, 0, None, 5, None, True),
            _field("adoption", "Adoption", "percent", 0.82, 0, 1, 0.01,
                   "Share of target users actively using the product.", True),
            _field("utilisation", "Utilisation", "percent", 0.9, 0, 1, 0.05,
                   "Depth of use among adopters.", True),
            _field("realisation", "Realisation", "percent", 0.9, 0, 1, 0.05,
                   "Share of released time that becomes usable capacity.", True),
        ],
        "compute": _prod_compute, "explain": _prod_explain,
    },
}


def fields_for(kind: str):
    return MODELS[kind]["fields"]


def default_inputs(kind: str):
    return {f["key"]: f["def"] for f in MODELS[kind]["fields"]}
