#!/usr/bin/env python3
"""Attach non-photographic build/schema cohort identity to EDGEPLACEMENT rows.

Research-only. The metadata emitted here is NEVER a placement-classifier input.
Its only purpose is to make regression/readiness checks compare failure examples
against controls produced by a compatible diagnostic/render build.

The source JSON already records fields such as:
- m9Build.version
- m9Build.instrumentation
- m9Build.rendererSchemaFrozen
- m9SceneExposureDiagnostic.schema
- renderMeterDiagnostic.schema (where available)
- m9Renderer.schema

This postprocessor re-indexes JSON sidecars / diagnostic bundles by capture
identity, extracts those strings, and appends them to edge_features*.csv.
No pixels, capture settings, TC20 values, or renderer output are modified.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


def walk_dicts(obj: Any) -> Iterable[dict]:
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_dicts(value)


def capture_key_from_obj(obj: Any, fallback: str) -> str:
    preferred = (
        "dng", "captureIdentity", "sourceDng", "sourceDngName",
        "rawFilename", "rawFileName", "dngFilename", "dngFileName",
    )
    for d in walk_dicts(obj):
        for key in preferred:
            value = d.get(key)
            if isinstance(value, str) and value:
                name = Path(value).name
                if name.lower().endswith(".dng"):
                    return Path(name).stem
    stem = Path(fallback).stem
    stem = re.sub(r"_M9_PRIMARY$", "", stem, flags=re.I)
    stem = re.sub(r"_M9$", "", stem, flags=re.I)
    return stem


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def first_dict_named(obj: Any, key: str) -> dict | None:
    for d in walk_dicts(obj):
        value = d.get(key)
        if isinstance(value, dict):
            return value
    return None


def find_scene_diag(obj: Any) -> dict | None:
    for d in walk_dicts(obj):
        q = d.get("m9SceneExposureDiagnostic")
        if isinstance(q, dict):
            return q
        if text(d.get("schema")).startswith("m9cam.sceneexposure."):
            return d
    return None


def find_render_diag(obj: Any) -> dict | None:
    for d in walk_dicts(obj):
        q = d.get("renderMeterDiagnostic")
        if isinstance(q, dict):
            return q
        if text(d.get("schema")).startswith("m9cam.rendermeter."):
            return d
    return None


def find_renderer(obj: Any) -> dict | None:
    for d in walk_dicts(obj):
        q = d.get("m9Renderer")
        if isinstance(q, dict):
            return q
        if text(d.get("schema")).startswith("m9cam.renderer."):
            return d
    return None


def extract_metadata(obj: Any) -> dict[str, str]:
    build = first_dict_named(obj, "m9Build") or {}
    scene = find_scene_diag(obj) or {}
    render_diag = find_render_diag(obj) or {}
    renderer = find_renderer(obj) or {}

    build_version = text(build.get("version"))
    instrumentation = text(build.get("instrumentation"))
    build_renderer_schema = text(build.get("rendererSchemaFrozen"))
    renderer_schema = text(renderer.get("schema")) or build_renderer_schema
    scene_schema = text(scene.get("schema"))
    render_meter_schema = text(render_diag.get("schema"))

    # Cohort identity deliberately excludes camera/photographic measurements.
    # Prefer explicit build identity. If unavailable, schemas still protect
    # against comparing diagnostics that did not exist in older builds.
    parts = [
        f"build={build_version}" if build_version else "",
        f"scene={scene_schema}" if scene_schema else "",
        f"rendermeter={render_meter_schema}" if render_meter_schema else "",
        f"renderer={renderer_schema}" if renderer_schema else "",
    ]
    cohort_key = "|".join(p for p in parts if p)
    schema_key = "|".join(p for p in (
        f"scene={scene_schema}" if scene_schema else "",
        f"rendermeter={render_meter_schema}" if render_meter_schema else "",
        f"renderer={renderer_schema}" if renderer_schema else "",
    ) if p)

    return {
        "cohortBuildVersion": build_version,
        "cohortInstrumentation": instrumentation,
        "cohortSceneSchema": scene_schema,
        "cohortRenderMeterSchema": render_meter_schema,
        "cohortRendererSchema": renderer_schema,
        "cohortSchemaKey": schema_key,
        "cohortKey": cohort_key,
    }


@dataclass
class MetaRecord:
    key: str
    values: dict[str, str] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


def merge_values(record: MetaRecord, values: dict[str, str], source: str) -> None:
    if source not in record.sources:
        record.sources.append(source)
    for key, value in values.items():
        if not value:
            continue
        old = record.values.get(key, "")
        if old and old != value:
            record.conflicts.append(f"{key}: {old!r} != {value!r} @ {source}")
            continue
        record.values[key] = value


def ingest(root: Path) -> dict[str, MetaRecord]:
    records: dict[str, MetaRecord] = {}
    for jp in sorted(root.rglob("*.json")):
        try:
            obj = json.loads(jp.read_text(errors="replace"))
        except Exception:
            continue

        candidates: list[dict] = []
        if isinstance(obj, dict):
            candidates.append(obj)
            entries = obj.get("entries")
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    payload = entry.get("payload")
                    if isinstance(payload, dict):
                        candidates.append(payload)

        for candidate in candidates:
            values = extract_metadata(candidate)
            if not any(values.values()):
                continue
            key = capture_key_from_obj(candidate, jp.name)
            record = records.setdefault(key, MetaRecord(key))
            merge_values(record, values, str(jp))
    return records


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def match_record(key: str, records: dict[str, MetaRecord]) -> MetaRecord | None:
    if key in records:
        return records[key]
    hits = [record for rkey, record in records.items() if key and (key in rkey or rkey in key)]
    return hits[0] if len(hits) == 1 else None


def self_test() -> None:
    fixture = {
        "schema": "m9cam.photon.capture.v2",
        "dng": "IMG_20260904_080247_123_00.dng",
        "m9Build": {
            "version": "1.52-test",
            "instrumentation": "LUMA2.4",
            "rendererSchemaFrozen": "m9cam.renderer.test.v1",
        },
        "m9SceneExposureDiagnostic": {"schema": "m9cam.sceneexposure.v8.test"},
        "renderMeterDiagnostic": {"schema": "m9cam.rendermeter.v1.test"},
        "m9Renderer": {"schema": "m9cam.renderer.test.v1"},
    }
    meta = extract_metadata(fixture)
    assert meta["cohortBuildVersion"] == "1.52-test"
    assert meta["cohortSceneSchema"] == "m9cam.sceneexposure.v8.test"
    assert meta["cohortRenderMeterSchema"] == "m9cam.rendermeter.v1.test"
    assert "build=1.52-test" in meta["cohortKey"]
    assert "renderer=m9cam.renderer.test.v1" in meta["cohortKey"]
    print("M9EDGEPLACEMENT1A cohort-metadata self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, nargs="?", help="root containing original M9 JSON sidecars/bundles")
    ap.add_argument("--features", type=Path, help="edge_features*.csv to augment")
    ap.add_argument("--out", type=Path, default=Path("M9EDGEPLACEMENT1A_RESULTS/edge_features_cohort.csv"))
    ap.add_argument("--summary", type=Path, default=Path("M9EDGEPLACEMENT1A_RESULTS/cohort_metadata_summary.json"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        self_test(); return
    if not a.root or not a.features:
        ap.error("root and --features are required unless --self-test")

    records = ingest(a.root)
    rows = read_csv(a.features)
    out_rows: list[dict[str, Any]] = []
    matched = 0
    conflicts: dict[str, list[str]] = {}
    for row in rows:
        key = (row.get("captureKey") or "").strip()
        record = match_record(key, records)
        additions = {
            "cohortBuildVersion": "",
            "cohortInstrumentation": "",
            "cohortSceneSchema": "",
            "cohortRenderMeterSchema": "",
            "cohortRendererSchema": "",
            "cohortSchemaKey": "",
            "cohortKey": "",
            "cohortMetadataSourceCount": 0,
        }
        if record:
            matched += 1
            additions.update(record.values)
            additions["cohortMetadataSourceCount"] = len(record.sources)
            if record.conflicts:
                conflicts[key] = record.conflicts
        out_rows.append({**row, **additions})

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.summary.parent.mkdir(parents=True, exist_ok=True)
    write_csv(a.out, out_rows)
    summary = {
        "schema": "m9edgeplacement1a.cohortmetadata.v1",
        "mode": "research_only_metadata_not_classifier_features",
        "featureRowCount": len(rows),
        "metadataRecordCount": len(records),
        "matchedFeatureRowCount": matched,
        "unmatchedFeatureRowCount": len(rows) - matched,
        "conflictCaptureCount": len(conflicts),
        "conflicts": conflicts,
        "invariant": "cohort fields are evaluation guards only and must never enter photographic placement rule search",
    }
    a.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
