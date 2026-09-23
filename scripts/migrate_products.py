"""One-off: convert the products table from a single JSONB blob per row to
real columns per known field (see app/db.py for the column layout and why).

Reads whatever is currently in products (old schema: id, data jsonb,
updated_at), converts each row's data dict, then drops and recreates the
table with the new schema and reinserts — so any live edits already in the
table are preserved, not just the seeded catalogue.

Run once, after the products schema in app/db.py changes:

    .venv/Scripts/python.exe scripts/migrate_products.py
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from app.db import SCHEMA, _PRODUCT_COLUMNS, _product_to_row

ROOT = Path(__file__).resolve().parent.parent


def database_url() -> str:
    with open(ROOT / ".streamlit" / "secrets.toml", "rb") as f:
        return tomllib.load(f)["DATABASE_URL"]


def main() -> None:
    with psycopg.connect(database_url()) as conn:
        existing = conn.execute("select id, data from products").fetchall()
        products = [data for _id, data in existing]
        print(f"Read {len(products)} existing products (old schema)")

        conn.execute("drop table products")
        conn.execute(SCHEMA)  # recreates catalog_entries (if exists) + products (new schema)

        with conn.cursor() as cur:
            cur.executemany(
                f"insert into products ({', '.join(_PRODUCT_COLUMNS)}) "
                f"values ({', '.join(['%s'] * len(_PRODUCT_COLUMNS))})",
                [_product_to_row(p) for p in products])
        conn.commit()
        count = conn.execute("select count(*) from products").fetchone()[0]
    print(f"products now has {count} rows under the new column schema")


if __name__ == "__main__":
    main()
