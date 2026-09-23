"""Plotly ports of the six chart components in src/components/charts.

Recharts is replaced by Plotly, but the encodings, the palette, the axis
treatment and the tooltip content are kept as they were: same series slots,
same compact-number ticks, same direct labelling, same annotations.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go

from .data.catalogs import CATEGORY_META
from .format import compact_number, money, months_short, pct
from .theme import tokens

FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'


def _base_layout(t, height, margin=None):
    return dict(
        height=height,
        margin=margin or dict(l=8, r=8, t=10, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=11.5, color=t["text-muted"]),
        hoverlabel=dict(bgcolor=t["surface-inv"], bordercolor=t["surface-inv"],
                        font=dict(color=t["surface-1"], size=12, family=FONT)),
        showlegend=False,
        dragmode=False,
    )


def _axes(fig, t, y_zero_line=True):
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=t["axis"],
                     tickfont=dict(color=t["text-muted"], size=11.5))
    fig.update_yaxes(showgrid=True, gridcolor=t["grid"], zeroline=y_zero_line,
                     zerolinecolor=t["axis"], zerolinewidth=1, linecolor="rgba(0,0,0,0)",
                     tickfont=dict(color=t["text-muted"], size=11.5))


CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False}


# ── Value waterfall ──────────────────────────────────────────────────────────

def value_waterfall(valuation, currency, theme="light", height=320, show_investment=True):
    """Gross benefit categories build up, operating cost comes off, net is the
    closing bar. Investment is a reference line — it is capital, not run-rate.

    Drawn as floating bars rather than go.Waterfall so each category keeps its
    own series colour, exactly as the original does.
    """
    t = tokens(theme)
    by = valuation["byCategory"]
    steps = [
        ("Revenue", by["revenue"], "add", t["s1"], "Incremental and protected revenue"),
        ("Cost savings", by["costSavings"], "add", t["s3"], "Run-rate cost removed"),
        ("Cost avoidance", by["costAvoidance"], "add", t["s4"], "Probability-weighted future cost avoided"),
        ("Productivity", by["productivity"], "add", t["s7"], "Capacity released at fully-loaded cost"),
        ("Risk reduction", by["risk"], "add", t["s2"], "Risk-adjusted expected loss reduction"),
        ("Operating cost", -valuation["annualOperatingCost"], "sub", t["s8"], "Technology and run cost"),
        ("Net annual value", valuation["netAnnualValue"], "total", t["text-primary"], ""),
    ]
    steps = [s for s in steps if s[2] == "total" or abs(s[1]) > 0]

    bases, heights, labels, colours, notes, values = [], [], [], [], [], []
    running = 0.0
    for label, value, kind, colour, note_text in steps:
        if kind == "total":
            bases.append(0.0)
            heights.append(value)
        else:
            bases.append(running if value >= 0 else running + value)
            heights.append(abs(value))
            running += value
        labels.append(label)
        colours.append(colour)
        notes.append(note_text)
        values.append(value)

    fig = go.Figure(go.Bar(
        x=labels, y=heights, base=bases, width=0.62,
        marker=dict(color=colours, line=dict(color=t["surface-1"], width=2)),
        text=[("−" if v < 0 else "") + money(abs(v), currency).replace(f"{currency} ", "")
              for v in values],
        textposition="outside",
        textfont=dict(size=11, color=t["text-primary"], family=FONT),
        cliponaxis=False,
        customdata=list(zip([money(v, currency) for v in values], notes)),
        hovertemplate="<b>%{x}</b><br>%{customdata[0]} per year"
                      "<br><span style='opacity:.75'>%{customdata[1]}</span><extra></extra>",
    ))
    fig.update_layout(**_base_layout(t, height, dict(l=8, r=8, t=30, b=8)), bargap=0.3)
    _axes(fig, t)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=True,
                     zerolinecolor=t["axis"], zerolinewidth=1)
    fig.update_xaxes(tickfont=dict(color=t["text-secondary"], size=11))

    inv = valuation["costs"]["initialInvestment"]
    if show_investment and inv > 0:
        fig.add_hline(y=inv, line=dict(color=t["axis"], width=1, dash="dash"),
                      annotation_text=f"Investment {money(inv, currency)}",
                      annotation_position="top left",
                      annotation_font=dict(size=10.5, color=t["text-secondary"]))
    return fig


# ── Cashflow ─────────────────────────────────────────────────────────────────

def cashflow_chart(valuation, currency, theme="light", height=272):
    """Cumulative net cashflow. The line crosses zero at payback."""
    t = tokens(theme)
    cum = valuation["cumulativeNet"]
    xs = list(range(len(cum)))
    benefits = valuation["monthlyBenefits"]
    costs = valuation["monthlyCosts"]

    fig = go.Figure(go.Scatter(
        x=xs, y=cum, mode="lines", line=dict(color=t["s1"], width=2, shape="spline", smoothing=0.4),
        fill="tozeroy", fillcolor=_alpha(t["s1"], 0.13),
        customdata=list(zip([money(b, currency) for b in benefits],
                            [money(c, currency) for c in costs])),
        hovertemplate="<b>Month %{x}</b><br>Cumulative net %{y:,.0f}"
                      "<br>Benefits this month %{customdata[0]}"
                      "<br>Cost this month %{customdata[1]}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(t, height, dict(l=4, r=8, t=14, b=8)))
    _axes(fig, t)
    ticks = [m for m in xs if m % 12 == 0]
    fig.update_xaxes(tickmode="array", tickvals=ticks,
                     ticktext=["Start" if m == 0 else f"Yr {m // 12}" for m in ticks],
                     range=[0, valuation["horizonMonths"] - 1])
    fig.update_yaxes(tickformat="~s")

    if valuation["goLiveMonth"] > 0:
        fig.add_vline(x=valuation["goLiveMonth"], line=dict(color=t["text-muted"], width=1, dash="dash"),
                      annotation_text="Go-live", annotation_position="bottom left",
                      annotation_font=dict(size=11, color=t["text-muted"]))
    pb = valuation["paybackMonths"]
    if math.isfinite(pb) and pb < valuation["horizonMonths"]:
        fig.add_vline(x=pb, line=dict(color=t["s3"], width=2),
                      annotation_text=f"Payback · {round(pb)} mo", annotation_position="top right",
                      annotation_font=dict(size=11, color=t["s3"]))
    return fig


# ── Scenarios ────────────────────────────────────────────────────────────────

def scenario_chart(scenarios, currency, theme="light", height=250):
    t = tokens(theme)
    colours = [t["s4"], t["s1"], t["s3"]]
    labels = [s["label"] for s in scenarios]
    values = [s["valuation"]["threeYearValue"] for s in scenarios]

    fig = go.Figure(go.Bar(
        x=labels, y=values, marker=dict(color=colours, line=dict(color=t["surface-1"], width=2)),
        text=[money(v, currency) for v in values], textposition="outside",
        textfont=dict(size=12, color=t["text-primary"], family=FONT),
        customdata=[[pct(s["valuation"]["roi"]), money(s["valuation"]["npv"], currency),
                     months_short(s["valuation"]["paybackMonths"])] for s in scenarios],
        hovertemplate="<b>%{x}</b><br>3-year value %{y:,.0f}<br>ROI %{customdata[0]}"
                      "<br>NPV %{customdata[1]}<br>Payback %{customdata[2]}<extra></extra>",
        width=0.55,
    ))
    fig.update_layout(**_base_layout(t, height, dict(l=4, r=8, t=30, b=8)), bargap=0.35)
    _axes(fig, t)
    fig.update_yaxes(tickformat="~s")
    fig.update_xaxes(tickfont=dict(color=t["text-secondary"], size=12))
    return fig


# ── Tornado / sensitivity ────────────────────────────────────────────────────

def tornado_chart(rows, currency, theme="light"):
    """Diverging bars: each assumption moved through its own plausible range."""
    t = tokens(theme)
    if not rows:
        return None
    rows = list(reversed(rows))  # plotly draws the first category at the bottom
    labels = [r["label"] for r in rows]
    # Disambiguate repeated field labels across benefit lines.
    seen = {}
    axis_labels = []
    for r in rows:
        key = r["label"]
        seen[key] = seen.get(key, 0) + 1
        axis_labels.append(key)
    lows = [r["lowDelta"] for r in rows]
    highs = [r["highDelta"] for r in rows]

    fig = go.Figure()
    fig.add_bar(y=list(range(len(rows))), x=lows, orientation="h", name="Low",
                marker=dict(color=t["s2"], line=dict(color=t["surface-1"], width=2)),
                customdata=[[r["benefitLabel"] or "", r["rangeNote"], money(r["low"], currency)]
                            for r in rows],
                hovertemplate="<b>%{customdata[0]}</b><br>Low end (%{customdata[1]})"
                              "<br>3-year value %{customdata[2]}<extra></extra>")
    fig.add_bar(y=list(range(len(rows))), x=highs, orientation="h", name="High",
                marker=dict(color=t["s1"], line=dict(color=t["surface-1"], width=2)),
                customdata=[[r["benefitLabel"] or "", r["rangeNote"], money(r["high"], currency)]
                            for r in rows],
                hovertemplate="<b>%{customdata[0]}</b><br>High end (%{customdata[1]})"
                              "<br>3-year value %{customdata[2]}<extra></extra>")

    height = max(180, 30 * len(rows) + 46)
    fig.update_layout(**_base_layout(t, height, dict(l=4, r=64, t=6, b=20)),
                      barmode="overlay", bargap=0.42)
    _axes(fig, t, y_zero_line=False)
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"], zeroline=True,
                     zerolinecolor=t["axis"], zerolinewidth=1, tickformat="~s")
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(rows))), ticktext=axis_labels,
                     showgrid=False, tickfont=dict(color=t["text-secondary"], size=11.5))
    # Swing magnitude, direct-labelled at the right edge (the original's third column).
    for idx, r in enumerate(rows):
        fig.add_annotation(x=1.005, y=idx, xref="paper", yref="y",
                           text=f"±{money(r['swing'] / 2, currency)}", showarrow=False,
                           xanchor="left", font=dict(size=11, color=t["text-primary"]))
    return fig


# ── Realisation ──────────────────────────────────────────────────────────────

def realisation_chart(periods, currency, theme="light", height=270):
    t = tokens(theme)
    labels = [p["period"] for p in periods]
    forecast = [p["forecastRevenue"] + p["forecastSavings"] + p["forecastProductivity"] + p["forecastRisk"]
                for p in periods]
    actual = [p["actualRevenue"] + p["actualSavings"] + p["actualProductivity"] + p["actualRisk"]
              for p in periods]

    fig = go.Figure()
    fig.add_bar(x=labels, y=forecast, name="Forecast value",
                marker=dict(color=t["s1"], line=dict(color=t["surface-1"], width=2)),
                hovertemplate="<b>%{x}</b><br>Forecast %{y:,.0f}<extra></extra>")
    fig.add_bar(x=labels, y=actual, name="Realised value",
                marker=dict(color=t["s3"], line=dict(color=t["surface-1"], width=2)),
                customdata=[[pct(a / max(1, f)), pct(p["actualAdoption"])]
                            for a, f, p in zip(actual, forecast, periods)],
                hovertemplate="<b>%{x}</b><br>Realised %{y:,.0f}"
                              "<br>Realisation %{customdata[0]}"
                              "<br>Adoption (actual) %{customdata[1]}<extra></extra>")
    fig.update_layout(**_base_layout(t, height, dict(l=4, r=8, t=10, b=8)),
                      barmode="group", bargap=0.42, bargroupgap=0.12)
    _axes(fig, t)
    fig.update_yaxes(tickformat="~s")
    fig.update_xaxes(tickfont=dict(color=t["text-secondary"], size=12))
    return fig


# ── Portfolio matrix ─────────────────────────────────────────────────────────

LIFECYCLE_SLOT = {
    "Idea": "s5", "Business Case": "s7", "Approved": "s1", "Build": "s4",
    "Pilot": "s2", "Production": "s3", "Scale": "s6", "Optimise": "s1", "Retire": "s8",
}

QUADRANTS = [
    {"key": "quick", "title": "High-Value Quick Wins", "icon": "▲", "slot": "s3",
     "blurb": "High value, low complexity — fund and ship."},
    {"key": "bets", "title": "Strategic Bets", "icon": "★", "slot": "s1",
     "blurb": "High value, high complexity — stage-gate and sequence."},
    {"key": "optimise", "title": "Optimise", "icon": "◆", "slot": "s4",
     "blurb": "Modest value, low cost — automate or bundle."},
    {"key": "reconsider", "title": "Reconsider", "icon": "●", "slot": "s8",
     "blurb": "Low value, high complexity — challenge the case."},
]


def portfolio_matrix(rows, currency, theme="light", height=470):
    """Business value against implementation complexity and investment.
    Bubble size is five-year economic value."""
    t = tokens(theme)
    if not rows:
        return None

    max_invest = max([1.0] + [r["valuation"]["costs"]["initialInvestment"] for r in rows])
    values = [r["valuation"]["threeYearValue"] for r in rows]
    max_value = max([1.0] + values)
    min_value = min([0.0] + values)
    max_size = max([1.0] + [abs(r["valuation"]["fiveYearValue"]) for r in rows])
    span = (max_value - min(0.0, min_value)) or 1

    xs, ys, sizes, colours, texts, names = [], [], [], [], [], []
    for r in rows:
        v, p = r["valuation"], r["product"]
        invest_norm = v["costs"]["initialInvestment"] / max_invest
        complexity_norm = p["complexity"] / 10
        xs.append(min(1, max(0, invest_norm * 0.55 + complexity_norm * 0.45)))
        ys.append(min(1, max(0, (v["threeYearValue"] - min(0.0, min_value)) / span)))
        sizes.append(22 + 42 * math.sqrt(max(0.0, v["fiveYearValue"]) / max_size))
        colours.append(t[LIFECYCLE_SLOT.get(p["lifecycle"], "s1")])
        names.append(p["name"])
        texts.append(
            f"<b>{p['name']}</b><br>{p['businessUnit']} · {p['lifecycle']}"
            f"<br>3-year value {money(v['threeYearValue'], currency)}"
            f"<br>Investment {money(v['costs']['initialInvestment'], currency)}"
            f"<br>Payback {months_short(v['paybackMonths'])}"
            f"<br>Priority {r['priority']['score']} · {r['priority']['band']}")

    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers", marker=dict(
            size=sizes, sizemode="diameter",
            color=[_alpha(c, 0.6) for c in colours],
            line=dict(color=colours, width=1.5)),
        text=texts, hovertemplate="%{text}<extra></extra>"
    ))

    # Direct labels for the four largest bubbles.
    order = sorted(range(len(rows)), key=lambda i: sizes[i], reverse=True)[:4]
    for i in order:
        fig.add_annotation(x=xs[i], y=ys[i], text=names[i], showarrow=False,
                           yshift=sizes[i] / 2 + 11, font=dict(size=10.5, color=t["text-secondary"]),
                           bgcolor=_alpha(t["surface-1"], 0.82), borderpad=2)

    fig.update_layout(**_base_layout(t, height, dict(l=52, r=18, t=18, b=42)))
    fig.update_xaxes(range=[-0.09, 1.09], showgrid=False, zeroline=False, showticklabels=False,
                     linecolor="rgba(0,0,0,0)",
                     title=dict(text="Lower complexity & investment  →  Higher complexity & investment",
                                font=dict(size=11, color=t["text-muted"])))
    fig.update_yaxes(range=[-0.11, 1.11], showgrid=False, zeroline=False, showticklabels=False,
                     linecolor="rgba(0,0,0,0)",
                     title=dict(text="Business value (3-year)  →", font=dict(size=11, color=t["text-muted"])))

    # Quadrant tinting and dividers.
    tint = [("s3", 0, 0.5, 0.5, 1), ("s1", 0.5, 1, 0.5, 1),
            ("s4", 0, 0.5, 0, 0.5), ("s8", 0.5, 1, 0, 0.5)]
    shapes = []
    for slot, x0, x1, y0, y1 in tint:
        shapes.append(dict(type="rect", xref="x", yref="y", x0=_sx(x0), x1=_sx(x1),
                           y0=_sy(y0), y1=_sy(y1), line=dict(width=0),
                           fillcolor=_alpha(t[slot], 0.06), layer="below"))
    shapes.append(dict(type="line", xref="x", yref="paper", x0=0.5, x1=0.5, y0=0, y1=1,
                       line=dict(color=t["hairline-strong"], width=1), layer="below"))
    shapes.append(dict(type="line", xref="paper", yref="y", x0=0, x1=1, y0=0.5, y1=0.5,
                       line=dict(color=t["hairline-strong"], width=1), layer="below"))
    fig.update_layout(shapes=shapes)

    corners = [(QUADRANTS[0], 0.02, 0.98, "left", "top"), (QUADRANTS[1], 0.98, 0.98, "right", "top"),
               (QUADRANTS[2], 0.02, 0.02, "left", "bottom"), (QUADRANTS[3], 0.98, 0.02, "right", "bottom")]
    for q, x, y, xa, ya in corners:
        fig.add_annotation(x=x, y=y, xref="paper", yref="paper", xanchor=xa, yanchor=ya,
                           showarrow=False, align="left",
                           text=f"<span style='color:{t[q['slot']]}'>{q['icon']}</span> "
                                f"<b>{q['title'].upper()}</b>",
                           font=dict(size=10.5, color=t["text-muted"]))
    return fig


def _sx(v):
    return -0.09 + v * (1.09 - -0.09)


def _sy(v):
    return -0.11 + v * (1.11 - -0.11)


def _alpha(hex_or_rgba: str, a: float) -> str:
    """Blend a token colour with alpha, accepting #rgb/#rrggbb or rgba()."""
    if hex_or_rgba.startswith("rgba") or hex_or_rgba.startswith("rgb"):
        return hex_or_rgba
    h = hex_or_rgba.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{a})"


def category_donut(valuation, currency, theme="light", height=210):
    """Small share-of-value ring used on comparison cards."""
    t = tokens(theme)
    labels, values, colours = [], [], []
    for key, meta in CATEGORY_META.items():
        val = valuation["byCategory"][key]
        if val > 0:
            labels.append(meta["short"])
            values.append(val)
            colours.append(t[meta["series"]])
    if not values:
        return None
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.62,
                           marker=dict(colors=colours, line=dict(color=t["surface-1"], width=2)),
                           textinfo="none",
                           hovertemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percent}<extra></extra>"))
    fig.update_layout(**_base_layout(t, height, dict(l=4, r=4, t=4, b=4)))
    return fig
