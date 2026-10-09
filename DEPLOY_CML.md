# Deploying Data Product Value as a CML Application

The app runs inside one CML Application container: `launch_app.py` calls
`airgap/bootstrap_cml.sh`, which starts a bundled PostgreSQL 16 (data kept in
`airgap/pgdata/` in the project folder) and then Streamlit on `$CDSW_APP_PORT`,
bound to `127.0.0.1` as CML requires. No network access is needed inside CML.

## No pip needed in CML
Every Python library the app uses (about 40 packages: Streamlit, pandas,
Plotly, psycopg, numpy, pyarrow and their dependencies) is already unpacked in
`airgap/vendor/py310`, built for Linux x86_64 / Python 3.10. PostgreSQL 16 is in
`airgap/vendor/postgres`. At start-up the app loads that folder through
`PYTHONPATH`. Nothing is installed, and CML never needs internet, PyPI or pip.

## 1. Check your CML runtime is Python 3.10
In a CML Session terminal, run `python3 --version`. If you ever move to a
different Python, rebuild the bundle on a machine with internet with
`bash airgap/vendor.sh 3.11` (for example) and bring the new `py311` folder in.

## 2. Bring the package into CML
**Projects → New Project → Local Files**, and upload the package zip (about 115 MB).
If CML unpacks it into a subfolder, move its contents up to the project root, or
set the Application script to that subfolder's `launch_app.py`.

If your CML limits upload size: create the project from your Git repo for the
code, upload `airgap/vendor/` separately as a `.tgz`, and in a Session terminal
run `tar -xzf vendor.tgz -C airgap`.

Check it landed:
```bash
ls airgap/vendor        # postgres  py310
```

## 3. Create the Application
**Applications → New Application**

| Field | Value |
|---|---|
| Name | Data Product Value |
| Subdomain | e.g. `dp-value` |
| Script | `launch_app.py` |
| Runtime | Editor: Workbench (or JupyterLab) · Kernel: Python *(same version as step 1)* · Edition: Standard |
| Resource profile | 2 vCPU / 4 GiB memory, no GPU |
| Environment variables | none needed |

Click **Create Application**. The first start takes ~1 minute (creates the
database and loads `data/full_dump.sql`); later starts take ~15 seconds.
When the status shows **Running**, open the app URL.

## 4. Operating it
- **Logs**: Applications → your app → *Logs*. Postgres's own log is `airgap/postgres.log`.
- **Deploy a code change**: pull/upload the new code, then **Restart** the Application.
- **Reset the data to the shipped dump**: stop the Application, then in a Session
  terminal `rm -rf airgap/pgdata airgap/.init_complete`, then start the Application.
- **Back up the data**: stop the Application, then in a Session terminal:
  ```bash
  export PATH=$PWD/airgap/vendor/postgres/bin:$PATH LD_LIBRARY_PATH=$PWD/airgap/vendor/postgres/lib
  pg_ctl -D airgap/pgdata -o "-p 5432 -k $PWD/airgap/pgdata" -l airgap/postgres.log -w start
  PGPASSWORD=$(cat airgap/.pgpassword) pg_dump -h localhost -U appuser dataproducts > backup_$(date +%F).sql
  pg_ctl -D airgap/pgdata -m fast stop
  ```

## Rules that protect the data
- **Only one thing may run Postgres on `airgap/pgdata` at a time.** Never run
  `bootstrap_cml.sh` in a Session, or create a second Application on this
  project, while the Application is running. Different CML containers cannot
  see each other's lock, so two servers would corrupt the database.
- All users of the app share one database: a product saved by one person is
  visible to everyone.
- `airgap/.pgpassword` and `.streamlit/secrets.toml` are generated at first run
  and are git-ignored. Don't commit them.

## Troubleshooting
| Symptom | Likely cause / fix |
|---|---|
| `airgap/vendor/postgres/bin/postgres not found` | The vendor folder didn't come across; see step 2. |
| `there is no airgap/vendor/pyXYZ folder` | The Application's runtime isn't Python 3.10. Pick a Python 3.10 runtime, or run `bash airgap/vendor.sh <version>` on an internet machine and bring the new folder in. |
| `initdb: could not change permissions of directory` | The project filesystem refuses `chmod 700`; ask your CML admin (NFS export options). |
| App shows "Please wait…" forever | Check the app logs; confirm the Streamlit line says `127.0.0.1:<port>`. |
| Log floods with `inotify instance limit reached` | `.streamlit/config.toml` is missing (it sets `fileWatcherType = "none"`); re-upload it. |
| Postgres fails to start after a crash | Read `airgap/postgres.log`; a stale `postmaster.pid` is normally cleared automatically. |
