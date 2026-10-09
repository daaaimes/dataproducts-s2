#!/usr/bin/env bash
# Run this ONCE on any machine with internet access — NOT inside CML.
# Needs: bash, python3 + pip, unzip. (It installs the 'uv' tool with pip if missing.) Works on Linux or macOS (it always fetches
# Linux x86_64 builds, whatever machine it runs on).
#
# It builds everything the app needs so that CML never runs pip:
#   airgap/vendor/py<VER>/   every Python library, already unpacked. The app
#                            loads it through PYTHONPATH; nothing is installed.
#   airgap/vendor/postgres/  a self-contained PostgreSQL 16 server (no root).
#
# Usage:  bash airgap/vendor.sh 3.10          (your CML runtime's Python)
#         bash airgap/vendor.sh 3.10 3.11     (several, if unsure)
set -euo pipefail

VERSIONS=("$@")
if [ ${#VERSIONS[@]} -eq 0 ]; then
  echo "Usage: bash airgap/vendor.sh <python-version> [...]   e.g. 3.10"
  echo "Find it in a CML session terminal with: python3 --version"
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR="$ROOT/airgap/vendor"
mkdir -p "$VENDOR"
# uv resolves dependencies for the *target* Python (pip would use this
# machine's Python and silently miss version-specific dependencies).
command -v uv >/dev/null 2>&1 || python3 -m pip install --quiet --user uv
UV="$(command -v uv || echo "$(python3 -m site --user-base)/bin/uv")"

for V in "${VERSIONS[@]}"; do
  TAG="${V//./}"
  DEST="$VENDOR/py$TAG"
  echo "== Unpacking Python libraries for Python $V into airgap/vendor/py$TAG =="
  rm -rf "$DEST"
  # x86_64-manylinux_2_17 = runs on any Linux with glibc 2.17+, i.e. every CML runtime.
  "$UV" pip install --quiet --link-mode copy --target "$DEST" --only-binary :all: \
    --python-platform x86_64-manylinux_2_17 --python-version "$V" \
    -r "$ROOT/requirements.txt"
  rm -rf "$DEST/bin"            # console scripts point at this machine's Python
  # Drop what is never loaded at runtime: C headers, test suites, notebook extras.
  rm -rf "$DEST/share" "$DEST/pyarrow/include" "$DEST/pyarrow/tests" "$DEST/pyarrow/src" \
         "$DEST/pandas/tests"
  find "$DEST" -type d -name tests -path "*/numpy/*" -prune -exec rm -rf {} +
  find "$DEST" \( -name "*.pxd" -o -name "*.pyx" -o -name "*.h" -o -name "*.hpp" -o -name "*.pyi" \) -delete
done

# PostgreSQL: EDB no longer publishes Linux tarballs for any release after 10,
# so we take the relocatable PostgreSQL 16 build that ships inside the
# "pgserver" wheel on PyPI and unpack just the server out of it.
echo "== Unpacking portable PostgreSQL 16 into airgap/vendor/postgres =="
TMP="$(mktemp -d)"
pip download --quiet --no-deps --platform manylinux2014_x86_64 --python-version 3.10 \
  --implementation cp --abi cp310 --only-binary=:all: -d "$TMP" "pgserver==0.1.4"
unzip -q "$TMP"/pgserver-*.whl -d "$TMP/x"
rm -rf "$VENDOR/postgres"
mv "$TMP/x/pgserver/pginstall" "$VENDOR/postgres"
cp "$TMP"/x/pgserver.libs/* "$VENDOR/postgres/lib/"
rm -rf "$TMP" "$VENDOR/postgres/include"

echo "== Done. Carry airgap/vendor/ into CML alongside the rest of this repo. =="
du -sh "$VENDOR"/*
