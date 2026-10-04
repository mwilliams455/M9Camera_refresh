#!/usr/bin/env python3
"""M9EDGEPLACEMENT1A offline diagnostic/classification harness.

Research-only. This script never modifies Camera2 exposure, TC20, the frozen M9
renderer, or JPEG pixels. It extracts already-existing capture/render evidence,
joins it by capture identity, applies optional user labels, and searches for
conservative tail-separation rules with GOOD false-positive rate as the primary
objective.

Classes:
    GOOD        frozen renderer is photographically healthy; do nothing
    BRIGHT_FAIL frozen JPEG is too open / ambience-density is lost
    DARK_FAIL   frozen JPEG is too dense / useful scene body is starved

The harness intentionally treats Frozen as the fallback. Candidate rules are
research output only and must not be promoted directly to live code.
"""
from __future__ import annotations
import argparse, csv, json, math, re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

LABELS = {"GOOD", "BRIGHT_FAIL", "DARK_FAIL"}
NUMERIC_FEATURES = [
    "captureIso", "captureShutterNs", "captureEnergyIsoSeconds",
    "previewGlobalMedian", "previewGlobalQ95", "previewGlobalQ99",
    "previewDarkFractionLE64", "previewBrightFractionGE192",
    "previewBrightFractionGE224", "previewBrightFractionGE240",
    "previewCenterMedian", "previewCenterMinusGlobal",
    "structuralLowKeyScore", "lowKeyMedianEvidence", "lowKeyDarkBodyEvidence",
    "spatialAxisSeparationScore", "mfmAchievedIntentEv",
    "tc20Gain", "tc20GainEv", "baseMedianGain", "tc20GuardGain",
    "guardMarginAboveBaseEv", "rawUq99", "rawHardClipFraction",
    "renderRgbChannelClipFraction", "renderNearWhiteFraction",
    "renderGlobalMedian", "renderGlobalQ95", "renderGlobalQ99",
    "renderDarkFractionLE64", "renderBrightFractionGE224",
    "renderCenterMedian", "renderCenterQ95", "renderCenterMinusGlobal",
    "renderMiddleCenterMedian", "renderMiddleCenterQ95",
    "renderLiftNeedEvidence", "renderHoldEvidence",
    "wholeFrameStarvationEvidence", "localizedUpperPlacementEvidence",
    "globalBrightSupportEvidence",
]


def num(v: Any) -> float | None:
    try:
        if v is None or isinstance(v, bool): return None
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def walk_dicts(obj: Any) -> Iterable[dict]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_dicts(v)


def get_path(obj: Any, *path: str) -> Any:
    cur = obj
    for k in path:
        if not isinstance(cur, dict) or k not in cur: return None
        cur = cur[k]
    return cur


def first_named(obj: Any, names: tuple[str, ...]) -> Any:
    for d in walk_dicts(obj):
        for n in names:
            if n in d and d[n] is not None:
                return d[n]
    return None


def capture_key_from_obj(obj: Any, fallback: str) -> str:
    preferred = (
        "dng", "captureIdentity", "sourceDng", "sourceDngName",
        "rawFilename", "rawFileName", "dngFilename", "dngFileName",
    )
    for d in walk_dicts(obj):
        for k in preferred:
            v = d.get(k)
            if isinstance(v, str) and v:
                name = Path(v).name
                if name.lower().endswith(".dng"):
                    return Path(name).stem
    s = Path(fallback).stem
    s = re.sub(r"_M9_PRIMARY$", "", s, flags=re.I)
    s = re.sub(r"_M9$", "", s, flags=re.I)
    return s


def find_scene_diag(obj: Any) -> dict | None:
    for d in walk_dicts(obj):
        q = d.get("m9SceneExposureDiagnostic")
        if isinstance(q, dict): return q
        if str(d.get("schema", "")).startswith("m9cam.sceneexposure."):
            return d
    return None


def find_render_diag(obj: Any) -> dict | None:
    for d in walk_dicts(obj):
        q = d.get("renderMeterDiagnostic")
        if isinstance(q, dict): return q
        if str(d.get("schema", "")).startswith("m9cam.rendermeter."):
            return d
    return None


