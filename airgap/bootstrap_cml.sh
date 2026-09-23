#!/usr/bin/env bash
# Runs INSIDE the airgapped CML session — this is what actually starts the
# app. No network access is used anywhere in this script; everything it
# needs must already be sitting in airgap/vendor/ (see vendor.sh and
# README_AIRGAP.md).
#
# What it does, in order:
#   1. First run only: initializes a Postgres data directory and loads the
#      full data dump (data/full_dump.sql) into it.
#   2. Starts that Postgres as a background process, local to this session.
#   3. Installs the app's Python dependencies from the vendored wheels
#      (no PyPI access needed).
#   4. Starts the Streamlit app in the foreground, which is what CML expects
#      to keep running.
#
# CML-SPECIFIC THING TO VERIFY: the port Streamlit binds to at the bottom of
# this script uses $CDSW_APP_PORT, which is the port env var older Cloudera
# Data Science Workbench / CML Applications have historically used. Newer
# CML versions may use a different variable, or assign the port a different
# way — check your CML Application's own docs/settings and adjust the
# `--server.port` line below if `$CDSW_APP_PORT` isn't set in your session.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGHOME="$ROOT/airgap/vendor/postgres"
PGDATA="$ROOT/airgap/pgdata"
PGPORT=5432
PGUSER="appuser"
DBNAME="dataproducts"

if [ ! -d "$PGHOME/bin" ]; then
  echo "ERROR: $PGHOME/bin not found. Run airgap/vendor.sh on a machine with"
  echo "internet access first, then carry airgap/vendor/ in alongside this repo."
  exit 1
fi

export PATH="$PGHOME/bin:$PATH"
export LD_LIBRARY_PATH="$PGHOME/lib:${LD_LIBRARY_PATH:-}"

# ── First run: initialize Postgres and load the data ────────────────────
if [ ! -d "$PGDATA" ]; then
  echo "== First run: initializing Postgres data directory =="
  PGPASSWORD_GENERATED="$(head -c 18 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24)"
  echo "$PGPASSWORD_GENERATED" > "$ROOT/airgap/.pgpassword"

  initdb -D "$PGDATA" -U "$PGUSER" --auth=scram-sha-256 --pwfile=<(echo "$PGPASSWORD_GENERATED")

  echo "== Starting Postgres for initial load =="
  pg_ctl -D "$PGDATA" -o "-p $PGPORT -k $PGDATA" -l "$ROOT/airgap/postgres.log" -w start

  export PGPASSWORD="$PGPASSWORD_GENERATED"
  createdb -h localhost -p "$PGPORT" -U "$PGUSER" "$DBNAME"

  echo "== Loading data/full_dump.sql (all 5 tables, current live data) =="
  psql -h localhost -p "$PGPORT" -U "$PGUSER" -d "$DBNAME" -f "$ROOT/data/full_dump.sql"

  mkdir -p "$ROOT/.streamlit"
  cat > "$ROOT/.streamlit/secrets.toml" <<EOF
DATABASE_URL = "postgresql://$PGUSER:$PGPASSWORD_GENERATED@localhost:$PGPORT/$DBNAME"
EOF
  echo "== Postgres initialized. Credentials written to .streamlit/secrets.toml =="
else
  echo "== Postgres data directory already exists, starting it =="
  pg_ctl -D "$PGDATA" -o "-p $PGPORT -k $PGDATA" -l "$ROOT/airgap/postgres.log" -w start
fi

# ── Install app dependencies from vendored wheels, no network ───────────
echo "== Installing Python dependencies from airgap/vendor/wheels (offline) =="
pip install --no-index --find-links="$ROOT/airgap/vendor/wheels" -r "$ROOT/requirements.txt"

# ── Run the app ───────────────────────────────────────────────────────────
echo "== Starting Streamlit =="
cd "$ROOT"
exec streamlit run streamlit_app.py \
  --server.port "${CDSW_APP_PORT:-8501}" \
  --server.address 0.0.0.0 \
  --server.headless true
