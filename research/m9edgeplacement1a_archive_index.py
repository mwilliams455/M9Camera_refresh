#!/usr/bin/env python3
"""Index the September-4 M9 field ZIPs without modifying image data.

Purpose
-------
Recover visual-corpus ordinal -> exact capture identity deterministically once
the five v0.7ZZS archives are byte-accessible again.

Critical distinction
--------------------
The original visual review covered **121 JPEG instances** but only **120 unique
complete capture/RAW identities**. Therefore review ordinals such as #4, #40,
#73, #80, #86, #87 and #98 MUST be reconstructed from JPEG-instance ordering,
not from a deduplicated capture-stem list. One duplicate/extra JPEG is enough to
shift every later ordinal.

The tool emits both domains:

JPEG-instance orderings (authoritative candidates for visual review ordinals):
  * archive/member JPEG order
  * archive/lexical JPEG order
  * global chronological JPEG order

Capture-identity orderings (diagnostic join/reference only):
  * archive/member capture order
  * archive/lexical capture order
  * global chronological capture order

No files are extracted and no pixels are decoded.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

CAP_RE = re.compile(
    r"(?P<stem>IMG_(?P<date>\d{8})_(?P<time>\d{6})(?:_(?P<epoch>\d+)_\d+)?)"
    r"(?P<suffix>_M9_PRIMARY|_M9|_M9_PARITY)?(?P<ext>\.[^.\\/]+)$",
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
        return (
            self.date, self.time,
            self.epoch if self.epoch is not None else -1,
            self.archive_index, self.first_member_index, self.stem,
        )


@dataclass(frozen=True)
class JpegInstance:
    archive_index: int
    archive_name: str
    member_index: int
    member_name: str
    stem: str
    date: str
    time: str
    epoch: int | None

    @property
    def chronological_key(self):
        return (
            self.date, self.time,
            self.epoch if self.epoch is not None else -1,
            self.archive_index, self.member_index, self.member_name,
        )


def classify_member(name: str) -> tuple[str, str, str, str, str, int | None] | None:
    base = Path(name).name
    m = CAP_RE.match(base)
    if not m:
        return None
    stem = m.group("stem")
    suffix = (m.group("suffix") or "").upper()
    ext = m.group("ext").lower()
    epoch = int(m.group("epoch")) if m.group("epoch") else None
    return stem, suffix, ext, m.group("date"), m.group("time"), epoch


def index_archive(path: Path, archive_index: int) -> tuple[list[Capture], list[JpegInstance]]:
    by_stem: dict[str, Capture] = {}
    jpegs: list[JpegInstance] = []
    with zipfile.ZipFile(path) as z:
        for member_index, info in enumerate(z.infolist(), start=1):
            if info.is_dir():
                continue
            parsed = classify_member(info.filename)
            if parsed is None:
                continue
            stem, suffix, ext, date, tm, epoch = parsed
            capture = by_stem.get(stem)
            if capture is None:
                capture = Capture(
                    archive_index, path.name, member_index,
                    stem, date, tm, epoch,
                )
                by_stem[stem] = capture
            capture.members.append(info.filename)

            if ext in {".jpg", ".jpeg"} and not suffix:
                capture.jpeg_members.append(info.filename)
                jpegs.append(JpegInstance(
                    archive_index=archive_index,
                    archive_name=path.name,
                    member_index=member_index,
                    member_name=info.filename,
                    stem=stem,
                    date=date,
                    time=tm,
                    epoch=epoch,
                ))
            elif ext == ".dng" and not suffix:
                capture.dng_members.append(info.filename)
            elif ext == ".json" and suffix == "_M9":
                capture.capture_json_members.append(info.filename)
            elif ext == ".json" and suffix == "_M9_PRIMARY":
                capture.primary_json_members.append(info.filename)
    return list(by_stem.values()), jpegs


def capture_rows_for(order: str, captures: Iterable[Capture]) -> list[dict]:
    out = []
    for ordinal, c in enumerate(captures, start=1):
        out.append({
            "ordering": order,
            "captureOrdinal": ordinal,
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


def jpeg_rows_for(order: str, jpegs: Iterable[JpegInstance], global_capture_counts: dict[str, int]) -> list[dict]:
    out = []
    seen_stems: dict[str, int] = {}
    for ordinal, item in enumerate(jpegs, start=1):
        seen_stems[item.stem] = seen_stems.get(item.stem, 0) + 1
        out.append({
            "ordering": order,
            "visualJpegOrdinal": ordinal,
            "visualOrdinalNote": VISUAL_ORDINALS.get(ordinal, ""),
            "captureStem": item.stem,
            "jpegOccurrenceForStemInThisOrder": seen_stems[item.stem],
            "jpegInstancesForStemGlobal": global_capture_counts.get(item.stem, 0),
            "isRepeatedVisualStem": global_capture_counts.get(item.stem, 0) > 1,
            "archiveIndex": item.archive_index,
            "archive": item.archive_name,
            "memberIndex": item.member_index,
            "jpegMember": item.member_name,
            "date": item.date,
            "time": item.time,
            "epochMillis": "" if item.epoch is None else item.epoch,
        })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_indexes(archives: list[Path]) -> tuple[dict[str, list[Capture]], dict[str, list[JpegInstance]], dict]:
    all_caps: list[Capture] = []
    all_jpegs: list[JpegInstance] = []
    per_archive_caps: list[list[Capture]] = []
    per_archive_jpegs: list[list[JpegInstance]] = []

    for archive_index, path in enumerate(archives, start=1):
        if not path.is_file():
            raise SystemExit(f"archive not found: {path}")
        caps, jpegs = index_archive(path, archive_index)
        per_archive_caps.append(caps)
        per_archive_jpegs.append(jpegs)
        all_caps.extend(caps)
        all_jpegs.extend(jpegs)

    capture_orders = {
        "archive_member": [
            c for caps in per_archive_caps
            for c in sorted(caps, key=lambda x: x.first_member_index)
        ],
        "archive_lexical": [
            c for caps in per_archive_caps
            for c in sorted(caps, key=lambda x: (x.stem, x.first_member_index))
        ],
        "global_chronological": sorted(all_caps, key=lambda x: x.chronological_key),
    }

    jpeg_orders = {
        "archive_member_jpeg": [
            j for jpegs in per_archive_jpegs
            for j in sorted(jpegs, key=lambda x: x.member_index)
        ],
        "archive_lexical_jpeg": [
            j for jpegs in per_archive_jpegs
            for j in sorted(jpegs, key=lambda x: (x.stem, x.member_index))
        ],
        "global_chronological_jpeg": sorted(all_jpegs, key=lambda x: x.chronological_key),
    }

    jpeg_count_by_stem: dict[str, int] = {}
    for item in all_jpegs:
        jpeg_count_by_stem[item.stem] = jpeg_count_by_stem.get(item.stem, 0) + 1

    unique_stems = {c.stem for c in all_caps}
    complete_stems = {
        c.stem for c in all_caps
        if c.dng_members and c.jpeg_members
    }
    summary = {
        "uniqueCaptureStemCount": len(unique_stems),
        "completeCaptureStemCount": len(complete_stems),
        "jpegInstanceCount": len(all_jpegs),
        "uniqueJpegStemCount": len(jpeg_count_by_stem),
        "repeatedJpegStems": {
            stem: count for stem, count in sorted(jpeg_count_by_stem.items()) if count > 1
        },
        "captureCountByArchive": {
            str(archives[i]): len(per_archive_caps[i]) for i in range(len(archives))
        },
        "jpegInstanceCountByArchive": {
            str(archives[i]): len(per_archive_jpegs[i]) for i in range(len(archives))
        },
    }
    return capture_orders, jpeg_orders, {**summary, "jpegCountByStem": jpeg_count_by_stem}


def self_test() -> None:
    # Synthetic case intentionally has 4 visual JPEG instances but only 3 unique
    # capture stems: B is repeated in archive 2. Visual ordinal #4 must therefore
    # resolve from JPEG order, not from a 3-stem capture list.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        a1 = root / "one.zip"
        a2 = root / "two.zip"
        with zipfile.ZipFile(a1, "w") as z:
            z.writestr("IMG_20260904_080001_1001_00.jpg", b"jpeg-a")
            z.writestr("IMG_20260904_080001_1001_00.dng", b"dng-a")
            z.writestr("IMG_20260904_080001_1001_00_M9.json", b"{}")
            z.writestr("IMG_20260904_080002_1002_00.jpg", b"jpeg-b")
            z.writestr("IMG_20260904_080002_1002_00.dng", b"dng-b")
        with zipfile.ZipFile(a2, "w") as z:
            z.writestr("IMG_20260904_080002_1002_00.jpg", b"jpeg-b-repeat")
            z.writestr("IMG_20260904_080003_1003_00.jpg", b"jpeg-c")
            z.writestr("IMG_20260904_080003_1003_00.dng", b"dng-c")

        capture_orders, jpeg_orders, summary = build_indexes([a1, a2])
        assert summary["jpegInstanceCount"] == 4, summary
        assert summary["uniqueJpegStemCount"] == 3, summary
        assert summary["uniqueCaptureStemCount"] == 3, summary
        assert summary["repeatedJpegStems"]["IMG_20260904_080002_1002_00"] == 2
        assert len(jpeg_orders["archive_member_jpeg"]) == 4
        assert jpeg_orders["archive_member_jpeg"][3].stem == "IMG_20260904_080003_1003_00"
        assert len(capture_orders["global_chronological"]) == 4  # archive-local capture groups include repeated B
        print("M9EDGEPLACEMENT1A archive-index JPEG-ordinal self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", action="append", type=Path,
                    help="ZIP path; repeat in the same archive order used for the original visual review")
    ap.add_argument("--out", type=Path,
                    default=Path("M9EDGEPLACEMENT1A_ARCHIVE_INDEX"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        self_test()
        return
    if not a.archive:
        ap.error("at least one --archive is required unless --self-test")

    a.out.mkdir(parents=True, exist_ok=True)
    capture_orders, jpeg_orders, summary_bits = build_indexes(a.archive)
    jpeg_count_by_stem = summary_bits.pop("jpegCountByStem")

    for name, captures in capture_orders.items():
        write_csv(a.out / f"capture_index_{name}.csv", capture_rows_for(name, captures))

    jpeg_candidate_rows = []
    for name, jpegs in jpeg_orders.items():
        rows = jpeg_rows_for(name, jpegs, jpeg_count_by_stem)
        write_csv(a.out / f"visual_jpeg_index_{name}.csv", rows)
        jpeg_candidate_rows.extend(
            row for row in rows if row["visualJpegOrdinal"] in VISUAL_ORDINALS
        )
    write_csv(a.out / "visual_labelled_ordinal_candidates.csv", jpeg_candidate_rows)

    summary = {
        "schema": "m9edgeplacement1a.archiveindex.v2.jpegordinal",
        "researchOnly": True,
        "archiveCount": len(a.archive),
        "archives": [str(p) for p in a.archive],
        **summary_bits,
        "captureOrderingsEmitted": list(capture_orders),
        "visualJpegOrderingsEmitted": list(jpeg_orders),
        "visualOrdinals": VISUAL_ORDINALS,
        "ordinalAuthority": "JPEG-instance ordering only; capture-stem ordinals are not valid substitutes for the 121-JPEG visual review",
        "expectedHistoricalShape": {
            "jpegInstances": 121,
            "uniqueCompleteCaptureRawSets": 120,
        },
        "warning": (
            "Do not choose an ordinal mapping solely because one ordering looks plausible. "
            "First verify 121 JPEG instances / 120 unique complete capture identities, then reconcile "
            "candidate mappings against known scene/time/telemetry evidence before copying exact patterns into labels."
        ),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
