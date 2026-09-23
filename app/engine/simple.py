"""Simple mode — a port of src/engine/simple.ts.

A small set of questions a product manager can answer from memory, expanded
into a complete valuation using published-style benchmarks per product
archetype. Every derived assumption stays visible and editable in Detailed
mode, and every benefit line still explains its own arithmetic.
"""
from __future__ import annotations

import copy

from ..data.factory import make_assumption, make_benefit, make_investment, now_iso, uid
from ..format import js_round
from .scenarios import DEFAULT_SCENARIOS

EVIDENCE_LEVELS = [
    {"key": "Measured", "label": "Measured", "blurb": "We have actuals from a live baseline."},
    {"key": "Piloted", "label": "Piloted", "blurb": "We ran a pilot and measured the result."},
    {"key": "Benchmarked", "label": "Benchmarked", "blurb": "Based on comparable products or peers."},
    {"key": "Estimated", "label": "Estimated", "blurb": "Informed judgement, not yet measured."},
]

EVIDENCE_PROFILE = {
    "Measured": {
        "evidence": "Actual", "stars": 5, "attribution": 0.7, "realisation": 0.9, "probability": 0.85,
        "confidence": {"baselineQuality": 88, "dataAvailability": 86, "assumptionStrength": 82,
                       "historicalEvidence": 84, "attributionConfidence": 78, "adoptionConfidence": 80,
                       "financialValidation": 76, "measurementMaturity": 82},
    },
    "Piloted": {
        "evidence": "Pilot", "stars": 4, "attribution": 0.6, "realisation": 0.8, "probability": 0.75,
        "confidence": {"baselineQuality": 74, "dataAvailability": 72, "assumptionStrength": 70,
                       "historicalEvidence": 66, "attributionConfidence": 64, "adoptionConfidence": 70,
                       "financialValidation": 62, "measurementMaturity": 68},
    },
    "Benchmarked": {
        "evidence": "Benchmark", "stars": 3, "attribution": 0.5, "realisation": 0.7, "probability": 0.65,
        "confidence": {"baselineQuality": 60, "dataAvailability": 58, "assumptionStrength": 58,
                       "historicalEvidence": 52, "attributionConfidence": 50, "adoptionConfidence": 56,
                       "financialValidation": 48, "measurementMaturity": 54},
    },
    "Estimated": {
        "evidence": "Estimate", "stars": 2, "attribution": 0.4, "realisation": 0.6, "probability": 0.55,
        "confidence": {"baselineQuality": 46, "dataAvailability": 44, "assumptionStrength": 42,
                       "historicalEvidence": 36, "attributionConfidence": 38, "adoptionConfidence": 44,
                       "financialValidation": 34, "measurementMaturity": 40},
    },
}


def _s(a, c, r, k, d, ai):
    return {"strategicAlignment": a, "customerImpact": c, "reusability": r,
            "riskReduction": k, "dataDemocratisation": d, "aiReadiness": ai}


