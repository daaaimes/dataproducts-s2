"""Postgres access for the banking catalogue and the live product store.

Every table uses a real column per known field so a plain `select *` is
readable on its own, rather than hiding everything behind one JSONB blob.

`assumptions`, `benefits` and `realisation` are one-to-many child tables
(foreign-keyed to products.id, cascade-deleted with their product) rather
than JSONB arrays on the products row — each entry is its own record with
its own real columns, the way a normal relational schema would model it.
`benefits.inputs` stays JSONB: its shape is polymorphic per benefit kind
(e.g. analystProductivity has users/hoursSaved/adoption; simpleRevenue has
annualRevenue/probability), so it can't be flattened to fixed columns.

`input` on a catalog entry, and `investment`/`confidence`/`strategic`/
`scenarios` on a product, stay as single JSONB columns — each is one
nested object per row, not a repeating list of independent records, and
each is consumed as one unit everywhere in the engine.

products also carries an `extra` JSONB catch-all: unlike the catalogue,
which is static, products are edited through the wizard, and the Detailed
mode "Advanced assumptions" step can add optional keys (discountRate,
horizonYears) on top of the base shape. Known optional keys get their own
column; extra exists so an unanticipated key is never silently dropped on
a round trip through Postgres.

Connections are opened fresh per call rather than pooled: Neon's free-tier
compute suspends itself after a few minutes idle, which silently kills any
connection a client-side pool is holding open, and the next query against
it fails with a confusing SSL/connection error. Opening a new connection
each time avoids that class of bug entirely — Neon's own endpoint already
pools underneath, so this doesn't add much latency.
"""
from __future__ import annotations

import streamlit as st
import psycopg
from psycopg.types.json import Jsonb

SCHEMA = """
create table if not exists catalog_entries (
    code text primary key,
    domain text not null,
    lifecycle text not null,
    problem text not null,
    datasets text not null,
    outcome text not null,
    value_note text not null,
    key_assumption text not null,
    input jsonb not null
);

create table if not exists products (
    id text primary key,
    name text not null,
    code text not null,
    description text not null,
    problem_statement text not null,
    owner text not null,
    sponsor text not null,
    business_unit text not null,
    domain text not null,
    type text not null,
    lifecycle text not null,
    strategic_priority text not null,
    target_users text not null,
    user_count integer not null,
    usage_frequency text not null,
    geographic_scope text not null,
    tags text[] not null default '{}',
    created_at text not null,
    updated_at text not null,
    adoption_assumption double precision not null,
    complexity integer not null,
    time_to_value_months integer not null,
    discount_rate double precision,
    horizon_years integer,
    investment jsonb not null,
    confidence jsonb not null,
    strategic jsonb not null,
    scenarios jsonb not null,
    extra jsonb not null default '{}'
);

create table if not exists assumptions (
    id text primary key,
    product_id text not null references products(id) on delete cascade,
    assumption text not null,
    value double precision not null,
    unit text not null,
    source text not null,
    owner text not null,
    evidence text not null,
    confidence integer not null,
    last_updated text not null,
    evidence_ref text
);

create table if not exists benefits (
    id text primary key,
    product_id text not null references products(id) on delete cascade,
    driver_id text,
    kind text not null,
    category text not null,
    label text not null,
    attribution double precision not null,
    start_month integer not null,
    ramp_months integer not null,
    evidence text not null,
    evidence_strength integer not null,
    evidence_note text,
    inputs jsonb not null
);

create table if not exists realisation (
    product_id text not null references products(id) on delete cascade,
    period text not null,
    forecast_revenue double precision not null,
    actual_revenue double precision not null,
    forecast_savings double precision not null,
    actual_savings double precision not null,
    forecast_productivity double precision not null,
    actual_productivity double precision not null,
    forecast_risk double precision not null,
    actual_risk double precision not null,
    forecast_adoption double precision not null,
    actual_adoption double precision not null,
    primary key (product_id, period)
);
"""

