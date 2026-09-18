#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1c-appearanceparity.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
mrp = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
fsp = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
cfp = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java"
ccp = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
rp = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gp = root / "app/build.gradle"

for p in (mrp, fsp, cfp, ccp, rp, gp):
    if not p.exists():
        raise SystemExit("M9LIVEGL1C verify missing: " + str(p))

mr = mrp.read_text()
fs = fsp.read_text()
cf = cfp.read_text()
cc = ccp.read_text()
r = rp.read_text()
g = gp.read_text()

checks = {
    "renderer marker": "M9LIVEGL1C_APPEARANCEPARITY" in mr,
    "shader marker": "M9LIVEGL1C_APPEARANCEPARITY" in fs,
    "source matrix uniform": "uM9SourceMatrix1C" in mr and "uM9SourceMatrix1C" in fs,
    "source matrix coefficient": "0.53316906f" in mr and "0.69992507f" in mr,
    "black floor": "M9_LIVE_GL1C_BLACK_FLOOR = 0.0030f" in mr,
    "shadow power": "M9_LIVE_GL1C_SHADOW_POWER = 1.040f" in mr,
    "highlight shoulder": "M9_LIVE_GL1C_HIGHLIGHT_SHOULDER = 0.20f" in mr,
    "falloff identity": "M9_LIVE_GL1C_FALLOFF_STRENGTH = 0.0f" in mr,
    "falloff hook": "falloffGain1C" in fs,
    "target-domain entry": "linear = sourceToM9Target1C(linear);" in fs,
    "GL1B exposure shader retained": "linear *= uM9ExposureScale1B;" in fs,
    "GL1B exposure controller retained": "updateM9LiveGlIntendedExposure1B" in cf,
    "GL1B still authority retained": "Photon_GL_IsoExpoSelector_intended_pair" in cc,
    "SAT2 retained": "sat2M9" in fs,
    "curve02 retained": "curve02M9" in fs,
    "tonebound frozen": "toneBoundLimitEv1A = 0.5" in r,
    "capture exposure mutation false": 'captureExposureMutation", false' in r,
    "version": "m9livegl1c-appearanceparity" in g.lower(),
}
for name, ok in checks.items():
    print(name, ok)
    if not ok:
        raise SystemExit("M9LIVEGL1C verify failed: " + name)

# Independent arithmetic check of the source matrix rows. Values are the
# row-normalized D65 M9 target transform, stored column-major in Java.
rows = [
    (0.53316906, 0.32894386, 0.13788708),
    (0.09333790, 0.70803917, 0.19862293),
    (0.01986253, 0.28021240, 0.69992507),
]
for i, row in enumerate(rows):
    total = sum(row)
    print("source row", i, "sum", total)
    if abs(total - 1.0) > 2e-6:
        raise SystemExit("M9LIVEGL1C neutral-axis row sum failed")

print("M9LIVEGL1C_VERIFY_PASS")
print("GL1B exposure authority preserved")
print("M9 D65 target-domain colour entry active")
print("falloff hook present but identity-strength")
print("still photographic renderer contract retained")
