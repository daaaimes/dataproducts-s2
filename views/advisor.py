"""Value Advisor — a port of src/components/valuation/ValueAdvisor.tsx.

The Advisor explains and challenges assumptions from the numbers already in the
model. It never changes the user's inputs.
"""
from __future__ import annotations

import math

import streamlit as st

from app import store
from app.engine.recommendations import recommendations_for
from app.format import money, months, pct, ratio_pct

PROMPTS = [
    "How should I value this product?",
    "Are my assumptions reasonable?",
    "Why is my ROI low?",
    "What assumptions should I validate?",
    "What information do I need from Finance?",
    "How can I improve this business case?",
]


def answer(q: str, row, settings, portfolio_summary: str) -> str:
    lower = q.lower()
    if not row:
        return (f"Open a data product and I can work through its valuation with you. Across the "
                f"portfolio right now: {portfolio_summary}\n\nA good place to start is the Portfolio "
                "Value Matrix on the dashboard — the products in the lower-right quadrant are "
                "absorbing investment without a corresponding value case.")

    p, v = row["product"], row["valuation"]
    c = settings["currency"]

    if "how should i value" in lower or "where do i start" in lower or "value this" in lower:
        actual = sum(1 for b in v["benefits"] if b["benefit"]["evidence"] == "Actual")
        weighted = (sum(b["benefit"]["attribution"] * b["annualValue"] for b in v["benefits"])
                    / max(1, v["annualGrossValue"]))
        return (f"For {p['name']}, work in this order.\n\n"
                f"1. Establish the baseline. Every credible benefit line needs a measured \"before\" — "
                f"{p['name']} currently rests on {actual} of {len(v['benefits'])} lines backed by "
                f"actuals.\n\n"
                f"2. Separate the value types. You have {money(v['hardDollarValue'], c)} of "
                f"hard-dollar value and {money(v['softValue'], c)} of indirect value (productivity, "
                "risk, avoidance). Present these separately — combining them is the fastest way to "
                "lose a CFO.\n\n"
                f"3. Set attribution deliberately. A data product rarely drives an outcome alone. "
                f"Your weighted attribution is around {pct(weighted)}.\n\n"
                f"4. Load the cost base fully — build, change, technology and run. Yours totals "
                f"{money(v['costs']['initialInvestment'], c)} initial plus "
                f"{money(v['annualOperatingCost'], c)} a year.\n\n"
                f"That produces {money(v['netAnnualValue'], c)} of net annual value and a "
                f"{money(v['threeYearValue'], c)} three-year case.")

    if "reasonable" in lower or "realistic" in lower or "sanity" in lower:
        if not v["guardrails"]:
            weakest = sorted(v["confidence"]["dimensions"], key=lambda d: d["value"])[0]
            return (f"Nothing in {p['name']} trips a benchmark guardrail. The assumptions sit inside "
                    "the ranges we would expect:\n\n"
                    "• Attribution is at or below 80% on every line.\n"
                    "• Adoption assumptions are within observed enterprise ranges.\n"
                    f"• ROI of {ratio_pct(v['roi'])} is inside the normal band for approved data "
                    "investments.\n\n"
                    f"The remaining question is evidence quality rather than plausibility. Confidence "
                    f"is {v['confidence']['score']}/100, held back mainly by {weakest['label'].lower()}.")
        n = len(v["guardrails"])
        listed = "\n\n".join(f"{i + 1}. {g['title']}. {g['detail']}"
                             for i, g in enumerate(v["guardrails"]))
        return (f"I would challenge {n} thing{'s' if n > 1 else ''} in {p['name']}:\n\n{listed}\n\n"
                "None of these mean the case is wrong — they mean an investment committee will ask "
                "about them, so it is better to have the answer ready.")

    if "roi" in lower and ("low" in lower or "why" in lower):
        run_share = (v["annualOperatingCost"] / v["annualGrossValue"]
                     if v["annualGrossValue"] > 0 else 0)
        slowest = max(v["benefits"], key=lambda b: b["benefit"]["rampMonths"], default=None)
        return (f"{p['name']} returns {ratio_pct(v['roi'])} over {round(v['horizonMonths'] / 12)} "
                "years. Three things move that number:\n\n"
                f"• Operating cost absorbs {pct(run_share)} of gross annual value "
                f"({money(v['annualOperatingCost'], c)} against {money(v['annualGrossValue'], c)}). "
                "Anything above roughly 30% is worth examining — model monitoring and platform costs "
                "are the usual culprits.\n\n"
                f"• Time to value. Build runs {p['investment']['buildMonths']} months and the slowest "
                f"benefit line (\"{slowest['benefit']['label'] if slowest else '—'}\") takes a further "
                f"{slowest['benefit']['rampMonths'] if slowest else 0} months to reach run-rate. Value "
                "that arrives in year three barely moves a three-year ROI.\n\n"
                "• Attribution and adoption. These are multiplicative — a 70% adoption and 60% "
                "attribution assumption together keep 42% of the theoretical benefit.\n\n"
                "The sensitivity analysis on the valuation page ranks which of these actually moves "
                "your number most.")

    if "validate" in lower or "evidence" in lower:
        weak = sorted([b for b in v["benefits"] if b["benefit"]["evidence"] != "Actual"],
                      key=lambda b: b["annualValue"], reverse=True)[:3]
        parts = []
        for i, b in enumerate(weak):
            if b["benefit"]["kind"] == "riskReduction":
                tail = "Ask second-line risk to confirm the base rate and the severity."
            elif b["category"] == "revenue":
                tail = "A hold-out group is the only thing that settles attribution arguments."
            else:
                tail = ("An observed process baseline — even a two-week sample — moves this from "
                        "estimate to measured.")
            parts.append(f"{i + 1}. {b['benefit']['label']} — {money(b['annualValue'], c)} a year, "
                         f"currently supported by {b['benefit']['evidence'].lower()}. {tail}")
        share = (weak[0]["annualValue"] / max(1, v["annualGrossValue"])) if weak else 0
        return ("Validate in value order, not in list order. For "
                f"{p['name']} that means:\n\n" + "\n\n".join(parts)
                + f"\n\nIf you can only do one thing, do the first. It carries {pct(share)} of the "
                  "annual value.")

    if "finance" in lower:
        hourly = (v["byCategory"]["productivity"] / v["capacityReleaseHours"]
                  if v["capacityReleaseHours"] > 0 else 0)
        return (f"Ask Finance for five things before you take {p['name']} to an investment "
                "committee:\n\n"
                f"1. Fully-loaded cost rates for the affected population — you are currently using "
                f"rates that imply roughly {money(hourly, c)} an hour.\n\n"
                "2. An agreed attribution rule for the revenue lines, ideally tied to a hold-out "
                "group.\n\n"
                f"3. Confirmation of the treatment of released capacity. "
                f"{money(v['byCategory']['productivity'], c)} of your annual value is capacity, "
                f"equivalent to about {v['fteEquivalent']:.1f} FTE. Finance decides whether that "
                "reduces budget or is redeployed.\n\n"
                f"4. The baseline cost lines behind your {money(v['byCategory']['costSavings'], c)} of "
                f"savings and {money(v['byCategory']['costAvoidance'], c)} of avoidance — with a "
                "named budget owner for each.\n\n"
                f"5. The discount rate and horizon to use. You are modelling {pct(v['discountRate'])} "
                f"over {round(v['horizonMonths'] / 12)} years.")

    if "improve" in lower or "better" in lower or "stronger" in lower:
        recs = recommendations_for(p, settings, v)
        listed = "\n\n".join(
            f"{i + 1}. {r['title']}. {r['body']}" + (f" {r['impact']}" if r.get("impact") else "")
            for i, r in enumerate(recs[:4]))
        return f"Four things would materially strengthen {p['name']}:\n\n{listed}"

    if "payback" in lower:
        return (f"{p['name']} pays back in {months(v['paybackMonths'])} from the start of investment, "
                f"or {months(v['paybackFromGoLive'])} from go-live. The difference matters in a "
                "committee: business sponsors usually think from go-live, Finance always thinks from "
                "first spend. Quote both.")

    if "risk" in lower:
        return (f"{money(v['byCategory']['risk'], c)} of {p['name']}'s annual value is risk-adjusted "
                "expected loss reduction. Two rules for presenting it:\n\n"
                "• Never call it a saving. In any single year the realised outcome is either zero or "
                "the full loss event. It is an expected value across many years.\n\n"
                "• Show the arithmetic. Expected loss before minus expected loss after, with the base "
                "rate sourced from the risk register and signed off by second line.\n\n"
                "Presented that way it is credible. Presented as a cost saving it will be struck out.")

    if "confidence" in lower:
        weakest = sorted(v["confidence"]["dimensions"], key=lambda d: d["value"])[:3]
        listed = "\n".join(f"• {d['label']} ({d['value']}/100)" for d in weakest)
        penalty = (f", and guardrail flags cost a further {v['confidence']['guardrailPenalty']} points"
                   if v["confidence"]["guardrailPenalty"] > 0 else "")
        return (f"Confidence for {p['name']} is {v['confidence']['score']}/100 — "
                f"{v['confidence']['band'].lower()}. The three weakest dimensions are:\n\n{listed}\n\n"
                f"Evidence quality contributes {v['confidence']['evidenceScore']}/100 on its own"
                f"{penalty}. Confidence is not a judgement on the product — it tells the committee "
                "how much weight to put on the number.")

    return (f"I can help with {p['name']} on any of these: how to structure the valuation, whether "
            "the assumptions hold up against benchmarks, what is driving ROI and payback, which "
            "assumptions to validate first, what to ask Finance for, and how to strengthen the "
            f"case.\n\nWhere it stands today: {money(v['threeYearValue'], c)} of three-year economic "
            f"value, {ratio_pct(v['roi'])} ROI, {months(v['paybackMonths'])} payback.")


