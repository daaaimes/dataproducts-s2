#!/usr/bin/env bash
# Runs INSIDE the airgapped CML session/application — this is what actually
# starts the app. No network access is used anywhere in this script; everything
# it needs must already be sitting in airgap/vendor/ (see vendor.sh and
# README_AIRGAP.md).
#
# Normally started by launch_app.py (the CML Application script). It can also be
# run by hand from a CML Session terminal for debugging — but NEVER while the
# Application is running: both would start a Postgres on the same data folder
# from different containers, which corrupts it. Stop the Application first.
#
# What it does, in order:
#   1. First run only: initializes a Postgres data directory and loads the
#      full data dump (data/full_dump.sql) into it. If that fails part-way, the
#      next run starts the first-run setup again from scratch.
#   2. Starts that Postgres as a background process, local to this container.
#   3. Points Python at the pre-unpacked libraries in airgap/vendor/py<VER> (no pip).
#   4. Starts Streamlit in the foreground on $CDSW_APP_PORT, which is what a
#      CML Application expects to keep running.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PGHOME="$ROOT/airgap/vendor/postgres"
PGDATA="$ROOT/airgap/pgdata"
PGPORT="${PGPORT:-5432}"
PGUSER="appuser"
DBNAME="dataproducts"
PWFILE="$ROOT/airgap/.pgpassword"
DONE_MARKER="$ROOT/airgap/.init_complete"
PGLOG="$ROOT/airgap/postgres.log"

# Uploading/unzipping through CML can drop the executable bit; restore it.
chmod u+x "$PGHOME"/bin/* 2>/dev/null || true

if [ ! -x "$PGHOME/bin/postgres" ]; then
  echo "ERROR: $PGHOME/bin/postgres not found. Run airgap/vendor.sh on a machine with"
  echo "internet access first, then carry airgap/vendor/ in alongside this repo."
  exit 1
fi

export PATH="$PGHOME/bin:$PATH"
export LD_LIBRARY_PATH="$PGHOME/lib:${LD_LIBRARY_PATH:-}"

start_pg() {
  pg_ctl -D "$PGDATA" -o "-p $PGPORT -k $PGDATA -c listen_addresses=localhost" \
         -l "$PGLOG" -w -t 120 start
}

# ── First run (or a previous first run that didn't finish) ───────────────
if [ ! -f "$DONE_MARKER" ]; then
  echo "== First run: initializing Postgres data directory =="
  pg_ctl -D "$PGDATA" -m fast stop >/dev/null 2>&1 || true
  rm -rf "$PGDATA"

  PGPASSWORD_GENERATED="$(head -c 48 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24)"
  ( umask 077; printf '%s\n' "$PGPASSWORD_GENERATED" > "$PWFILE" )

  initdb -D "$PGDATA" -U "$PGUSER" --auth=scram-sha-256 --pwfile="$PWFILE" -E UTF8

  echo "== Starting Postgres for initial load =="
  start_pg

  export PGPASSWORD="$PGPASSWORD_GENERATED"
  createdb -h localhost -p "$PGPORT" -U "$PGUSER" "$DBNAME"

  # The dump was taken with pg_dump 18; drop the three lines older servers
  # reject (\restrict/\unrestrict and SET transaction_timeout), then load with
  # ON_ERROR_STOP so any *real* error fails loudly instead of being skipped.
  echo "== Loading data/full_dump.sql (all 5 tables) =="
  grep -vE '^\\(un)?restrict |^SET transaction_timeout' "$ROOT/data/full_dump.sql" \
    | psql -q -v ON_ERROR_STOP=1 -h localhost -p "$PGPORT" -U "$PGUSER" -d "$DBNAME" -f -

  touch "$DONE_MARKER"
  echo "== Postgres initialized =="
else
  echo "== Postgres data directory already initialized, starting it =="
  start_pg
fi

# Always (re)write the app's connection string from the saved password, so a
# lost or stale secrets.toml can't stop the app.
mkdir -p "$ROOT/.streamlit"
( umask 077
  printf 'DATABASE_URL = "postgresql://%s:%s@localhost:%s/%s"\n' \
    "$PGUSER" "$(cat "$PWFILE")" "$PGPORT" "$DBNAME" > "$ROOT/.streamlit/secrets.toml" )

# ── Use the pre-unpacked Python libraries — no pip, nothing installed ────
PYTAG="$(python3 -c 'import sys; print(f"{sys.version_info[0]}{sys.version_info[1]}")')"
PYLIB="$ROOT/airgap/vendor/py$PYTAG"
if [ ! -d "$PYLIB" ]; then
  echo "ERROR: this CML runtime runs Python $(python3 -V 2>&1 | cut -d' ' -f2), but there is no"
  echo "airgap/vendor/py$PYTAG folder. Available: $(ls -d "$ROOT"/airgap/vendor/py* 2>/dev/null | xargs -n1 basename | tr '\n' ' ')"
  echo "Either pick the matching Python runtime for the Application, or rebuild with:"
  echo "  bash airgap/vendor.sh <that version>   (on a machine with internet)"
  exit 1
fi
# Put ours first so they win over any older copies preinstalled in the runtime.
export PYTHONPATH="$PYLIB${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONNOUSERSITE=1
echo "== Using Python libraries from airgap/vendor/py$PYTAG =="

# ── Run the app ───────────────────────────────────────────────────────────
if [ -z "${CDSW_APP_PORT:-}" ]; then
  echo "WARNING: CDSW_APP_PORT is not set (not running as a CML Application?). Using 8501."
fi
echo "== Starting Streamlit on port ${CDSW_APP_PORT:-8501} =="
cd "$ROOT"
exec python3 -m streamlit run streamlit_app.py \
  --server.port "${CDSW_APP_PORT:-8501}" \
  --server.address 127.0.0.1 \
  --server.headless true \
  --server.fileWatcherType none \
  --global.developmentMode false