_CATALOG_COLUMNS = ("code", "domain", "lifecycle", "problem", "datasets",
                     "outcome", "value_note", "key_assumption", "input")

_PRODUCT_SCALAR_COLUMNS = (
    "id", "name", "code", "description", "problem_statement", "owner", "sponsor",
    "business_unit", "domain", "type", "lifecycle", "strategic_priority", "target_users",
    "user_count", "usage_frequency", "geographic_scope", "tags", "created_at", "updated_at",
    "adoption_assumption", "complexity", "time_to_value_months", "discount_rate", "horizon_years",
)
# (column, product dict key)
_PRODUCT_SCALAR_KEYS = (
    ("id", "id"), ("name", "name"), ("code", "code"), ("description", "description"),
    ("problem_statement", "problemStatement"), ("owner", "owner"), ("sponsor", "sponsor"),
    ("business_unit", "businessUnit"), ("domain", "domain"), ("type", "type"),
    ("lifecycle", "lifecycle"), ("strategic_priority", "strategicPriority"),
    ("target_users", "targetUsers"), ("user_count", "userCount"),
    ("usage_frequency", "usageFrequency"), ("geographic_scope", "geographicScope"),
    ("tags", "tags"), ("created_at", "createdAt"), ("updated_at", "updatedAt"),
    ("adoption_assumption", "adoptionAssumption"), ("complexity", "complexity"),
    ("time_to_value_months", "timeToValueMonths"), ("discount_rate", "discountRate"),
    ("horizon_years", "horizonYears"),
)
_PRODUCT_JSON_KEYS = ("investment", "confidence", "strategic", "scenarios")
# stored in child tables, not as columns on products — excluded from the extra catch-all too
_PRODUCT_CHILD_KEYS = ("assumptions", "benefits", "realisation")
_PRODUCT_KNOWN_KEYS = {k for _, k in _PRODUCT_SCALAR_KEYS} | set(_PRODUCT_JSON_KEYS) | set(_PRODUCT_CHILD_KEYS)
_PRODUCT_COLUMNS = _PRODUCT_SCALAR_COLUMNS + _PRODUCT_JSON_KEYS + ("extra",)

ASSUMPTION_COLUMNS = ("id", "product_id", "assumption", "value", "unit", "source",
                      "owner", "evidence", "confidence", "last_updated", "evidence_ref")
BENEFIT_COLUMNS = ("id", "product_id", "driver_id", "kind", "category", "label", "attribution",
                   "start_month", "ramp_months", "evidence", "evidence_strength",
                   "evidence_note", "inputs")
REALISATION_COLUMNS = ("product_id", "period", "forecast_revenue", "actual_revenue",
                       "forecast_savings", "actual_savings", "forecast_productivity",
                       "actual_productivity", "forecast_risk", "actual_risk",
                       "forecast_adoption", "actual_adoption")


def _catalog_row_to_entry(row: tuple) -> dict:
    (code, domain, lifecycle, problem, datasets, outcome,
     value_note, key_assumption, input_) = row
    return {"code": code, "domain": domain, "lifecycle": lifecycle, "problem": problem,
            "datasets": datasets, "outcome": outcome, "valueNote": value_note,
            "keyAssumption": key_assumption, "input": input_}


def _catalog_entry_to_row(e: dict) -> tuple:
    return (e["code"], e["domain"], e["lifecycle"], e["problem"], e["datasets"],
            e["outcome"], e["valueNote"], e["keyAssumption"], Jsonb(e["input"]))


def _product_row_to_dict(row: tuple) -> dict:
    values = dict(zip(_PRODUCT_COLUMNS, row))
    extra = values.pop("extra") or {}
    out = {key: values[col] for col, key in _PRODUCT_SCALAR_KEYS if values[col] is not None
           or col not in ("discount_rate", "horizon_years")}
    for key in _PRODUCT_JSON_KEYS:
        out[key] = values[key]
    out.update(extra)
    return out


