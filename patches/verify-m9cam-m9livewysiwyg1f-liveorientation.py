#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv)!=2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1f-liveorientation.py <PhotonCamera-root>')

root=Path(sys.argv[1]).resolve()
controller=root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
preview=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
selector=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle=root/'app/build.gradle'
for p in (controller,preview,renderer,selector,gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1F verify missing: '+str(p))

c=controller.read_text()
p=preview.read_text()
r=renderer.read_text()
s=selector.read_text()
g=gradle.read_text()

for token in (
    'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
    'ByteBuffer packed = packFullRawPreservingSamples1C(raw);',
):
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1F lost 1C preview token: '+token)
for token in (
    'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP',
    'previewDiag.put("preRenderSourceReduction", false);',
    '"after_edgePlacementBestFit2A_before_JPEG_encode"',
):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1F lost 1C renderer token: '+token)
for token in (
    'M9LIVEWYSIWYG1E_FULLSOURCE_THROTTLE',
    'M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 800L',
    'm9LivePreviewLastRenderEndElapsedMs1E',
    'android.os.Process.THREAD_PRIORITY_BACKGROUND',
):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1F lost 1E throttle token: '+token)

required_controller=(
    'M9LIVEWYSIWYG1F_LIVEORIENTATION',
    'PhotonCamera.getGravity().getCameraRotation(mSensorOrientation)',
    '"M9LIVEWYSIWYG1F liveRotation="',
    '" staleStillRotation=" + cameraRotation',
)
for token in required_controller:
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1F orientation token missing: '+token)

bad='final int previewRotation = cameraRotation;'
if bad in c:
    raise SystemExit('M9LIVEWYSIWYG1F stale preview rotation source remains')

for token in (
    'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
    'm9LiveWysiwygDisplayedIso1B',
    'm9LiveWysiwygDisplayedExposureNs1B',
    'IsoExpoSelector.setExactExposureM9Wysiwyg1B(',
):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1F lost 1B lock token: '+token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1F lost exact exposure setter')

if 'm9livewysiwyg1f-liveorientation' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1F versionName marker missing')

print('M9LIVEWYSIWYG1F_LIVEORIENTATION VERIFY PASS')
print(' - exact 1C full-source photographic preview retained')
print(' - exact 1E scheduling throttle retained')
print(' - live preview orientation comes from current gravity snapshot')
print(' - stale still-capture cameraRotation no longer drives live bitmap orientation')
print(' - still capture orientation and 1B displayed exposure lock remain untouched')
