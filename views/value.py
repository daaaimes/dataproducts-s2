"""Value a Data Product — Simple and Detailed modes.

A port of src/pages/ValuePage.tsx, SimpleValue.tsx and Wizard.tsx. Simple mode
is the eight-question form with a live valuation panel; Detailed mode is the
five-step wizard with full control of every driver, cost line and assumption.
"""
from __future__ import annotations

import copy

import streamlit as st

from app import store
from app.charts import value_waterfall
from app.data.catalogs import BUSINESS_UNITS, CATEGORY_META, DOMAINS, DRIVER_GROUPS, DRIVERS
from app.data.factory import empty_product, make_benefit, uid
from app.domain import (COST_FIELD_LABELS, EVIDENCE_TYPES, GEOGRAPHIC_SCOPES,
                        INVESTMENT_GROUPS, LIFECYCLE_STAGES, PRODUCT_TYPES,
                        STRATEGIC_PRIORITIES, USAGE_FREQUENCIES)
from app.engine.models import MODELS
from app.engine.simple import (ARCHETYPES, EVIDENCE_LEVELS, LEVERS, apply_archetype,
                               build_product_from_simple, default_simple_input)
from app.engine.valuation import value_product
from app.format import money, months, num, pct, ratio_pct
from app.theme import tokens
from app.ui import badge, card, esc, h3, rule, swatch, write
from .common import goto, page_header

STEPS = [
    (1, "What are you building?", "Product"),
    (2, "Who benefits?", "Users"),
    (3, "How does it create value?", "Value"),
    (4, "What will it cost?", "Cost"),
    (5, "How confident are you?", "Confidence"),
]


def render() -> None:
    settings = store.settings()
    editing_id = st.session_state.get("edit_product")
    editing = editing_id and store.row_by_id(editing_id)

    page_header(
        f"Edit valuation — {editing['product']['name']}" if editing else "Value a Data Product",
        "Full control of every driver, cost line and assumption." if editing else
        "Two ways in: Simple takes under a minute on benchmarks, Detailed gives you every lever.")

    if editing:
        _wizard(settings, editing["product"])
        return

    simple_tab, detailed_tab = st.tabs(["⚡  Simple · 45s", "⚙  Detailed · 5 steps"])
    with simple_tab:
        _simple(settings)
    with detailed_tab:
        _wizard(settings, None)


# ── Simple mode ──────────────────────────────────────────────────────────────

