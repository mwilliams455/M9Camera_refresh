#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-m9tungstencont1a.py <PhotonCamera-root>")

root=Path(sys.argv[1]).resolve()
files={
"gpu":root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9GpuPreview2A.java",
"continuity":root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewSourceContinuity1A.java",
"pairer":root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewStatePairer1A.java",
"camera":root/"app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java",
"state":root/"app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewFrameState1W.java",
"renderer":root/"app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java",
"shader":root/"app/src/main/assets/shaders/preview/main_fs.glsl",
"gradle":root/"app/build.gradle",
"still":root/"app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java",
}
for name,p in files.items():
    if not p.exists(): raise SystemExit("M9TUNGSTENCONT1A missing "+name)

checks={
"continuity revision":"M9TUNGSTENCONT1A" in files["continuity"].read_text(),
"one second hold":"HOLD_LAST_GOOD_NS = 1_000_000_000L" in files["continuity"].read_text(),
"same camera hold":"id.equals(lastGood.cameraId)" in files["continuity"].read_text(),
"held frame":"heldForContinuity" in files["gpu"].read_text(),
"held diagnostic":"continuityHeld" in files["gpu"].read_text(),
"camera bridge":"M9PreviewSourceContinuity1A.resolve" in files["camera"].read_text(),
"draw TG1 independent":"frame1W.source2A.continuityHeld || !frame1W.source2A.ready" in files["renderer"].read_text(),
"ready-only TG1 removed":"glUniform1f(uTungsten2A, source.tungstenWeight)" not in files["renderer"].read_text(),
"fallback TG1 shader":"return tungsten2A(fallback1A);" in files["shader"].read_text(),
"fallback diagnostic":"processed_OES_exposure_plus_TG1_fallback" in files["state"].read_text(),
"pairer revision":"M9PREVIEWPAIR1A" in files["pairer"].read_text(),
"pairer exact match":"exact_timestamp_match" in files["pairer"].read_text(),
"pairer bounded defer":"MAX_DEFER_NS = 120_000_000L" in files["pairer"].read_text(),
"renderer pairer offer":"mM9Pairer1A.offer(state)" in files["renderer"].read_text(),
"renderer paired draw":"mM9Pairer1A.select(" in files["renderer"].read_text(),
"renderer unmatched defer":"if (frame1W == null) return;" in files["renderer"].read_text(),
"pair diagnostics":"stateTexturePair1A" in files["renderer"].read_text(),
"version":"1.61-m9detail1h-tg1pair1a" in files["gradle"].read_text(),
}
for name,ok in checks.items():
    print(name,ok)
    if not ok: raise SystemExit("M9TUNGSTENCONT1A verify failed: "+name)

still_sha=hashlib.sha256(files["still"].read_bytes()).hexdigest()
if still_sha!="a7dfa41df5eaa92c69ef4236e6d697f10e6681cadfbfc46d66869628d405ab56":
    raise SystemExit("M9TUNGSTENCONT1A still renderer freeze failed")
print("still renderer frozen",still_sha)
print("M9TUNGSTENCONT1A_VERIFY_PASS")
