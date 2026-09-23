"""Banking data product catalogue — a port of the expansion half of banking200.ts.

The 200 catalogue entries live in the catalog_entries table in Postgres
(originally extracted verbatim from banking200.ts into banking200.json, then
loaded in by scripts/migrate_catalog.py). Each entry is a Simple-mode input
plus the catalogue metadata it came from; the Simple-mode engine does the
financial work here, exactly as it does for a product a user creates by hand.
"""
from __future__ import annotations

from functools import lru_cache

from .. import db
from ..format import js_round
from ..engine.simple import build_product_from_simple
from .factory import make_realisation

FREQUENCY = {
    "Decision Engine": "Real-time",
    "Data Service / API": "Real-time",
    "Automation": "Daily",
    "AI / ML Product": "Daily",
    "GenAI Application": "Daily",
    "Dashboard": "Weekly",
    "Data Application": "Daily",
    "Data Product": "Daily",
    "Data Platform Capability": "Daily",
    "Regulatory / Compliance Product": "Monthly",
}

EV_FACTORS = {
    "Measured": {"attr": 0.7, "real": 0.9, "prob": 0.85},
    "Piloted": {"attr": 0.6, "real": 0.8, "prob": 0.75},
    "Benchmarked": {"attr": 0.5, "real": 0.7, "prob": 0.65},
    "Estimated": {"attr": 0.4, "real": 0.6, "prob": 0.55},
}


@lru_cache(maxsize=1)
def catalog_entries():
    return db.fetch_catalog_entries()


def id_for(code: str) -> str:
    """Deterministic id so deep links and comparisons stay stable across reloads."""
    return f"dp_{code.lower().replace('-', '_')}"


def priority_of(entry) -> str:
    lv = entry["input"]["levers"]
    regulated = entry["input"]["type"] == "Regulatory / Compliance Product"
    weight = lv["revenue"] / 4 + lv["costSavings"] + lv["costAvoidance"] + lv["risk"] / 40
    if regulated or weight > 2_400_000:
        return "Critical"
    if weight > 1_400_000:
        return "High"
    if weight > 600_000:
        return "Medium"
    return "Low"


def realisation_for(entry, hourly_cost):
    """Four quarters of tracking for products already in production.

    Forecast is the recognised plan ramping to steady state; actual lands a
    little under it, which is what actually happens — that gap is the
    conversation the Value Realisation page exists to start.
    """
    lv = entry["input"]["levers"]
    i = entry["input"]
    k = EV_FACTORS[i["evidenceLevel"]]
    ramp = [0.4, 0.65, 0.85, 1]

    revenue = lv["revenue"] * k["prob"] * k["attr"]
    savings = (lv["costSavings"] * k["real"] + lv["costAvoidance"] * k["prob"]) * k["attr"]
    productivity = (i["userCount"] * i["hoursSaved"] * 12 * hourly_cost
                    * i["adoption"] * 0.85 * k["real"] * k["attr"])
    risk = lv["risk"] * 0.028 * k["attr"]

    seed = sum(ord(ch) for ch in entry["code"])

    def drift(n):
        return 0.8 + ((seed * (n + 3)) % 16) / 100

    rows = []
    for n, period in enumerate(["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"]):
        f = ramp[n] / 4
        d = drift(n)
        rows.append({
            "period": period,
            "forecastRevenue": js_round(revenue * f),
            "actualRevenue": js_round(revenue * f * d),
            "forecastSavings": js_round(savings * f),
            "actualSavings": js_round(savings * f * d),
            "forecastProductivity": js_round(productivity * f),
            "actualProductivity": js_round(productivity * f * d),
            "forecastRisk": js_round(risk * f),
            "actualRisk": js_round(risk * f * d),
            "forecastAdoption": min(1, i["adoption"] * ramp[n]),
            "actualAdoption": min(1, i["adoption"] * ramp[n] * d),
        })
    return make_realisation(rows)


def build_catalog_products(settings):
    """Expands the catalogue into fully-valued data products."""
    out = []
    for entry in catalog_entries():
        hourly_cost = 135_000 / max(1, settings["annualWorkingHours"])
        p = build_product_from_simple(entry["input"], settings, id_for(entry["code"]))
        datasets = [d.strip().rstrip(".") for d in entry["datasets"].split(",")]
        datasets = [d for d in datasets if d]

        p["code"] = entry["code"]
        p["domain"] = entry["domain"]
        p["lifecycle"] = entry["lifecycle"]
        p["description"] = entry["outcome"]
        p["problemStatement"] = entry["problem"]
        p["sponsor"] = entry["input"]["owner"]
        p["strategicPriority"] = priority_of(entry)
        p["usageFrequency"] = FREQUENCY.get(entry["input"]["type"], "Daily")
        p["geographicScope"] = ("Group-wide" if entry["input"]["businessUnit"].startswith("Group")
                                else "Regional")
        p["targetUsers"] = f"{entry['input']['userCount']} users in {entry['input']['businessUnit']}"
        p["tags"] = ["Banking catalogue", entry["domain"]] + datasets[:3]
        if entry["lifecycle"] in ("Production", "Scale"):
            p["realisation"] = realisation_for(entry, hourly_cost)
        p["assumptions"] = p["assumptions"] + [{
            "id": f"{p['id']}_note",
            "productId": p["id"],
            "assumption": entry["keyAssumption"],
            "value": 0,
            "unit": "note",
            "source": "Catalogue review — to be replaced by a measured baseline",
            "owner": entry["input"]["owner"],
            "evidence": "Estimate" if entry["input"]["evidenceLevel"] == "Estimated" else "Benchmark",
            "confidence": 35 if entry["input"]["evidenceLevel"] == "Estimated" else 55,
            "lastUpdated": p["updatedAt"][:10],
            "evidenceRef": None,
        }]
        out.append(p)
    return out


@lru_cache(maxsize=1)
def catalog_by_id():
    """Catalogue metadata keyed by product id, for surfaces that want the source text."""
    return {id_for(e["code"]): e for e in catalog_entries()}
