#!/usr/bin/env python3
"""Guard against interpreting EDGEPLACEMENT rule search on a tiny corpus.

This is research-process infrastructure only. It never changes pixels or live code.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

DEFAULTS = {"GOOD": 30, "BOUNDARY": 2, "BRIGHT_FAIL": 2, "DARK_FAIL": 2}


def count_labels(path: Path) -> dict[str, int]:
    counts = {k: 0 for k in DEFAULTS}
    with path.open(newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lab = (r.get("researchLabel") or r.get("label") or "").strip().upper()
            if lab in counts:
                counts[lab] += 1
    return counts


def evaluate(counts: dict[str, int], minimums: dict[str, int]) -> dict:
    common_ready = counts["GOOD"] >= minimums["GOOD"] and counts["BOUNDARY"] >= minimums["BOUNDARY"]
    targets = {}
    for target in ("BRIGHT_FAIL", "DARK_FAIL"):
        ready = common_ready and counts[target] >= minimums[target]
        targets[target] = {
            "readyForRuleInterpretation": ready,
            "available": {"GOOD": counts["GOOD"], "BOUNDARY": counts["BOUNDARY"], target: counts[target]},
            "minimum": {"GOOD": minimums["GOOD"], "BOUNDARY": minimums["BOUNDARY"], target: minimums[target]},
            "disposition": "candidate rules may be compared, still research-only" if ready else "exploratory only; do not interpret zero-FP result",
        }
    return {
        "schema":"m9edgeplacement1a.readiness.v1",
        "researchOnly": True,
        "counts": counts,
        "minimums": minimums,
        "targets": targets,
        "productionNote":"Even readiness here is not promotion. Broad frozen regression and visual validation remain mandatory.",
    }


def self_test() -> None:
    a = evaluate({"GOOD":1,"BOUNDARY":0,"BRIGHT_FAIL":6,"DARK_FAIL":5}, DEFAULTS)
    assert not a["targets"]["BRIGHT_FAIL"]["readyForRuleInterpretation"]
    b = evaluate({"GOOD":40,"BOUNDARY":2,"BRIGHT_FAIL":6,"DARK_FAIL":5}, DEFAULTS)
    assert b["targets"]["BRIGHT_FAIL"]["readyForRuleInterpretation"]
    assert b["targets"]["DARK_FAIL"]["readyForRuleInterpretation"]
    print("M9EDGEPLACEMENT1A readiness self-test PASS")


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--labels", type=Path, help="edge_features_research_labels.csv or compatible label CSV")
    ap.add_argument("--out", type=Path, default=Path("M9EDGEPLACEMENT1A_RESULTS/readiness.json"))
    ap.add_argument("--min-good", type=int, default=DEFAULTS["GOOD"])
    ap.add_argument("--min-boundary", type=int, default=DEFAULTS["BOUNDARY"])
    ap.add_argument("--min-bright", type=int, default=DEFAULTS["BRIGHT_FAIL"])
    ap.add_argument("--min-dark", type=int, default=DEFAULTS["DARK_FAIL"])
    ap.add_argument("--self-test", action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.labels:
        ap.error("--labels required unless --self-test")
    mins={"GOOD":a.min_good,"BOUNDARY":a.min_boundary,"BRIGHT_FAIL":a.min_bright,"DARK_FAIL":a.min_dark}
    result=evaluate(count_labels(a.labels),mins)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
