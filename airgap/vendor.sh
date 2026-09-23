#!/usr/bin/env bash
# Run this ONCE on any machine with internet access — NOT inside the
# airgapped CML session, which by definition can't reach any of this.
#
# It downloads everything the app needs to run with zero network access:
#   1. Python wheels for every dependency in requirements.txt
#   2. A self-contained PostgreSQL server build (no install, no root needed)
#
# Output goes into airgap/vendor/ (gitignored — this is NOT meant to go
# through git; carry this folder into the airgap via whatever bulk file
# transfer process your environment approves — USB, an internal file drop,
# etc. It's ~300-500MB, too large and too binary for a git repo).
#
# BEFORE RUNNING — fill in these two values. Both need to match your
# actual CML session, not this machine:
set -euo pipefail

# 1. Python version your CML session runs. Check with: python3 --version
#    inside an actual CML session/terminal — this MUST match, a wheel built
#    for the wrong Python version will fail to install.
PYTHON_VERSION="3.10"

# 2. PostgreSQL version to fetch from EnterpriseDB's generic Linux binaries.
#    This URL pattern occasionally changes version numbers as new releases
#    ship — if it 404s, check https://www.enterprisedb.com/download-postgresql-binaries
#    for the current filename and update PG_VERSION below.
PG_VERSION="16.4-1"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="$ROOT/airgap/vendor"
mkdir -p "$VENDOR/wheels" "$VENDOR/postgres"

echo "== Downloading Python wheels for linux x86_64 / Python $PYTHON_VERSION =="
pip download \
  --platform manylinux2014_x86_64 \
  --python-version "$PYTHON_VERSION" \
  --implementation cp \
  --abi "cp${PYTHON_VERSION//./}" \
  --only-binary=:all: \
  -d "$VENDOR/wheels" \
  -r "$ROOT/requirements.txt"

echo "== Downloading portable PostgreSQL $PG_VERSION (Linux x86_64) =="
PG_URL="https://get.enterprisedb.com/postgresql/postgresql-${PG_VERSION}-linux-x64-binaries.tar.gz"
curl -fL "$PG_URL" -o "$VENDOR/postgres/postgres.tar.gz" \
  || { echo "Download failed — check $PG_URL is still current, see comment above PG_VERSION."; exit 1; }
tar -xzf "$VENDOR/postgres/postgres.tar.gz" -C "$VENDOR/postgres" --strip-components=1
rm "$VENDOR/postgres/postgres.tar.gz"

echo "== Done. airgap/vendor/ is ready to carry into the airgap alongside the rest of this repo. =="
du -sh "$VENDOR"
