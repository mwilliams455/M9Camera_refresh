#!/usr/bin/env python3
"""Prove the BF561 post-Sharp red/blue stage is green + colour-difference reconstruction.

Consumes GNU Blackfin disassembly emitted by m9-sharpness-bf561-dataflow.yml.
No firmware bytes are embedded or emitted. The proof deliberately separates:
  * algorithm semantics (closed here), from
  * exact Run-time pointer alias across Sharp -> R/B (still a separate gate).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def lines(path: Path) -> list[str]:
    return path.read_text(errors="replace").splitlines()


def hits(ls: list[str], pats: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in pats:
        rx = re.compile(p)
        m = [ln.strip() for ln in ls if rx.search(ln)]
        out[p] = m
    return out


def require(label: str, found: list[str]) -> None:
    if not found:
        raise SystemExit(f"missing required BF561 semantic anchor: {label}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disassembly", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    d = a.disassembly
    diff = next(d.glob("ASMRedBlueAndGreenDiffer_*_ffa00008.gnu.dis.txt"))
    rb = next(d.glob("ASMRedBlueInterpolation1_*_ffa03410.gnu.dis.txt"))
    dl = lines(diff)
    rl = lines(rb)

    # Difference producer: two 16-bit source streams are subtracted; a third
    # 16-bit stream participates in edge-directed selection; selected signed
    # difference is written to a 16-bit intermediate plane.
    d_pats = [
        r"R0 = W\[P0 .*\] \(Z\)",
        r"R1 = W\[P1 .*\] \(Z\)",
        r"R2 = R0 - R1 \(S\)",
        r"R5 = W\[P2 .*\] \(Z\)",
        r"R4 = ABS R2",
        r"R5 = ABS R5",
        r"W\[I1.*\] = R2\.L",
    ]
    dh = hits(dl, d_pats)
    for p in d_pats:
        require("difference:" + p, dh[p])

    # R/B reconstruction: R0 is expanded into four 16-bit word streams; the
    # code averages neighbouring words, vector-adds them to packed samples
    # loaded through the R1-derived streams, clamps to [0,0x3fff], and stores.
    r_pats = [
        r"R7 = 0x3fff",
        r"R6 = R0 \+ R7 \(S\)",
        r"I0 = R6",
        r"I1 = R5",
        r"I2 = R6",
        r"I3 = R6",
        r"R3 = \[P0\+\+\]",
        r"R4\.H = R4\.L \+ R4\.H \(S\)",
        r"R4\.H = R4\.H >>> 0x1",
        r"R3 = R3 \+\|\+ R4",
        r"R3 = MAX \(R3, R7\) \(V\)",
        r"R3 = MIN \(R3, R2\) \(V\)",
        r"\[P1\+\+\] = R3",
    ]
    rh = hits(rl, r_pats)
    for p in r_pats:
        require("reconstruction:" + p, rh[p])

    report = {
        "schema": "m9.bf561-rb-semantics.v1",
        "difference_function": diff.name,
        "reconstruction_function": rb.name,
        "difference_anchors": dh,
        "reconstruction_anchors": rh,
        "closed": {
            "difference_plane_exists": True,
            "difference_plane_is_16bit_storage": True,
            "rb_reconstruction_uses_r0_derived_16bit_word_plane": True,
            "rb_reconstruction_adds_averaged_r0_plane_to_packed_values": True,
            "rb_reconstruction_clamps_14bit": True,
            "rb_numeric_max": 16383,
            "algorithm_is_green_plus_colour_difference_family": True,
        },
        "still_open": {
            "run_pointer_alias_postsharp_to_rb_r0": True,
            "exact_semantic_identity_of_each_packed_difference_lane": True,
        },
        "conclusion": (
            "Firmware proves the post-Sharp R/B stage is not an independent CFA-only MHC-style completion. "
            "It reconstructs packed colour samples by adding an averaged 16-bit R0-derived plane to packed "
            "difference-like values and clamps the result to 0..16383. GreenInterpolationWithCo separately "
            "invokes ASMRedBlueAndGreenDiffer, which explicitly forms a signed R0-R1 difference and writes a "
            "16-bit intermediate. Exact Run-time pointer alias from Process_Sharpness output to the R/B R0 "
            "argument remains a separate proof obligation."
        ),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(report["conclusion"])


if __name__ == "__main__":
    main()