def _simple(settings) -> None:
    c = settings["currency"]
    th = store.theme()
    t = tokens(th)

    if "simple_input" not in st.session_state:
        st.session_state.simple_input = default_simple_input()
    inp = st.session_state.simple_input

    form, panel = st.columns([1.7, 1], gap="large")

    with form:
        write(_section(1, "What are you building?"))
        a, b = st.columns(2)
        inp["name"] = a.text_input("Product name *", inp["name"],
                                   placeholder="e.g. Merchant Insights API", key="s_name")
        inp["owner"] = b.text_input("Product owner *", inp["owner"],
                                    placeholder="Who is accountable?", key="s_owner")
        new_type = a.selectbox("Product type", PRODUCT_TYPES, PRODUCT_TYPES.index(inp["type"]),
                               key="s_type", help="Seeds delivery, run-cost and adoption benchmarks.")
        if new_type != inp["type"]:
            st.session_state.simple_input = apply_archetype(inp, new_type)
            st.rerun()
        inp["businessUnit"] = b.selectbox("Business unit", BUSINESS_UNITS,
                                          BUSINESS_UNITS.index(inp["businessUnit"]), key="s_bu")

        arche = ARCHETYPES[inp["type"]]
        write(rule() + _section(2, "Who benefits, and how much time do they get back?"))
        u1, u2, u3 = st.columns(3)
        inp["userCount"] = u1.number_input("People who will use it", 0, 1_000_000,
                                           int(inp["userCount"]), 10, key="s_users")
        inp["hoursSaved"] = u2.slider("Hours saved / user / month", 0.0, 24.0,
                                      float(inp["hoursSaved"]), 0.5, key="s_hours")
        inp["adoption"] = u3.slider("Expected adoption", 0.1, 1.0, float(inp["adoption"]), 0.05,
                                    key="s_adopt", format="%.2f")
        warn = ('<span style="color:var(--warn)"> · adoption above 85% is unusually high for '
                "year one</span>" if inp["adoption"] > 0.85 else "")
        loaded = inp.get("fullyLoadedAnnualCost") or arche["fullyLoadedAnnualCost"]
        write(f'<p style="margin:6px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
              f'Defaults come from the <strong style="color:var(--text-secondary)">{esc(inp["type"])}'
              f"</strong> benchmark. Released time is valued at a fully-loaded "
              f"{money(loaded, c)} a year per person{warn}.</p>")

        write(rule() + _section(3, "How else does it create value?",
                                "Optional — add only what you can defend."))
        cols = st.columns(4)
        for i, lever in enumerate(LEVERS):
            with cols[i]:
                on = st.checkbox(lever["label"], value=inp["levers"][lever["key"]] > 0,
                                 key=f"s_lv_{lever['key']}", help=lever["help"])
                if on:
                    inp["levers"][lever["key"]] = st.number_input(
                        lever["field"], 0, 10_000_000_000,
                        int(inp["levers"][lever["key"]]), 100_000,
                        key=f"s_lvv_{lever['key']}", help=lever["help"])
                else:
                    inp["levers"][lever["key"]] = 0

        write(rule() + _section(4, "What will it cost to build?"))
        cost_a, cost_b = st.columns(2)
        inp["buildInvestment"] = cost_a.number_input(
            f"Build investment ({c})", 0, 10_000_000_000, int(inp["buildInvestment"]), 100_000,
            key="s_build", help="One-off delivery cost. Change and run costs are derived from it.")

        draft = build_product_from_simple(inp, settings, "preview")
        live = value_product(draft, settings)
        build_months_label = f"{draft['investment']['buildMonths']} months"
        with cost_b:
            write(f'<div class="dpv-tile"><div class="dpv-eyebrow">Derived from the benchmark</div>'
                  f'{_row("Change & adoption", money(live["costs"]["changeTotal"], c))}'
                  f'{_row("Total initial investment", money(live["costs"]["initialInvestment"], c), True)}'
                  f'{_row("Annual operating cost", money(live["annualOperatingCost"], c))}'
                  f'{_row("Build duration", build_months_label)}</div>')

        write(rule() + _section(5, "How solid is the evidence?", "Sets attribution and realisation."))
        levels = [e["key"] for e in EVIDENCE_LEVELS]
        inp["evidenceLevel"] = st.radio(
            "Evidence level", levels, levels.index(inp["evidenceLevel"]), key="s_ev",
            horizontal=True, label_visibility="collapsed",
            format_func=lambda k: next(e["label"] for e in EVIDENCE_LEVELS if e["key"] == k))
        write(f'<p style="margin:2px 0 0;font-size:11.5px;color:var(--text-muted)">'
              f'{esc(next(e["blurb"] for e in EVIDENCE_LEVELS if e["key"] == inp["evidenceLevel"]))}</p>')

        st.write("")
        inp["problem"] = st.text_input(
            "What problem does it solve?", inp["problem"], key="s_problem",
            placeholder="Analysts rebuild the same report by hand every week across four systems.",
            help="Optional. One line is enough — it heads the business case.")

        with st.expander("Override the benchmarks"):
            o1, o2, o3 = st.columns(3)
            inp["fullyLoadedAnnualCost"] = o1.number_input(
                f"Fully-loaded annual cost / user ({c})", 0, 10_000_000,
                int(inp.get("fullyLoadedAnnualCost") or arche["fullyLoadedAnnualCost"]), 5_000,
                key="s_loaded")
            default_attr = draft["benefits"][0]["attribution"] if draft["benefits"] else 0.5
            inp["attribution"] = o2.slider(
                "Attribution to this product", 0.0, 1.0,
                float(inp.get("attribution") or default_attr), 0.05, key="s_attr", format="%.2f")
            inp["buildMonths"] = o3.number_input(
                "Build duration (months)", 1, 36,
                int(inp.get("buildMonths") or arche["buildMonths"]), 1, key="s_bm")
            write('<p style="margin:8px 0 0;font-size:11px;line-height:1.7;color:var(--text-muted)">'
                  "Everything else — ramp curves, cost split and strategic scores — is derived from "
                  "the archetype and is fully editable in Detailed mode after you generate.</p>")

        st.session_state.simple_input = inp
        draft = build_product_from_simple(inp, settings, "preview")
        live = value_product(draft, settings)

        write(rule())
        ready = (len(inp["name"].strip()) > 1 and len(inp["owner"].strip()) > 1
                and live["annualGrossValue"] > 0)
        left, right = st.columns([3, 1.4])
        left.markdown(
            '<div style="padding-top:8px;font-size:11.5px;color:var(--text-muted)">'
            "⏱ Everything else is filled from benchmarks — refine later in Detailed mode.</div>"
            if ready else
            '<div style="padding-top:8px;font-size:11.5px;color:var(--text-muted)">'
            + ("Give the product a name" if len(inp["name"].strip()) < 2
               else "Give the product an owner" if len(inp["owner"].strip()) < 2
               else "Add users or a value lever") + "</div>",
            unsafe_allow_html=True)
        if right.button("✦  Generate valuation", type="primary", disabled=not ready,
                        use_container_width=True, key="s_go"):
            product = build_product_from_simple(inp, settings)
            store.save_product(product)
            st.session_state.simple_input = default_simple_input()
            goto("product", selected_product=product["id"])

    with panel:
        _live_panel(live, c, th, "Set a user population or add a value lever and the valuation "
                                 "builds here in real time.")


