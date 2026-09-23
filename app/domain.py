"""Core domain constants — a port of src/types/index.ts.

Products are carried as plain dicts with exactly the same shape as the
TypeScript interfaces, so the engine, the JSON catalogue and session state all
speak the same structure.
"""
from __future__ import annotations

CURRENCY_CODES = ["SGD", "USD", "EUR", "GBP", "AUD", "HKD", "INR"]

PRODUCT_TYPES = [
    "Data Product", "Data Application", "Data Service / API", "Dashboard",
    "AI / ML Product", "GenAI Application", "Automation", "Decision Engine",
    "Data Platform Capability", "Regulatory / Compliance Product",
]

LIFECYCLE_ORDER = [
    "Idea", "Business Case", "Approved", "Build",
    "Pilot", "Production", "Scale", "Optimise", "Retire",
]
LIFECYCLE_STAGES = LIFECYCLE_ORDER

VALUE_CATEGORIES = ["revenue", "costSavings", "costAvoidance", "productivity", "risk"]
VALUE_CLASSES = ["direct", "indirect"]
EVIDENCE_TYPES = ["Actual", "Pilot", "Benchmark", "Estimate", "Management Assumption"]
VALUE_MATURITIES = ["Proven", "Expected", "Potential"]
STRATEGIC_PRIORITIES = ["Critical", "High", "Medium", "Low"]
USAGE_FREQUENCIES = ["Real-time", "Daily", "Weekly", "Monthly", "Quarterly", "Ad hoc"]
GEOGRAPHIC_SCOPES = ["Single market", "Regional", "Group-wide", "Global"]

EMPTY_INVESTMENT = {
    "buildMonths": 6,
    "build": {
        "internalDevelopment": 0, "externalDevelopment": 0, "consulting": 0,
        "dataEngineering": 0, "mlDevelopment": 0, "uxProductManagement": 0,
    },
    "technology": {
        "cloud": 0, "onPremInfrastructure": 0, "gpu": 0, "llmApi": 0,
        "softwareLicences": 0, "dataVendors": 0, "storage": 0, "compute": 0,
    },
    "run": {
        "support": 0, "operations": 0, "modelMonitoring": 0, "dataQuality": 0,
        "cybersecurity": 0, "maintenance": 0, "productTeam": 0,
    },
    "change": {
        "training": 0, "changeManagement": 0, "communications": 0, "businessAdoption": 0,
    },
}

INVESTMENT_GROUPS = [
    {"key": "build", "label": "Build cost", "note": "One-off delivery cost",
     "fields": ["internalDevelopment", "externalDevelopment", "consulting",
                "dataEngineering", "mlDevelopment", "uxProductManagement"]},
    {"key": "technology", "label": "Technology cost", "note": "Annual run-rate",
     "fields": ["cloud", "onPremInfrastructure", "gpu", "llmApi",
                "softwareLicences", "dataVendors", "storage", "compute"]},
    {"key": "run", "label": "Run cost", "note": "Annual run-rate",
     "fields": ["support", "operations", "modelMonitoring", "dataQuality",
                "cybersecurity", "maintenance", "productTeam"]},
    {"key": "change", "label": "Change & adoption", "note": "One-off",
     "fields": ["training", "changeManagement", "communications", "businessAdoption"]},
]

COST_FIELD_LABELS = {
    "internalDevelopment": "Internal development", "externalDevelopment": "External development",
    "consulting": "Consulting", "dataEngineering": "Data engineering",
    "mlDevelopment": "AI / ML development", "uxProductManagement": "UX & product management",
    "cloud": "Cloud", "onPremInfrastructure": "On-premise infrastructure", "gpu": "GPU",
    "llmApi": "LLM / API", "softwareLicences": "Software licences", "dataVendors": "Data vendors",
    "storage": "Storage", "compute": "Compute", "support": "Support", "operations": "Operations",
    "modelMonitoring": "Model monitoring", "dataQuality": "Data quality",
    "cybersecurity": "Cybersecurity", "maintenance": "Maintenance", "productTeam": "Product team",
    "training": "Training", "changeManagement": "Change management",
    "communications": "Communications", "businessAdoption": "Business adoption",
}

DEFAULT_CONFIDENCE = {
    "baselineQuality": 60, "dataAvailability": 60, "assumptionStrength": 60,
    "historicalEvidence": 50, "attributionConfidence": 55, "adoptionConfidence": 55,
    "financialValidation": 45, "measurementMaturity": 50,
}

DEFAULT_STRATEGIC = {
    "strategicAlignment": 65, "customerImpact": 55, "reusability": 50,
    "riskReduction": 45, "dataDemocratisation": 50, "aiReadiness": 50,
}

DEFAULT_SETTINGS = {
    "currency": "SGD",
    "discountRate": 0.10,
    "horizonYears": 5,
    "annualWorkingHours": 1800,
    "priorityWeights": {
        "economicValue": 30, "strategicAlignment": 20, "timeToValue": 15,
        "confidence": 10, "customerImpact": 10, "riskReduction": 10, "reusability": 5,
    },
    "organisationName": "Meridian Bank",
    "theme": "light",
    "guardrailsEnabled": True,
}

WEIGHT_META = [
    {"key": "economicValue", "label": "Economic Value",
     "help": "Log-normalised three-year economic value relative to the largest product in the portfolio."},
    {"key": "strategicAlignment", "label": "Strategic Alignment",
     "help": "Fit with the stated data and AI strategy."},
    {"key": "timeToValue", "label": "Time to Value", "help": "How quickly measurable value arrives."},
    {"key": "confidence", "label": "Confidence",
     "help": "Evidence and delivery confidence, from the assumption quality behind the case."},
    {"key": "customerImpact", "label": "Customer Impact",
     "help": "Effect on customer experience and outcomes."},
    {"key": "riskReduction", "label": "Risk Reduction",
     "help": "Blend of risk score and the risk share of economic value."},
    {"key": "reusability", "label": "Reusability",
     "help": "How much of the product can be reused by other teams."},
]
