"""HTML primitives — ports of the components in src/components/ui.

Streamlit has no component model, so the original Card / Badge / Meter / KPI
pieces are rendered as small HTML fragments against the same design tokens.
Everything here returns a string so fragments can be composed before one
st.markdown call, which keeps the DOM (and the reruns) cheap.
"""
from __future__ import annotations

import html

import streamlit as st

from .format import money, num, pct
from .theme import color

BADGE_TONES = {"neutral", "good", "warn", "critical", "info", "accent"}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


_WS = __import__("re").compile(r"\n\s*")


def write(*fragments: str) -> None:
    """Render HTML fragments.

    Newlines and their following indentation are collapsed first: Streamlit runs
    the string through a markdown parser, which would treat an indented line as
    a code block and dump raw tags onto the page.
    """
    st.markdown(_WS.sub(" ", "".join(fragments)), unsafe_allow_html=True)


def card(inner: str, flush: bool = False, style: str = "") -> str:
    cls = "dpv-card flush" if flush else "dpv-card"
    return f'<div class="{cls}" style="{style}">{inner}</div>'


def h1(text: str, sub: str = "") -> str:
    out = f'<h1 class="dpv-h1">{esc(text)}</h1>'
    if sub:
        out += f'<p class="dpv-sub">{sub}</p>'
    return out


def h2(text: str, sub: str = "") -> str:
    out = f'<h2 class="dpv-h2">{esc(text)}</h2>'
    if sub:
        out += f'<p class="dpv-sub">{sub}</p>'
    return out


def h3(text: str, sub: str = "") -> str:
    out = f'<h3 class="dpv-h3">{esc(text)}</h3>'
    if sub:
        out += f'<p class="dpv-sub">{sub}</p>'
    return out


def badge(text: str, tone: str = "neutral", dot: bool = False) -> str:
    tone = tone if tone in BADGE_TONES else "neutral"
    d = '<span class="dot" style="background:currentColor;opacity:.85"></span>' if dot else ""
    return f'<span class="dpv-badge b-{tone}">{d}{esc(text)}</span>'


def band_tone(band: str) -> str:
    return {"Invest Now": "good", "Accelerate": "info",
            "Validate": "warn", "Reassess": "critical"}.get(band, "neutral")


def lifecycle_tone(stage: str) -> str:
    if stage in ("Production", "Scale", "Optimise"):
        return "good"
    return "info" if stage == "Pilot" else "neutral"


def evidence_tone(evidence: str) -> str:
    if evidence == "Actual":
        return "good"
    return "info" if evidence in ("Pilot", "Benchmark") else "warn"


def meter(value: float, maximum: float, colour: str, height: int = 7) -> str:
    w = 0 if maximum <= 0 else max(0.0, min(1.0, value / maximum)) * 100
    return (f'<div class="dpv-meter" style="height:{height}px">'
            f'<i style="width:{w:.2f}%;background:{colour}"></i></div>')


def swatch(colour: str) -> str:
    return f'<span class="dpv-swatch" style="background:{colour}"></span>'


def kpi(label: str, value: str, sub: str = "", small: bool = False) -> str:
    cls = "dpv-kpi sm" if small else "dpv-kpi"
    sub_html = f'<div class="s">{sub}</div>' if sub else ""
    return (f'<div class="{cls}"><div class="dpv-eyebrow">{esc(label)}</div>'
            f'<div class="v">{esc(value)}</div>{sub_html}</div>')


def kpi_grid(items: str) -> str:
    return f'<div class="dpv-kpi-grid">{items}</div>'


def rule() -> str:
    return '<div class="dpv-rule"></div>'


def note(body: str, tone: str = "", icon: str = "") -> str:
    cls = f"dpv-note {tone}".strip()
    ic = f'<span style="flex:none">{icon}</span>' if icon else ""
    return f'<div class="{cls}">{ic}<div>{body}</div></div>'


def tile(inner: str) -> str:
    return f'<div class="dpv-tile">{inner}</div>'


def key_value(pairs, dense: bool = True) -> str:
    """A label/value list — the KeyValue component."""
    rows = []
    for label, value, *rest in pairs:
        muted = bool(rest and rest[0])
        colr = "var(--text-muted)" if muted else "var(--text-primary)"
        rows.append(
            f'<div style="display:flex;align-items:baseline;justify-content:space-between;'
            f'gap:12px;padding:{"7px" if dense else "10px"} 0;border-bottom:1px solid var(--hairline)">'
            f'<span style="font-size:12.5px;color:var(--text-muted)">{esc(label)}</span>'
            f'<span class="tnum" style="font-size:13px;font-weight:600;color:{colr}">{esc(value)}</span>'
            f"</div>")
    return "".join(rows)