def render() -> None:
    """The Advisor as a page.

    Streamlit re-runs the whole script on every interaction, and a modal that
    has to survive those re-runs reopens itself on unrelated re-runs. A page is
    both robust and roomier for a conversation.
    """
    rows = store.rows()
    settings = store.settings()
    totals = store.totals()
    c = settings["currency"]

    from .common import page_header, product_picker
    page_header("Value Advisor",
                "Ask about a valuation and I will explain the reasoning — how to structure it, "
                "whether the assumptions hold up, what is driving ROI, and what to validate first. "
                "I never change your inputs.")

    ids = ["__portfolio__"] + [r["product"]["id"] for r in rows]
    names = {r["product"]["id"]: r["product"]["name"] for r in rows}
    current = st.session_state.get("selected_product")
    default = current if current in names else "__portfolio__"
    pid = st.selectbox("Context", ids, ids.index(default), key="adv_ctx",
                       format_func=lambda i: ("Whole portfolio" if i == "__portfolio__"
                                              else names[i]))
    row = next((r for r in rows if r["product"]["id"] == pid), None)
    summary = f"{len(rows)} products, {money(totals['threeYear'], c)} of three-year economic value."

    if st.session_state.get("_adv_ctx") != pid:
        st.session_state._adv_ctx = pid
        st.session_state.advisor_msgs = [(
            "advisor",
            (f"I have {row['product']['name']} open. It currently values at "
             f"{money(row['valuation']['threeYearValue'], c)} over three years.\n\n"
             "Ask me anything about the valuation — I will explain the reasoning rather than "
             "change your assumptions for you.") if row else
            ("I can help you value, challenge and present data product business cases.\n\n"
             f"Portfolio position: {summary}"))]

    st.caption("Suggested questions")
    cols = st.columns(3)
    for i, prompt in enumerate(PROMPTS):
        if cols[i % 3].button(prompt, key=f"adv_p_{i}", use_container_width=True):
            st.session_state.advisor_msgs.append(("user", prompt))
            st.session_state.advisor_msgs.append(("advisor", answer(prompt, row, settings, summary)))
            st.rerun()

    typed = st.chat_input("Ask about this valuation…")
    if typed:
        st.session_state.advisor_msgs.append(("user", typed))
        st.session_state.advisor_msgs.append(("advisor", answer(typed, row, settings, summary)))
        st.rerun()

    st.write("")
    for role, text in st.session_state.advisor_msgs:
        with st.chat_message("user" if role == "user" else "assistant"):
            st.markdown(text)

    if len(st.session_state.advisor_msgs) > 1:
        if st.button("Clear conversation", key="adv_clear"):
            st.session_state.pop("_adv_ctx", None)
            st.rerun()
