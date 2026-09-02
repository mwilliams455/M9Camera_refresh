#!/usr/bin/env python3
"""Self-contained smoke regression for LUMA2.2 using eight v0.7J field metrics."""
import json
from pathlib import Path
from luma2_2_backlight_scorer_reference import score

HERE = Path(__file__).resolve().parent
ROWS = json.loads((HERE / "luma2_2_independent_inputs.json").read_text())
EXPECTED = {
    "180145": (False, 0.000000),
    "180202": (True,  0.750000),
    "180216": (True,  0.41935670457692387),
    "180236": (True,  0.5474369682478378),
    "180311": (True,  0.750000),
    "181706": (False, 0.000000),
    "182446": (False, 0.000000),
    "182457": (True,  0.750000),
}

def minimal(r):
    return {
        "photonExposureDecision": {"preview": {"exposureEnergyIsoSeconds": r["energy"]}},
        "subjectMotion": {"previewLuma": {
            "global": {
                "median": r["median"], "q95": r["q95"], "q99": r["q99"],
                "darkFractionLE64": r["dark64"], "brightFractionGE192": r["bright192"],
                "q95MinusMedian": r["sep"],
            },
            "center50": {"medianMinusGlobalMedian": r["centerDelta"]},
        }},
    }

for r in ROWS:
    got = score(minimal(r))
    want_apply, want_ev = EXPECTED[r["frame"]]
    assert got["wouldApply"] == want_apply, (r["frame"], got)
    assert abs(got["recommendedExposureCorrectionEv"] - want_ev) < 1e-9, (r["frame"], got)

print("LUMA2.2 independent 8-frame smoke regression: PASS")
