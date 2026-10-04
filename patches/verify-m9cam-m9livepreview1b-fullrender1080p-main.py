#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livepreview1b-fullrender1080p-main.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
for p in (preview, renderer, controller):
    if not p.exists():
        raise SystemExit('M9LIVEPREVIEW1B VERIFY missing: ' + str(p))

p = preview.read_text()
checks = [
    'public static final int LANDSCAPE_WIDTH = 1440;',
    'public static final int LANDSCAPE_HEIGHT = 1080;',
    'M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN',
    'reduceBayerParityPreserving',
    'M9R35Renderer.renderLivePreview1A('
]
for marker in checks:
    if marker not in p:
        raise SystemExit('M9LIVEPREVIEW1B VERIFY preview marker missing: ' + marker)
for stale in ('LANDSCAPE_WIDTH = 960;', 'LANDSCAPE_HEIGHT = 720;'):
    if stale in p:
        raise SystemExit('M9LIVEPREVIEW1B VERIFY stale 720p target remains: ' + stale)

r = renderer.read_text()
for marker in ('M9SENSORTARGET1A', 'm9cam.tonebound.v1a.050ev', 'SAT2_M04_M05',
               'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN'):
    if marker not in r:
        raise SystemExit('M9LIVEPREVIEW1B VERIFY renderer marker missing: ' + marker)
if 'FULL_PRODUCTION_RENDER_REDUCED_RAW_960x720' in r:
    raise SystemExit('M9LIVEPREVIEW1B VERIFY stale renderer 720p diagnostic remains')

c = controller.read_text()
for marker in ('m9LivePreviewProbeInFlight', 'm9LivePreviewRenderBusy',
               'M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN'):
    if marker not in c:
        raise SystemExit('M9LIVEPREVIEW1B VERIFY controller marker missing: ' + marker)

print('M9LIVEPREVIEW1B VERIFY PASS')
print(' - 1440x1080 CFA-preserving RAW preview target present')
print(' - production M9SENSORTARGET1A/TONEBOUND/SAT2 renderer markers present')
print(' - single-flight live-render guards retained')
print(' - scope: main-sensor device validation before other lenses')