def extract_capture(obj: dict) -> dict:
    out: dict[str, Any] = {}
    cr = get_path(obj, "captureResult")
    if not isinstance(cr, dict): cr = {}
    out["captureIso"] = num(cr.get("iso"))
    out["captureShutterNs"] = num(cr.get("exposureTimeNs"))
    if out["captureIso"] is not None and out["captureShutterNs"] is not None:
        out["captureEnergyIsoSeconds"] = out["captureIso"] * out["captureShutterNs"] / 1e9
    else:
        out["captureEnergyIsoSeconds"] = num(first_named(obj, ("energyIsoSeconds",)))

    sd = find_scene_diag(obj)
    if sd:
        inp = sd.get("inputs") if isinstance(sd.get("inputs"), dict) else {}
        maps = {
            "previewGlobalMedian":"globalMedian", "previewGlobalQ95":"globalQ95", "previewGlobalQ99":"globalQ99",
            "previewDarkFractionLE64":"darkFractionLE64", "previewBrightFractionGE192":"brightFractionGE192",
            "previewBrightFractionGE224":"brightFractionGE224", "previewBrightFractionGE240":"brightFractionGE240",
            "previewCenterMedian":"centerMedian", "previewCenterMinusGlobal":"centerMedianMinusGlobalMedian",
        }
        for dst, src in maps.items(): out[dst] = num(inp.get(src))
        pb = sd.get("positiveBodyPressure") if isinstance(sd.get("positiveBodyPressure"), dict) else {}
        for k in ("structuralLowKeyScore", "lowKeyMedianEvidence", "lowKeyDarkBodyEvidence", "spatialAxisSeparationScore"):
            out[k] = num(pb.get(k))

    out["mfmAchievedIntentEv"] = num(first_named(obj, (
        "mfmAchievedIntentEv", "achievedIntentEv", "mfmAppliedEv", "appliedMfmEv", "mfmExposureAssistEv",
    )))
    return out


def extract_render(obj: dict) -> dict:
    out: dict[str, Any] = {}
    rd = find_render_diag(obj)
    legacy = obj.get("m9Renderer") if isinstance(obj.get("m9Renderer"), dict) else {}
    if not rd and not legacy: return out
    obs = rd.get("observations") if isinstance(rd, dict) and isinstance(rd.get("observations"), dict) else {}
    # Newer builds expose a dedicated render-meter observation object. Older
    # frozen controls expose the same TC20/RAW facts directly in m9Renderer.
    for dst, names in {
        "tc20Gain":("tc20Gain","gain"), "tc20GainEv":("tc20GainEv",),
        "baseMedianGain":("baseMedianGain",), "tc20GuardGain":("tc20GuardGain",),
        "rawUq99":("rawUq99",), "rawHardClipFraction":("rawHardClipFraction",),
        "renderRgbChannelClipFraction":("renderRgbChannelClipFraction","rgb8ClipFraction"),
        "renderNearWhiteFraction":("renderNearWhiteFraction",),
    }.items():
        v=None
        for src in names:
            if src in obs and obs[src] is not None: v=obs[src]; break
            if src in legacy and legacy[src] is not None: v=legacy[src]; break
        out[dst] = num(v)
    if out.get("tc20GainEv") is None and out.get("tc20Gain") and out["tc20Gain"] > 0:
        out["tc20GainEv"] = math.log2(out["tc20Gain"])
    b, g = out.get("baseMedianGain"), out.get("tc20GuardGain")
    if b and g and b > 0 and g > 0:
        out["tc20Binding"] = "guard" if g <= b else "median"
        out["guardMarginAboveBaseEv"] = math.log2(g / b)

    tp = rd.get("tonalPlacement") if isinstance(rd, dict) and isinstance(rd.get("tonalPlacement"), dict) else {}
    if not tp:
        q = first_named(rd, ("tonalPlacement",)) if isinstance(rd, dict) else None
        if isinstance(q, dict): tp = q
    for dst, src in {
        "renderGlobalMedian":"globalMedian", "renderGlobalQ95":"globalQ95", "renderGlobalQ99":"globalQ99",
        "renderDarkFractionLE64":"globalDarkFractionLE64", "renderBrightFractionGE224":"globalBrightFractionGE224",
        "renderCenterMedian":"centerMedian", "renderCenterQ95":"centerQ95",
        "renderCenterMinusGlobal":"centerMedianMinusGlobalMedian",
        "renderMiddleCenterMedian":"middleCenterMedian", "renderMiddleCenterQ95":"middleCenterQ95",
    }.items(): out[dst] = num(tp.get(src))

    model = first_named(rd, ("renderMeterModel1C",)) if isinstance(rd, dict) else None
    if isinstance(model, dict):
        for k in ("renderLiftNeedEvidence", "renderHoldEvidence", "wholeFrameStarvationEvidence",
                  "localizedUpperPlacementEvidence", "globalBrightSupportEvidence"):
            out[k] = num(model.get(k))
    return out


@dataclass
class Record:
    key: str
    sources: list[str] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)


def ingest(root: Path) -> dict[str, Record]:
    recs: dict[str, Record] = {}
    for jp in sorted(root.rglob("*.json")):
        try: obj = json.loads(jp.read_text(errors="replace"))
        except Exception: continue
        candidates: list[dict] = []
        if isinstance(obj, dict): candidates.append(obj)
        entries = obj.get("entries") if isinstance(obj, dict) else None
        if isinstance(entries, list):
            for e in entries:
                if not isinstance(e, dict): continue
                p = e.get("payload")
                if isinstance(p, dict): candidates.append(p)
        for cand in candidates:
            c = extract_capture(cand); r = extract_render(cand)
            if not any(v is not None for v in list(c.values()) + list(r.values())): continue
            key = capture_key_from_obj(cand, jp.name)
            rr = recs.setdefault(key, Record(key))
            if str(jp) not in rr.sources: rr.sources.append(str(jp))
            for k, v in {**c, **r}.items():
                if v is not None: rr.values[k] = v
    return recs


