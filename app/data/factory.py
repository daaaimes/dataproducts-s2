"""Product and benefit constructors — a port of src/data/factory.ts."""
from __future__ import annotations

import copy
import random
import time
from datetime import datetime, timezone

from ..domain import DEFAULT_CONFIDENCE, DEFAULT_STRATEGIC, EMPTY_INVESTMENT
from ..engine.models import MODELS, default_inputs
from ..engine.scenarios import DEFAULT_SCENARIOS
from .catalogs import DRIVER_BY_ID

_seq = [0]


def uid(prefix: str = "id") -> str:
    _seq[0] += 1
    stamp = _base36(int(time.time() * 1000))
    tail = "".join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(4))
    return f"{prefix}_{stamp}_{_base36(_seq[0])}{tail}"


def _base36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        return "0"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def make_benefit(driver_id, label=None, kind=None, inputs=None, attribution=None,
                 start_month=None, ramp_months=None, evidence=None,
                 evidence_strength=None, evidence_note=None, id=None):
    driver = DRIVER_BY_ID.get(driver_id)
    kind = kind or (driver or {}).get("model") or "simpleRevenue"
    model = MODELS[kind]
    merged = default_inputs(kind)
    merged.update(inputs or {})
    return {
        "id": id or uid("ben"),
        "kind": kind,
        "category": model["category"],
        "driverId": driver_id,
        "label": label or (driver or {}).get("label") or model["name"],
        "attribution": 0.6 if attribution is None else attribution,
        "startMonth": 0 if start_month is None else start_month,
        "rampMonths": 9 if ramp_months is None else ramp_months,
        "evidence": evidence or "Estimate",
        "evidenceStrength": 3 if evidence_strength is None else evidence_strength,
        "evidenceNote": evidence_note,
        "inputs": merged,
    }


def make_investment(build_months=None, build=None, technology=None, run=None, change=None):
    inv = copy.deepcopy(EMPTY_INVESTMENT)
    inv["buildMonths"] = EMPTY_INVESTMENT["buildMonths"] if build_months is None else build_months
    inv["build"].update(build or {})
    inv["technology"].update(technology or {})
    inv["run"].update(run or {})
    inv["change"].update(change or {})
    return inv


def make_assumption(product_id, assumption, value, unit, source=None, owner=None,
                    evidence=None, confidence=None, last_updated=None, evidence_ref=None,
                    id=None):
    return {
        "id": id or uid("asm"),
        "productId": product_id,
        "assumption": assumption,
        "value": value,
        "unit": unit,
        "source": source or "Business estimate",
        "owner": owner or "Product owner",
        "evidence": evidence or "Estimate",
        "confidence": 60 if confidence is None else confidence,
        "lastUpdated": last_updated or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "evidenceRef": evidence_ref,
    }


def empty_product():
    now = now_iso()
    return {
        "id": uid("dp"), "name": "", "code": "", "description": "", "problemStatement": "",
        "owner": "", "sponsor": "", "businessUnit": "Consumer Banking", "domain": "Customer",
        "type": "Data Product", "lifecycle": "Idea", "strategicPriority": "Medium",
        "targetUsers": "", "userCount": 100, "usageFrequency": "Daily",
        "geographicScope": "Single market", "tags": [], "createdAt": now, "updatedAt": now,
        "adoptionAssumption": 0.65, "complexity": 5, "timeToValueMonths": 9,
        "benefits": [], "investment": make_investment(build_months=6),
        "confidence": dict(DEFAULT_CONFIDENCE), "strategic": dict(DEFAULT_STRATEGIC),
        "scenarios": copy.deepcopy(DEFAULT_SCENARIOS), "realisation": [], "assumptions": [],
    }


def make_realisation(rows):
    base = {
        "forecastRevenue": 0, "actualRevenue": 0, "forecastSavings": 0, "actualSavings": 0,
        "forecastProductivity": 0, "actualProductivity": 0, "forecastRisk": 0, "actualRisk": 0,
        "forecastAdoption": 0, "actualAdoption": 0,
    }
    return [{**base, **r} for r in rows]
