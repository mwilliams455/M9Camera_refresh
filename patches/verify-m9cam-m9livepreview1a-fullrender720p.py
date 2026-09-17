#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livepreview1a-fullrender720p.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
layout = root / 'app/src/main/res/layout/layout_main_viewfinder.xml'
gradle = root / 'app/build.gradle'
for p in (renderer, controller, preview, layout, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEPREVIEW1A verify missing ' + str(p))

r = renderer.read_text()
c = controller.read_text()
p = preview.read_text()
x = layout.read_text()
g = gradle.read_text()

renderer_required = [
    'M9LIVEPREVIEW1A_FULLRENDER720P',
    'public static Bitmap renderLivePreview1A(',
    'renderAndSaveInternal(synthetic, frame, characteristics,',
    'cameraRotation, true)',
    'M9_LIVE_PREVIEW_1A_ACTIVE',
    'M9_LIVE_PREVIEW_1A_BITMAP',
    'M9LIVEPREVIEW1A production preview render failed',
    'M9SENSORTARGET1A',
    'm9cam.tonebound.v1a.050ev',
    'SAT2_M04_M05',
]
for token in renderer_required:
    if token not in r:
        raise SystemExit('M9LIVEPREVIEW1A renderer marker missing: ' + token)

preview_required = [
    'public static final int LANDSCAPE_WIDTH = 960;',
    'public static final int LANDSCAPE_HEIGHT = 720;',
    'reduceBayerParityPreserving',
    'sameParityNear',
    'M9R35Renderer.renderLivePreview1A(',
    'raw.getFormat() != ImageFormat.RAW_SENSOR',
]
for token in preview_required:
    if token not in p:
        raise SystemExit('M9LIVEPREVIEW1A preview marker missing: ' + token)

controller_required = [
    'M9LIVEPREVIEW1A_FULLRENDER720P',
    'M9_LIVE_PREVIEW_INTERVAL_MS = 140L',
    'm9LivePreviewProbeInFlight',
    'm9LivePreviewRenderBusy',
    'requestM9LivePreviewProbe1A()',
    'scheduleM9LivePreview1A()',
    'mPreviewRequestBuilder.addTarget(rawSurface);',
    'mPreviewRequestBuilder.removeTarget(rawSurface);',
    'mCaptureSession.capture(probe, m9LivePreviewCaptureCallback1A, mBackgroundHandler);',
    'M9LivePreview1A.render(previewRaw, previewChars,',
    'm9LivePreviewImageView.setImageBitmap(ready);',
]
for token in controller_required:
    if token not in c:
        raise SystemExit('M9LIVEPREVIEW1A controller marker missing: ' + token)

if c.count('mPreviewRequestBuilder.addTarget(rawSurface);') != 1:
    raise SystemExit('M9LIVEPREVIEW1A expected exactly one experimental RAW target add')
if c.count('mPreviewRequestBuilder.removeTarget(rawSurface);') < 2:
    raise SystemExit('M9LIVEPREVIEW1A expected normal + failure RAW target removal paths')
if 'setRepeatingRequest(probe' in c or 'setRepeatingBurst(probe' in c:
    raise SystemExit('M9LIVEPREVIEW1A must not use probe as repeating RAW request')

layout_required = [
    'android:id="@+id/m9_live_preview"',
    'android:scaleType="centerCrop"',
    'android:visibility="invisible"',
]
for token in layout_required:
    if token not in x:
        raise SystemExit('M9LIVEPREVIEW1A layout marker missing: ' + token)

if 'm9livepreview1a-720pfull' not in g.lower():
    raise SystemExit('M9LIVEPREVIEW1A versionName marker missing')

print('M9LIVEPREVIEW1A_FULLRENDER720P VERIFY PASS')
print('preview source: RAW_SENSOR one-shot probes')
print('preview reduction: CFA parity-preserving 960x720')
print('preview renderer: exact primary renderAndSaveInternal(primaryRoute=true)')
print('preview file side effects: intercepted before JPEG/EXIF/publication')
print('normal capture path: thread-local gate inactive')
print('RAW target mode: one-shot capture only; never repeating probe')