def table(headers, body_rows: str, min_width: int = 0) -> str:
    """headers: list of (label, is_numeric)."""
    head = "".join(f'<th class="{"num" if numeric else ""}">{esc(label)}</th>'
                   for label, numeric in headers)
    style = f' style="min-width:{min_width}px"' if min_width else ""
    return (f'<div class="dpv-scroll"><table class="dpv-table"{style}>'
            f"<thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>")


def stars(value: int, size: int = 11) -> str:
    full = "★" * int(value)
    empty = "☆" * max(0, 5 - int(value))
    return (f'<span style="font-size:{size}px;letter-spacing:1px;color:var(--s4)">{full}'
            f'<span style="color:var(--text-muted);opacity:.5">{empty}</span></span>')


def gauge(value: int, label: str, sublabel: str, colour: str, size: int = 148) -> str:
    """Semi-circular priority gauge, drawn as a conic gradient ring."""
    frac = max(0.0, min(1.0, value / 100))
    return f"""
<div style="display:flex;flex-direction:column;align-items:center;gap:6px">
  <div style="width:{size}px;height:{size}px;border-radius:50%;
       background:conic-gradient({colour} {frac * 360:.1f}deg, var(--surface-3) 0);
       display:flex;align-items:center;justify-content:center">
    <div style="width:{size - 26}px;height:{size - 26}px;border-radius:50%;background:var(--surface-1);
         display:flex;flex-direction:column;align-items:center;justify-content:center">
      <div class="tnum" style="font-size:34px;font-weight:600;letter-spacing:-0.03em;
           color:var(--text-primary);line-height:1">{value}</div>
      <div style="font-size:11.5px;color:var(--text-muted);margin-top:2px">{esc(sublabel)}</div>
    </div>
  </div>
  <div style="font-size:13px;font-weight:600;color:{colour}">{esc(label)}</div>
</div>"""


def category_row(label: str, value: float, maximum: float, colour: str,
                 currency: str, blurb: str = "", share: float | None = None) -> str:
    share_html = (f'<span style="font-weight:400;color:var(--text-muted)"> · {pct(share)}</span>'
                  if share is not None else "")
    blurb_html = (f'<p style="margin:6px 0 0;font-size:11px;line-height:1.5;color:var(--text-muted)">'
                  f"{esc(blurb)}</p>" if blurb else "")
    return f"""
<div style="margin-bottom:14px">
  <div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:6px">
    <span style="display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--text-secondary)">
      {swatch(colour)}{esc(label)}</span>
    <span class="tnum" style="font-size:12.5px;font-weight:600;color:var(--text-primary)">
      {esc(money(value, currency))}{share_html}</span>
  </div>
  {meter(value, maximum, colour)}
  {blurb_html}
</div>"""


def empty_state(title: str, body: str = "", icon: str = "◍") -> str:
    return f"""
<div style="text-align:center;padding:54px 20px">
  <div style="font-size:22px;color:var(--text-muted)">{icon}</div>
  <div style="margin-top:10px;font-size:15px;font-weight:600;color:var(--text-primary)">{esc(title)}</div>
  <p style="margin:8px auto 0;max-width:460px;font-size:12.5px;line-height:1.65;color:var(--text-muted)">
    {esc(body)}</p>
</div>"""


def brand() -> str:
    mark = f"""<svg width="19" height="19" viewBox="0 0 64 64" aria-hidden="true">
      <rect x="8" y="32" width="11" height="24" rx="4" fill="{color('s1')}"/>
      <rect x="26.5" y="19" width="11" height="37" rx="4" fill="{color('s3')}"/>
      <rect x="45" y="8" width="11" height="48" rx="4" fill="{color('s4')}"/>
    </svg>"""
    return (f'<a class="dpv-brand" href="/" target="_self">'
            f'<span class="mark">{mark}</span>'
            f'<span class="name">Data Product Value</span></a>')


def disclaimer() -> str:
    return ('<p style="margin:26px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
            "Values shown are estimates based on user-provided assumptions and should be validated "
            "with Finance and business owners before formal investment approval. Demonstration data "
            "is fictional.</p>")
