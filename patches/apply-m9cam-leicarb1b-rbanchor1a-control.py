#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = "LEICARB1B_RBANCHOR1A_CONTROL"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <PhotonCamera root>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    cpp_path = root / "app/src/main/cpp/m9color_jni.cpp"
    timing_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java"
    if not cpp_path.is_file() or not timing_path.is_file():
        raise RuntimeError("assembled SHARPSOURCE1C-RBANCHOR1A baseline missing")

    cpp = cpp_path.read_text()
    timing = timing_path.read_text()

    # This isolation build must retain the proven RBANCHOR1A pixel path exactly.
    if "SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID" not in cpp:
        raise RuntimeError("RBANCHOR1A native identity missing")
    if "LEICARB1A_SHARPGREEN_RGGB" in cpp or "m9LeicaRbEstimate(" in cpp:
        raise RuntimeError("LEICARB1A native adapter unexpectedly present")
    if "const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;" not in cpp:
        raise RuntimeError("RBANCHOR1A MHC R-G proxy missing")
    if "const int db=static_cast<int>(m9ClosureQ14(base[2]))-mg;" not in cpp:
        raise RuntimeError("RBANCHOR1A MHC B-G proxy missing")
    if "m9SharpSourceLeicaGreen14" not in cpp or "m9ClosureSharpIso160Standard" not in cpp:
        raise RuntimeError("current Leica green/Sharp baseline missing")
    if MARKER in timing:
        raise RuntimeError("LEICARB1B control label already present")

    old = '        root.put("sharpnessRbPolicy", "RBANCHOR1A_sharpLeicaGreen_plus_frozenMHC_color_differences_proxy");\n'
    new = (
        old
        + '        root.put("leicaRbIsolationExperiment", "LEICARB1B_RBANCHOR1A_CONTROL");\n'
        + '        root.put("leicaRbIsolationPixelPath", "SHARPSOURCE1C_RBANCHOR1A_exact_parent_no_Interp1_adapter");\n'
        + '        root.put("leicaRbIsolationPurpose", "foliage_sky_sharpness_regression_control_against_LEICARB1A");\n'
    )
    timing = replace_once(timing, old, new, "primary timing RBANCHOR1A policy")
    timing_path.write_text(timing)

    print("LEICARB1B_RBANCHOR1A_CONTROL applied")
    print(" - native pixel path unchanged from assembled SHARPSOURCE1C-RBANCHOR1A parent")
    print(" - Leica green / Standard mode4 x2 / Noise2 / 9px support preserved")
    print(" - frozen MHC R-G/B-G proxy restored as the active R/B reconstruction")
    print(" - timing sidecar label only; no native pixel arithmetic modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
