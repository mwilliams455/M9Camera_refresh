#!/usr/bin/env python3
"""M9EDGEPLACEMENT1A conservative asymmetric rule search.

Research-only postprocessor for edge_features.csv produced by
m9edgeplacement1a_replay.py. It never modifies capture, TC20, renderer, or JPEGs.

It searches BRIGHT_FAIL and DARK_FAIL independently, ranks GOOD false positives
first, BOUNDARY false positives second, and tail recall third, and permits small
interpretable two-feature AND rules when single features are insufficient.
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path
from typing import Any

PLACEMENT = {"GOOD", "BRIGHT_FAIL", "DARK_FAIL"}
RESEARCH_LABELS = PLACEMENT | {"BOUNDARY"}
TARGETS = ("BRIGHT_FAIL", "DARK_FAIL")
META = {
    "captureKey", "label", "labelNotes", "m9ness", "m9nessNotes",
    "sources", "sourceCount", "darkTailProbe", "brightLowKeyProbe",
}


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


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)


def read_labels(path: Path) -> list[dict[str, str]]:
    out = []
    for r in read_csv(path):
        pattern = (r.get("pattern") or r.get("frame") or "").strip()
        label = (r.get("label") or "").strip().upper()
        if not pattern or not label:
            continue
        if label not in RESEARCH_LABELS:
            raise SystemExit(f"unknown research label {label!r} for {pattern}")
        out.append({
            "pattern": pattern,
            "label": label,
            "m9ness": (r.get("m9ness") or "").strip().upper(),
            "notes": (r.get("notes") or "").strip(),
        })
    return out


def apply_labels(rows: list[dict[str, str]], labels: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    matched: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = row.get("captureKey", "")
        hits = [r for r in labels if r["pattern"] in key]
        if hits:
            labs = {r["label"] for r in hits}
            if len(labs) != 1:
                raise SystemExit(f"conflicting research labels for {key}: {sorted(labs)}")
            row = dict(row)
            row["researchLabel"] = hits[0]["label"]
            row["researchM9ness"] = hits[0]["m9ness"]
            row["researchNotes"] = " | ".join(r["notes"] for r in hits if r["notes"])
            matched.update(r["pattern"] for r in hits)
        else:
            row = dict(row)
            row["researchLabel"] = ""
            row["researchM9ness"] = ""
            row["researchNotes"] = ""
        out.append(row)
    unmatched = sorted({r["pattern"] for r in labels} - matched)
    return out, unmatched


def numeric_features(rows: list[dict[str, Any]]) -> list[str]:
    banned = META | {"researchLabel", "researchM9ness", "researchNotes", "tc20Binding"}
    feats = []
    for k in sorted({k for r in rows for k in r} - banned):
        vals = [num(r.get(k)) for r in rows]
        vals = [v for v in vals if v is not None]
        if len(vals) >= 4 and len(set(vals)) >= 2:
            feats.append(k)
    return feats


def thresholds(values: list[float], cap: int = 48) -> list[float]:
    u = sorted(set(values))
    mids = [(a+b)/2 for a,b in zip(u,u[1:])]
    if len(mids) <= cap:
        return mids
    idx = sorted({round(i*(len(mids)-1)/(cap-1)) for i in range(cap)})
    return [mids[i] for i in idx]


def hit_atom(row: dict[str, Any], atom: dict[str, Any]) -> bool:
    x = num(row.get(atom["feature"]))
    if x is None:
        return False
    return x <= atom["threshold"] if atom["op"] == "<=" else x >= atom["threshold"]


def stats(rows: list[dict[str, Any]], target: str, atoms: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [r for r in rows if all(hit_atom(r, a) for a in atoms)]
    good_n = sum(r.get("researchLabel") == "GOOD" for r in rows)
    boundary_n = sum(r.get("researchLabel") == "BOUNDARY" for r in rows)
    target_n = sum(r.get("researchLabel") == target for r in rows)
    other = "DARK_FAIL" if target == "BRIGHT_FAIL" else "BRIGHT_FAIL"
    tp = sum(r.get("researchLabel") == target for r in selected)
    good_fp = sum(r.get("researchLabel") == "GOOD" for r in selected)
    boundary_fp = sum(r.get("researchLabel") == "BOUNDARY" for r in selected)
    other_tail_fp = sum(r.get("researchLabel") == other for r in selected)
    labelled_selected = sum(r.get("researchLabel") in RESEARCH_LABELS for r in selected)
    return {
        "target": target,
        "targetN": target_n,
        "goodN": good_n,
        "boundaryN": boundary_n,
        "tp": tp,
        "recall": tp/target_n if target_n else 0.0,
        "goodFp": good_fp,
        "goodFpRate": good_fp/good_n if good_n else None,
        "boundaryFp": boundary_fp,
        "boundaryFpRate": boundary_fp/boundary_n if boundary_n else None,
        "otherTailFp": other_tail_fp,
        "labelledSelected": labelled_selected,
    }


def ranking_key(r: dict[str, Any]):
    return (
        r["goodFp"], r["boundaryFp"], r["otherTailFp"],
        -r["tp"], -r["recall"], r.get("complexity", 1),
        r.get("feature1", ""), r.get("feature2", ""),
    )


def atom_mask(rows: list[dict[str, Any]], atom: dict[str, Any]) -> tuple[bool, ...]:
    return tuple(hit_atom(r, atom) for r in rows)


def build_atoms(rows: list[dict[str, Any]], features: list[str], target: str) -> list[dict[str, Any]]:
    atoms: list[dict[str, Any]] = []
    for feat in features:
        vals = [num(r.get(feat)) for r in rows if r.get("researchLabel") in RESEARCH_LABELS]
        vals = [v for v in vals if v is not None]
        if len(vals) < 4:
            continue
        for th in thresholds(vals):
            for op in ("<=", ">="):
                atom = {"feature": feat, "op": op, "threshold": th}
                st = stats(rows, target, [atom])
                if st["tp"] == 0:
                    continue
                atoms.append({**atom, **st, "complexity": 1})
    atoms.sort(key=ranking_key)
    seen: set[tuple[bool, ...]] = set()
    dedup = []
    for a in atoms:
        m = atom_mask(rows, a)
        if m in seen:
            continue
        seen.add(m); dedup.append(a)
        if len(dedup) >= 120:
            break
    return dedup


def search_pairs(rows: list[dict[str, Any]], target: str, atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    seen_masks: set[tuple[bool, ...]] = set()
    for i, a in enumerate(atoms):
        for b in atoms[i+1:]:
            if a["feature"] == b["feature"]:
                continue
            if a["goodFp"] > max(2, math.ceil((a["goodN"] or 0)*0.05)):
                continue
            if b["goodFp"] > max(2, math.ceil((b["goodN"] or 0)*0.05)):
                continue
            st = stats(rows, target, [a, b])
            if st["tp"] == 0:
                continue
            mask = tuple(hit_atom(r, a) and hit_atom(r, b) for r in rows)
            if mask in seen_masks:
                continue
            seen_masks.add(mask)
            out.append({
                **st, "complexity": 2,
                "feature1": a["feature"], "op1": a["op"], "threshold1": a["threshold"],
                "feature2": b["feature"], "op2": b["op"], "threshold2": b["threshold"],
            })
    out.sort(key=ranking_key)
    return out[:500]


def flatten_single(a: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": a["target"], "complexity": 1,
        "feature1": a["feature"], "op1": a["op"], "threshold1": a["threshold"],
        "feature2": "", "op2": "", "threshold2": "",
        "targetN": a["targetN"], "goodN": a["goodN"], "boundaryN": a["boundaryN"],
        "tp": a["tp"], "recall": a["recall"], "goodFp": a["goodFp"],
        "goodFpRate": a["goodFpRate"], "boundaryFp": a["boundaryFp"],
        "boundaryFpRate": a["boundaryFpRate"], "otherTailFp": a["otherTailFp"],
        "labelledSelected": a["labelledSelected"],
    }


def self_test() -> None:
    rows = []
    for i in range(12):
        rows.append({"captureKey": f"good{i}", "researchLabel":"GOOD", "lowkey":.10+i*.02, "body":60+i, "upper":190+i})
    rows += [
        {"captureKey":"edge0", "researchLabel":"BOUNDARY", "lowkey":.70, "body":52, "upper":205},
        {"captureKey":"edge1", "researchLabel":"BOUNDARY", "lowkey":.74, "body":49, "upper":210},
        {"captureKey":"b0", "researchLabel":"BRIGHT_FAIL", "lowkey":.90, "body":94, "upper":218},
        {"captureKey":"b1", "researchLabel":"BRIGHT_FAIL", "lowkey":.83, "body":92, "upper":221},
        {"captureKey":"d0", "researchLabel":"DARK_FAIL", "lowkey":.75, "body":11, "upper":96},
        {"captureKey":"d1", "researchLabel":"DARK_FAIL", "lowkey":.72, "body":15, "upper":102},
    ]
    feats = numeric_features(rows)
    for target in TARGETS:
        atoms = build_atoms(rows, feats, target)
        pairs = search_pairs(rows, target, atoms)
        assert atoms
        best = sorted([flatten_single(a) for a in atoms] + pairs, key=ranking_key)[0]
        assert best["goodFp"] == 0 and best["boundaryFp"] == 0 and best["tp"] >= 1
    print("M9EDGEPLACEMENT1A conjunction self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path, help="edge_features.csv from replay harness")
    ap.add_argument("--labels", type=Path, help="pattern,label,m9ness,notes; BOUNDARY allowed research-only")
    ap.add_argument("--out", type=Path, default=Path("M9EDGEPLACEMENT1A_RESULTS"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.features or not a.labels:
        ap.error("--features and --labels required unless --self-test")

    rows, unmatched = apply_labels(read_csv(a.features), read_labels(a.labels))
    feats = numeric_features(rows)
    a.out.mkdir(parents=True, exist_ok=True)
    write_csv(a.out / "edge_features_research_labels.csv", rows)

    summary: dict[str, Any] = {
        "schema":"m9edgeplacement1a.conjunction.v1",
        "mode":"research_only_frozen_default",
        "ranking":"GOOD false positives -> BOUNDARY false positives -> opposite-tail false positives -> recall",
        "featureCount": len(feats),
        "unmatchedLabelPatterns": unmatched,
        "researchLabelCounts": {lab:sum(r.get("researchLabel")==lab for r in rows) for lab in sorted(RESEARCH_LABELS)},
        "targets":{},
    }
    all_singles=[]; all_pairs=[]
    for target in TARGETS:
        atoms = build_atoms(rows, feats, target)
        singles = [flatten_single(a) for a in atoms]
        pairs = search_pairs(rows, target, atoms)
        all_singles.extend(singles[:500]); all_pairs.extend(pairs)
        all_rules = sorted(singles + pairs, key=ranking_key)
        zero = [r for r in all_rules if r["goodFp"]==0 and r["boundaryFp"]==0]
        summary["targets"][target] = {
            "singleAtomCount":len(singles), "pairRuleCount":len(pairs),
            "bestRule": all_rules[0] if all_rules else None,
            "bestZeroGoodAndBoundaryFpRule": zero[0] if zero else None,
            "note":"candidate rules are research output only; no live promotion",
        }
    write_csv(a.out / "candidate_rules_single.csv", all_singles)
    write_csv(a.out / "candidate_rules_and2.csv", all_pairs)
    (a.out / "conjunction_summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
