#!/usr/bin/env python3
"""Attach the independent visual M9ness axis to EDGEPLACEMENT1A output.

Research-only. This postprocessor deliberately runs *after* placement feature
extraction/rule search so M9_STRONG vs M9_IMPROVABLE cannot become accidental
authority for GOOD/BRIGHT_FAIL/DARK_FAIL selection.

Input labels CSV columns:
    pattern,label,m9ness,notes

Allowed m9ness values:
    M9_STRONG
    M9_IMPROVABLE

The placement label remains whatever EDGEPLACEMENT1A produced. This script only
adds visual-review metadata and reports GOOD-subset M9ness counts.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

M9NESS = {"M9_STRONG", "M9_IMPROVABLE"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path, required=True,
                    help="edge_features.csv from m9edgeplacement1a_replay.py")
    ap.add_argument("--labels", type=Path, required=True,
                    help="CSV with pattern,label,m9ness,notes")
    ap.add_argument("--out", type=Path,
                    default=Path("M9EDGEPLACEMENT1A_RESULTS/edge_features_with_m9ness.csv"))
    ap.add_argument("--summary", type=Path,
                    default=Path("M9EDGEPLACEMENT1A_RESULTS/m9ness_summary.json"))
    a = ap.parse_args()

    features = read_csv(a.features)
    labels = read_csv(a.labels)

    review = []
    for r in labels:
        pattern = (r.get("pattern") or "").strip()
        m9ness = (r.get("m9ness") or "").strip().upper()
        if not pattern or not m9ness:
            continue
        if m9ness not in M9NESS:
            raise SystemExit(f"unknown m9ness value {m9ness!r} for {pattern}")
        review.append({
            "pattern": pattern,
            "m9ness": m9ness,
            "notes": (r.get("notes") or "").strip(),
        })

    matched_review_patterns: set[str] = set()
    out_rows = []
    for row in features:
        key = row.get("captureKey", "")
        hits = [r for r in review if r["pattern"] in key]
        m9ness = ""
        m9notes = ""
        if hits:
            vals = {r["m9ness"] for r in hits}
            if len(vals) != 1:
                raise SystemExit(f"conflicting m9ness labels for {key}: {sorted(vals)}")
            m9ness = hits[0]["m9ness"]
            m9notes = " | ".join(r["notes"] for r in hits if r["notes"])
            matched_review_patterns.update(r["pattern"] for r in hits)
        out_rows.append({**row, "m9ness": m9ness, "m9nessNotes": m9notes})

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    write_csv(a.out, out_rows)

    good = [r for r in out_rows if r.get("label") == "GOOD"]
    summary = {
        "schema": "m9edgeplacement1a.m9ness.v1",
        "researchOnly": True,
        "placementTrainingAuthority": False,
        "purpose": "carry independent visual M9ness labels without allowing them to influence EDGEPLACEMENT gate search",
        "recordCount": len(out_rows),
        "m9nessCounts": {k: sum(r.get("m9ness") == k for r in out_rows) for k in sorted(M9NESS)},
        "goodM9nessCounts": {k: sum(r.get("m9ness") == k for r in good) for k in sorted(M9NESS)},
        "matchedReviewPatterns": sorted(matched_review_patterns),
        "unmatchedReviewPatterns": sorted({r["pattern"] for r in review} - matched_review_patterns),
        "invariant": "GOOD + M9_IMPROVABLE remains GOOD for placement-gate training",
    }
    a.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
