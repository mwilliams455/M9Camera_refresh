#!/usr/bin/env python3
"""Audit EDGEPLACEMENT candidate rules for diagnostic-schema coverage.

Research-only. Historical GOOD/BOUNDARY controls can come from older diagnostic
builds than the September-4 BRIGHT_FAIL corpus. Missing feature values therefore
must never be interpreted as a negative classifier result. This tool rejects a
candidate rule unless every feature used by the rule is sufficiently populated
in the classes needed to evaluate its specificity and recall.

Pipeline:
  m9edgeplacement1a_replay.py
    -> m9edgeplacement1a_conjunction_search.py
    -> THIS COVERAGE AUDIT
    -> readiness / human interpretation

No capture, TC20, renderer or JPEG mutation occurs here.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

LABELS = ("GOOD", "BOUNDARY", "BRIGHT_FAIL", "DARK_FAIL")
TARGETS = ("BRIGHT_FAIL", "DARK_FAIL")


def num(v: Any) -> float | None:
    try:
        if v is None or isinstance(v, bool) or v == "":
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def research_label(row: dict[str, str]) -> str:
    return (row.get("researchLabel") or row.get("label") or "").strip().upper()


def feature_coverage(rows: list[dict[str, str]], feature: str, label: str) -> tuple[int, int, float | None]:
    cohort = [r for r in rows if research_label(r) == label]
    n = len(cohort)
    present = sum(num(r.get(feature)) is not None for r in cohort)
    return present, n, present / n if n else None


def rule_features(rule: dict[str, str]) -> list[str]:
    out = []
    for k in ("feature1", "feature2"):
        v = (rule.get(k) or "").strip()
        if v and v not in out:
            out.append(v)
    return out


def audit_rule(
    rows: list[dict[str, str]],
    rule: dict[str, str],
    min_good: float,
    min_target: float,
    min_boundary: float,
    min_other_tail: float,
) -> dict[str, Any]:
    target = (rule.get("target") or "").strip().upper()
    if target not in TARGETS:
        return {**rule, "coverageEligible": False, "coverageRejectReason": "unknown_target"}
    other = "DARK_FAIL" if target == "BRIGHT_FAIL" else "BRIGHT_FAIL"
    feats = rule_features(rule)
    if not feats:
        return {**rule, "coverageEligible": False, "coverageRejectReason": "no_features"}

    details: list[str] = []
    eligible = True
    reasons: list[str] = []
    aggregate: dict[str, float] = {}

    for feat in feats:
        for lab, threshold, key in (
            ("GOOD", min_good, "good"),
            (target, min_target, "target"),
            ("BOUNDARY", min_boundary, "boundary"),
            (other, min_other_tail, "otherTail"),
        ):
            present, total, frac = feature_coverage(rows, feat, lab)
            details.append(f"{feat}:{lab}={present}/{total}" if total else f"{feat}:{lab}=NA")
            # A class absent from the exact corpus cannot be coverage-qualified;
            # it is handled by readiness rather than making every rule fail.
            if total == 0:
                continue
            aggregate[f"{key}CoverageMin"] = min(
                aggregate.get(f"{key}CoverageMin", 1.0), frac if frac is not None else 0.0
            )
            if frac is not None and frac + 1e-12 < threshold:
                eligible = False
                reasons.append(f"{feat}_{lab.lower()}_coverage_{frac:.3f}_lt_{threshold:.3f}")

    out: dict[str, Any] = dict(rule)
    out.update(aggregate)
    out["coverageEligible"] = eligible
    out["coverageRejectReason"] = " | ".join(reasons)
    out["coverageDetail"] = " ; ".join(details)
    return out


def audit_rules(
    features: list[dict[str, str]],
    rules: list[dict[str, str]],
    min_good: float,
    min_target: float,
    min_boundary: float,
    min_other_tail: float,
) -> list[dict[str, Any]]:
    return [
        audit_rule(features, r, min_good, min_target, min_boundary, min_other_tail)
        for r in rules
    ]


def self_test() -> None:
    # 10 GOOD and two examples of each non-GOOD class. `newOnly` is deliberately
    # present only in BRIGHT_FAIL, reproducing the dangerous cross-build case:
    # missing GOOD values would otherwise look like zero false positives.
    rows: list[dict[str, str]] = []
    for i in range(10):
        rows.append({"researchLabel": "GOOD", "shared": str(10 + i), "newOnly": ""})
    rows += [
        {"researchLabel": "BOUNDARY", "shared": "25", "newOnly": ""},
        {"researchLabel": "BOUNDARY", "shared": "27", "newOnly": ""},
        {"researchLabel": "BRIGHT_FAIL", "shared": "90", "newOnly": "0.9"},
        {"researchLabel": "BRIGHT_FAIL", "shared": "92", "newOnly": "0.8"},
        {"researchLabel": "DARK_FAIL", "shared": "3", "newOnly": ""},
        {"researchLabel": "DARK_FAIL", "shared": "5", "newOnly": ""},
    ]
    fake_rules = [
        {"target": "BRIGHT_FAIL", "feature1": "newOnly", "feature2": ""},
        {"target": "BRIGHT_FAIL", "feature1": "shared", "feature2": ""},
    ]
    audited = audit_rules(rows, fake_rules, 0.8, 0.8, 0.5, 0.5)
    assert audited[0]["coverageEligible"] is False, audited[0]
    assert "good_coverage" in audited[0]["coverageRejectReason"], audited[0]
    assert audited[1]["coverageEligible"] is True, audited[1]
    print("M9EDGEPLACEMENT1A rule-coverage self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path,
                    help="edge_features_research_labels.csv from conjunction search")
    ap.add_argument("--single", type=Path, help="candidate_rules_single.csv")
    ap.add_argument("--and2", type=Path, help="candidate_rules_and2.csv")
    ap.add_argument("--out", type=Path, default=Path("M9EDGEPLACEMENT1A_RESULTS"))
    ap.add_argument("--min-good-coverage", type=float, default=0.80)
    ap.add_argument("--min-target-coverage", type=float, default=0.80)
    ap.add_argument("--min-boundary-coverage", type=float, default=0.67)
    ap.add_argument("--min-other-tail-coverage", type=float, default=0.50)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        self_test()
        return
    if not a.features or not a.single or not a.and2:
        ap.error("--features, --single and --and2 are required unless --self-test")
    for name, value in (
        ("min-good-coverage", a.min_good_coverage),
        ("min-target-coverage", a.min_target_coverage),
        ("min-boundary-coverage", a.min_boundary_coverage),
        ("min-other-tail-coverage", a.min_other_tail_coverage),
    ):
        if not 0 <= value <= 1:
            ap.error(f"--{name} must be between 0 and 1")

    features = read_csv(a.features)
    singles = audit_rules(features, read_csv(a.single), a.min_good_coverage,
                          a.min_target_coverage, a.min_boundary_coverage,
                          a.min_other_tail_coverage)
    pairs = audit_rules(features, read_csv(a.and2), a.min_good_coverage,
                        a.min_target_coverage, a.min_boundary_coverage,
                        a.min_other_tail_coverage)

    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out / "candidate_rules_single_coverage.csv", singles)
    write_csv(a.out / "candidate_rules_and2_coverage.csv", pairs)

    all_rules = singles + pairs
    summary: dict[str, Any] = {
        "schema": "m9edgeplacement1a.rulecoverage.v1",
        "mode": "research_only_missing_values_never_count_as_clean_negatives",
        "thresholds": {
            "good": a.min_good_coverage,
            "target": a.min_target_coverage,
            "boundary": a.min_boundary_coverage,
            "otherTail": a.min_other_tail_coverage,
        },
        "researchLabelCounts": {
            lab: sum(research_label(r) == lab for r in features) for lab in LABELS
        },
        "ruleCount": len(all_rules),
        "coverageEligibleRuleCount": sum(bool(r.get("coverageEligible")) for r in all_rules),
        "targets": {},
        "invariant": "A rule cannot earn specificity credit from missing diagnostics; readiness and coverage must both pass before interpretation.",
    }
    for target in TARGETS:
        subset = [r for r in all_rules if (r.get("target") or "").upper() == target]
        eligible = [r for r in subset if r.get("coverageEligible")]
        summary["targets"][target] = {
            "ruleCount": len(subset),
            "coverageEligibleRuleCount": len(eligible),
            "zeroGoodAndBoundaryFpCoverageEligibleCount": sum(
                bool(r.get("coverageEligible"))
                and str(r.get("goodFp", "")) in {"0", "0.0"}
                and str(r.get("boundaryFp", "")) in {"0", "0.0"}
                for r in subset
            ),
        }
    (a.out / "rule_coverage_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