# ── Detailed mode (the five-step wizard) ─────────────────────────────────────

def _wizard(settings, existing) -> None:
    c = settings["currency"]
    th = store.theme()

    key = f"wizard_{existing['id']}" if existing else "wizard_new"
    if st.session_state.get("_wizard_key") != key:
        st.session_state._wizard_key = key
        st.session_state.wizard_draft = (copy.deepcopy(existing) if existing else empty_product())
        st.session_state.wizard_step = 1
    draft = st.session_state.wizard_draft

    rail = " ".join(
        f'<span style="display:inline-flex;align-items:center;gap:7px;padding:5px 10px;'
        f'border-radius:10px;{"background:var(--surface-3)" if n == st.session_state.wizard_step else ""}">'
        f'<span style="width:19px;height:19px;border-radius:999px;display:inline-flex;'
        f'align-items:center;justify-content:center;font-size:10px;font-weight:700;'
        f'background:{"var(--s1)" if n == st.session_state.wizard_step else "var(--surface-3)"};'
        f'color:{"#fff" if n == st.session_state.wizard_step else "var(--text-muted)"}">{n}</span>'
        f'<span style="font-size:12.5px;color:{"var(--text-primary)" if n == st.session_state.wizard_step else "var(--text-muted)"};'
        f'{"font-weight:600" if n == st.session_state.wizard_step else ""}">{short}</span></span>'
        for n, _title, short in STEPS)
    write(card(rail, style="padding:10px 14px"))

    body, panel = st.columns([1.75, 1], gap="large")
    live = value_product(draft, settings)

    with body:
        step = st.session_state.wizard_step
        advanced = st.toggle("Advanced assumptions", key="wz_adv")
        _, title, _ = STEPS[step - 1]
        blurbs = {
            1: "Describe the product and the business problem it solves. This framing is what senior management reads first.",
            2: "The size and engagement of the user base drives most of the value in a data product. Adoption is the assumption most business cases get wrong.",
            3: "Select every way this product creates value. Each selection opens the specific inputs its model needs — nothing more.",
            4: "Load the cost base fully. An understated cost base is the fastest way to lose credibility with Finance — and the most common reason a business case fails at review.",
            5: "Confidence is not a judgement on the product. It tells senior management how much weight to place on the number — and it is what separates a credible business case from an optimistic one.",
        }
        write(f'<div class="dpv-eyebrow" style="color:var(--s1);letter-spacing:.1em">'
              f"Step {step} of 5</div>"
              f'<h2 style="margin:6px 0 0;font-size:24px;font-weight:600;letter-spacing:-0.025em;'
              f'color:var(--text-primary)">{esc(title)}</h2>'
              f'<p class="dpv-sub" style="max-width:44em">{esc(blurbs[step])}</p>')
        st.write("")

        if step == 1:
            _step1(draft)
        elif step == 2:
            _step2(draft)
        elif step == 3:
            _step3(draft, live, c, advanced)
        elif step == 4:
            _step4(draft, c, settings, advanced)
        else:
            _step5(draft, live)

        st.session_state.wizard_draft = draft
        live = value_product(draft, settings)

        write(rule())
        can_advance = (len(draft["name"].strip()) > 1 and len(draft["owner"].strip()) > 1
                       if step == 1 else bool(draft["benefits"]) if step == 3 else True)
        nav_a, nav_b, nav_c = st.columns([1, 2.4, 1.4])
        if nav_a.button("←  Back", disabled=step == 1, key="wz_back", use_container_width=True):
            st.session_state.wizard_step = max(1, step - 1)
            st.rerun()
        if not can_advance:
            nav_b.markdown('<div style="padding-top:9px;text-align:right;font-size:11.5px;'
                           'color:var(--text-muted)">'
                           + ("Product name and owner are required" if step == 1
                              else "Select at least one value driver") + "</div>",
                           unsafe_allow_html=True)
        if step < 5:
            if nav_c.button("Continue  →", type="primary", disabled=not can_advance,
                            key="wz_next", use_container_width=True):
                st.session_state.wizard_step = step + 1
                st.rerun()
        else:
            if nav_c.button("✦  Generate valuation", type="primary", key="wz_finish",
                            use_container_width=True):
                product = dict(draft)
                product["code"] = product["code"] or "DP-000"
                product["id"] = product["id"] or uid("dp")
                store.save_product(product)
                st.session_state.pop("_wizard_key", None)
                st.session_state.pop("edit_product", None)
                goto("product", selected_product=product["id"])

    with panel:
        _live_panel(live, c, th, "Select how this product creates value in step 3 and the "
                                 "valuation will build here in real time.")


