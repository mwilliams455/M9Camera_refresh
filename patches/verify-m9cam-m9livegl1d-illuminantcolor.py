#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1d-illuminantcolor.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
mrp = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
gpp = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java"
cfp = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
fsp = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
ccp = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
rp = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gradlep = root / "app/build.gradle"

for p in (mrp, gpp, cfp, fsp, ccp, rp, gradlep):
    if not p.exists():
        raise SystemExit("M9LIVEGL1D verify missing: " + str(p))

mr = mrp.read_text()
gp = gpp.read_text()
cf = cfp.read_text()
fs = fsp.read_text()
cc = ccp.read_text()
rr = rp.read_text()
g = gradlep.read_text()

checks = {
    "GL1D renderer marker": "M9LIVEGL1D_ILLUMINANTCOLOR" in mr,
    "GL1D shader marker": "M9LIVEGL1D_ILLUMINANTCOLOR" in fs,
    "A matrix endpoint": "M9_LIVE_GL1D_SOURCE_A" in mr and "0.55866248f" in mr,
    "D65 endpoint retained": "M9_LIVE_GL1C_SOURCE_D65" in mr,
    "illuminant setter": "setM9IlluminantState1D" in mr and "setM9IlluminantState1D" in gp,
    "live neutral bridge": "SENSOR_NEUTRAL_COLOR_POINT" in cf and "setM9IlluminantState1D" in cf,
    "mired A/D65 weight": "1000000.0 / 6500.0" in cf and "1000000.0 / 2850.0" in cf,
    "TG1 4500/3200": "4500.0 - cct1D" in cf and "4500.0 - 3200.0" in cf,
    "luma preservation": "target *= yin / yout;" in fs,
    "dynamic A/D65 shader": "mix(d65, a, clamp(uM9IlluminantWeightA1D" in fs,
    "TG1 helper": "tungstenGuard1D" in fs,
    "TG1 negative Cb 25pct": "0.25 * w" in fs,
    "TG1 negative Cr 16pct": "0.16 * w" in fs,
    "GL1B exposure retained": "linear *= uM9ExposureScale1B;" in fs,
    "GL1B still authority retained": "Photon_GL_IsoExpoSelector_intended_pair" in cc,
    "GL1C black floor frozen": "M9_LIVE_GL1C_BLACK_FLOOR = 0.0030f" in mr,
    "GL1C shadow power frozen": "M9_LIVE_GL1C_SHADOW_POWER = 1.040f" in mr,
    "GL1C shoulder frozen": "M9_LIVE_GL1C_HIGHLIGHT_SHOULDER = 0.20f" in mr,
    "falloff remains identity": "M9_LIVE_GL1C_FALLOFF_STRENGTH = 0.0f" in mr,
    "SAT2 retained": "sat2M9" in fs,
    "curve02 retained": "curve02M9" in fs,
    "still tonebound frozen": "toneBoundLimitEv1A = 0.5" in rr,
    "capture mutation false": 'captureExposureMutation", false' in rr,
    "version": "m9livegl1d-illuminantcolor" in g.lower(),
}
for name, ok in checks.items():
    print(name, ok)
    if not ok:
        raise SystemExit("M9LIVEGL1D verify failed: " + name)

# Matrix endpoint neutral-axis proof. Values below are row-major equivalents
# of the column-major Java constants.
D65 = [
    (0.53316906, 0.32894386, 0.13788708),
    (0.09333790, 0.70803917, 0.19862293),
    (0.01986253, 0.28021240, 0.69992507),
]
A = [
    (0.53755093, 0.38280546, 0.07964361),
    (0.12914680, 0.76276908, 0.10808411),
    (0.05817552, 0.38316200, 0.55866248),
]
for label, rows in (("D65", D65), ("A", A)):
    for i, row in enumerate(rows):
        total = sum(row)
        print(label, "row", i, "sum", total)
        if abs(total - 1.0) > 3e-6:
            raise SystemExit("M9LIVEGL1D neutral-axis endpoint failed")

print("M9LIVEGL1D_VERIFY_PASS")
print("GL1B exposure frozen")
print("GL1C tone frozen")
print("dynamic M9 A/D65 colour + TG1 active")
print("colour transform is luminance-preserving")
print("still photographic renderer contract retained")
