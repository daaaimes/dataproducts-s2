"""One-at-a-time sensitivity analysis — a port of src/engine/sensitivity.ts."""
from __future__ import annotations

import copy
import math

from ..format import _to_fixed, js_round
from .models import MODELS
from .valuation import NEUTRAL_LEVERS, value_product

# Assumption-specific uncertainty bands. A flat ±20% on every input produces a
# useless tornado for multiplicative models — every factor moves the answer by
# the same amount. These ranges reflect how much each kind of assumption
# actually varies in practice.
ATTRIBUTION_BAND = {"kind": "abs", "delta": 0.15}
COST_BAND = 0.2


def band_for(key: str, unit: str):
    k = key.lower()
    if "adoption" in k:
        return {"kind": "abs", "delta": 0.15}
    if "utilisation" in k or "realisation" in k:
        return {"kind": "abs", "delta": 0.10}
    if "controleffectiveness" in k:
        return {"kind": "abs", "delta": 0.12}
    if "probability" in k:
        return {"kind": "abs", "delta": 0.15}
    if "conversion" in k or "churn" in k:
        return {"kind": "rel", "delta": 0.30}
    if "eligible" in k:
        return {"kind": "abs", "delta": 0.08}
    if "margin" in k:
        return {"kind": "rel", "delta": 0.20}
    if "reduction" in k:
        return {"kind": "rel", "delta": 0.25}
    if unit == "hours":
        return {"kind": "rel", "delta": 0.30}
    if unit == "count":
        return {"kind": "rel", "delta": 0.12}
    if "financialimpact" in k:
        return {"kind": "rel", "delta": 0.35}
    if unit == "currency":
        return {"kind": "rel", "delta": 0.18}
    return {"kind": "rel", "delta": 0.20}


def effective_delta(v: float, b) -> float:
    """Absolute bands are capped at half the current value, so a 5% base
    probability is not swung by 15 percentage points."""
    return min(b["delta"], max(0.01, abs(v) * 0.5)) if b["kind"] == "abs" else b["delta"]


def _apply_band(v: float, b, direction: int) -> float:
    d = effective_delta(v, b)
    return v + direction * d if b["kind"] == "abs" else v * (1 + direction * d)


def _scale_group(o, f):
    for k in list(o.keys()):
        o[k] = o[k] * f


def tornado(p, settings, levers=None, limit: int = 9):
    """Each candidate assumption is moved through its own plausible range and the
    three-year economic value recomputed. Largest movers first."""
    levers = levers or NEUTRAL_LEVERS
    base = value_product(p, settings, levers)["threeYearValue"]
    rows = []

    def evaluate(mutate):
        d = copy.deepcopy(p)
        mutate(d)
        return value_product(d, settings, levers)["threeYearValue"]

    for bi, b in enumerate(p["benefits"]):
        model = MODELS[b["kind"]]
        for f in model["fields"]:
            if not f["sensitive"]:
                continue
            cur = b["inputs"].get(f["key"])
            if not isinstance(cur, (int, float)) or cur == 0:
                continue
            band = band_for(f["key"], f["unit"])
            cap = (f["max"] if f["max"] is not None else 1) if f["unit"] == "percent" else math.inf
            lo = max(f["min"] if f["min"] is not None else 0, _apply_band(cur, band, -1))
            hi = min(cap, _apply_band(cur, band, 1))
            if abs(hi - lo) < 1e-9:
                continue

            def set_lo(d, bi=bi, key=f["key"], lo=lo):
                d["benefits"][bi]["inputs"][key] = lo

            def set_hi(d, bi=bi, key=f["key"], hi=hi):
                d["benefits"][bi]["inputs"][key] = hi

            low = evaluate(set_lo)
            high = evaluate(set_hi)
            swing = abs(high - low)
            if swing < 1:
                continue
            ed = effective_delta(cur, band)
            rows.append({
                "key": f"{b['id']}:{f['key']}",
                "label": f["label"],
                "benefitLabel": b["label"],
                "base": base, "low": low, "high": high, "swing": swing,
                "swingPct": swing / abs(base) if base != 0 else 0,
                "lowDelta": low - base, "highDelta": high - base,
                "rangeNote": (f"±{_to_fixed(ed * 100, 1 if ed < 0.05 else 0)}pp"
                              if band["kind"] == "abs"
                              else f"±{int(js_round(band['delta'] * 100))}%"),
            })

        attr = b["attribution"]
        if attr > 0:
            a_delta = min(ATTRIBUTION_BAND["delta"], max(0.01, attr * 0.5))

            def set_attr_lo(d, bi=bi, attr=attr, a_delta=a_delta):
                d["benefits"][bi]["attribution"] = max(0.02, attr - a_delta)

            def set_attr_hi(d, bi=bi, attr=attr, a_delta=a_delta):
                d["benefits"][bi]["attribution"] = min(1, attr + a_delta)

            low = evaluate(set_attr_lo)
            high = evaluate(set_attr_hi)
            swing = abs(high - low)
            if swing >= 1:
                rows.append({
                    "key": f"{b['id']}:attribution", "label": "Attribution", "benefitLabel": b["label"],
                    "base": base, "low": low, "high": high, "swing": swing,
                    "swingPct": swing / abs(base) if base != 0 else 0,
                    "lowDelta": low - base, "highDelta": high - base,
                    "rangeNote": f"±{_to_fixed(min(0.15, max(0.01, attr * 0.5)) * 100, 0)}pp",
                })

    # Portfolio-level cost levers
    def cost_low(d):
        _scale_group(d["investment"]["run"], 1 - COST_BAND)
        _scale_group(d["investment"]["technology"], 1 - COST_BAND)

    def cost_high(d):
        _scale_group(d["investment"]["run"], 1 + COST_BAND)
        _scale_group(d["investment"]["technology"], 1 + COST_BAND)

    run_low = evaluate(cost_low)
    run_high = evaluate(cost_high)
    rows.append({
        "key": "cost:run", "label": "Annual operating cost", "benefitLabel": None, "base": base,
        "low": run_low, "high": run_high, "swing": abs(run_high - run_low),
        "swingPct": abs(run_high - run_low) / abs(base) if base != 0 else 0,
        "lowDelta": run_low - base, "highDelta": run_high - base, "rangeNote": "±20%",
    })

    def ramp_low(d):
        for b in d["benefits"]:
            b["rampMonths"] = js_round(b["rampMonths"] * 1.5)

    def ramp_high(d):
        for b in d["benefits"]:
            b["rampMonths"] = max(1, js_round(b["rampMonths"] * 0.6))

    r_low = evaluate(ramp_low)
    r_high = evaluate(ramp_high)
    rows.append({
        "key": "time:ramp", "label": "Benefit ramp-up speed", "benefitLabel": None, "base": base,
        "low": r_low, "high": r_high, "swing": abs(r_high - r_low),
        "swingPct": abs(r_high - r_low) / abs(base) if base != 0 else 0,
        "lowDelta": r_low - base, "highDelta": r_high - base, "rangeNote": "0.6–1.5×",
    })

    rows.sort(key=lambda r: r["swing"], reverse=True)
    return rows[:limit]