def _step1(draft) -> None:
    a, b = st.columns(2)
    draft["name"] = a.text_input("Product name *", draft["name"], key="wz_name",
                                 placeholder="e.g. RM Copilot")
    draft["owner"] = b.text_input("Product owner *", draft["owner"], key="wz_owner",
                                  placeholder="Who is accountable for delivery?")
    draft["sponsor"] = a.text_input("Business sponsor", draft["sponsor"], key="wz_sponsor",
                                    placeholder="Who owns the value?")
    draft["businessUnit"] = b.selectbox("Business unit", BUSINESS_UNITS,
                                        BUSINESS_UNITS.index(draft["businessUnit"]), key="wz_bu")
    draft["domain"] = a.selectbox("Data domain", DOMAINS, DOMAINS.index(draft["domain"]), key="wz_dom")
    draft["type"] = b.selectbox("Product type", PRODUCT_TYPES, PRODUCT_TYPES.index(draft["type"]),
                                key="wz_type")
    draft["lifecycle"] = a.selectbox("Lifecycle stage", LIFECYCLE_STAGES,
                                     LIFECYCLE_STAGES.index(draft["lifecycle"]), key="wz_life")
    draft["strategicPriority"] = b.selectbox(
        "Strategic priority", STRATEGIC_PRIORITIES,
        STRATEGIC_PRIORITIES.index(draft["strategicPriority"]), key="wz_prio")
    draft["geographicScope"] = a.selectbox(
        "Geographic scope", GEOGRAPHIC_SCOPES,
        GEOGRAPHIC_SCOPES.index(draft["geographicScope"]), key="wz_geo")
    draft["problemStatement"] = st.text_area(
        "Business problem", draft["problemStatement"], key="wz_problem", height=90,
        help="What is broken today, and what does it cost the organisation? Be specific and quantified where you can.",
        placeholder="Relationship managers spend 30–40% of their week assembling client material by hand across five systems…")
    draft["description"] = st.text_area(
        "What the product does", draft["description"], key="wz_desc", height=90,
        placeholder="A GenAI assistant embedded in the RM desktop that…")