ARCHETYPES = {
    "Data Product": {
        "buildMonths": 8, "rampMonths": 10, "hoursSaved": 6, "adoption": 0.65,
        "runCostRatio": 0.32, "changeRatio": 0.14, "complexity": 6, "timeToValueMonths": 10,
        "fullyLoadedAnnualCost": 135_000, "strategic": _s(78, 58, 84, 52, 80, 68),
        "defaultInvestment": 330_000, "defaultUsers": 400,
    },
    "Data Application": {
        "buildMonths": 6, "rampMonths": 8, "hoursSaved": 5, "adoption": 0.7,
        "runCostRatio": 0.30, "changeRatio": 0.16, "complexity": 5, "timeToValueMonths": 8,
        "fullyLoadedAnnualCost": 130_000, "strategic": _s(72, 76, 58, 46, 56, 52),
        "defaultInvestment": 380_000, "defaultUsers": 500,
    },
    "Data Service / API": {
        "buildMonths": 7, "rampMonths": 10, "hoursSaved": 7, "adoption": 0.6,
        "runCostRatio": 0.28, "changeRatio": 0.10, "complexity": 6, "timeToValueMonths": 9,
        "fullyLoadedAnnualCost": 150_000, "strategic": _s(76, 44, 92, 50, 82, 72),
        "defaultInvestment": 330_000, "defaultUsers": 300,
    },
    "Dashboard": {
        "buildMonths": 4, "rampMonths": 6, "hoursSaved": 3.5, "adoption": 0.6,
        "runCostRatio": 0.22, "changeRatio": 0.12, "complexity": 3, "timeToValueMonths": 5,
        "fullyLoadedAnnualCost": 140_000, "strategic": _s(58, 50, 48, 40, 66, 36),
        "defaultInvestment": 300_000, "defaultUsers": 450,
    },
    "AI / ML Product": {
        "buildMonths": 6, "rampMonths": 8, "hoursSaved": 5, "adoption": 0.7,
        "runCostRatio": 0.38, "changeRatio": 0.14, "complexity": 6, "timeToValueMonths": 8,
        "fullyLoadedAnnualCost": 135_000, "strategic": _s(82, 68, 62, 54, 50, 84),
        "defaultInvestment": 360_000, "defaultUsers": 600,
    },
    "GenAI Application": {
        "buildMonths": 5, "rampMonths": 8, "hoursSaved": 6.5, "adoption": 0.6,
        "runCostRatio": 0.45, "changeRatio": 0.18, "complexity": 5, "timeToValueMonths": 7,
        "fullyLoadedAnnualCost": 125_000, "strategic": _s(84, 74, 70, 44, 74, 92),
        "defaultInvestment": 460_000, "defaultUsers": 900,
    },
    "Automation": {
        "buildMonths": 5, "rampMonths": 6, "hoursSaved": 8, "adoption": 0.8,
        "runCostRatio": 0.26, "changeRatio": 0.12, "complexity": 4, "timeToValueMonths": 6,
        "fullyLoadedAnnualCost": 115_000, "strategic": _s(66, 46, 60, 62, 46, 48),
        "defaultInvestment": 360_000, "defaultUsers": 250,
    },
    "Decision Engine": {
        "buildMonths": 8, "rampMonths": 10, "hoursSaved": 4, "adoption": 0.7,
        "runCostRatio": 0.36, "changeRatio": 0.16, "complexity": 7, "timeToValueMonths": 10,
        "fullyLoadedAnnualCost": 140_000, "strategic": _s(84, 70, 72, 60, 50, 80),
        "defaultInvestment": 250_000, "defaultUsers": 450,
    },
    "Data Platform Capability": {
        "buildMonths": 10, "rampMonths": 14, "hoursSaved": 8, "adoption": 0.55,
        "runCostRatio": 0.34, "changeRatio": 0.12, "complexity": 8, "timeToValueMonths": 13,
        "fullyLoadedAnnualCost": 155_000, "strategic": _s(86, 40, 94, 58, 90, 82),
        "defaultInvestment": 380_000, "defaultUsers": 400,
    },
    "Regulatory / Compliance Product": {
        "buildMonths": 9, "rampMonths": 12, "hoursSaved": 10, "adoption": 0.9,
        "runCostRatio": 0.30, "changeRatio": 0.16, "complexity": 7, "timeToValueMonths": 11,
        "fullyLoadedAnnualCost": 130_000, "strategic": _s(84, 30, 60, 90, 40, 44),
        "defaultInvestment": 410_000, "defaultUsers": 220,
    },
}

LEVERS = [
    {"key": "revenue", "label": "Revenue growth", "field": "Annual revenue in scope", "series": "s1",
     "help": "Revenue this product can plausibly influence in a year, before attribution."},
    {"key": "costSavings", "label": "Cost reduction", "field": "Annual cost you can remove", "series": "s3",
     "help": "Run-rate cost with an identified budget line and owner."},
    {"key": "costAvoidance", "label": "Cost avoidance", "field": "Future annual cost avoided", "series": "s4",
     "help": "Spend already in the plan that will no longer be needed."},
    {"key": "risk", "label": "Risk reduction", "field": "Annual loss exposure in scope", "series": "s2",
     "help": "Size of the loss event. A benchmark probability reduction is applied — open the explain panel to see it."},
]

RISK_BASE_PROBABILITY = 0.08
RISK_RESIDUAL_PROBABILITY = 0.045
RISK_CONTROL_EFFECTIVENESS = 0.8


def default_simple_input(product_type: str = "AI / ML Product"):
    a = ARCHETYPES[product_type]
    return {
        "name": "", "owner": "", "businessUnit": "Consumer Banking", "type": product_type,
        "problem": "", "userCount": a["defaultUsers"], "hoursSaved": a["hoursSaved"],
        "adoption": a["adoption"],
        "levers": {"revenue": 0, "costSavings": 0, "costAvoidance": 0, "risk": 0},
        "buildInvestment": a["defaultInvestment"], "evidenceLevel": "Benchmarked",
    }


