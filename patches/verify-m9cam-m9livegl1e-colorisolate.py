#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1e-colorisolate.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
mrp = root / "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java"
fsp = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
ccp = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
rp = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
gradlep = root / "app/build.gradle"

for p in (mrp, fsp, ccp, rp, gradlep):
    if not p.exists():
        raise SystemExit("M9LIVEGL1E verify missing: " + str(p))

mr = mrp.read_text()
fs = fsp.read_text()
cc = ccp.read_text()
rr = rp.read_text()
g = gradlep.read_text()

checks = {
    "GL1E renderer marker": "M9LIVEGL1E_COLORISOLATE" in mr,
    "GL1E shader marker": "M9LIVEGL1E_COLORISOLATE" in fs,
    "Photon OES source retained": "samplerExternalOES" in fs,
    "GL1B exposure retained": "linear *= uM9ExposureScale1B;" in fs,
    "GL1C tone retained": "linear = tonePlacement1C(linear);" in fs,
    "GL1C falloff retained": "linear *= falloffGain1C(uv);" in fs,
    "display gain retained": "linear * uM9DisplayGain" in fs,
    "curve02 retained": "curve02M9(toned1E.r)" in fs,
    "GL1D source helper still assembled": "sourceToM9Target1D" in fs,
    "SAT2 helper still assembled": "sat2M9" in fs,
    "TG1 helper still assembled": "tungstenGuard1D" in fs,
    "GL1B still authority retained": "Photon_GL_IsoExpoSelector_intended_pair" in cc,
    "GL1C black floor frozen": "M9_LIVE_GL1C_BLACK_FLOOR = 0.0030f" in mr,
    "GL1C shadow power frozen": "M9_LIVE_GL1C_SHADOW_POWER = 1.040f" in mr,
    "GL1C shoulder frozen": "M9_LIVE_GL1C_HIGHLIGHT_SHOULDER = 0.20f" in mr,
    "falloff still identity": "M9_LIVE_GL1C_FALLOFF_STRENGTH = 0.0f" in mr,
    "still tonebound frozen": "toneBoundLimitEv1A = 0.5" in rr,
    "capture mutation false": 'captureExposureMutation", false' in rr,
    "version": "m9livegl1e-colorisolate" in g.lower(),
}
for name, ok in checks.items():
    print(name, ok)
    if not ok:
        raise SystemExit("M9LIVEGL1E verify failed: " + name)

# Prove the live transform itself bypasses the three colour-domain operations.
start = fs.find("vec3 m9DisplayTransform(vec3 photonSrgb, vec2 uv)")
if start < 0:
    raise SystemExit("M9LIVEGL1E transform missing")
end = fs.find("\n}", start)
if end < 0:
    raise SystemExit("M9LIVEGL1E transform end missing")
transform = fs[start:end+2]

for forbidden in (
    "sourceToM9Target1D(linear)",
    "sat2M9(linear)",
    "tungstenGuard1D(",
):
    ok = forbidden not in transform
    print("transform bypass " + forbidden, ok)
    if not ok:
        raise SystemExit("M9LIVEGL1E colour isolation failed: " + forbidden)

for required in (
    "linear *= uM9ExposureScale1B;",
    "linear = tonePlacement1C(linear);",
    "linear *= falloffGain1C(uv);",
    "linear * uM9DisplayGain",
    "curve02M9(toned1E.r)",
):
    ok = required in transform
    print("transform retain " + required, ok)
    if not ok:
        raise SystemExit("M9LIVEGL1E frozen preview stage missing: " + required)

print("M9LIVEGL1E_VERIFY_PASS")
print("sensor-domain target matrix bypassed")
print("SAT2 bypassed")
print("TG1 bypassed")
print("GL1B exposure frozen")
print("GL1C tone frozen")
print("curve02 retained")
print("still photographic renderer retained")
