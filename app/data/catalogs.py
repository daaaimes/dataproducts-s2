"""Driver, category and currency catalogues — a port of src/data/catalogs.ts."""
from __future__ import annotations


def _d(id, label, group, category, hint, model=None):
    return {"id": id, "label": label, "group": group, "category": category,
            "model": model, "hint": hint}


DRIVERS = [
    # Revenue
    _d("newCustomerAcquisition", "New customer acquisition", "Revenue", "revenue",
       "Incremental customers won through better targeting or lead scoring.", "crossSell"),
    _d("crossSell", "Cross-sell", "Revenue", "revenue",
       "Additional products sold to existing customers.", "crossSell"),
    _d("upsell", "Upsell", "Revenue", "revenue",
       "Migration of customers to higher-value propositions.", "crossSell"),
    _d("increasedConversion", "Increased conversion", "Revenue", "revenue",
       "Higher conversion on an existing funnel.", "crossSell"),
    _d("increasedAUM", "Increased AUM", "Revenue", "revenue",
       "Incremental assets under management × net revenue margin.", "balanceGrowth"),
    _d("increasedDeposits", "Increased deposits", "Revenue", "revenue",
       "Incremental deposit balances × net interest margin.", "balanceGrowth"),
    _d("increasedLending", "Increased lending", "Revenue", "revenue",
       "Incremental loan balances × risk-adjusted margin.", "balanceGrowth"),
    _d("tradingRevenue", "Increased trading revenue", "Revenue", "revenue",
       "Incremental flow or spread capture.", "simpleRevenue"),
    _d("feeIncome", "Increased fee income", "Revenue", "revenue",
       "Advisory, transaction or subscription fees.", "simpleRevenue"),
    _d("reducedChurn", "Reduced customer churn", "Revenue", "revenue",
       "Revenue protected rather than revenue created.", "churnReduction"),
    _d("fasterTimeToMarket", "Faster time-to-market", "Revenue", "revenue",
       "Revenue pulled forward by shipping earlier.", "simpleRevenue"),
    # Cost savings
    _d("manualProcessReduction", "Manual process reduction", "Cost Savings", "costSavings",
       "Hours removed from a manual process.", "fteSaving"),
    _d("fteReduction", "FTE reduction", "Cost Savings", "costSavings",
       "Only select where headcount is genuinely removed from plan.", "fteSaving"),
    _d("processingEfficiency", "Processing efficiency", "Cost Savings", "costSavings",
       "Lower unit cost per transaction processed.", "runRateReduction"),
    _d("technologyConsolidation", "Technology consolidation", "Cost Savings", "costSavings",
       "Decommissioned platforms and duplicated tooling.", "runRateReduction"),
    _d("infrastructureOptimisation", "Infrastructure optimisation", "Cost Savings", "costSavings",
       "Compute, storage and licence right-sizing.", "runRateReduction"),
    _d("vendorCostReduction", "Vendor cost reduction", "Cost Savings", "costSavings",
       "Renegotiated or terminated vendor spend.", "runRateReduction"),
    _d("operationalEfficiency", "Operational efficiency", "Cost Savings", "costSavings",
       "Straight-through processing and fewer touchpoints.", "fteSaving"),
    _d("reducedRework", "Reduced rework", "Cost Savings", "costSavings",
       "Fewer breaks, exceptions and reconciliations.", "fteSaving"),
    # Cost avoidance
    _d("avoidHiring", "Avoid future hiring", "Cost Avoidance", "costAvoidance",
       "Roles in the plan that no longer need to be filled.", "costAvoidance"),
    _d("avoidTechSpend", "Avoid future technology spend", "Cost Avoidance", "costAvoidance",
       "Planned build or purchase no longer required.", "costAvoidance"),
    _d("avoidInfraExpansion", "Avoid infrastructure expansion", "Cost Avoidance", "costAvoidance",
       "Capacity uplift deferred or removed.", "costAvoidance"),
    _d("avoidConsulting", "Avoid external consulting", "Cost Avoidance", "costAvoidance",
       "Advisory spend brought in-house.", "costAvoidance"),
    _d("avoidVendorCosts", "Avoid vendor costs", "Cost Avoidance", "costAvoidance",
       "Contract renewals or scale-ups avoided.", "costAvoidance"),
    _d("avoidRegulatoryRemediation", "Avoid regulatory remediation", "Cost Avoidance",
       "costAvoidance", "Remediation programmes avoided through earlier control.", "costAvoidance"),
    # Risk
    _d("fraudReduction", "Fraud reduction", "Risk", "risk",
       "Expected fraud loss before minus after.", "riskReduction"),
    _d("creditLossReduction", "Credit loss reduction", "Risk", "risk",
       "Expected credit loss reduction from earlier warning.", "riskReduction"),
    _d("complianceRisk", "Compliance risk reduction", "Risk", "risk",
       "Lower probability of a compliance breach event.", "riskReduction"),
    _d("operationalRisk", "Operational risk reduction", "Risk", "risk",
       "Lower probability or severity of operational loss.", "riskReduction"),
    _d("cyberRisk", "Cyber risk reduction", "Risk", "risk",
       "Reduced likelihood of a data or security incident.", "riskReduction"),
    _d("modelRisk", "Model risk reduction", "Risk", "risk",
       "Better monitoring reduces model failure exposure.", "riskReduction"),
    _d("regulatoryPenalty", "Regulatory penalty avoidance", "Risk", "risk",
       "Probability-weighted penalty exposure removed.", "riskReduction"),
    # Productivity
    _d("analystProductivity", "Analyst productivity", "Productivity", "productivity",
       "Time released from data wrangling and reporting.", "productivity"),
    _d("rmProductivity", "RM productivity", "Productivity", "productivity",
       "Relationship manager preparation and admin time.", "productivity"),
    _d("developerProductivity", "Developer productivity", "Productivity", "productivity",
       "Engineering time released by reusable data assets.", "productivity"),
    _d("operationsProductivity", "Operations productivity", "Productivity", "productivity",
       "Back- and middle-office handling time.", "productivity"),
    _d("managementProductivity", "Management productivity", "Productivity", "productivity",
       "Leadership time spent assembling numbers.", "productivity"),
    _d("fasterDecisionMaking", "Faster decision making", "Productivity", "productivity",
       "Released time redeployed into revenue-generating work.", "revenueProductivity"),
    # Customer
    _d("improvedCX", "Improved customer experience", "Customer", "strategic",
       "Scored into customer impact — not added to economic value."),
    _d("fasterResponse", "Faster response", "Customer", "productivity",
       "Handling-time reduction with a measurable cost basis.", "productivity"),
    _d("increasedRetention", "Increased retention", "Customer", "revenue",
       "Revenue protected through retention.", "churnReduction"),
    _d("serviceQuality", "Improved service quality", "Customer", "strategic",
       "Scored into customer impact."),
    _d("reducedComplaints", "Reduced complaints", "Customer", "costSavings",
       "Complaint handling and remediation cost.", "runRateReduction"),
    _d("higherNPS", "Higher NPS", "Customer", "strategic", "Scored into customer impact."),
    # Strategic
    _d("fasterInnovation", "Faster innovation", "Strategic", "strategic", "Strategic Value Score only."),
    _d("dataDemocratisation", "Data democratisation", "Strategic", "strategic", "Strategic Value Score only."),
    _d("platformReuse", "Platform reuse", "Strategic", "strategic", "Strategic Value Score only."),
    _d("aiReadiness", "AI readiness", "Strategic", "strategic", "Strategic Value Score only."),
    _d("strategicDifferentiation", "Strategic differentiation", "Strategic", "strategic",
       "Strategic Value Score only."),
]

