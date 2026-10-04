#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1g-normalpriority.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
preview=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
selector=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle=root/'app/build.gradle'
for p in (controller,preview,renderer,selector,gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1G verify missing: '+str(p))

c=controller.read_text(); p=preview.read_text(); r=renderer.read_text(); s=selector.read_text(); g=gradle.read_text()

for token in (
    'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
    'ByteBuffer packed = packFullRawPreservingSamples1C(raw);'):
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1G lost 1C preview token: '+token)
for token in (
    'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP',
    'previewDiag.put("preRenderSourceReduction", false);',
    '"after_edgePlacementBestFit2A_before_JPEG_encode"'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1G lost 1C renderer token: '+token)
for token in (
    'M9LIVEWYSIWYG1F_LIVEORIENTATION',
    'PhotonCamera.getGravity().getCameraRotation(mSensorOrientation)',
    'M9LIVEWYSIWYG1G_NORMALPRIORITY',
    'M9_LIVE_PREVIEW_INTERVAL_MS = 120L',
    'M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 200L',
    'android.os.Process.THREAD_PRIORITY_DEFAULT',
    '"M9LIVEWYSIWYG1G renderWallMs="'):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1G controller token missing: '+token)
for forbidden in (
    'android.os.Process.THREAD_PRIORITY_BACKGROUND',
    'M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 800L',
    'M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER'):
    if forbidden in c or forbidden in p or forbidden in r:
        raise SystemExit('M9LIVEWYSIWYG1G forbidden old path present: '+forbidden)

for token in (
    'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
    'm9LiveWysiwygDisplayedIso1B',
    'm9LiveWysiwygDisplayedExposureNs1B',
    'IsoExpoSelector.setExactExposureM9Wysiwyg1B('):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1G lost 1B lock token: '+token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1G exact exposure setter missing')

if 'm9livewysiwyg1g-normalpriority' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1G versionName marker missing')

print('M9LIVEWYSIWYG1G_NORMALPRIORITY VERIFY PASS')
print(' - exact 1C full-source photographic preview retained')
print(' - 1F live orientation retained')
print(' - 1B displayed exposure lock retained')
print(' - worker priority restored to DEFAULT')
print(' - post-render idle reduced to 200 ms')
print(' - per-frame render wall time logged')
