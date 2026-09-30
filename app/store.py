"""Session state and the derived portfolio — a port of src/store/AppStore.tsx.

The React app kept products, settings and comparison selection in a reducer
backed by localStorage. Streamlit's session_state caches the same data for
the life of one browser session; the products themselves now live in the
`products` table in Postgres, shared by every session, so a valuation
created or edited in one browser is there for everyone else too. The first
session ever to run against an empty table seeds it from the banking
catalogue; every session after that just loads what's already there.
"""
from __future__ import annotations

import copy
import math

import streamlit as st

from . import auth, db, persist
from .data.catalog import build_catalog_products
from .data.factory import now_iso, uid
from .domain import DEFAULT_SETTINGS
from .engine.valuation import compute_priority, value_product

DEFAULT_COMPARE = ["dp_fc_111", "dp_cr_084", "dp_op_174"]


def init() -> None:
    ss = st.session_state
    if "settings" not in ss:
        ss.settings = copy.deepcopy(DEFAULT_SETTINGS)
        # A refresh starts a new Streamlit session; recover what the user chose.
        persist.load_into(ss.settings)
    if "products" not in ss:
        if db.product_count() == 0:
            db.replace_products(build_catalog_products(ss.settings))
        ss.products = db.fetch_products()
    if "compare_ids" not in ss:
        ss.compare_ids = [i for i in DEFAULT_COMPARE
                          if any(p["id"] == i for p in ss.products)]
    ss.setdefault("dirty", 0)


def settings():
    return st.session_state.settings


def currency() -> str:
    return st.session_state.settings["currency"]


def theme() -> str:
    return st.session_state.settings.get("theme", "light")


def set_settings(patch: dict) -> None:
    st.session_state.settings.update(patch)
    st.session_state.dirty += 1
    persist.save(st.session_state.settings)


def save_product(product: dict) -> None:
    products = st.session_state.products
    idx = next((i for i, p in enumerate(products) if p["id"] == product["id"]), None)
    from .data.factory import now_iso
    product = {**product, "updatedAt": now_iso()}
    db.upsert_product(product)
    if idx is None:
        products.insert(0, product)
    else:
        products[idx] = product
    st.session_state.dirty += 1


def delete_product(pid: str) -> None:
    db.delete_product(pid)
    st.session_state.products = [p for p in st.session_state.products if p["id"] != pid]
    st.session_state.compare_ids = [i for i in st.session_state.compare_ids if i != pid]
    st.session_state.dirty += 1


def set_compare(ids) -> None:
    st.session_state.compare_ids = list(ids)


def reset_demo() -> None:
    products = build_catalog_products(st.session_state.settings)
    db.replace_products(products)
    st.session_state.products = products
    st.session_state.compare_ids = [i for i in DEFAULT_COMPARE
                                    if any(p["id"] == i for p in st.session_state.products)]
    st.session_state.dirty += 1


def _all_rows():
    """Every product valued and scored, regardless of status or ownership.

    Memoised on a revision counter rather than st.cache_data: the products are
    large nested dicts, so hashing them on every rerun costs more than the
    valuation itself, and cache_data would hand back a deep copy each time.
    """
    ss = st.session_state
    cached = ss.get("_rows_cache")
    if cached is not None and cached[0] == ss.dirty:
        return cached[1]

    cfg = ss.settings
    vals = [(p, value_product(p, cfg)) for p in ss.products]
    max_value = max([1.0] + [v["threeYearValue"] for _, v in vals])
    out = [{"product": p, "valuation": v,
            "priority": compute_priority(v, p, cfg["priorityWeights"], max_value)}
           for p, v in vals]
    ss._rows_cache = (ss.dirty, out)
    return out


def rows():
    """Published products visible to the current user.

    Portfolio-tier users see every owner's published work; everyone else sees
    only their own (plus legacy/demo data that predates ownership). This is
    what feeds the Dashboard, Portfolio and every other aggregate view.
    """
    return [r for r in _all_rows()
            if r["product"].get("recordStatus", "published") == "published"
            and auth.can_view(r["product"])]


def row_by_id(pid: str):
    r = next((r for r in _all_rows() if r["product"]["id"] == pid), None)
    if r is None or not auth.can_view(r["product"]):
        return None
    return r