DRIVER_BY_ID = {d["id"]: d for d in DRIVERS}

DRIVER_GROUPS = ["Revenue", "Cost Savings", "Cost Avoidance", "Risk",
                 "Productivity", "Customer", "Strategic"]

BUSINESS_UNITS = [
    "Consumer Banking", "Wealth Management", "Corporate & Institutional Banking",
    "Global Markets", "Risk & Compliance", "Operations & Technology",
    "Finance", "Group Data & AI", "Transaction Banking",
]

DOMAINS = ["Customer", "Product", "Risk", "Finance", "Channel",
           "Operations", "Regulatory", "Platform"]

# Series colours resolved to hex per theme in app/theme.py; `series` is the slot.
CATEGORY_META = {
    "revenue": {"label": "Revenue value", "short": "Revenue", "series": "s1",
                "blurb": "Incremental and protected revenue attributable to the product."},
    "costSavings": {"label": "Cost savings", "short": "Cost savings", "series": "s3",
                    "blurb": "Run-rate cost genuinely removed from the cost base."},
    "costAvoidance": {"label": "Cost avoidance", "short": "Avoidance", "series": "s4",
                      "blurb": "Probability-weighted future cost that will not now be incurred."},
    "productivity": {"label": "Productivity", "short": "Productivity", "series": "s7",
                     "blurb": "Economic value of capacity released, at fully-loaded cost."},
    "risk": {"label": "Risk reduction", "short": "Risk", "series": "s2",
             "blurb": "Risk-adjusted expected loss reduction — not a guaranteed saving."},
}

CURRENCIES = {
    "SGD": {"symbol": "SGD", "label": "Singapore Dollar"},
    "USD": {"symbol": "USD", "label": "US Dollar"},
    "EUR": {"symbol": "EUR", "label": "Euro"},
    "GBP": {"symbol": "GBP", "label": "Pound Sterling"},
    "AUD": {"symbol": "AUD", "label": "Australian Dollar"},
    "HKD": {"symbol": "HKD", "label": "Hong Kong Dollar"},
    "INR": {"symbol": "INR", "label": "Indian Rupee"},
}
