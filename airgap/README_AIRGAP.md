# Running this app inside an airgapped CML session

This package was built to work with **zero network access from inside CML** —
no PyPI, no internal mirror, nothing. Everything the app needs is either
already in this repo, or fetched once ahead of time on a machine that *does*
have internet, then carried in as a separate file transfer.

## Important: what's verified vs. what needs your own testing

Everything about the **Postgres data and the app code itself** was built and
tested directly — the schema, the data dump, and the app all work exactly as
Damien's copy does.

**What could *not* be verified, because it depends on your specific CML
environment, which I have no access to:**
- Whether a CML session can run a second background process (Postgres)
  alongside the main app process. This is common and usually fine, but
  hasn't been tested in your actual environment.
- The exact port environment variable CML uses to expose an Application
  (`bootstrap_cml.sh` assumes `$CDSW_APP_PORT`, the historically common one
  — check your CML docs/session settings if the app doesn't come up).
- The exact Python version in your CML runtime image (`vendor.sh` has a
  placeholder — you must set it correctly before running).
- Whether the portable PostgreSQL binaries (built for generic Linux x86_64)
  run cleanly in your specific container image. They're designed to need no
  install and no root, but every container base image is slightly different.

Budget time for the first run to need some back-and-forth adjustment — this
is a solid starting point, not a guaranteed one-shot.

## Step-by-step

### 1. On a machine WITH internet access (not CML)
```bash
# Open airgap/vendor.sh first and set PYTHON_VERSION to match your CML
# session's actual Python (check inside CML with: python3 --version)
bash airgap/vendor.sh
```
This downloads Python wheels and a portable Postgres build into
`airgap/vendor/` (~300-500MB). This folder is deliberately **not** committed
to git — it's binary, large, and machine-specific.

### 2. Get everything into the airgapped environment
- The rest of this repo (code, scripts, `data/full_dump.sql`) → via git,
  same as normal (clone from wherever your GitHub is reachable from).
- The `airgap/vendor/` folder from step 1 → via whatever bulk file transfer
  your organization approves for moving files into the airgap (USB, an
  internal drop location, etc.) — **not** through git.

Once both are in place inside CML, `airgap/vendor/` should sit exactly where
it does in this repo, alongside `airgap/vendor.sh`.

### 3. Inside your CML session
```bash
bash airgap/bootstrap_cml.sh
```
First run: initializes a local Postgres, loads `data/full_dump.sql` (all 5
tables — catalog_entries, products, assumptions, benefits, realisation —
with the current live data), installs the app's Python dependencies from
the vendored wheels, and starts the app.

Every run after that: Postgres data persists in `airgap/pgdata/` (as long as
your CML session storage persists between runs — if it doesn't, you'll
re-run the full first-run flow each time, which is still correct, just
slower).

## What's deliberately excluded

The Iceberg sync script isn't in this package — that was a separate,
unfinished piece unrelated to what you're setting up here.

## If something doesn't come up

Check `airgap/postgres.log` first — that's where Postgres's own startup
output goes. Most first-run failures are one of the three "not verified"
items above (Python version mismatch, port variable, or a container
permission issue) rather than a problem with the data or app code itself.
