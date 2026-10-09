"""Entry point for both CML and a local run.

CML: set this file as the Application's "Script". CML runs it with plain Python
and the project's runtime; it hands off to airgap/bootstrap_cml.sh, which starts
the bundled Postgres and then Streamlit on $CDSW_APP_PORT. This process stays
alive for as long as Streamlit runs, which is what CML expects of an app.

Local (VS Code / laptop):  streamlit run launch_app.py
Streamlit is already running the script in that case, so it runs the app
directly against the local Postgres in .streamlit/secrets.toml instead of
calling the bootstrap script (which needs Linux).
"""
import os
import runpy
import subprocess
import sys

try:
    ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:  # some CML kernels run scripts without __file__
    ROOT = os.environ.get("CDSW_PROJECT_ROOT", "/home/cdsw")


def _inside_streamlit() -> bool:
    """True only when `streamlit run` is executing this script. On CML the runtime
    may not even have Streamlit installed (it is vendored later), so any failure
    here means "not inside Streamlit"."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx(suppress_warning=True) is not None
    except Exception:
        return False


if _inside_streamlit():
    runpy.run_path(os.path.join(ROOT, "streamlit_app.py"), run_name="__main__")
else:
    os.chdir(ROOT)
    sys.exit(subprocess.call(["bash", os.path.join(ROOT, "airgap", "bootstrap_cml.sh")]))
