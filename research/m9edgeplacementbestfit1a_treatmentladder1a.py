#!/usr/bin/env python3
"""Research-only edge-case rerender rollback ladder.

Assumes BESTFIT1A has already selected a DARK candidate. HOLD always returns
baseline. DARK candidates are tested strongest-to-weakest against the same
finished-highlight budget used by HIGHLIGHTBUDGET1A.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

Q95_CEILING_Y = 242.0
BRIGHT224_DELTA_MAX = 0.040
LADDER = (0.50, 0.35, 0.25, 0.15, 0.0)
DARK_SELECTORS = {"DARK_INTENT", "DARK_ZERO_INTENT", "DARK_FOREGROUND"}


def run(rows, selector):
    rows = {round(float(r['ev']),2): r for r in rows}
    base = rows.get(0.0)
    if base is None:
        raise ValueError('0 EV baseline required')
    if selector not in DARK_SELECTORS:
        return {
            'schema':'m9edgeplacementbestfit1a.treatmentladder1a.shadow.v1',
            'mode':'offline_shadow_no_live_mutation',
            'selector':selector,
            'chosenEv':0.0,
            'attempts':[],
            'reason':'HOLD_or_unknown_selector_publish_frozen_baseline',
        }
    b0=float(base['bright224'])
    attempts=[]
    chosen=0.0
    for ev in LADDER:
        r=rows.get(round(ev,2))
        if r is None:
            continue
        q95=float(r['q95Y']); b=float(r['bright224']); delta=b-b0
        ok=q95<=Q95_CEILING_Y and delta<=BRIGHT224_DELTA_MAX+1e-12
        attempts.append({'ev':ev,'q95Y':q95,'bright224':b,'bright224Delta':delta,'insideBudget':ok})
        if ok:
            chosen=ev
            break
    return {
        'schema':'m9edgeplacementbestfit1a.treatmentladder1a.shadow.v1',
        'mode':'offline_shadow_no_live_mutation',
        'selector':selector,
        'chosenEv':chosen,
        'attempts':attempts,
        'budget':{'q95CeilingY':Q95_CEILING_Y,'bright224DeltaMax':BRIGHT224_DELTA_MAX},
        'ladder':list(LADDER),
        'thresholdStatus':'provisional_falsification_seed_not_frozen_not_live',
        'reason':'first_strong_to_weak_candidate_inside_finished_highlight_budget',
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('metrics_json',type=Path)
    ap.add_argument('--selector',required=True)
    a=ap.parse_args()
    print(json.dumps(run(json.loads(a.metrics_json.read_text()),a.selector),indent=2,sort_keys=True))

if __name__=='__main__':
    main()
