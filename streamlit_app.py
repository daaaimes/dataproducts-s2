"""Data Product Value — Streamlit application entry point.

A Python/Streamlit port of the React app at data-product-value.vercel.app.
The valuation engine under app/engine is a line-for-line translation of the
original TypeScript engine and is verified against it by tests/test_parity.py.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Data Product Value",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"about": "Data Product Value — quantify, prioritise and prove the business "
                         "value of data and AI investments."},
)

from app import store, theme  # noqa: E402  (must follow set_page_config)
from app.format import money  # noqa: E402
from app.ui import brand, write  # noqa: E402

store.init()
theme.inject(store.theme())

NAV = [
    ("dashboard", "Dashboard", "⌂", "views/pages/dashboard_page.py"),
    ("value", "Value a Product", "✦", "views/pages/value_page.py"),
    ("portfolio", "Portfolio", "▤", "views/pages/portfolio_page.py"),
    ("product", "Valuation", "◎", "views/pages/product_page.py"),
    ("compare", "Compare", "⇄", "views/pages/compare_page.py"),
    ("advisor", "Value Advisor", "✦", "views/pages/advisor_page.py"),
    ("realisation", "Value Realisation", "↗", "views/pages/realisation_page.py"),
    ("reports", "Reports", "▦", "views/pages/reports_page.py"),
    ("assumptions", "Assumptions", "☰", "views/pages/assumptions_page.py"),
    ("boardroom", "Boardroom Mode", "▶", "views/pages/boardroom_page.py"),
    ("settings", "Settings", "⚙", "views/pages/settings_page_view.py"),
]

# st.Page only accepts real emoji as icons; the sidebar renders its own glyphs
# in the link label instead, which keeps the original's typographic marks.
pages = {}
for key, title, _icon, path in NAV:
    is_home = key == "dashboard"
    # The default page is served at "/" — giving it its own url_path would 404.
    pages[key] = (st.Page(path, title=title, default=True) if is_home
                  else st.Page(path, title=title, url_path=key))
st.session_state["_pages"] = pages

nav = st.navigation(list(pages.values()), position="hidden")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    settings = store.settings()
    write(brand())

    for key, title, icon, _path in NAV:
        if key == "product":
            continue  # reached from the portfolio, not the nav
        if key == "boardroom":
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.page_link(pages[key], label=f"{icon}\u2003{title}")

    totals = store.totals()
    write(f'<div class="dpv-side-foot">'
          f'<div class="dpv-eyebrow" style="font-size:10.5px;letter-spacing:.07em">'
          f"Portfolio 3-year value</div>"
          f'<div class="tnum" style="margin-top:4px;font-size:19px;font-weight:600;line-height:1;'
          f'color:var(--text-primary)">{money(totals["threeYear"], settings["currency"])}</div>'
          f'<div style="margin-top:6px;font-size:11px;color:var(--text-muted)">'
          f'{totals["count"]} valued products</div></div>')

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    dark = store.theme() == "dark"
    if st.button("☀  Switch to light" if dark else "☾  Switch to dark",
                 use_container_width=True, key="side_theme"):
        store.set_settings({"theme": "light" if dark else "dark"})
        st.rerun()

nav.run()

st.markdown(
    '<p style="margin:36px 0 0;padding-top:16px;border-top:1px solid var(--hairline);'
    'font-size:11px;line-height:1.7;color:var(--text-muted)">'
    "Values shown are estimates based on user-provided assumptions and should be validated with "
    "Finance and business owners before formal investment approval. Demonstration data is "
    "fictional.</p>", unsafe_allow_html=True)