def _product_to_row(p: dict) -> tuple:
    scalars = tuple(p.get(key) for _, key in _PRODUCT_SCALAR_KEYS)
    jsons = tuple(Jsonb(p.get(key)) for key in _PRODUCT_JSON_KEYS)
    extra = {k: v for k, v in p.items() if k not in _PRODUCT_KNOWN_KEYS}
    return scalars + jsons + (Jsonb(extra),)


def _assumption_to_row(product_id: str, a: dict) -> tuple:
    return (a["id"], product_id, a["assumption"], a["value"], a["unit"], a["source"],
            a["owner"], a["evidence"], a["confidence"], a["lastUpdated"], a.get("evidenceRef"))


def _assumption_row_to_dict(row: tuple) -> dict:
    (id_, product_id, assumption, value, unit, source, owner,
     evidence, confidence, last_updated, evidence_ref) = row
    return {"id": id_, "productId": product_id, "assumption": assumption, "value": value,
            "unit": unit, "source": source, "owner": owner, "evidence": evidence,
            "confidence": confidence, "lastUpdated": last_updated, "evidenceRef": evidence_ref}


def _benefit_to_row(product_id: str, b: dict) -> tuple:
    return (b["id"], product_id, b.get("driverId"), b["kind"], b["category"], b["label"],
            b["attribution"], b["startMonth"], b["rampMonths"], b["evidence"],
            b["evidenceStrength"], b.get("evidenceNote"), Jsonb(b["inputs"]))


def _benefit_row_to_dict(row: tuple) -> dict:
    (id_, product_id, driver_id, kind, category, label, attribution, start_month,
     ramp_months, evidence, evidence_strength, evidence_note, inputs) = row
    return {"id": id_, "kind": kind, "category": category, "driverId": driver_id, "label": label,
            "attribution": attribution, "startMonth": start_month, "rampMonths": ramp_months,
            "evidence": evidence, "evidenceStrength": evidence_strength,
            "evidenceNote": evidence_note, "inputs": inputs}


def _realisation_to_row(product_id: str, r: dict) -> tuple:
    return (product_id, r["period"], r["forecastRevenue"], r["actualRevenue"],
            r["forecastSavings"], r["actualSavings"], r["forecastProductivity"],
            r["actualProductivity"], r["forecastRisk"], r["actualRisk"],
            r["forecastAdoption"], r["actualAdoption"])


def _realisation_row_to_dict(row: tuple) -> dict:
    (product_id, period, forecast_revenue, actual_revenue, forecast_savings, actual_savings,
     forecast_productivity, actual_productivity, forecast_risk, actual_risk,
     forecast_adoption, actual_adoption) = row
    return {"period": period, "forecastRevenue": forecast_revenue, "actualRevenue": actual_revenue,
            "forecastSavings": forecast_savings, "actualSavings": actual_savings,
            "forecastProductivity": forecast_productivity, "actualProductivity": actual_productivity,
            "forecastRisk": forecast_risk, "actualRisk": actual_risk,
            "forecastAdoption": forecast_adoption, "actualAdoption": actual_adoption}


def _insert_children(cur, products: list[dict]) -> None:
    assumption_rows, benefit_rows, realisation_rows = [], [], []
    for p in products:
        pid = p["id"]
        assumption_rows += [_assumption_to_row(pid, a) for a in p.get("assumptions", [])]
        benefit_rows += [_benefit_to_row(pid, b) for b in p.get("benefits", [])]
        realisation_rows += [_realisation_to_row(pid, r) for r in p.get("realisation", [])]
    if assumption_rows:
        cur.executemany(
            f"insert into assumptions ({', '.join(ASSUMPTION_COLUMNS)}) "
            f"values ({', '.join(['%s'] * len(ASSUMPTION_COLUMNS))})", assumption_rows)
    if benefit_rows:
        cur.executemany(
            f"insert into benefits ({', '.join(BENEFIT_COLUMNS)}) "
            f"values ({', '.join(['%s'] * len(BENEFIT_COLUMNS))})", benefit_rows)
    if realisation_rows:
        cur.executemany(
            f"insert into realisation ({', '.join(REALISATION_COLUMNS)}) "
            f"values ({', '.join(['%s'] * len(REALISATION_COLUMNS))})", realisation_rows)


