"""Monthly-granularity corporate finance primitives — a port of src/engine/finance.ts."""
from __future__ import annotations

import math

INF = float("inf")


def monthly_discount_factor(annual_rate: float, month: float) -> float:
    return 1 / math.pow(1 + annual_rate, month / 12)


def npv(monthly_net, annual_rate: float) -> float:
    return sum(cf * monthly_discount_factor(annual_rate, m + 0.5)
               for m, cf in enumerate(monthly_net))


def payback_months(monthly_net) -> float:
    """Payback in months, with linear interpolation inside the crossing month."""
    cum = 0.0
    for m, cf in enumerate(monthly_net):
        prev = cum
        cum += cf
        if prev < 0 and cum >= 0:
            frac = 0.0 if cf == 0 else -prev / cf
            return m + frac
        if m == 0 and cum >= 0:
            return 0.5
    return INF


def irr(monthly_net) -> float:
    """Annualised IRR by bisection on the monthly rate. Returns NaN when undefined."""
    has_neg = any(v < 0 for v in monthly_net)
    has_pos = any(v > 0 for v in monthly_net)
    if not has_neg or not has_pos:
        return math.nan

    def f(rm: float) -> float:
        total = 0.0
        for m, cf in enumerate(monthly_net):
            try:
                total += cf / math.pow(1 + rm, m + 0.5)
            except (OverflowError, ZeroDivisionError):
                return math.inf if cf > 0 else -math.inf
        return total

    lo, hi = -0.9, 3.0
    flo = f(lo)
    if not math.isfinite(flo):
        return math.nan
    fhi = f(hi)
    if flo * fhi > 0:
        return math.nan

    for _ in range(200):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(fm) < 1e-6:
            lo = hi = mid
            break
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm

    rm = (lo + hi) / 2
    try:
        annual = math.pow(1 + rm, 12) - 1
    except (OverflowError, ValueError):
        return math.nan
    return annual if math.isfinite(annual) else math.nan


def cumulative(arr):
    out, c = [], 0.0
    for v in arr:
        c += v
        out.append(c)
    return out


def sum_range(arr, frm: int, to: int) -> float:
    return sum(arr[i] for i in range(frm, min(to, len(arr))))


def ramp_factor(m: int, start: float, ramp_months: float) -> float:
    """Linear ramp multiplier in [0,1] for month `m` given a start and ramp length."""
    if m < start:
        return 0.0
    if ramp_months <= 0:
        return 1.0
    t = (m - start + 0.5) / ramp_months
    return 1.0 if t >= 1 else t
