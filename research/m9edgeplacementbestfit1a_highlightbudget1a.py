#!/usr/bin/env python3
"""
HIGHLIGHTBUDGET1A research-only treatment ceiling.

This script does NOT classify photographs and MUST NOT be wired into live capture.
It assumes BESTFIT1A has already selected a DARK rescue candidate and consumes an
offline pre-curve EV sweep metrics JSON. It chooses the strongest tested EV that
stays inside a provisional finished-highlight budget.

The selector and treatment remain deliberately separate.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

Q95_CEILING_Y = 242.0
BRIGHT224_DELTA_MAX = 0.040
MAX_EV = 0.50
DARK_SELECTORS = {"DARK_INTENT", "DARK_ZERO_INTENT", "DARK_FOREGROUND"}


def choose(rows, selector: str):
    if selector not in DARK_SELECTORS:
        return {
            "selector": selector,
            "chosenEv": 0.0,
            "reason": "selector_hold_or_unknown_no_treatment",
            "budget": {
                "q95CeilingY": Q95_CEILING_Y,
                "bright224DeltaMax": BRIGHT224_DELTA_MAX,
                "maxEv": MAX_EV,
            },
        }
    rows = sorted(rows, key=lambda r: float(r["ev"]))
    baseline = next((r for r in rows if abs(float(r["ev"])) < 1e-9), rows[0])
    b0 = float(baseline["bright224"])
    eligible = []
    audited = []
    for r in rows:
        ev = float(r["ev"])
        q95 = float(r["q95Y"])
        b = float(r["bright224"])
        delta = b - b0
        ok = ev <= MAX_EV + 1e-9 and q95 <= Q95_CEILING_Y and delta <= BRIGHT224_DELTA_MAX + 1e-12
        audited.append({
            "ev": ev,
            "q95Y": q95,
            "bright224": b,
            "bright224Delta": delta,
            "eligible": ok,
        })
        if ok:
            eligible.append(ev)
    chosen = max(eligible) if eligible else 0.0
    return {
        "schema": "m9edgeplacementbestfit1a.highlightbudget1a.shadow.v1",
        "mode": "offline_treatment_shadow_no_live_mutation",
        "selector": selector,
        "chosenEv": chosen,
        "reason": "strongest_tested_ev_inside_finished_highlight_budget",
        "baselineBright224": b0,
        "budget": {
            "q95CeilingY": Q95_CEILING_Y,
            "bright224DeltaMax": BRIGHT224_DELTA_MAX,
            "maxEv": MAX_EV,
        },
        "audit": audited,
        "thresholdStatus": "provisional_falsification_seed_not_frozen_not_live",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metrics_json", type=Path)
    ap.add_argument("--selector", required=True)
    args = ap.parse_args()
    rows = json.loads(args.metrics_json.read_text())
    print(json.dumps(choose(rows, args.selector), indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
