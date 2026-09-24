"""Design tokens and global CSS — a port of src/index.css.

The original app drives everything from CSS custom properties and swaps the
palette on :root[data-theme]. Streamlit cannot re-read its config at runtime,
so the same tokens are injected here and the Streamlit chrome is restyled to
sit on them. Switching theme re-injects this block with the other palette.
"""
from __future__ import annotations

import streamlit as st

LIGHT = {
    "surface-1": "#ffffff", "surface-2": "#f6f7fa", "surface-3": "#eef1f6",
    "surface-inv": "#0b1220",
    "text-primary": "#0b1220", "text-secondary": "#4b5b78", "text-muted": "#6b7b98",
    "hairline": "rgba(11, 18, 32, 0.09)", "hairline-strong": "rgba(11, 18, 32, 0.16)",
    "grid": "#e6eaf1", "axis": "#c7cedd",
    "elev-1": "0 1px 2px rgba(11,18,32,.05), 0 1px 1px rgba(11,18,32,.04)",
    "elev-2": "0 4px 16px -4px rgba(11,18,32,.10), 0 1px 2px rgba(11,18,32,.05)",
    "elev-3": "0 18px 48px -12px rgba(11,18,32,.22), 0 2px 8px rgba(11,18,32,.06)",
    "s1": "#2a78d6", "s2": "#eb6834", "s3": "#1baf7a", "s4": "#eda100",
    "s5": "#e87ba4", "s6": "#008300", "s7": "#4a3aa7", "s8": "#e34948",
    "good": "#0ca30c", "warn": "#fab219", "serious": "#ec835a", "critical": "#d03b3b",
    "good-ink": "#046b04", "warn-ink": "#8a5f00", "critical-ink": "#b02b2b",
}

DARK = {
    "surface-1": "#131a28", "surface-2": "#0d121c", "surface-3": "#1b2334",
    "surface-inv": "#ffffff",
    "text-primary": "#f4f6fa", "text-secondary": "#aab6cc", "text-muted": "#8493ad",
    "hairline": "rgba(255, 255, 255, 0.10)", "hairline-strong": "rgba(255, 255, 255, 0.18)",
    "grid": "#212a3c", "axis": "#33415c",
    "elev-1": "0 1px 2px rgba(0,0,0,.4)",
    "elev-2": "0 4px 18px -4px rgba(0,0,0,.55)",
    "elev-3": "0 20px 56px -12px rgba(0,0,0,.7)",
    "s1": "#3987e5", "s2": "#d95926", "s3": "#199e70", "s4": "#c98500",
    "s5": "#d55181", "s6": "#008300", "s7": "#9085e9", "s8": "#e66767",
    "good": "#0ca30c", "warn": "#fab219", "serious": "#ec835a", "critical": "#d03b3b",
    "good-ink": "#3ec93e", "warn-ink": "#fab219", "critical-ink": "#e86a6a",
}


def tokens(theme: str = "light"):
    return DARK if theme == "dark" else LIGHT


def color(name: str, theme: str = "light") -> str:
    """Resolve a token name (e.g. 's1', 'text-muted') to a hex/rgba value."""
    return tokens(theme).get(name, name)


def series_color(slot: str, theme: str = "light") -> str:
    return tokens(theme)[slot]


def _vars(t) -> str:
    return "\n".join(f"  --{k}: {v};" for k, v in t.items())