@st.cache_resource
def _schema_ready() -> bool:
    with psycopg.connect(st.secrets["DATABASE_URL"]) as conn:
        conn.execute(SCHEMA)
    return True


def _connect() -> psycopg.Connection:
    _schema_ready()
    return psycopg.connect(st.secrets["DATABASE_URL"])


def fetch_catalog_entries() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            f"select {', '.join(_CATALOG_COLUMNS)} from catalog_entries order by code").fetchall()
    return [_catalog_row_to_entry(r) for r in rows]


def catalog_entry_count() -> int:
    with _connect() as conn:
        return conn.execute("select count(*) from catalog_entries").fetchone()[0]


def replace_catalog_entries(entries: list[dict]) -> None:
    with _connect() as conn:
        conn.execute("truncate catalog_entries")
        with conn.cursor() as cur:
            cur.executemany(
                f"insert into catalog_entries ({', '.join(_CATALOG_COLUMNS)}) "
                f"values ({', '.join(['%s'] * len(_CATALOG_COLUMNS))})",
                [_catalog_entry_to_row(e) for e in entries])


def fetch_products() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            f"select {', '.join(_PRODUCT_COLUMNS)} from products order by updated_at desc").fetchall()
        products = [_product_row_to_dict(r) for r in rows]

        assumptions_by_product: dict[str, list[dict]] = {}
        for row in conn.execute(f"select {', '.join(ASSUMPTION_COLUMNS)} from assumptions").fetchall():
            d = _assumption_row_to_dict(row)
            assumptions_by_product.setdefault(d["productId"], []).append(d)

        benefits_by_product: dict[str, list[dict]] = {}
        for row in conn.execute(f"select {', '.join(BENEFIT_COLUMNS)} from benefits").fetchall():
            benefits_by_product.setdefault(row[1], []).append(_benefit_row_to_dict(row))

        realisation_by_product: dict[str, list[dict]] = {}
        for row in conn.execute(
                f"select {', '.join(REALISATION_COLUMNS)} from realisation order by period").fetchall():
            realisation_by_product.setdefault(row[0], []).append(_realisation_row_to_dict(row))

    for p in products:
        p["assumptions"] = assumptions_by_product.get(p["id"], [])
        p["benefits"] = benefits_by_product.get(p["id"], [])
        p["realisation"] = realisation_by_product.get(p["id"], [])
    return products


def product_count() -> int:
    with _connect() as conn:
        return conn.execute("select count(*) from products").fetchone()[0]


def replace_products(products: list[dict]) -> None:
    with _connect() as conn:
        conn.execute("truncate assumptions, benefits, realisation, products")
        with conn.cursor() as cur:
            cur.executemany(
                f"insert into products ({', '.join(_PRODUCT_COLUMNS)}) "
                f"values ({', '.join(['%s'] * len(_PRODUCT_COLUMNS))})",
                [_product_to_row(p) for p in products])
            _insert_children(cur, products)


def upsert_product(product: dict) -> None:
    pid = product["id"]
    row = _product_to_row(product)
    assignments = ", ".join(f"{col} = excluded.{col}" for col in _PRODUCT_COLUMNS if col != "id")
    with _connect() as conn:
        conn.execute(
            f"insert into products ({', '.join(_PRODUCT_COLUMNS)}) "
            f"values ({', '.join(['%s'] * len(_PRODUCT_COLUMNS))}) "
            f"on conflict (id) do update set {assignments}",
            row)
        conn.execute("delete from assumptions where product_id = %s", (pid,))
        conn.execute("delete from benefits where product_id = %s", (pid,))
        conn.execute("delete from realisation where product_id = %s", (pid,))
        with conn.cursor() as cur:
            _insert_children(cur, [product])


def delete_product(product_id: str) -> None:
    with _connect() as conn:
        conn.execute("delete from products where id = %s", (product_id,))
