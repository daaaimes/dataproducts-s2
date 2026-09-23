"""Automatically generated portfolio observations — a port of src/engine/insights.ts."""
from __future__ import annotations

import math

from ..format import money, months, pct

CAT_LABEL = {
    "revenue": "Revenue", "costSavings": "Cost savings", "costAvoidance": "Cost avoidance",
    "productivity": "Productivity", "risk": "Risk reduction",
}


def portfolio_insights(rows, settings):
    if not rows:
        return []
    c = settings["currency"]
    out = []

    ordered = sorted(rows, key=lambda r: r["valuation"]["threeYearValue"], reverse=True)
    total = sum(max(0.0, r["valuation"]["threeYearValue"]) for r in ordered)

    # Concentration
    cum, n = 0.0, 0
    for r in ordered:
        cum += max(0.0, r["valuation"]["threeYearValue"])
        n += 1
        if total and cum / total >= 0.78:
            break
    out.append({
        "id": "concentration", "tone": "neutral", "metric": f"{n} of {len(rows)}",
        "text": (f"{n} product{'s' if n > 1 else ''} generate {pct(cum / total)} of portfolio value. Concentration "
                 "this high means portfolio performance is really the performance of a handful of products."),
    })

    # Estimate-heavy products
    weak = [r for r in rows
            if r["valuation"]["byMaturity"]["Potential"] / (r["valuation"]["annualGrossValue"] or 1) > 0.5]
    weak_value = sum(max(0.0, r["valuation"]["threeYearValue"]) for r in weak)
    if weak:
        out.append({
            "id": "evidence", "tone": "warn" if weak_value / total > 0.3 else "neutral",
            "metric": pct(weak_value / total),
            "text": (f"{pct(weak_value / total)} of portfolio value sits in {len(weak)} "
                     f"product{'s' if len(weak) > 1 else ''} where most of the annual value still rests on estimated "
                     f"(not measured or piloted) evidence. That is {money(weak_value, c)} that needs stronger "
                     "evidence before it belongs in a financial plan."),
        })

    # Best category
    cats = {}
    for r in rows:
        for k, v in r["valuation"]["byCategory"].items():
            cats[k] = cats.get(k, 0.0) + v
    if cats:
        top_key, top_val = sorted(cats.items(), key=lambda kv: kv[1], reverse=True)[0]
        tail = ("Released capacity is real economic value but does not reduce budget unless it is redeployed or "
                "removed — agree the treatment with Finance." if top_key == "productivity"
                else "Cost avoidance does not reduce current-year budget; present it separately from hard savings."
                if top_key == "costAvoidance" else "This is the value story to lead with.")
        out.append({
            "id": "topcat", "tone": "neutral", "metric": money(top_val, c),
            "text": (f"{CAT_LABEL[top_key]} is the largest source of annual value at {money(top_val, c)}. {tail}"),
        })

    # Fast payback
    fast = [r for r in rows if r["valuation"]["paybackMonths"] <= 12]
    if fast:
        names = ", ".join(r["product"]["name"] for r in fast[:3])
        more = f" and {len(fast) - 3} more" if len(fast) > 3 else ""
        out.append({
            "id": "payback", "tone": "good", "metric": f"{len(fast)}",
            "text": (f"{len(fast)} product{'s have' if len(fast) > 1 else ' has'} a payback period under 12 months: "
                     f"{names}{more}. These are the strongest near-term funding candidates."),
        })

    # Unrealised value
    with_real = [r for r in rows if r["product"]["realisation"]]
    if with_real:
        forecast = actual = 0.0
        for r in with_real:
            for p in r["product"]["realisation"]:
                forecast += (p["forecastRevenue"] + p["forecastSavings"]
                             + p["forecastProductivity"] + p["forecastRisk"])
                actual += (p["actualRevenue"] + p["actualSavings"]
                           + p["actualProductivity"] + p["actualRisk"])
        gap = forecast - actual
        out.append({
            "id": "realisation", "tone": "warn" if gap > 0 else "good",
            "metric": pct(actual / max(1, forecast)),
            "text": ((f"{money(gap, c)} of forecast value is not yet realised across {len(with_real)} products in "
                      f"production — a realisation rate of {pct(actual / forecast)}. Use the variance to recalibrate "
                      "assumptions on the products still in business case.") if gap > 0 else
                     (f"Products in production are delivering {pct(actual / forecast)} of forecast value. Forecasting "
                      "is running accurate or conservative — worth reflecting in future cases.")),
        })

    # Reassess candidates
    reassess = [r for r in rows if r["priority"]["band"] == "Reassess"]
    if reassess:
        spend = sum(r["valuation"]["costs"]["initialInvestment"] + r["valuation"]["annualOperatingCost"]
                    for r in reassess)
        out.append({
            "id": "reassess", "tone": "warn", "metric": money(spend, c),
            "text": (f"{len(reassess)} product{'s score' if len(reassess) > 1 else ' scores'} below 60 on priority "
                     f"({', '.join(r['product']['name'] for r in reassess)}), carrying {money(spend, c)} of "
                     "committed and run-rate spend. Either strengthen the case or release the capacity."),
        })

    # Capacity
    fte = sum(r["valuation"]["fteEquivalent"] for r in rows)
    if fte > 1:
        out.append({
            "id": "capacity", "tone": "neutral", "metric": f"{fte:.0f} FTE",
            "text": (f"The portfolio releases the equivalent of {fte:.0f} FTE of capacity a year. Only the portion "
                     "the business formally removes or redeploys reaches the P&L — the rest is capability, not cost "
                     "reduction."),
        })

    # Average payback
    paybacks = [r["valuation"]["paybackMonths"] for r in rows
                if math.isfinite(r["valuation"]["paybackMonths"])]
    if paybacks:
        avg = sum(paybacks) / len(paybacks)
        from_go_live = sum((r["valuation"]["paybackFromGoLive"]
                            if math.isfinite(r["valuation"]["paybackFromGoLive"]) else 0)
                           for r in rows) / len(rows)
        out.append({
            "id": "avgpayback", "tone": "good" if avg <= 24 else "neutral", "metric": months(avg),
            "text": (f"Average payback across the portfolio is {months(avg)} from first spend. Measured from go-live "
                     f"it is {months(from_go_live)}."),
        })

    return out
