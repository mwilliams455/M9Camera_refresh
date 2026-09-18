#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1f-tonelut1a.py <PhotonCamera-root>")
root = Path(sys.argv[1]).resolve()

files = {
    "main_renderer": root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java",
    "shader": root / "app/src/main/assets/shaders/preview/main_fs.glsl",
    "tone_model": root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java",
    "analyzer": root / "app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java",
    "lut_raw": root / "app/src/main/assets/m9/m9_preview_standard_gl1f_17.rgb",
    "lut_cube": root / "app/src/main/assets/m9/m9_preview_standard_gl1f_17.cube",
    "curve02": root / "app/src/main/assets/m9/m9_curve02_firmware.bin",
}
for name, p in files.items():
    if not p.exists():
        raise SystemExit(f"GL1F missing {name}: {p}")

main = files["main_renderer"].read_text()
shader = files["shader"].read_text()
tone = files["tone_model"].read_text()
analyzer = files["analyzer"].read_text()

checks = [
    ("MainRenderer build marker", "M9LIVEGL1F_TONELUT1A" in main),
    ("MainRenderer gain uniform", "uM9PreviewGainEv1F" in main),
    ("tone model schema", "m9cam.livepreview.gl1f.tonelut1a" in tone),
    ("analyzer live tone stats", "fillLiveToneStats1F" in analyzer),
    ("shader GL1F marker", "M9LIVEGL1F_TONELUT1A" in shader),
    ("shader intended exposure", "linear *= uM9ExposureScale1B" in shader),
    ("shader tone placement", "tonePlacement1F(linear)" in shader),
    ("shader curve02 after tone", "curve02M9(toned1F.r)" in shader),
    ("shader display LUT", "previewLut1F(curved1F)" in shader),
]
for label, ok in checks:
    print(("OK   " if ok else "FAIL ") + label)
    if not ok:
        raise SystemExit("GL1F contract failure: " + label)

start = shader.find("vec3 m9DisplayTransform(vec3 photonSrgb, vec2 uv)")
if start < 0:
    raise SystemExit("GL1F display transform missing")
end = shader.find("\n}", start)
if end < 0:
    raise SystemExit("GL1F display transform end missing")
transform = shader[start:end + 2]
for marker in (
    "sourceToM9Target1D(linear)",
    "sat2M9(linear)",
    "tungstenGuard1D(",
):
    ok = marker not in transform
    print(("OK   " if ok else "FAIL ") + "live bypass " + marker)
    if not ok:
        raise SystemExit("GL1F forbidden live colour operation active: " + marker)

raw = files["lut_raw"].read_bytes()
expected = 17 * 17 * 17 * 3
print("LUT_BYTES", len(raw), "EXPECTED", expected)
if len(raw) != expected:
    raise SystemExit(f"GL1F raw LUT size mismatch: {len(raw)} != {expected}")

cube = files["lut_cube"].read_text()
if "LUT_3D_SIZE 17" not in cube:
    raise SystemExit("GL1F cube LUT size declaration missing")

print("CURVE02_SHA256", hashlib.sha256(files["curve02"].read_bytes()).hexdigest())
print("PREVIEW_LUT_SHA256", hashlib.sha256(raw).hexdigest())
print("M9LIVEGL1F readable verification PASS")
