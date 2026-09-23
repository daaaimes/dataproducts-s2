"""One-off: load banking200.json into the catalog_entries table in Postgres.

Run once against a fresh database, or after banking200.json changes, or
after the catalog_entries schema changes (drops and recreates the table):

    .venv/Scripts/python.exe scripts/migrate_catalog.py
"""
from __future__ import annotations

import json
import tomllib
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parent.parent

CREATE_TABLES = """
drop table if exists catalog_entries;

create table catalog_entries (
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
    data jsonb not null,
    updated_at timestamptz not null default now()
);
"""

CATALOG_COLUMNS = ("code", "domain", "lifecycle", "problem", "datasets",
                    "outcome", "value_note", "key_assumption", "input")


def database_url() -> str:
    with open(ROOT / ".streamlit" / "secrets.toml", "rb") as f:
        return tomllib.load(f)["DATABASE_URL"]


def to_row(e: dict) -> tuple:
    return (e["code"], e["domain"], e["lifecycle"], e["problem"], e["datasets"],
            e["outcome"], e["valueNote"], e["keyAssumption"], Jsonb(e["input"]))


def main() -> None:
    entries = json.loads((ROOT / "app" / "data" / "banking200.json").read_text(encoding="utf-8"))
    print(f"Loaded {len(entries)} entries from banking200.json")

    with psycopg.connect(database_url()) as conn:
        conn.execute(CREATE_TABLES)
        with conn.cursor() as cur:
            cur.executemany(
                f"insert into catalog_entries ({', '.join(CATALOG_COLUMNS)}) "
                f"values ({', '.join(['%s'] * len(CATALOG_COLUMNS))})",
                [to_row(e) for e in entries])
        conn.commit()
        count = conn.execute("select count(*) from catalog_entries").fetchone()[0]
    print(f"catalog_entries now has {count} rows")


if __name__ == "__main__":
    main()
