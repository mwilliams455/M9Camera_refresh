#!/usr/bin/env python3
"""EDGEPLACEMENTLIFT1A conservative DARK gate probe.

Research-only. This tool does not modify capture exposure, TC20, the renderer,
or JPEG pixels. It evaluates the current Part-3 spatial-collapse hypothesis
against already-extracted finished-render geometry.

The thresholds below are descriptive probe values observed in the historical
same-build cohort. They are NOT production constants. Frozen remains mandatory
fallback until prospective hard negatives (especially 084858) are tested by a
live diagnostic-only gate.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

PROBE = {
    "achievedIntentEvMin": 0.10,
    "upperLowerShiftEvMin": 1.50,
    "renderCellMedianP75Max": 30.0,
    "integralRelativeShiftEvMax": 0.15,
}
LIFT_BANK_EV = (0.15, 0.25, 0.35)


def num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def active(row: dict[str, Any]) -> bool:
    intent = num(row.get("achievedIntentEv") or row.get("intent"))
    shift = num(row.get("upperLowerShiftEv") or row.get("upperLowerShift"))
    body = num(row.get("renderCellMedianP75") or row.get("cellMedP75"))
    integral = num(row.get("integralRelativeShiftEv") or row.get("integralRelativeShift"))
    if None in (intent, shift, body, integral):
        return False
    return bool(
        intent >= PROBE["achievedIntentEvMin"]
        and shift >= PROBE["upperLowerShiftEvMin"]
        and body <= PROBE["renderCellMedianP75Max"]
        and integral <= PROBE["integralRelativeShiftEvMax"]
    )


def self_test() -> None:
    rows = [
        {"id":"163553","label":"GOOD","intent":0.0,"upperLowerShift":-0.267,"cellMedP75":26.25,"integralRelativeShift":0.267},
        {"id":"163702","label":"BOUNDARY","intent":0.0,"upperLowerShift":0.737,"cellMedP75":4.0,"integralRelativeShift":0.486},
        {"id":"163847","label":"GOOD","intent":0.0,"upperLowerShift":0.237,"cellMedP75":22.0,"integralRelativeShift":0.265},
        {"id":"164019","label":"DARK_CANDIDATE","intent":0.299,"upperLowerShift":2.492,"cellMedP75":15.25,"integralRelativeShift":-0.018},
        {"id":"164048","label":"DARK_FAIL","intent":0.138,"upperLowerShift":2.865,"cellMedP75":24.75,"integralRelativeShift":0.097},
        {"id":"164247","label":"GOOD","intent":0.0,"upperLowerShift":0.420,"cellMedP75":27.25,"integralRelativeShift":0.185},
        {"id":"164331","label":"GOOD","intent":0.0,"upperLowerShift":-1.218,"cellMedP75":16.25,"integralRelativeShift":0.475},
        {"id":"164402","label":"GOOD","intent":0.202,"upperLowerShift":0.459,"cellMedP75":13.5,"integralRelativeShift":0.529},
    ]
    hits = [r["id"] for r in rows if active(r)]
    assert hits == ["164019", "164048"], hits
    print("EDGEPLACEMENTLIFT1A gate probe self-test PASS", hits)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("features", type=Path, nargs="?")
    ap.add_argument("--out", type=Path, default=Path("edgeplacementlift1a_gate_probe.csv"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        return
    if not a.features:
        ap.error("features CSV required unless --self-test")
    with a.features.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        q = dict(row)
        q["edgePlacementLift1aProbe"] = active(row)
        q["treatmentBankEv"] = "|".join(f"+{x:.2f}" for x in LIFT_BANK_EV) if q["edgePlacementLift1aProbe"] else "FROZEN"
        out.append(q)
    fields = []
    for r in out:
        for k in r:
            if k not in fields:
                fields.append(k)
    with a.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(out)
    print(json.dumps({
        "schema":"m9edgeplacementlift1a.gateprobe.v1",
        "researchOnly":True,
        "probe":PROBE,
        "liftBankEv":LIFT_BANK_EV,
        "activeCount":sum(active(r) for r in rows),
        "invariant":"Frozen is mandatory fallback; no live pixel mutation is authorized by this probe.",
    }, indent=2))


if __name__ == "__main__":
    main()
