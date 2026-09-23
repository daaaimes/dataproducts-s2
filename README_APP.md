# Data Product Value — Streamlit

Quantify the revenue, savings, productivity and risk value of data and AI
investments. Quantify. Prioritise. Track.

This is a Python/Streamlit port of the React application at
`data-product-value.vercel.app`. The valuation engine is a line-for-line
translation of the original TypeScript engine and is verified against it: see
[Engine parity](#engine-parity).

## Run it locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens at <http://localhost:8501> and ships with a 200-product banking
data catalogue, so there is something to look at immediately.

## Deploy to Streamlit Community Cloud

1. Push this repository to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), choose **New app**.
3. Point it at this repository, branch `main`, main file `streamlit_app.py`.
4. Deploy. No secrets or environment variables are required.

`requirements.txt` and `.streamlit/config.toml` are already set up for Cloud.

## What is in it

| Page | What it does |
| --- | --- |
| **Dashboard** | Portfolio KPIs, where value comes from, value maturity, the investment matrix and generated executive insights. |
| **Value a Product** | *Simple* — eight questions answered from memory, expanded into a full valuation from archetype benchmarks, with a live panel. *Detailed* — the five-step wizard with every driver, cost line and assumption. |
| **Portfolio** | All products, filterable and sortable, with CSV export and comparison selection. |
| **Valuation** | The full product view: waterfall, benefit lines with per-line explanations, guardrails, scenarios, what-if levers, sensitivity, cashflow, priority and recommendations. |
| **Compare** | Up to four products side by side, with the strongest value in each row highlighted and a written recommendation. |
| **Value Advisor** | Explains and challenges a valuation. It never changes your inputs. |
| **Value Realisation** | Forecast versus actual by period, with calibration notes and an editor for recording actuals. |
| **Reports** | A fourteen-section board-ready investment paper, downloadable as Markdown. |
| **Assumptions** | The register: every material assumption with source, owner, evidence grade and confidence. |
| **Boardroom Mode** | Six presentation slides driven by the same numbers. |
| **Settings** | Currency, discount rate, horizon, working hours, guardrails and the priority weights. |

## How the valuation works

Ten benefit models (conversion uplift, balance growth, churn reduction, effort
reduction, run-rate reduction, cost avoidance, expected loss reduction,
productivity and two more) each compute a steady-state annual value from named
inputs. Every line then passes through attribution, a ramp curve and the active
scenario levers, and is projected month by month across the horizon. From those
streams the engine derives NPV, IRR, payback, ROI, three- and five-year economic
value, a confidence score, a strategic score, a priority score and a set of
guardrail flags that challenge assumptions falling outside benchmark ranges.

Economic value and strategic value are kept apart throughout: strategic
contribution is scored, never added to the financials. Hard-dollar value is
reported separately from indirect value (productivity, risk-adjusted and
probability-weighted).

## Engine parity

`tests/test_parity.py` runs the Python engine over all 200 catalogue products
and compares **48,119 values** against a golden fixture generated from the
original TypeScript engine — every headline financial, the monthly cashflow
streams, category and maturity splits, confidence and priority scores and their
components, guardrail flags, scenarios, sensitivity rows, recommendations and
portfolio insights, including the generated prose.

```bash
GOLDEN=tests/golden.json python tests/test_parity.py
```

Two details make exact agreement possible: `Math.round` rounds half toward
positive infinity where Python's `round` uses banker's rounding, and
`Number.toFixed` rounds half away from zero on the exact binary value. Both are
reimplemented in `app/format.py`, so formatted output matches the original
character for character.

## Tests

```bash
python tests/test_parity.py     # engine equivalence with the TypeScript original
python tests/smoke.py           # every page renders with no exceptions
python tests/interactions.py    # theme, dialogs, levers, wizard, navigation
```

The two browser tests need `pip install playwright && playwright install
chromium`, and the app running on port 8501.

## Layout

```
streamlit_app.py        entry point: page config, theme, navigation, sidebar
app/
  domain.py             constants and default settings
  format.py             money/percent/number formatting (JS-compatible rounding)
  theme.py              design tokens and global CSS, light and dark
  ui.py                 HTML primitives: card, badge, meter, KPI, table, gauge
  charts.py             Plotly ports of the six chart types
  store.py              session state and the derived portfolio
  persist.py            keeps settings across a browser refresh via the URL
  engine/               models, finance, valuation, scenarios, sensitivity,
                        insights, recommendations, simple mode
  data/                 driver catalogue, factories, the 200-product catalogue
views/                  one module per page, plus the page entry points
tests/                  parity, smoke and interaction tests
```

## Differences from the React original

* **Session persistence.** The original stored the whole workspace in
  `localStorage`. Streamlit has no equivalent, so settings (theme, currency,
  discount rate, horizon, working hours, guardrails, organisation name) are
  mirrored into the URL and survive a refresh, while products created or edited
  during a session are session-scoped. The catalogue rebuilds identically on
  every load.
* **The Value Advisor is a page rather than a slide-over.** A Streamlit modal
  that has to survive re-runs reopens itself on unrelated re-runs; a page is
  robust and gives the conversation more room.
* **Charts are Plotly rather than Recharts**, keeping the same encodings,
  palette, axis treatment and tooltip content.
* **No command palette.** `Cmd-K` needs a key handler Streamlit does not expose;
  search lives on the Portfolio and Assumption pages instead.

## Data

The catalogue is fictional and sized for a Singapore universal bank of roughly
SGD 4.6B operating income. Benefit figures are deliberately conservative: lever
values are stated gross and the engine applies attribution, realisation and
probability haircuts by evidence grade. Values are estimates and should be
validated with Finance and business owners before any investment decision.
