"""Scenario levers — a port of src/engine/scenarios.ts."""
from __future__ import annotations

import copy

from .valuation import value_product

DEFAULT_SCENARIOS = {
    "conservative": {"adoption": 0.7, "revenueUplift": 0.6, "costSavings": 0.7,
                     "attribution": 0.75, "implementationCost": 1.25, "runCost": 1.15},
    "base": {"adoption": 1.0, "revenueUplift": 1.0, "costSavings": 1.0,
             "attribution": 1.0, "implementationCost": 1.0, "runCost": 1.0},
    "upside": {"adoption": 1.15, "revenueUplift": 1.35, "costSavings": 1.25,
               "attribution": 1.1, "implementationCost": 0.9, "runCost": 0.92},
}

LEVER_META = [
    {"key": "adoption", "label": "Adoption",
     "help": "Scales adoption, conversion and realisation assumptions."},
    {"key": "revenueUplift", "label": "Revenue uplift", "help": "Scales all revenue benefit lines."},
    {"key": "costSavings", "label": "Cost & efficiency benefits",
     "help": "Scales savings, avoidance, productivity and risk lines."},
    {"key": "attribution", "label": "Attribution",
     "help": "Scales the share of the outcome credited to this product."},
    {"key": "implementationCost", "label": "Implementation cost",
     "help": "Scales build and change investment."},
    {"key": "runCost", "label": "Annual run cost", "help": "Scales technology and run costs."},
]

SCENARIO_KEYS = ["conservative", "base", "upside"]
SCENARIO_LABELS = {"conservative": "Conservative", "base": "Base Case", "upside": "Upside"}


def run_scenarios(p, settings):
    scenario_set = p.get("scenarios") or DEFAULT_SCENARIOS
    return [{
        "key": key,
        "label": SCENARIO_LABELS[key],
        "levers": scenario_set[key],
        "valuation": value_product(p, settings, scenario_set[key]),
    } for key in SCENARIO_KEYS]
