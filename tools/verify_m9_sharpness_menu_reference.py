#!/usr/bin/env python3
"""Cross-check the Sharp reference model against derived canonical firmware rows."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_reference(path: Path):
    spec = importlib.util.spec_from_file_location("m9_sharpness_reference", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load reference module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, required=True)
    ap.add_argument("--reference", type=Path, default=Path("tools/m9_sharpness_reference.py"))
    args = ap.parse_args()

    rows = json.loads(args.rows.read_text())
    ref = load_reference(args.reference)

    fw_rows = {
        "off": tuple(rows["mode_rows"]["Off"]),
        "low": tuple(rows["mode_rows"]["Low"]),
        "standard": tuple(rows["mode_rows"]["Standard"]),
        "medium_high": tuple(rows["mode_rows"]["Medium high"]),
        "high": tuple(rows["mode_rows"]["High"]),
    }
    assert tuple(rows["iso_labels"]) == tuple(ref.ISO_LABELS)
    assert fw_rows == ref.MENU_MODE_ROWS
    assert rows["standard_crosscheck"] is True

    # Exact mode fingerprints.  Mode 6 is deliberately not float 1.5x.
    expected = {
        1: {-5: -2, -3: -1, 3: 0, 5: 1},
        2: {-5: -3, -3: -2, 3: 1, 5: 2},
        3: {-5: -5, -3: -3, 3: 3, 5: 5},
        4: {-5: -10, -3: -6, 3: 6, 5: 10},
        5: {-5: -20, -3: -12, 3: 12, 5: 20},
        6: {-5: -9, -3: -6, 3: 3, 5: 6},
        7: {-5: -15, -3: -9, 3: 9, 5: 15},
    }
    for mode, cases in expected.items():
        for value, want in cases.items():
            got = ref.transform_coefficient(value, mode)
            assert got == want, (mode, value, got, want)

    selftest = ref.self_test()
    assert selftest["synthetic_tests"] == "pass"

    print(json.dumps({
        "status": "PASS",
        "schema": "m9.sharpness-menu-reference-verify.v1",
        "firmware_rows_match_reference": True,
        "mode_1_to_7_integer_fingerprints": True,
        "mode6_rounding": selftest["mode6_rounding"],
        "standard_row": list(ref.MENU_MODE_ROWS["standard"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