def _step2(draft) -> None:
    draft["targetUsers"] = st.text_input(
        "Target users", draft["targetUsers"], key="wz_tu",
        help="Which roles will use this, and in what part of their work?",
        placeholder="Relationship managers, team leaders, investment counsellors")
    a, b = st.columns(2)
    draft["userCount"] = a.number_input("Number of users", 0, 1_000_000,
                                        int(draft["userCount"]), 10, key="wz_uc")
    draft["usageFrequency"] = b.selectbox("Usage frequency", USAGE_FREQUENCIES,
                                          USAGE_FREQUENCIES.index(draft["usageFrequency"]),
                                          key="wz_freq")
    write(rule())
    draft["adoptionAssumption"] = st.slider("Expected steady-state adoption", 0.05, 1.0,
                                            float(draft["adoptionAssumption"]), 0.01,
                                            key="wz_adopt", format="%.2f")
    extra = ('<span style="color:var(--warn)"> Above 85% is unusually high — validate with pilot '
             "data.</span>" if draft["adoptionAssumption"] > 0.85 else "")
    write(f'<p style="margin:2px 0 0;font-size:11.5px;line-height:1.7;color:var(--text-muted)">'
          f"Enterprise data products typically stabilise at 45–75% active adoption in year one.{extra}</p>")
    c1, c2 = st.columns(2)
    draft["complexity"] = c1.slider("Delivery complexity", 1, 10, int(draft["complexity"]), 1,
                                    key="wz_cx")
    draft["timeToValueMonths"] = c2.slider("Time to first measurable value (months)", 1, 36,
                                           int(draft["timeToValueMonths"]), 1, key="wz_ttv")

    write(rule() + '<p style="margin:0 0 10px;font-size:12px;line-height:1.7;color:var(--text-muted)">'
          "<strong style='color:var(--text-secondary)'>Strategic contribution.</strong> Scored "
          "separately from economic value. These never enter the financial case — they inform "
          "prioritisation.</p>")
    fields = [("strategicAlignment", "Strategic alignment"), ("customerImpact", "Customer impact"),
              ("reusability", "Reusability"), ("riskReduction", "Risk reduction"),
              ("dataDemocratisation", "Data democratisation"), ("aiReadiness", "AI readiness")]
    cols = st.columns(2)
    for i, (k, label) in enumerate(fields):
        draft["strategic"][k] = cols[i % 2].slider(label, 0, 100, int(draft["strategic"][k]), 5,
                                                   key=f"wz_st_{k}")


