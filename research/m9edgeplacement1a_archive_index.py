#!/usr/bin/env python3
"""Index the September-4 M9 field ZIPs without modifying any image data.

Purpose
-------
Recover corpus ordinal -> exact capture identity deterministically once the five
v0.7ZZS archives are byte-accessible again.  The original visual review retained
several ordinal labels (#4, #40, #73, #80, #86, #87, #98) but the exact
IMG_20260904_* mapping was not preserved in the handoff.

The tool deliberately emits multiple orderings rather than assuming how a prior
viewer enumerated the corpus:
  * archive/member order: explicit --archive argument order + ZIP member order
  * archive/sorted order: explicit --archive order + lexical capture identity
  * global chronological order: timestamp parsed from IMG_YYYYMMDD_HHMMSS and
    epoch-millis suffix when available

It also groups JPEG/DNG/_M9.json/_M9_PRIMARY.json/diagnostic-bundle membership by
capture stem.  No files are extracted and no pixels are decoded.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

CAP_RE = re.compile(
    r"(?P<stem>IMG_(?P<date>\d{8})_(?P<time>\d{6})(?:_(?P<epoch>\d+)_\d+)?)(?P<suffix>_M9_PRIMARY|_M9|_M9_PARITY)?(?P<ext>\.[^.\/]+)$",
    re.I,
)

VISUAL_ORDINALS = {
    4: "DARK_FAIL fire engine / toy truck by bright window",
    40: "DARK_FAIL backlit statue",
    73: "DARK_FAIL sculpture against bright field",
    80: "DARK_FAIL dark lane / bright background",
    86: "BOUNDARY shaded park / backlight",
    87: "BOUNDARY shaded park / backlight",
    98: "DARK_FAIL backlit tree",
    9: "SAFETY preview q95==255 cohort",
    41: "SAFETY preview q95==255 positive-assist cohort",
    43: "SAFETY preview q95==255 cohort",
    120: "SAFETY preview q95==255 cohort",
    121: "SAFETY preview q95==255 positive-assist cohort",
}


@dataclass
class Capture:
    archive_index: int
    archive_name: str
    first_member_index: int
    stem: str
    date: str
    time: str
    epoch: int | None
    members: list[str] = field(default_factory=list)
    jpeg_members: list[str] = field(default_factory=list)
    dng_members: list[str] = field(default_factory=list)
    capture_json_members: list[str] = field(default_factory=list)
    primary_json_members: list[str] = field(default_factory=list)

    @property
    def chronological_key(self):
        return (self.date, self.time, self.epoch if self.epoch is not None else -1,
                self.archive_index, self.first_member_index, self.stem)


def classify_member(name: str) -> tuple[str, str, str, str, int | None] | None:
    base = Path(name).name
    m = CAP_RE.match(base)
    if not m:
        return None
    stem = m.group("stem")
    suffix = (m.group("suffix") or "").upper()
    ext = m.group("ext").lower()
    epoch = int(m.group("epoch")) if m.group("epoch") else None
    return stem, suffix, ext, m.group("date"), m.group("time"), epoch


def index_archive(path: Path, archive_index: int) -> list[Capture]:
    by_stem: dict[str, Capture] = {}
    with zipfile.ZipFile(path) as z:
        for member_index, info in enumerate(z.infolist(), start=1):
            if info.is_dir():
                continue
            parsed = classify_member(info.filename)
            if parsed is None:
                continue
            stem, suffix, ext, date, tm, epoch = parsed
            c = by_stem.get(stem)
            if c is None:
                c = Capture(archive_index, path.name, member_index, stem, date, tm, epoch)
                by_stem[stem] = c
            c.members.append(info.filename)
            if ext in {".jpg", ".jpeg"} and not suffix:
                c.jpeg_members.append(info.filename)
            elif ext == ".dng" and not suffix:
                c.dng_members.append(info.filename)
            elif ext == ".json" and suffix == "_M9":
                c.capture_json_members.append(info.filename)
            elif ext == ".json" and suffix == "_M9_PRIMARY":
                c.primary_json_members.append(info.filename)
    return list(by_stem.values())


def rows_for(order: str, captures: Iterable[Capture]) -> list[dict]:
    out = []
    for ordinal, c in enumerate(captures, start=1):
        out.append({
            "ordering": order,
            "ordinal": ordinal,
            "visualOrdinalNote": VISUAL_ORDINALS.get(ordinal, ""),
            "captureStem": c.stem,
            "archiveIndex": c.archive_index,
            "archive": c.archive_name,
            "firstMemberIndex": c.first_member_index,
            "date": c.date,
            "time": c.time,
            "epochMillis": "" if c.epoch is None else c.epoch,
            "jpegCount": len(c.jpeg_members),
            "dngCount": len(c.dng_members),
            "captureJsonCount": len(c.capture_json_members),
            "primaryJsonCount": len(c.primary_json_members),
            "memberCount": len(c.members),
            "jpegMembers": " | ".join(c.jpeg_members),
            "dngMembers": " | ".join(c.dng_members),
            "captureJsonMembers": " | ".join(c.capture_json_members),
            "primaryJsonMembers": " | ".join(c.primary_json_members),
        })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", action="append", type=Path, required=True,
                    help="ZIP path; repeat in the same order used for the original corpus review")
    ap.add_argument("--out", type=Path,
                    default=Path("M9EDGEPLACEMENT1A_ARCHIVE_INDEX"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    all_caps: list[Capture] = []
    per_archive: list[list[Capture]] = []
    for ai, p in enumerate(a.archive, start=1):
        if not p.is_file():
            raise SystemExit(f"archive not found: {p}")
        caps = index_archive(p, ai)
        per_archive.append(caps)
        all_caps.extend(caps)

    member_order = [c for caps in per_archive
                    for c in sorted(caps, key=lambda x: x.first_member_index)]
    archive_sorted = [c for caps in per_archive
                      for c in sorted(caps, key=lambda x: x.stem)]
    chronological = sorted(all_caps, key=lambda x: x.chronological_key)

    orders = {
        "archive_member": member_order,
        "archive_lexical": archive_sorted,
        "global_chronological": chronological,
    }
    for name, caps in orders.items():
        write_csv(a.out / f"capture_index_{name}.csv", rows_for(name, caps))

    candidates = []
    for name, caps in orders.items():
        rowset = rows_for(name, caps)
        candidates.extend(r for r in rowset if r["ordinal"] in VISUAL_ORDINALS)
    write_csv(a.out / "labelled_ordinal_candidates.csv", candidates)

    summary = {
        "schema": "m9edgeplacement1a.archiveindex.v1",
        "researchOnly": True,
        "archiveCount": len(a.archive),
        "archives": [str(p) for p in a.archive],
        "uniqueCaptureStemCount": len({c.stem for c in all_caps}),
        "captureCountByArchive": {
            str(a.archive[i]): len(per_archive[i]) for i in range(len(a.archive))
        },
        "orderingsEmitted": list(orders),
        "visualOrdinals": VISUAL_ORDINALS,
        "warning": "Do not choose an ordinal mapping solely because one ordering looks plausible. Reconcile against known scene/time/metadata evidence before copying exact patterns into placement labels.",
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