def read_labels(path: Path | None) -> list[dict]:
    if path is None: return []
    out=[]
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            lab=(r.get("label") or "").strip().upper(); pat=(r.get("pattern") or "").strip()
            if lab not in LABELS or not pat: continue
            out.append({"pattern":pat,"label":lab,"notes":r.get("notes","")})
    return out


def apply_label(key: str, labels: list[dict]) -> tuple[str|None,str]:
    hits=[r for r in labels if r["pattern"] in key]
    if not hits: return None,""
    labs={r["label"] for r in hits}
    if len(labs)>1: raise RuntimeError(f"conflicting labels for {key}: {sorted(labs)}")
    return hits[0]["label"], " | ".join(r["notes"] for r in hits if r["notes"])


def provisional_diagnostics(v: dict[str,Any]) -> dict[str,Any]:
    lift=v.get("renderLiftNeedEvidence"); hold=v.get("renderHoldEvidence"); starve=v.get("wholeFrameStarvationEvidence")
    dark = bool(lift is not None and lift >= .95 and (hold is None or hold <= .10) and (starve is None or starve >= .85))
    bright_probe = bool(v.get("tc20Binding") == "median" and (v.get("structuralLowKeyScore") or 0.0) >= .50)
    return {"darkTailProbe":dark,"brightLowKeyProbe":bright_probe}


def candidate_thresholds(vals: list[float]) -> list[float]:
    u=sorted(set(vals))
    if len(u)<2:return u
    mids=[(a+b)/2 for a,b in zip(u,u[1:])]
    if len(mids)>80:
        step=(len(mids)-1)/79.0
        mids=[mids[round(i*step)] for i in range(80)]
    return mids


def rule_search(rows: list[dict], target: str) -> list[dict]:
    good=[r for r in rows if r.get("label")=="GOOD"]
    pos=[r for r in rows if r.get("label")==target]
    if len(good)<5 or len(pos)<2:return []
    rules=[]
    for feat in NUMERIC_FEATURES:
        data=[num(r.get(feat)) for r in good+pos]; vals=[x for x in data if x is not None]
        if len(vals)<4: continue
        for t in candidate_thresholds(vals):
            for op in (">=","<="):
                def hit(r):
                    x=num(r.get(feat)); return False if x is None else (x>=t if op==">=" else x<=t)
                fp=sum(hit(r) for r in good); tp=sum(hit(r) for r in pos)
                rules.append({"target":target,"feature":feat,"op":op,"threshold":t,"goodN":len(good),"tailN":len(pos),
                              "falsePositiveN":fp,"falsePositiveRate":fp/len(good),"truePositiveN":tp,"recall":tp/len(pos)})
    rules.sort(key=lambda r:(r["falsePositiveRate"],-r["recall"],r["falsePositiveN"],r["feature"]))
    return rules[:200]


def write_csv(path: Path, rows: list[dict]):
    if not rows: path.write_text(""); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path,help="directory containing M9 JSON sidecars/bundles")
    ap.add_argument("--labels",type=Path,default=None,help="CSV: pattern,label,notes")
    ap.add_argument("--out",type=Path,default=Path("M9EDGEPLACEMENT1A_RESULTS"))
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    recs=ingest(a.root); labels=read_labels(a.labels); rows=[]
    for key in sorted(recs):
        rr=recs[key]; lab,notes=apply_label(key,labels); vals=dict(rr.values); vals.update(provisional_diagnostics(vals))
        rows.append({"captureKey":key,"label":lab or "","labelNotes":notes,"sourceCount":len(rr.sources),"sources":" | ".join(rr.sources),**vals})
    write_csv(a.out/"edge_features.csv",rows)
    labelled=[r for r in rows if r.get("label") in LABELS]
    bright=rule_search(labelled,"BRIGHT_FAIL"); dark=rule_search(labelled,"DARK_FAIL")
    write_csv(a.out/"candidate_rules_bright.csv",bright); write_csv(a.out/"candidate_rules_dark.csv",dark)
    summary={"schema":"m9edgeplacement1a.offline.v1","mode":"diagnostic_only_no_capture_or_renderer_mutation","recordCount":len(rows),
             "labelCounts":{k:sum(r.get("label")==k for r in rows) for k in sorted(LABELS)},
             "darkTailProbeCount":sum(bool(r.get("darkTailProbe")) for r in rows),
             "brightLowKeyProbeCount":sum(bool(r.get("brightLowKeyProbe")) for r in rows),
             "ruleSearchPolicy":"rank GOOD false-positive rate first, tail recall second; candidate rules are research only",
             "frozenFallback":"mandatory when exception confidence is not high"}
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