def my_entries():
    """Every one of the current user's own submissions, any status."""
    lan_id = auth.current_lan_id()
    if not lan_id:
        return []
    return sorted(
        (r for r in _all_rows() if r["product"].get("ownerLanId") == lan_id),
        key=lambda r: r["product"]["updatedAt"], reverse=True)


def archive_queue():
    """Published entries submitted by people who report to the current user."""
    if not auth.has_level(auth.current_user(), "archive"):
        return []
    return [r for r in _all_rows()
            if r["product"].get("recordStatus") == "published"
            and auth.can_archive_entry(r["product"].get("ownerLanId", ""))]


def publish_product(pid: str) -> bool:
    r = row_by_id(pid)
    if not r or not auth.can_submit():
        return False
    p = r["product"]
    if p.get("ownerLanId") != auth.current_lan_id() or p.get("recordStatus") != "draft":
        return False
    save_product({**p, "recordStatus": "published"})
    return True


def archive_product(pid: str) -> bool:
    r = row_by_id(pid)
    if not r:
        return False
    p = r["product"]
    if p.get("recordStatus") != "published" or not auth.can_archive_entry(p.get("ownerLanId", "")):
        return False
    save_product({**p, "recordStatus": "archived"})
    return True


def duplicate_product(pid: str) -> str | None:
    r = row_by_id(pid)
    if not r or not auth.can_submit():
        return None
    p = r["product"]
    if p.get("ownerLanId") != auth.current_lan_id():
        return None
    new_product = copy.deepcopy(p)
    new_id = uid("dp")
    new_product["id"] = new_id
    new_product["recordStatus"] = "draft"
    new_product["duplicatedFromId"] = pid
    new_product["createdAt"] = now_iso()
    new_product["updatedAt"] = now_iso()
    for a in new_product.get("assumptions", []):
        a["id"] = uid("asm")
        a["productId"] = new_id
    for b in new_product.get("benefits", []):
        b["id"] = uid("ben")
    save_product(new_product)
    return new_id


def totals():
    t = {k: 0.0 for k in [
        "annualGross", "annualNet", "threeYear", "fiveYear", "revenue", "costSavings",
        "costAvoidance", "productivity", "risk", "investment", "annualRunCost",
        "totalBenefits", "totalCosts", "hardDollar", "npv", "fteEquivalent",
        "proven", "expected", "potential"]}
    rs = rows()
    t["count"] = len(rs)
    for r in rs:
        v = r["valuation"]
        t["annualGross"] += v["annualGrossValue"]
        t["annualNet"] += v["netAnnualValue"]
        t["threeYear"] += v["threeYearValue"]
        t["fiveYear"] += v["fiveYearValue"]
        t["revenue"] += v["byCategory"]["revenue"]
        t["costSavings"] += v["byCategory"]["costSavings"]
        t["costAvoidance"] += v["byCategory"]["costAvoidance"]
        t["productivity"] += v["byCategory"]["productivity"]
        t["risk"] += v["byCategory"]["risk"]
        t["investment"] += v["costs"]["initialInvestment"]
        t["annualRunCost"] += v["annualOperatingCost"]
        t["totalBenefits"] += v["totalBenefits"]
        t["totalCosts"] += v["totalCosts"]
        t["hardDollar"] += v["hardDollarValue"]
        t["npv"] += v["npv"]
        t["fteEquivalent"] += v["fteEquivalent"]
        t["proven"] += v["byMaturity"]["Proven"]
        t["expected"] += v["byMaturity"]["Expected"]
        t["potential"] += v["byMaturity"]["Potential"]

    paybacks = [r["valuation"]["paybackMonths"] for r in rs
                if math.isfinite(r["valuation"]["paybackMonths"])]
    t["roi"] = ((t["totalBenefits"] - t["totalCosts"]) / t["totalCosts"]) if t["totalCosts"] > 0 else 0.0
    t["avgPayback"] = (sum(paybacks) / len(paybacks)) if paybacks else float("inf")
    t["avgConfidence"] = (round(sum(r["valuation"]["confidence"]["score"] for r in rs) / len(rs))
                          if rs else 0)
    return t