def inject(theme: str = "light") -> None:
    t = tokens(theme)
    scheme = "dark" if theme == "dark" else "light"
    st.markdown(f"""<style>
:root {{
{_vars(t)}
  --font-sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color-scheme: {scheme};
}}

/* ── Streamlit chrome, restyled onto the design tokens ─────────────────── */
html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: var(--surface-2) !important;
  color: var(--text-primary);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}}
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ right: 8px; }}
#MainMenu, footer, [data-testid="stStatusWidget"] {{ visibility: hidden; }}
.stAppDeployButton {{ display: none; }}
.block-container {{ padding: 1.35rem 2rem 4rem; max-width: 1480px; }}
[data-testid="stSidebar"] {{
  background: var(--surface-1) !important;
  border-right: 1px solid var(--hairline);
  width: 256px !important;
}}
[data-testid="stSidebar"] > div {{ padding-top: .6rem; }}
[data-testid="stSidebarCollapseButton"] button {{ color: var(--text-muted); }}
[data-testid="stSidebarNav"] {{ display: none; }}
section[data-testid="stSidebar"] .block-container {{ padding: 0; }}

h1, h2, h3, h4 {{ letter-spacing: -0.021em; color: var(--text-primary); font-family: var(--font-sans); }}
p, span, div, label, li, td, th {{ font-family: var(--font-sans); }}
a {{ color: var(--s1); }}
hr {{ border-color: var(--hairline); }}
::selection {{ background: color-mix(in srgb, var(--s1) 24%, transparent); }}
:focus-visible {{ outline: 2px solid var(--s1); outline-offset: 2px; border-radius: 6px; }}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{
  background: var(--hairline-strong); border-radius: 8px;
  border: 3px solid transparent; background-clip: content-box;
}}
::-webkit-scrollbar-track {{ background: transparent; }}

/* Widgets */
.stButton > button, .stDownloadButton > button, .stLinkButton > a {{
  border-radius: 10px; font-weight: 500; font-size: 13.5px; min-height: 38px;
  background: var(--surface-1); color: var(--text-primary);
  border: 1px solid var(--hairline-strong); box-shadow: none;
  transition: all .15s ease; white-space: nowrap;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{
  border-color: var(--s1); color: var(--s1);
}}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
  background: var(--s1); color: #fff; border-color: var(--s1);
}}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.1); color: #fff; }}
.stButton > button:focus:not(:active) {{ color: var(--s1); }}
.stButton > button[kind="primary"]:focus:not(:active) {{ color: #fff; }}

[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"],
.stTextArea textarea, .stNumberInput input, .stTextInput input {{
  background: var(--surface-1) !important;
  border-color: var(--hairline-strong) !important;
  color: var(--text-primary) !important;
  border-radius: 10px !important;
}}
[data-baseweb="popover"] li, [data-baseweb="menu"] {{
  background: var(--surface-1) !important; color: var(--text-primary) !important;
}}
/* Newer Streamlit builds render selects and text fields through
   react-aria-components internals rather than BaseWeb, so the rule above
   never matches them — they were falling back to Streamlit's own native
   theme, which config.toml locks to light regardless of our own toggle. */
[data-testid="stSelectbox"] [class*="react-aria-"],
[data-testid="stMultiSelect"] [class*="react-aria-"],
[data-testid="stTextInput"] [class*="react-aria-"],
[data-testid="stNumberInput"] [class*="react-aria-"],
[data-testid="stTextArea"] [class*="react-aria-"] {{
  background: var(--surface-1) !important;
  color: var(--text-primary) !important;
  border-color: var(--hairline-strong) !important;
}}
input::placeholder, textarea::placeholder {{
  color: var(--text-muted) !important; opacity: 1 !important;
}}
[data-baseweb="tag"] {{ background: var(--s1) !important; }}
.stSlider [data-baseweb="slider"] div[role="slider"] {{ background: var(--surface-1); }}
.stSlider [data-testid="stTickBar"], .stSlider [data-testid="stTickBarMin"],
.stSlider [data-testid="stTickBarMax"] {{ display: none; }}
.stSlider [data-baseweb="slider"] > div > div {{ background: var(--s1) !important; }}
[data-testid="stWidgetLabel"] p {{
  font-size: 12.5px !important; font-weight: 500; color: var(--text-secondary);
}}
[data-testid="stMetricValue"] {{ color: var(--text-primary); font-variant-numeric: tabular-nums; }}
[data-testid="stExpander"] {{
  border: 1px solid var(--hairline); border-radius: 14px; background: var(--surface-1);
}}
[data-testid="stExpander"] summary {{ font-size: 13px; color: var(--text-primary); }}
[data-testid="stExpander"] summary:hover {{ color: var(--s1); }}
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--hairline); }}
.stTabs [data-baseweb="tab"] {{
  height: 40px; font-size: 13.5px; font-weight: 500; color: var(--text-muted);
  border-radius: 9px 9px 0 0; padding: 0 14px;
}}
.stTabs [aria-selected="true"] {{ color: var(--text-primary) !important; background: var(--surface-3); }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--s1); }}
[data-testid="stDialog"] > div {{
  background: var(--surface-1); border-radius: 16px; box-shadow: var(--elev-3);
}}
[data-testid="stCheckbox"] p, [data-testid="stRadio"] label p {{ font-size: 13px; }}
[data-testid="stToast"] {{ background: var(--surface-inv); color: var(--surface-1); }}

/* Dataframe */
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
[data-testid="stDataFrame"] * {{ font-variant-numeric: tabular-nums; }}

/* ── App primitives (ported from index.css utilities) ──────────────────── */
.dpv-card {{
  background: var(--surface-1); border-radius: 16px;
  box-shadow: inset 0 0 0 1px var(--hairline), var(--elev-1);
  padding: 20px 22px; margin-bottom: 6px;
}}
.dpv-card.flush {{ padding: 0; overflow: hidden; }}
.txt-1 {{ color: var(--text-primary); }}
.txt-2 {{ color: var(--text-secondary); }}
.txt-3 {{ color: var(--text-muted); }}
.tnum {{ font-variant-numeric: tabular-nums; }}
.stApp h1.dpv-h1, .stApp .dpv-h1 {{
  font-size: 24px; font-weight: 600; letter-spacing: -0.025em; line-height: 1.2;
  color: var(--text-primary); margin: 0; padding: 0;
}}
.stApp h2.dpv-h2, .stApp .dpv-h2 {{
  font-size: 19px; font-weight: 600; letter-spacing: -0.02em; line-height: 1.25;
  color: var(--text-primary); margin: 0; padding: 0;
}}
.stApp h3.dpv-h3, .stApp .dpv-h3 {{
  font-size: 15px; font-weight: 600; line-height: 1.35;
  color: var(--text-primary); margin: 0 0 2px; padding: 0;
}}
.stApp .dpv-paper h1 {{ padding: 0; }}
.stApp .dpv-stage h1, .stApp .dpv-stage h2 {{ padding: 0; }}
.stApp .dpv-hero h1 {{ padding: 0; }}
.dpv-sub {{ font-size: 13px; line-height: 1.6; color: var(--text-muted); margin: 6px 0 0; }}
.dpv-eyebrow {{
  font-size: 11px; font-weight: 500; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--text-muted);
}}
.dpv-hero {{
  border-radius: 22px; padding: 40px 48px; box-shadow: inset 0 0 0 1px var(--hairline);
  background:
    radial-gradient(1200px 420px at 10% -10%, color-mix(in srgb, var(--s1) 18%, transparent), transparent 65%),
    radial-gradient(900px 380px at 88% 0%, color-mix(in srgb, var(--s3) 14%, transparent), transparent 60%),
    linear-gradient(180deg, var(--surface-1), var(--surface-1));
}}
.dpv-badge {{
  display: inline-flex; align-items: center; gap: 6px; border-radius: 999px;
  padding: 3px 10px; font-size: 11.5px; font-weight: 500; line-height: 1.5; white-space: nowrap;
}}
.dpv-badge .dot {{ width: 6px; height: 6px; border-radius: 999px; }}
.b-neutral {{ background: color-mix(in srgb, var(--text-muted) 12%, transparent); color: var(--text-secondary); }}
.b-good {{ background: color-mix(in srgb, var(--good) 14%, transparent); color: color-mix(in srgb, var(--good) 78%, var(--text-primary)); }}
.b-warn {{ background: color-mix(in srgb, var(--warn) 20%, transparent); color: color-mix(in srgb, var(--warn-ink) 82%, var(--text-primary)); }}
.b-critical {{ background: color-mix(in srgb, var(--critical) 14%, transparent); color: color-mix(in srgb, var(--critical) 82%, var(--text-primary)); }}
.b-info {{ background: color-mix(in srgb, var(--s1) 13%, transparent); color: color-mix(in srgb, var(--s1) 82%, var(--text-primary)); }}
.b-accent {{ background: color-mix(in srgb, var(--s7) 13%, transparent); color: color-mix(in srgb, var(--s7) 82%, var(--text-primary)); }}
.dpv-meter {{ height: 7px; border-radius: 999px; background: var(--surface-3); overflow: hidden; }}
.dpv-meter > i {{ display: block; height: 100%; border-radius: 999px; }}
.dpv-kpi-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 1px; background: var(--hairline); border-radius: 16px; overflow: hidden;
  box-shadow: inset 0 0 0 1px var(--hairline);
}}
.dpv-kpi {{ background: var(--surface-1); padding: 18px 20px; }}
.dpv-kpi .v {{
  font-size: 28px; font-weight: 600; letter-spacing: -0.025em; line-height: 1.05;
  color: var(--text-primary); margin-top: 8px; font-variant-numeric: tabular-nums;
}}
.dpv-kpi.sm .v {{ font-size: 21px; }}
.dpv-kpi .s {{ font-size: 12px; color: var(--text-muted); margin-top: 7px; }}
.dpv-table {{ width: 100%; border-collapse: separate; border-spacing: 0; }}
.dpv-table thead th {{
  background: var(--surface-1); font-size: 11px; font-weight: 600; letter-spacing: .055em;
  text-transform: uppercase; color: var(--text-muted); text-align: left;
  padding: 10px 14px; white-space: nowrap; border-bottom: 1px solid var(--hairline);
}}
.dpv-table tbody td {{
  padding: 11px 14px; font-size: 13px; border-bottom: 1px solid var(--hairline);
  vertical-align: middle; color: var(--text-secondary);
}}
.dpv-table tbody tr:hover {{ background: color-mix(in srgb, var(--s1) 4%, transparent); }}
.dpv-table .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.dpv-table .strong {{ color: var(--text-primary); font-weight: 600; }}
.dpv-cmp .dpv-table th:first-child, .dpv-cmp .dpv-table td:first-child {{
  min-width: 210px; color: var(--text-secondary);
}}
.dpv-scroll {{ overflow-x: auto; }}
.dpv-note {{
  border-radius: 12px; padding: 13px 15px; display: flex; gap: 11px;
  background: var(--surface-3); font-size: 12.5px; line-height: 1.6; color: var(--text-secondary);
}}
.dpv-note.severe {{ background: color-mix(in srgb, var(--critical) 9%, transparent); }}
.dpv-note.warn {{ background: color-mix(in srgb, var(--warn) 12%, transparent); }}
.dpv-tile {{ border-radius: 12px; padding: 14px 16px; background: var(--surface-3); }}
.dpv-swatch {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
.dpv-rule {{ height: 1px; background: var(--hairline); margin: 18px 0; }}

/* Sidebar identity block */
.dpv-brand {{
  display: flex; align-items: center; gap: 11px; padding: 6px 6px 16px;
  text-decoration: none !important; cursor: pointer; border-radius: 10px;
  margin: -2px -2px 0; transition: background .15s ease;
}}
.dpv-brand:hover {{ background: color-mix(in srgb, var(--s1) 6%, transparent); }}
.dpv-brand .mark {{
  width: 36px; height: 36px; border-radius: 10px; flex: none;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(155deg, var(--surface-inv) 0%, color-mix(in srgb, var(--surface-inv) 82%, var(--s1) 30%) 100%);
  box-shadow: 0 1px 2px color-mix(in srgb, var(--surface-inv) 35%, transparent);
}}
.dpv-brand .name {{
  font-size: 16px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.15;
  color: var(--text-primary);
}}
/* Streamlit dims inactive page links; the original keeps them legible. */
[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
  border-radius: 10px; padding: 7px 11px; font-size: 13px; font-weight: 500;
  opacity: 1 !important; transition: background .15s ease, color .15s ease;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a,
[data-testid="stSidebar"] [data-testid="stPageLink"] a span,
[data-testid="stSidebar"] [data-testid="stPageLink"] a p {{
  color: var(--text-secondary) !important; font-size: 13px; opacity: 1 !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{ background: var(--surface-3); }}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover,
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover span,
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p {{
  color: var(--text-primary) !important;
}}
.dpv-side-foot {{
  border-top: 1px solid var(--hairline); margin-top: 10px; padding: 14px 6px 4px;
}}

/* Boardroom */
.dpv-stage {{
  border-radius: 22px; padding: 54px 56px; min-height: 460px;
  background:
    radial-gradient(1100px 620px at 12% -8%, color-mix(in srgb, var(--s1) 22%, transparent), transparent 62%),
    radial-gradient(900px 520px at 92% 12%, color-mix(in srgb, var(--s7) 16%, transparent), transparent 60%),
    radial-gradient(800px 480px at 60% 108%, color-mix(in srgb, var(--s3) 12%, transparent), transparent 62%),
    var(--surface-2);
  box-shadow: inset 0 0 0 1px var(--hairline);
}}
.dpv-stage .eyebrow {{
  font-size: 13px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.2em; color: var(--s1);
}}
.dpv-stage h1 {{
  font-size: 62px; font-weight: 600; line-height: 1; letter-spacing: -0.04em; margin: 20px 0 0;
}}
.dpv-stage .lede {{
  font-size: 23px; font-weight: 300; line-height: 1.35; letter-spacing: -0.015em;
  color: var(--text-secondary); margin-top: 26px; max-width: 46em;
}}
.dpv-stage .huge {{
  font-size: 104px; font-weight: 600; line-height: .9; letter-spacing: -0.05em;
  color: var(--text-primary); font-variant-numeric: tabular-nums; margin-top: 14px;
}}

/* Report paper */
.dpv-paper {{ background: var(--surface-1); border-radius: 18px; padding: 44px 56px;
  box-shadow: inset 0 0 0 1px var(--hairline), var(--elev-1); }}
.dpv-paper h2 {{ font-size: 16px; font-weight: 600; letter-spacing: -0.015em; margin: 30px 0 10px; }}
.dpv-paper h2 .n {{ font-size: 12px; color: var(--s1); margin-right: 9px; font-variant-numeric: tabular-nums; }}
.dpv-paper p, .dpv-paper li {{ font-size: 13.5px; line-height: 1.65; color: var(--text-secondary); }}
.dpv-paper strong {{ color: var(--text-primary); font-weight: 600; }}

@media (max-width: 900px) {{
  .block-container {{ padding: 1rem 1rem 3rem; }}
  .dpv-hero {{ padding: 28px 24px; }}
  .dpv-paper {{ padding: 26px 22px; }}
  .dpv-stage {{ padding: 30px 26px; }}
  .dpv-stage h1 {{ font-size: 38px; }}
  .dpv-stage .huge {{ font-size: 54px; }}
}}
</style>""", unsafe_allow_html=True)
