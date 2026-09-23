# Data Product Value — airgapped CML package

This is a self-contained copy of the Data Product Value app, packaged to run
inside an airgapped CML session with its own bundled Postgres database.

**Start here: [airgap/README_AIRGAP.md](airgap/README_AIRGAP.md)** — the full
setup walkthrough, including what's been tested and what still needs
verification against your specific CML environment.

## What's in this repo

| Path | What it is |
|---|---|
| `app/`, `views/`, `streamlit_app.py` | The application itself — unchanged from the working copy. |
| `app/db.py` | All Postgres access. Reads its connection string from `.streamlit/secrets.toml`, which `airgap/bootstrap_cml.sh` generates automatically at runtime. |
| `data/full_dump.sql` | A full dump of the current live data — all 5 tables (catalog_entries, products, assumptions, benefits, realisation), loaded automatically on first run. |
| `scripts/` | The original one-time migration scripts (catalog → Postgres, schema reshaping). Kept for reference; you shouldn't need to run these directly — `full_dump.sql` already has everything they produce. |
| `airgap/vendor.sh` | Run once on a machine WITH internet, before entering the airgap. Downloads Python dependencies and a portable Postgres build. |
| `airgap/bootstrap_cml.sh` | Run inside CML. Starts Postgres, loads the data, installs dependencies, starts the app — no network access required. |
| `requirements.txt` | Python dependencies. |

## What's intentionally not included

- The Iceberg sync script — separate, unrelated, unfinished work.
- Any real database credentials — `.streamlit/secrets.toml` is generated
  fresh at runtime by `bootstrap_cml.sh`, never committed.
- `airgap/vendor/` — the downloaded Postgres binaries and Python wheels are
  large, binary, and machine-specific. They travel separately from git (see
  the airgap README for how).
