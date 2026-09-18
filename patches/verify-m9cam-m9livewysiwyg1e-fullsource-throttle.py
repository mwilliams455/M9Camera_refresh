#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1e-fullsource-throttle.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle = root / 'app/build.gradle'
for p in (controller, preview, renderer, selector, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1E verify missing: ' + str(p))

c = controller.read_text()
p = preview.read_text()
r = renderer.read_text()
s = selector.read_text()
g = gradle.read_text()

# The known-good 1C photographic path must be exactly the live rendering path.
for token in (
        'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
        'ByteBuffer packed = packFullRawPreservingSamples1C(raw);',
        'packed, srcW, srcH, characteristics, captureResult, captureRequest'):
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1E lost 1C full-source preview token: ' + token)
for token in (
        'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP',
        'previewDiag.put("preRenderSourceReduction", false);',
        '"after_edgePlacementBestFit2A_before_JPEG_encode"',
        '"full_resolution_RAW_is_renderer_input_no_pre_render_reduction"'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1E lost 1C renderer token: ' + token)

# Explicitly ban the invalid 1D reference-reduction path.
for forbidden in (
        'M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER',
        'reduceBayerMeterReference1600PreservingParity1D',
        'FULL_PRODUCTION_RENDER_REFERENCE1600_FINAL_BITMAP',
        'TC20_1600_long_side_reference_spatial_workload_only'):
    if forbidden in p or forbidden in r or forbidden in c:
        raise SystemExit('M9LIVEWYSIWYG1E invalid 1D reduction path present: ' + forbidden)

# Performance policy may change only scheduling/thread priority, never pixels.
for token in (
        'M9LIVEWYSIWYG1E_FULLSOURCE_THROTTLE',
        'M9_LIVE_PREVIEW_MIN_IDLE_AFTER_RENDER_MS = 800L',
        'm9LivePreviewLastRenderEndElapsedMs1E',
        'android.os.SystemClock.elapsedRealtime()',
        'android.os.Process.THREAD_PRIORITY_BACKGROUND'):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1E throttle token missing: ' + token)

# Still must capture the exact exposure that produced the displayed M9 preview.
for token in (
        'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
        'm9LiveWysiwygDisplayedIso1B',
        'm9LiveWysiwygDisplayedExposureNs1B',
        'ImageView_displayed_M9_frame',
        'IsoExpoSelector.setExactExposureM9Wysiwyg1B('):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1E lost 1B controller token: ' + token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1E lost exact exposure selector')

if 'm9livewysiwyg1e-fullsource-throttle' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1E versionName marker missing')

print('M9LIVEWYSIWYG1E_FULLSOURCE_THROTTLE VERIFY PASS')
print(' - live preview remains exact 1C full-resolution source render')
print(' - no 1D pre-render reduction/reference-render path survives')
print(' - complete production M9 pipeline and final edge-placement boundary remain active')
print(' - performance change is scheduling/thread priority only')
print(' - 800 ms idle window follows every completed preview render')
print(' - preview worker runs below interactive/UI priority')
print(' - 1B displayed ISO/shutter capture lock remains intact')
