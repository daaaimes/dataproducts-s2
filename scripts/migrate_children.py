"""One-off: split products.benefits / .assumptions / .realisation out of
their JSONB-array columns into real child tables (see app/db.py for the
column layout and why).

Reads the arrays as they currently sit on each products row, drops those
three columns, creates the three child tables, and reinserts every entry
as its own row — so any live edits already in the table are preserved.

Run once, after the schema in app/db.py changes to child tables:

    .venv/Scripts/python.exe scripts/migrate_children.py
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from app.db import (ASSUMPTION_COLUMNS, BENEFIT_COLUMNS, REALISATION_COLUMNS, SCHEMA,
                    _assumption_to_row, _benefit_to_row, _realisation_to_row)

ROOT = Path(__file__).resolve().parent.parent


def database_url() -> str:
    with open(ROOT / ".streamlit" / "secrets.toml", "rb") as f:
        return tomllib.load(f)["DATABASE_URL"]


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        rows = conn.execute("select id, benefits, assumptions, realisation from products").fetchall()
        print(f"Read nested arrays from {len(rows)} products")

        conn.execute("alter table products "
                     "drop column if exists benefits, "
                     "drop column if exists assumptions, "
                     "drop column if exists realisation")
        conn.execute(SCHEMA)  # creates the three new child tables (products already exists)

        assumption_rows, benefit_rows, realisation_rows = [], [], []
        for pid, benefits, assumptions, realisation in rows:
            assumption_rows += [_assumption_to_row(pid, a) for a in assumptions]
            benefit_rows += [_benefit_to_row(pid, b) for b in benefits]
            realisation_rows += [_realisation_to_row(pid, r) for r in realisation]

        with conn.cursor() as cur:
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
        conn.commit()

        counts = {t: conn.execute(f"select count(*) from {t}").fetchone()[0]
                 for t in ("products", "assumptions", "benefits", "realisation")}
    print(counts)


if __name__ == "__main__":
    main()
