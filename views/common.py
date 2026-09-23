"""Helpers shared by the page modules."""
from __future__ import annotations

import streamlit as st

from app import store
from app.charts import CONFIG
from app.ui import esc


def goto(page: str, **params) -> None:
    """Navigate to another page, carrying deep-link state."""
    for k, v in params.items():
        st.session_state[k] = v
    st.switch_page(st.session_state["_pages"][page])


def open_product(pid: str) -> None:
    goto("product", selected_product=pid)


def chart(fig, key: str | None = None) -> None:
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config=CONFIG, key=key)


def page_header(title: str, sub: str = "", actions=None) -> None:
    if actions:
        left, right = st.columns([3, 2], vertical_alignment="bottom")
    else:
        left, right = st.container(), None
    with left:
        st.markdown(f'<h1 class="dpv-h1">{esc(title)}</h1>'
                    + (f'<p class="dpv-sub">{sub}</p>' if sub else ""),
                    unsafe_allow_html=True)
    if actions and right is not None:
        with right:
            actions()
    st.write("")


def product_picker(label: str, rows, key: str, default_id: str | None = None,
                   help: str | None = None):
    ids = [r["product"]["id"] for r in rows]
    names = {r["product"]["id"]: r["product"]["name"] for r in rows}
    index = ids.index(default_id) if default_id in ids else 0
    return st.selectbox(label, ids, index=index, key=key,
                        format_func=lambda i: names[i], help=help)


def selected_product_id(rows) -> str | None:
    pid = st.session_state.get("selected_product")
    if pid and any(r["product"]["id"] == pid for r in rows):
        return pid
    return rows[0]["product"]["id"] if rows else None


def currency() -> str:
    return store.currency()


def theme() -> str:
    return store.theme()