def apply_archetype(inp, product_type: str):
    a = ARCHETYPES[product_type]
    out = dict(inp)
    out.update({
        "type": product_type,
        "hoursSaved": a["hoursSaved"],
        "adoption": a["adoption"],
        "buildInvestment": inp["buildInvestment"] if inp["buildInvestment"] > 0 else a["defaultInvestment"],
        "fullyLoadedAnnualCost": None,
        "buildMonths": None,
    })
    return out


def build_product_from_simple(inp, settings, existing_id=None):
    """Expands the simple inputs into a complete, fully explainable DataProduct."""
    arche = ARCHETYPES[inp["type"]]
    prof = EVIDENCE_PROFILE[inp["evidenceLevel"]]
    attribution = inp.get("attribution") if inp.get("attribution") is not None else prof["attribution"]
    loaded = (inp.get("fullyLoadedAnnualCost") if inp.get("fullyLoadedAnnualCost") is not None
              else arche["fullyLoadedAnnualCost"])
    hourly = loaded / max(1, settings["annualWorkingHours"])
    build_months = inp.get("buildMonths") if inp.get("buildMonths") is not None else arche["buildMonths"]
    pid = existing_id or uid("dp")
    now = now_iso()
    levers = inp["levers"]

    benefits = []

    if inp["userCount"] > 0 and inp["hoursSaved"] > 0:
        benefits.append(make_benefit(
            "analystProductivity", label="Time released for target users",
            attribution=attribution, ramp_months=arche["rampMonths"],
            evidence=prof["evidence"], evidence_strength=prof["stars"],
            evidence_note=(f"Benchmark for {inp['type'].lower()} deployments, adjusted for a "
                           f"{inp['evidenceLevel'].lower()} evidence base."),
            inputs={
                "users": inp["userCount"], "hoursSaved": inp["hoursSaved"],
                "hourlyCost": js_round(hourly), "adoption": inp["adoption"],
                "utilisation": 0.85, "realisation": prof["realisation"],
            }))

    if levers["revenue"] > 0:
        benefits.append(make_benefit(
            "feeIncome", label="Incremental revenue influenced", kind="simpleRevenue",
            attribution=attribution, ramp_months=arche["rampMonths"] + 2, start_month=1,
            evidence=prof["evidence"], evidence_strength=prof["stars"],
            inputs={"annualRevenue": levers["revenue"], "probability": prof["probability"],
                    "annualGrowth": 0.03}))

    if levers["costSavings"] > 0:
        benefits.append(make_benefit(
            "operationalEfficiency", label="Run-rate cost removed", kind="runRateReduction",
            attribution=attribution, ramp_months=arche["rampMonths"],
            evidence=prof["evidence"], evidence_strength=prof["stars"],
            inputs={"baselineAnnualCost": levers["costSavings"], "reductionPct": 1,
                    "realisation": prof["realisation"]}))

    if levers["costAvoidance"] > 0:
        benefits.append(make_benefit(
            "avoidTechSpend", label="Planned spend avoided", kind="costAvoidance",
            attribution=attribution, ramp_months=arche["rampMonths"], start_month=3,
            evidence=prof["evidence"], evidence_strength=prof["stars"],
            inputs={"baselineCost": js_round(levers["costAvoidance"] * 1.3),
                    "avoidedCost": levers["costAvoidance"], "probability": prof["probability"]}))

    if levers["risk"] > 0:
        benefits.append(make_benefit(
            "operationalRisk", label="Expected loss reduced", kind="riskReduction",
            attribution=attribution, ramp_months=arche["rampMonths"] + 2,
            evidence=prof["evidence"], evidence_strength=max(2, prof["stars"] - 1),
            evidence_note=("Probability reduction applied from the operational-risk benchmark range "
                           "for detection-led controls."),
            inputs={"financialImpact": levers["risk"],
                    "baselineProbability": RISK_BASE_PROBABILITY,
                    "expectedProbability": RISK_RESIDUAL_PROBABILITY,
                    "controlEffectiveness": RISK_CONTROL_EFFECTIVENESS}))

    build = inp["buildInvestment"]
    change = build * arche["changeRatio"]
    run_total = build * arche["runCostRatio"]
    is_ai = inp["type"] in ("AI / ML Product", "GenAI Application", "Decision Engine")

    investment = make_investment(
        build_months=build_months,
        build={
            "internalDevelopment": js_round(build * 0.38),
            "externalDevelopment": js_round(build * 0.16),
            "consulting": js_round(build * 0.08),
            "dataEngineering": js_round(build * (0.18 if is_ai else 0.26)),
            "mlDevelopment": js_round(build * (0.14 if is_ai else 0.02)),
            "uxProductManagement": js_round(build * 0.06),
        },
        technology={
            "cloud": js_round(run_total * 0.16),
            "compute": js_round(run_total * 0.10),
            "storage": js_round(run_total * 0.05),
            "softwareLicences": js_round(run_total * 0.09),
            "dataVendors": js_round(run_total * 0.04),
            "gpu": js_round(run_total * (0.05 if is_ai else 0)),
            "llmApi": js_round(run_total * (0.14 if inp["type"] == "GenAI Application" else 0)),
            "onPremInfrastructure": 0,
        },
        run={
            "support": js_round(run_total * 0.08),
            "operations": js_round(run_total * 0.08),
            "modelMonitoring": js_round(run_total * (0.09 if is_ai else 0.02)),
            "dataQuality": js_round(run_total * 0.06),
            "cybersecurity": js_round(run_total * 0.04),
            "maintenance": js_round(run_total * 0.07),
            "productTeam": js_round(run_total * 0.14),
        },
        change={
            "training": js_round(change * 0.3),
            "changeManagement": js_round(change * 0.36),
            "communications": js_round(change * 0.12),
            "businessAdoption": js_round(change * 0.22),
        })

    active_levers = [lv["label"].lower() for lv in LEVERS if levers[lv["key"]] > 0]
    problem_text = inp["problem"].strip()
    description = problem_text or (
        f"A {inp['type'].lower()} for {inp['businessUnit']}, serving {inp['userCount']} users. "
        f"Value is expected from released capacity"
        f"{' and ' + ', '.join(active_levers) if active_levers else ''}.")

    problem_statement = problem_text or (
        f"Target users spend around {_jsnum(inp['hoursSaved'])} hours a month on work this product can absorb. "
        f"This case was built in Simple mode using {inp['evidenceLevel'].lower()} benchmarks and should be refined "
        "with a measured baseline before approval.")

    assumptions = [
        make_assumption(pid, "Hours released per user per month", inp["hoursSaved"], "hours",
                        source=f"{inp['evidenceLevel']} — {inp['type']} benchmark",
                        owner=inp["owner"] or "Product owner", evidence=prof["evidence"],
                        confidence=int(js_round(prof["confidence"]["assumptionStrength"]))),
        make_assumption(pid, "Steady-state adoption", inp["adoption"], "%",
                        source=f"{inp['type']} archetype benchmark",
                        owner=inp["owner"] or "Product owner", evidence=prof["evidence"],
                        confidence=int(js_round(prof["confidence"]["adoptionConfidence"]))),
        make_assumption(pid, "Fully-loaded annual cost per user", js_round(loaded), "SGD",
                        source="Benchmark cost-to-serve rate — replace with the Finance rate",
                        owner="Finance Business Partner", evidence="Benchmark", confidence=60),
        make_assumption(pid, "Attribution to this product", attribution, "%",
                        source=f"Derived from a {inp['evidenceLevel'].lower()} evidence base",
                        owner=inp["owner"] or "Product owner", evidence=prof["evidence"],
                        confidence=int(js_round(prof["confidence"]["attributionConfidence"]))),
    ]

    if levers["risk"] > 0:
        assumptions.append(make_assumption(
            pid, "Annual probability of the loss event", RISK_BASE_PROBABILITY, "% p.a.",
            source="Operational risk benchmark — confirm with second line",
            owner="Operational Risk", evidence="Benchmark", confidence=48))

    return {
        "id": pid,
        "name": inp["name"].strip() or "Untitled data product",
        "code": f"DP-{str(int(__import__('time').time() * 1000))[-3:]}",
        "description": description,
        "problemStatement": problem_statement,
        "owner": inp["owner"].strip() or "Unassigned",
        "sponsor": "To be confirmed",
        "businessUnit": inp["businessUnit"],
        "domain": "Customer",
        "type": inp["type"],
        "lifecycle": "Business Case",
        "strategicPriority": "Medium",
        "targetUsers": "Target user population",
        "userCount": inp["userCount"],
        "usageFrequency": "Daily",
        "geographicScope": "Single market",
        "tags": ["Simple valuation", inp["evidenceLevel"]],
        "createdAt": now,
        "updatedAt": now,
        "adoptionAssumption": inp["adoption"],
        "complexity": arche["complexity"],
        "timeToValueMonths": arche["timeToValueMonths"],
        "benefits": benefits,
        "investment": investment,
        "confidence": dict(prof["confidence"]),
        "strategic": dict(arche["strategic"]),
        "scenarios": copy.deepcopy(DEFAULT_SCENARIOS),
        "realisation": [],
        "assumptions": assumptions,
    }


def _jsnum(v):
    return int(v) if float(v).is_integer() else v
