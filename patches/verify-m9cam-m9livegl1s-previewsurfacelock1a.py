#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9livegl1s-previewsurfacelock1a.py <PhotonCamera-root>")

root = Path(sys.argv[1]).resolve()
cc_path = root / "app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java"
shader_path = root / "app/src/main/assets/shaders/preview/main_fs.glsl"
tone_path = root / "app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LiveToneModel1F.java"
for p in (cc_path, shader_path, tone_path):
    if not p.exists():
        raise SystemExit("GL1S verify missing " + str(p))

cc = cc_path.read_text()
shader = shader_path.read_text()
tone = tone_path.read_text()

checks = [
    ("GL1S marker", "M9LIVEGL1S_PREVIEWSURFACELOCK1A" in cc),
    ("RAW target retained", "captureBuilder.addTarget(mImageReaderRaw.getSurface());" in cc),
    ("M9 isolation gate", "M9Config.isCaptureTest()" in cc and "m9IsolateStillFromPreview1S" in cc),
    ("M9 RAW-only log", "stillTargets=RAW_ONLY" in cc and "previewSurfaceTarget=false" in cc),
    ("preview target gated away", "if (!m9IsolateStillFromPreview1S" in cc),
    ("RAWVIDEO preserved", "selectedMode == CameraMode.RAWVIDEO" in cc),
    ("UNLIMITED preserved", "selectedMode == CameraMode.UNLIMITED" in cc),
    ("GL1B intended latch retained", "Photon_GL_IsoExpoSelector_intended_pair" in cc),
    ("exact exposure setter retained", "IsoExpoSelector.setExactExposureM9Wysiwyg1B(" in cc),
    ("capture ISO retained", "m9CaptureIso1B" in cc),
    ("capture shutter retained", "m9CaptureExposureNs1B" in cc),
    ("GL1Q shader retained", "M9LIVEGL1Q_PAIRCURVE1A" in shader and "linear *= uM9ExposureScale1B" in shader),
    ("FIX1 exposure authority retained", "M9LIVEGL1R_FIX1_EXPOSUREAUTHORITY1A" in tone),
]
for label, ok in checks:
    print(("OK   " if ok else "FAIL ") + label)
    if not ok:
        raise SystemExit("GL1S contract failure: " + label)

# Ensure the stale unconditional M9 path no longer exists.
stale = '''                if(frametime > 0.06 && !isDualSession || selectedMode == CameraMode.RAWVIDEO || selectedMode == CameraMode.UNLIMITED || (!IsoExpoSelector.HDR)) {
                    captureBuilder.addTarget(surface);
                }
'''
if stale in cc:
    raise SystemExit("GL1S stale unconditional still->preview target remains")

print("M9LIVEGL1S_PREVIEWSURFACELOCK1A VERIFY PASS")
print(" - M9 still request no longer targets live preview surface")
print(" - RAW capture target and GL1B exact exposure retained")
print(" - preview shader/tone architecture retained")