def _step3(draft, live, c, advanced) -> None:
    selected = {b["driverId"] for b in draft["benefits"]}
    for group in DRIVER_GROUPS:
        drivers = [d for d in DRIVERS if d["group"] == group]
        label = f"{group}  ·  scored, not monetised" if group == "Strategic" else group
        with st.expander(label, expanded=group == "Revenue"):
            cols = st.columns(3)
            for i, d in enumerate(drivers):
                active = d["id"] in selected or (not d["model"] and d["label"] in draft["tags"])
                if cols[i % 3].checkbox(d["label"], value=active, key=f"wz_drv_{d['id']}",
                                        help=d["hint"]) != active:
                    _toggle_driver(draft, d)
                    st.rerun()

    if not draft["benefits"]:
        return

    write(rule())
    for b in list(draft["benefits"]):
        model = MODELS[b["kind"]]
        res = next((r for r in live["benefits"] if r["benefit"]["id"] == b["id"]), None)
        with st.container():
            head, val = st.columns([3, 1])
            with head:
                b["label"] = st.text_input("Benefit label", b["label"], key=f"wz_bl_{b['id']}",
                                           label_visibility="collapsed")
                write(f'<p style="margin:-6px 0 6px;font-size:11.5px;line-height:1.6;'
                      f'color:var(--text-muted)">{swatch(tokens(store.theme())[CATEGORY_META[model["category"]]["series"]])} '
                      f'{esc(model["summary"])}</p>')
            with val:
                write(f'<div style="text-align:right;padding-top:6px">'
                      f'<div class="tnum" style="font-size:15px;font-weight:600;'
                      f'color:var(--text-primary)">{money(res["annualValue"] if res else 0, c)}</div>'
                      f'<div style="font-size:10.5px;color:var(--text-muted)">per year</div></div>')

            fcols = st.columns(3)
            idx = 0
            for f in model["fields"]:
                if f["unit"] == "toggle":
                    b["inputs"][f["key"]] = 1 if st.toggle(
                        f["label"], value=b["inputs"].get(f["key"], 0) >= 0.5,
                        key=f"wz_in_{b['id']}_{f['key']}", help=f["help"]) else 0
                    continue
                if f["key"] in ("annualGrowth", "baselineCost") and not advanced:
                    continue
                col = fcols[idx % 3]
                idx += 1
                cur = float(b["inputs"].get(f["key"], f["def"]))
                if f["unit"] == "percent":
                    hi = float(f["max"] if f["max"] is not None else 1)
                    lo = float(f["min"] if f["min"] is not None else 0)
                    b["inputs"][f["key"]] = col.slider(
                        f["label"], lo, hi, min(max(cur, lo), hi),
                        float(f["step"] or 0.01), key=f"wz_in_{b['id']}_{f['key']}",
                        help=f["help"] if advanced else None, format="%.3f")
                else:
                    prefix = f"{c} " if f["unit"] == "currency" else ""
                    b["inputs"][f["key"]] = col.number_input(
                        f'{prefix}{f["label"]}' if prefix else f["label"],
                        float(f["min"]) if f["min"] is not None else None,
                        float(f["max"]) if f["max"] is not None else None,
                        cur, float(f["step"] or 1), key=f"wz_in_{b['id']}_{f['key']}",
                        help=f["help"] if advanced else None)

            m1, m2, m3, m4 = st.columns(4)
            b["attribution"] = m1.slider("Attribution", 0.0, 1.0, float(b["attribution"]), 0.05,
                                         key=f"wz_at_{b['id']}", format="%.2f")
            b["evidence"] = m2.selectbox("Evidence", EVIDENCE_TYPES,
                                         EVIDENCE_TYPES.index(b["evidence"]),
                                         key=f"wz_ev_{b['id']}")
            b["evidenceStrength"] = m3.slider("Evidence strength", 1, 5,
                                              int(b["evidenceStrength"]), 1,
                                              key=f"wz_es_{b['id']}")
            b["rampMonths"] = m4.slider("Ramp to full value (months)", 1, 30,
                                        int(b["rampMonths"]), 1, key=f"wz_rm_{b['id']}")
            if advanced:
                x1, x2 = st.columns([1, 3])
                b["startMonth"] = x1.slider("Starts after go-live (months)", 0, 24,
                                            int(b["startMonth"]), 1, key=f"wz_sm_{b['id']}")
                b["evidenceNote"] = x2.text_input(
                    "Evidence reference", b.get("evidenceNote") or "", key=f"wz_en_{b['id']}",
                    placeholder="Time-and-motion study across 48 RMs, Q1 2026")
            if st.button("Remove this benefit line", key=f"wz_rmv_{b['id']}"):
                draft["benefits"] = [x for x in draft["benefits"] if x["id"] != b["id"]]
                st.rerun()
            write(rule())


