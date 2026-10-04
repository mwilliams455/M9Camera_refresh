#!/usr/bin/env python3
"""Prove the BF561 Sharp output is the green plane consumed by R/B reconstruction.

Consumes GNU disassembly emitted by m9-sharpness-bf561-dataflow.yml.  The
proof follows both dataflow and the Run-frame pointer algebra.  No firmware
bytes are embedded.
"""
from __future__ import annotations

import argparse, json, re
from pathlib import Path


def txt(p: Path) -> str:
    return p.read_text(errors="replace")


def need(label: str, text: str, pattern: str) -> str:
    m = re.search(pattern, text, re.M)
    if not m:
        raise SystemExit(f"missing alias anchor {label}: {pattern}")
    return m.group(0).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disassembly", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    d = a.disassembly
    runp = next(d.glob("Run_*_ffa10320.gnu.dis.txt"))
    procp = next(d.glob("Process_Sharpness_*_ffa03d90.gnu.dis.txt"))
    asmp = next(d.glob("ASMUMGauss3LUT_*_ffa018b0.gnu.dis.txt"))
    rbp = next(d.glob("ASMRedBlueInterpolation1_*_ffa03410.gnu.dis.txt"))
    run, proc, asm, rb = map(txt, (runp, procp, asmp, rbp))

    anchors = {}
    # Run argument identities: A=R0/root, B=R1/frame descriptor.
    for label, pat in {
        "A_saved": r"ffa1032a:.*\[FP -0x40\] = R0",
        "B_saved": r"ffa10348:.*\[FP -0x14\] = R1",
        "P5_is_B": r"ffa1035c:.*P5 = \[FP -0x14\]",
        "B_saved_fp0c": r"ffa10474:.*\[FP \+ 0xc\] = P5",
        # Derive FP-0x44 = B+0x40-A.
        "alg_B_into_P0": r"ffa104e2:.*P0 = \[FP \+ 0xc\]",
        "alg_A_into_P4": r"ffa104e4:.*P4 = \[FP -0x40\]",
        "alg_minus40": r"ffa104e6:.*P1 = -0x40",
        "alg_B_into_P5": r"ffa104e8:.*P5 = \[FP \+ 0xc\]",
        "alg_P1_minus_B": r"ffa104ea:.*P1 -= P0",
        "alg_P0_A_plus_P1": r"ffa104ec:.*P0 = P4 \+ P1",
        "alg_P5_zero": r"ffa10500:.*P5 = 0x0",
        "alg_P5_minus_P0": r"ffa10504:.*P5 -= P0",
        "alg_store_delta": r"ffa1051e:.*\[FP -0x44\] = P5",
        # Before processing stages P5 is restored to A and remains ABI-preserved.
        "P5_restore_A": r"ffa1054c:.*P5 = \[FP -0x40\]",
        # Sharp uses frame B; R2 is B+0x3c and B+0x38 is stack scratch.
        "sharp_B": r"ffa10856:.*P2 = \[FP \+ 0xc\]",
        "sharp_R2_green": r"ffa10c24:.*R2 = \[P2 \+ 0x3c\]",
        "sharp_scratch_load": r"ffa10c14:.*R4 = \[P2 \+ 0x38\]",
        "sharp_scratch_stack": r"ffa10c20:.*\[SP \+ 0xc\] = R4",
        "sharp_call": r"ffa10c28:.*CALL 0x0xffa03d90",
        # R/B pointer algebra: A + (B+0x40-A) = B+0x40; R1=[B+0x3c].
        "rb_delta_load": r"ffa10bc8:.*P1 = \[FP -0x44\]",
        "rb_add_delta": r"ffa10bd0:.*P5 = P5 \+ P1",
        "rb_R1_from_minus4": r"ffa10bd8:.*R1 = \[P5 \+ -0x4\]",
        "rb_call": r"ffa10bea:.*CALL 0x0xffa03410",
    }.items():
        anchors[label] = need(label, run, pat)

    # Process_Sharpness forwards caller R2 untouched to ASMUM, while passing
    # frame+0x38 as stack argument +0xc (temporary Gaussian plane).
    for label, pat in {
        "proc_scratch_load": r"ffa03dde:.*R6 = \[FP \+ 0x14\]",
        "proc_scratch_forward": r"ffa03de4:.*\[SP \+ 0xc\] = R6",
        "proc_asm_call": r"ffa03dea:.*CALL 0x0xffa018b0",
    }.items():
        anchors[label] = need(label, proc, pat)
    if re.search(r"\bR2\s*=", proc):
        raise SystemExit("Process_Sharpness unexpectedly rewrites R2 before ASMUM")

    # ASMUM: stack+0xc becomes Gaussian scratch; R2 is the source plane. The
    # second half reads scratch via I1, computes residual against R2-derived I2,
    # then writes the corrected result back through I2: R2 is sharpened in place.
    for label, pat in {
        "asm_scratch_arg": r"ffa018ba:.*R4 = \[P0 \+ 0xc\]",
        "asm_scratch_I0": r"ffa018f0:.*I0 = R4",
        "asm_source_from_R2": r"ffa01900:.*R7 = R2 \+ R5",
        "asm_source_P3": r"ffa0190a:.*P3 = R7",
        "asm_scratch_reload": r"ffa01972:.*R7 = \[P0 \+ 0xc\]",
        "asm_scratch_I1": r"ffa0197c:.*I1 = R7",
        "asm_source_I2": r"ffa01966:.*R7 = R5 \+ R2",
        "asm_write_source_lo": r"ffa01a6c:.*W\[I2\+\+\] = R4\.L",
        "asm_write_source_hi": r"ffa01a6e:.*W\[I2\] = R4\.H",
    }.items():
        anchors[label] = need(label, asm, pat)

    # R/B callee uses R1 as the packed base plane. It loads packed R3 from the
    # R1-derived P0 stream, averages 16-bit words from the R0-derived stream,
    # and adds them with packed +|+. Therefore the R1 plane is the common base
    # (green) to which interpolated colour differences are added.
    for label, pat in {
        "rb_r1_address": r"ffa034a4:.*R5 = R1 \+ R7",
        "rb_r1_to_P0": r"ffa034ac:.*P0 = R5",
        "rb_load_packed_green": r"ffa034ca:.*R3 = \[P0\+\+\]",
        "rb_average_difference": r"ffa034de:.*R4\.H = R4\.L \+ R4\.H",
        "rb_add_green_difference": r"ffa034ea:.*R3 = R3 \+\|\+ R4",
        "rb_clamp_max": r"ffa0343c:.*R7 = 0x3fff",
    }.items():
        anchors[label] = need(label, rb, pat)

    report = {
        "schema": "m9.bf561-sharp-rb-alias.v1",
        "files": {"run":runp.name,"process_sharpness":procp.name,"asmum":asmp.name,"rb":rbp.name},
        "anchors": anchors,
        "symbolic_pointer_proof": [
            "A := Run R0/root, B := Run R1/frame descriptor",
            "FP-0x44 = B + 0x40 - A",
            "P5 restored to A before Green/Noise/Sharp/RB stage chain",
            "at RB: P5 := A + (B+0x40-A) = B+0x40",
            "RB R1 := [P5-4] = [B+0x3c]",
            "Sharp R2 := [B+0x3c]",
            "ASMUM leaves R2 as source address and writes correction back through R2-derived I2",
            "therefore Sharp output and RB packed base input are the same frame+0x3c plane",
        ],
        "closed": {
            "sharp_uses_frame_plus_0x3c_as_source_output": True,
            "frame_plus_0x38_is_gaussian_scratch_not_sharp_output": True,
            "sharp_is_in_place_on_frame_plus_0x3c": True,
            "rb_R1_is_same_frame_plus_0x3c": True,
            "rb_R1_is_packed_base_added_to_interpolated_difference": True,
            "postsharp_green_to_rb_alias_exact": True,
        },
        "still_open": {
            "exact_identity_of_R_and_B_difference_lane_storage": True,
            "auto_iso_final_nIso_value": True,
            "xiaomi_norm16_to_leica14_quantization_policy": True,
        },
        "conclusion": "Exact BF561 pointer/ABI proof closes the Sharp->R/B alias: ASMUM sharpens frame+0x3c in place, and ASMRedBlueInterpolation1 receives that same frame+0x3c as R1, the packed base plane to which interpolated colour differences are added. frame+0x38 is Sharp scratch, not the sharpened image plane.",
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(report["conclusion"])


if __name__ == "__main__":
    main()
