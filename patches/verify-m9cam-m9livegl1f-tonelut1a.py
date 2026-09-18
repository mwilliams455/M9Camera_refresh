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
    ("GL1G display-delta marker", "M9LIVEGL1G_DISPLAYDELTA1A" in shader),
    ("GL1G linear to sRGB", "linearToSrgbM9(linear)" in shader),
    ("RGB8 unpack alignment fix", "M9LIVEGL1F_UNPACK1" in main and "glPixelStorei(GLES20.GL_UNPACK_ALIGNMENT, 1)" in main),
    ("unpack alignment restored", "glPixelStorei(GLES20.GL_UNPACK_ALIGNMENT, 4)" in main),
    ("LUT packed layout marker", "M9LIVEGL1F_LUTPACK1" in (root.parent / "patches/apply-m9cam-m9livegl1f-tonelut1a-fix1.py").read_text() if (root.parent / "patches/apply-m9cam-m9livegl1f-tonelut1a-fix1.py").exists() else True),
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
if "linear *= uM9ExposureScale1B" not in transform:
    raise SystemExit("GL1G exposure authority missing from active transform")
for marker in (
    "sourceToM9Target1D(linear)",
    "sat2M9(linear)",
    "tungstenGuard1D(",
    "tonePlacement1F(linear)",
    "linear * uM9DisplayGain",
    "curve02M9(toned1F.r)",
    "previewLut1F(curved1F)",
):
    ok = marker not in transform
    print(("OK   " if ok else "FAIL ") + "live bypass " + marker)
    if not ok:
        raise SystemExit("GL1F forbidden live colour operation active: " + marker)

raw = files["lut_raw"].read_bytes()
expected = 17 * 17 * 17 * 3
print("LUT_BYTES", len(raw), "EXPECTED", expected)
row_bytes = 17 * 17 * 3
print("LUT_ROW_BYTES", row_bytes, "MOD4", row_bytes % 4)
if row_bytes % 4 == 0:
    raise SystemExit("GL1F verifier premise changed: RGB8 row unexpectedly 4-byte aligned")
if len(raw) != expected:
    raise SystemExit(f"GL1F raw LUT size mismatch: {len(raw)} != {expected}")

cube = files["lut_cube"].read_text()
if "LUT_3D_SIZE 17" not in cube:
    raise SystemExit("GL1F cube LUT size declaration missing")

# Verify the raw texture is packed exactly as the shader expects:
# cube sequence = [B][G][R], texture memory = [G row][B tile][R].
vals = []
for line in cube.splitlines():
    line = line.strip()
    if not line or line.startswith(("TITLE", "LUT_3D_SIZE", "DOMAIN_")):
        continue
    parts = line.split()
    if len(parts) == 3:
        vals.append(tuple(float(x) for x in parts))
if len(vals) != 17*17*17:
    raise SystemExit(f"GL1F cube value count mismatch: {len(vals)}")

max_err = 0
for b in range(17):
    for g in range(17):
        for r in range(17):
            cube_i = (b*17 + g)*17 + r
            tex_i = (g*17*17 + b*17 + r)*3
            exp = tuple(int(round(max(0.0, min(1.0, x))*255.0)) for x in vals[cube_i])
            got = tuple(raw[tex_i+k] for k in range(3))
            max_err = max(max_err, *(abs(got[k]-exp[k]) for k in range(3)))
if max_err > 1:
    raise SystemExit(f"GL1F LUT packed-layout mismatch max_byte_error={max_err}")
print("LUTPACK1_MAX_BYTE_ERROR", max_err)

# Neutral diagonal must remain neutral after packing.
for i in (0, 1, 4, 8, 12, 16):
    tex_i = (i*17*17 + i*17 + i)*3
    rgb = tuple(raw[tex_i+k] for k in range(3))
    if max(rgb) - min(rgb) > 1:
        raise SystemExit(f"GL1F neutral diagonal corrupted at {i}: {rgb}")
print("LUTPACK1_NEUTRALS PASS")

print("CURVE02_SHA256", hashlib.sha256(files["curve02"].read_bytes()).hexdigest())
print("PREVIEW_LUT_SHA256", hashlib.sha256(raw).hexdigest())
print("M9LIVEGL1F readable verification PASS")