def _step4(draft, c, settings, advanced) -> None:
    draft["investment"]["buildMonths"] = st.slider(
        "Build duration before go-live (months)", 1, 30,
        int(draft["investment"]["buildMonths"]), 1, key="wz_bmn")
    for group in INVESTMENT_GROUPS:
        total = sum(draft["investment"][group["key"]].get(f, 0) for f in group["fields"])
        with st.expander(f"{group['label']} · {group['note']} · {money(total, c)}",
                         expanded=group["key"] == "build"):
            cols = st.columns(3)
            for i, f in enumerate(group["fields"]):
                draft["investment"][group["key"]][f] = cols[i % 3].number_input(
                    COST_FIELD_LABELS[f], 0.0, None,
                    float(draft["investment"][group["key"]].get(f, 0)), 10_000.0,
                    key=f"wz_cost_{group['key']}_{f}")
    if advanced:
        write(rule())
        a, b = st.columns(2)
        draft["discountRate"] = a.slider(
            "Discount rate", 0.0, 0.4,
            float(draft.get("discountRate") or settings["discountRate"]), 0.005,
            key="wz_dr", format="%.3f",
            help="Used for NPV. Default is the organisation-wide rate from Settings.")
        draft["horizonYears"] = b.selectbox(
            "Projection period (years)", [3, 5, 7, 10],
            [3, 5, 7, 10].index(int(draft.get("horizonYears") or settings["horizonYears"]))
            if int(draft.get("horizonYears") or settings["horizonYears"]) in (3, 5, 7, 10) else 1,
            key="wz_hy")


def _step5(draft, live) -> None:
    cols = st.columns(2)
    for i, dim in enumerate(live["confidence"]["dimensions"]):
        with cols[i % 2]:
            draft["confidence"][dim["key"]] = st.slider(
                dim["label"], 0, 100, int(draft["confidence"][dim["key"]]), 5,
                key=f"wz_cf_{dim['key']}")
            write(f'<p style="margin:-6px 0 8px;font-size:11px;color:var(--text-muted)">'
                  f'Weight {round(dim["weight"] * 100)}%</p>')
    if live["guardrails"]:
        write(rule() + '<div class="dpv-eyebrow">Before you submit</div>')
        for g in live["guardrails"]:
            write(f'<div class="dpv-note {"severe" if g["severity"] == "severe" else "warn"}" '
                  f'style="margin-top:9px"><span style="flex:none">⚠</span>'
                  f'<div><div style="font-size:12.5px;font-weight:500;color:var(--text-primary)">'
                  f'{esc(g["title"])}</div><p style="margin:3px 0 0;font-size:12px;line-height:1.6">'
                  f'{esc(g["detail"])}</p></div></div>')


def _toggle_driver(draft, d) -> None:
    if any(b["driverId"] == d["id"] for b in draft["benefits"]):
        draft["benefits"] = [b for b in draft["benefits"] if b["driverId"] != d["id"]]
        return
    if not d["model"]:
        if d["label"] in draft["tags"]:
            draft["tags"] = [x for x in draft["tags"] if x != d["label"]]
        else:
            draft["tags"] = list(dict.fromkeys(draft["tags"] + [d["label"]]))
        return
    b = make_benefit(d["id"], attribution=0.6, ramp_months=9, evidence="Estimate",
                     evidence_strength=3)
    if "adoption" in b["inputs"]:
        b["inputs"]["adoption"] = draft["adoptionAssumption"]
    if "users" in b["inputs"]:
        b["inputs"]["users"] = draft["userCount"]
    draft["benefits"].append(b)


# ── Shared live panel ────────────────────────────────────────────────────────

