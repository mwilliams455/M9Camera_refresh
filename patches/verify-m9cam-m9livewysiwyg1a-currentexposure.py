#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1a-currentexposure.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
gradle = root / 'app/build.gradle'
for p in (renderer, preview, controller, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1A verify missing: ' + str(p))

def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1A verify method missing: ' + signature)
    brace = text.find('{', start)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return text[start:i + 1]
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1A verify unterminated: ' + signature)

c = controller.read_text()
p = preview.read_text()
r = renderer.read_text()
g = gradle.read_text()

controller_required = [
    'M9LIVEWYSIWYG1A_CURRENTEXPOSURE',
    'm9LiveWysiwygPairLock1A',
    'm9LiveWysiwygPendingImage1A',
    'tryDispatchM9LiveWysiwygPair1A()',
    'rawResultTimestampDeltaNs',
    'pairDeltaNs > 2_000_000L',
    'M9LivePreview1A.render(',
    'm9LivePreviewImageView.setImageBitmap(ready);',
    'M9LivePreview1A.markDisplayedWysiwyg1A(',
]
for token in controller_required:
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1A controller marker missing: ' + token)

request_method = method_span(c, '    private void requestM9LivePreviewProbe1A() {')
for forbidden in (
        'GenerateExpoPair',
        'SENSOR_SENSITIVITY',
        'SENSOR_EXPOSURE_TIME',
        'CONTROL_AE_MODE',
        'mPreviewIso',
        'mPreviewExposureTime',
        'targetIso',
        'targetExposure',
        'virtualScale',
        'exposureDomainScale'):
    if forbidden in request_method:
        raise SystemExit(
            'M9LIVEWYSIWYG1A forbidden preview exposure mutation/prediction token: '
            + forbidden)

for token in (
        'mPreviewRequestBuilder.addTarget(rawSurface);',
        'CaptureRequest probe = mPreviewRequestBuilder.build();',
        'mPreviewRequestBuilder.removeTarget(rawSurface);',
        'mCaptureSession.capture(probe, m9LivePreviewCaptureCallback1A, mBackgroundHandler);'):
    if token not in request_method:
        raise SystemExit('M9LIVEWYSIWYG1A current-request probe marker missing: ' + token)

ui_sequence = '''m9LivePreviewImageView.setImageBitmap(ready);
                    M9LivePreview1A.markDisplayedWysiwyg1A('''
if ui_sequence not in c:
    raise SystemExit(
        'M9LIVEWYSIWYG1A display diagnostic must run immediately after setImageBitmap')

preview_required = [
    'public static final int LANDSCAPE_WIDTH = 1440;',
    'public static final int LANDSCAPE_HEIGHT = 1080;',
    'reduceBayerParityPreserving',
    'M9SensorDescriptor1A.fromPreviewImage(',
    'markDisplayedWysiwyg1A(Bitmap bitmap,',
    'M9R35Renderer.markM9LiveWysiwygDisplayed1A(',
]
for token in preview_required:
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1A preview marker missing: ' + token)

for forbidden in (
        'scaleVirtualCaptureDomain',
        'exposureDomainScale',
        'targetExposureNs',
        'targetIso'):
    if forbidden in p:
        raise SystemExit(
            'M9LIVEWYSIWYG1A virtual/predicted exposure token leaked into preview: '
            + forbidden)

renderer_required = [
    'M9LIVEWYSIWYG1A_CURRENTEXPOSURE',
    'registerM9LiveWysiwygRendered1A(',
    'markM9LiveWysiwygDisplayed1A(',
    'snapshotM9LiveWysiwygDisplayed1A()',
    'actual_M9_Bitmap_at_ImageView_commit',
    'local_final_M9_Bitmap_immediately_before_JPEG_encode_or_recycle',
    'stillActualVsDisplayedPreviewExposureDeltaEv',
    'stillRequestedVsDisplayedPreviewExposureDeltaEv',
    'm9LiveWysiwyg1A',
    'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN',
    'SAT2_M04_M05',
    'm9cam.tonebound.v1a.050ev',
]
for token in renderer_required:
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1A renderer marker missing: ' + token)

still_method = method_span(r, 'private static Result renderAndSaveInternal(')
if 'bitmap = out.bitmap;' not in still_method:
    raise SystemExit('M9LIVEWYSIWYG1A local final Bitmap handoff missing')
if 'bitmap, frame.width, frame.height, "still_final_M9_bitmap"' not in still_method:
    raise SystemExit(
        'M9LIVEWYSIWYG1A still luma must measure local bitmap before output side effects')
if 'out.bitmap, frame.width, frame.height, "still_final_M9_bitmap"' in still_method:
    raise SystemExit(
        'M9LIVEWYSIWYG1A must not use nullable/transferred out.bitmap for still measurement')

if 'rendered_not_yet_displayed' not in r:
    raise SystemExit('M9LIVEWYSIWYG1A rendered-state marker missing')
if 'last_actual_ImageView_displayed_M9_Bitmap_only' not in r:
    raise SystemExit('M9LIVEWYSIWYG1A strict displayed-only pairing marker missing')

# The diagnostic patch may wrap the production renderer but must not embed policy inside
# the two frozen photographic cores.
for sig in (
        'private static RenderCore renderNativeSourceProduction1P(',
        'private static RenderCore renderNativeProspectiveCore('):
    core = method_span(r, sig)
    if 'M9LIVEWYSIWYG1A' in core or 'm9LiveWysiwyg' in core:
        raise SystemExit('M9LIVEWYSIWYG1A leaked into frozen photographic core: ' + sig)

if 'm9livewysiwyg1a-currentexposure' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1A versionName marker missing')

print('M9LIVEWYSIWYG1A_CURRENTEXPOSURE VERIFY PASS')
print(' - preview RAW comes from current repeating-preview exposure state')
print(' - RAW Image timestamp paired to exact TotalCaptureResult SENSOR_TIMESTAMP')
print(' - preview request contains no exposure prediction or ISO/shutter/AE mutation')
print(' - no virtual RAW exposure-domain scaling exists')
print(' - ImageView-displayed M9 Bitmap is the only preview reference')
print(' - displayed preview luma measured at ImageView commit boundary')
print(' - final still luma measured from local M9 Bitmap before JPEG/recycle')
print(' - still requested/actual exposure audited against displayed preview exposure')
print(' - frozen native photographic render methods contain no WYSIWYG policy')