def _live_panel(live, c, th, empty_text: str) -> None:
    write('<h3 class="dpv-eyebrow" style="font-size:13px;letter-spacing:.07em">Live valuation</h3>')
    if live["annualGrossValue"] <= 0:
        write(f'<div class="dpv-card" style="text-align:center;padding:36px 20px">'
              f'<div style="font-size:20px;color:var(--text-muted)">✦</div>'
              f'<p style="margin:10px 0 0;font-size:12.5px;line-height:1.7;color:var(--text-muted)">'
              f"{esc(empty_text)}</p></div>")
        return

    rows = [("Annual value", money(live["annualGrossValue"], c)),
            ("Net annual", money(live["netAnnualValue"], c)),
            ("Investment", money(live["costs"]["initialInvestment"], c)),
            ("Run cost p.a.", money(live["annualOperatingCost"], c)),
            ("ROI", ratio_pct(live["roi"])),
            ("Payback", months(live["paybackMonths"])),
            ("NPV", money(live["npv"], c)),
            ("Capacity", f"{num(live['fteEquivalent'], 1)} FTE")]
    cells = "".join(
        f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:8px;'
        f'padding:7px 0;{"border-bottom:1px solid var(--hairline)" if i < 6 else ""}">'
        f'<span style="font-size:11.5px;color:var(--text-muted)">{esc(k)}</span>'
        f'<span class="tnum" style="font-size:12.5px;font-weight:600;color:var(--text-primary)">'
        f"{esc(val)}</span></div>" for i, (k, val) in enumerate(rows))
    write(f'<div class="dpv-card"><div class="dpv-eyebrow">3-year economic value</div>'
          f'<div class="tnum" style="margin-top:6px;font-size:32px;font-weight:600;line-height:1;'
          f'letter-spacing:-0.03em;color:var(--text-primary)">{money(live["threeYearValue"], c)}</div>'
          f'<div style="display:grid;grid-template-columns:1fr 1fr;column-gap:18px;margin-top:12px">'
          f"{cells}</div></div>")
    from .common import chart
    chart(value_waterfall(live, c, th, height=210, show_investment=False), key="live_wf")
    if live["guardrails"]:
        write(f'<p style="margin:4px 0 0;font-size:11px;line-height:1.7;color:var(--warn)">'
              f'{len(live["guardrails"])} assumption'
              f'{"s" if len(live["guardrails"]) > 1 else ""} outside the benchmark range — '
              "detail appears on the valuation.</p>")
    write('<p style="margin:10px 0 0;font-size:11px;line-height:1.7;color:var(--text-muted)">'
          "Estimates from benchmark assumptions. Validate with Finance before formal approval.</p>")


def _section(n: int, title: str, hint: str = "") -> str:
    hint_html = (f'<p style="margin:4px 0 0 29px;font-size:12px;line-height:1.6;'
                 f'color:var(--text-muted)">{esc(hint)}</p>' if hint else "")
    return (f'<div style="margin-bottom:12px"><div style="display:flex;align-items:center;gap:10px">'
            f'<span style="width:19px;height:19px;border-radius:999px;display:inline-flex;'
            f'align-items:center;justify-content:center;font-size:10px;font-weight:700;'
            f'background:color-mix(in srgb, var(--s1) 14%, transparent);color:var(--s1)">{n}</span>'
            f'<h3 style="margin:0;font-size:15px;font-weight:600;letter-spacing:-0.01em;'
            f'color:var(--text-primary)">{esc(title)}</h3></div>{hint_html}</div>')


def _row(label: str, value: str, strong: bool = False) -> str:
    return (f'<div style="display:flex;align-items:baseline;justify-content:space-between;gap:12px;'
            f'margin-top:6px"><span style="font-size:12px;color:var(--text-muted)">{esc(label)}</span>'
            f'<span class="tnum" style="font-size:12px;'
            f'{"font-weight:600;color:var(--text-primary)" if strong else "color:var(--text-secondary)"}">'
            f"{esc(value)}</span></div>")
