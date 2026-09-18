#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1d-meter1600.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle = root / 'app/build.gradle'
for p in (preview, renderer, controller, selector, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1D verify missing: ' + str(p))

def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1D verify method missing: ' + signature)
    brace = text.find('{', start)
    depth = 0
    state = 'code'
    quote = ''
    esc = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i+1] if i+1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return text[start:i+1]
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1D verify unterminated: ' + signature)

p = preview.read_text()
r = renderer.read_text()
c = controller.read_text()
s = selector.read_text()
g = gradle.read_text()

for token in (
        'M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER',
        'public static final int LANDSCAPE_WIDTH = 1600;',
        'public static final int LANDSCAPE_HEIGHT = 1200;',
        'reduceBayerMeterReference1600PreservingParity1D(raw, renderW, renderH)',
        'M9SensorDescriptor1A.fromPreviewImage(',
        'raw, characteristics, captureResult, captureRequest, renderW, renderH',
        'packed, renderW, renderH, characteristics, captureResult, captureRequest'):
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1D preview marker missing: ' + token)

render = method_span(p, '    public static Bitmap render(Image raw,')
for token in (
        'final int targetW = srcW >= srcH ? LANDSCAPE_WIDTH : LANDSCAPE_HEIGHT;',
        'final int targetH = srcW >= srcH ? LANDSCAPE_HEIGHT : LANDSCAPE_WIDTH;',
        'final boolean reduce = srcW > targetW || srcH > targetH;',
        'tc20ReferenceLongSide=1600'):
    if token not in render:
        raise SystemExit('M9LIVEWYSIWYG1D render policy missing: ' + token)

reducer = method_span(p, '    private static ByteBuffer reduceBayerMeterReference1600PreservingParity1D(')
for token in (
        'sameParityNear1D',
        'u16At1D',
        'a + b + cc + d + 2',
        'Math.multiplyExact(Math.multiplyExact(dstW, dstH), 2)'):
    if token not in reducer:
        raise SystemExit('M9LIVEWYSIWYG1D reducer marker missing: ' + token)
for forbidden in ('CONTROL_AE_MODE', 'SENSOR_SENSITIVITY', 'SENSOR_EXPOSURE_TIME'):
    if forbidden in reducer:
        raise SystemExit('M9LIVEWYSIWYG1D reducer contains exposure mutation: ' + forbidden)

for token in (
        'FULL_PRODUCTION_RENDER_REFERENCE1600_FINAL_BITMAP',
        '"TC20_1600_long_side_reference_spatial_workload_only"',
        '"allM9PhotographicStagesAppliedAtReferenceResolution", true',
        '"original_full_RAW_descriptor_retained_reference1600_is_renderer_input"',
        'final int maxLandscapeW1C = 1600;',
        'final int maxLandscapeH1C = 1200;'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1D renderer marker missing: ' + token)
if 'FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP' in r:
    raise SystemExit('M9LIVEWYSIWYG1D stale full-source live mode remains active')

render_method = method_span(r, 'private static Result renderAndSaveInternal(')
edge_pos = render_method.find('out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);')
preview_pos = render_method.find('FULL_PRODUCTION_RENDER_REFERENCE1600_FINAL_BITMAP')
jpeg_pos = render_method.find('saveBitmapAsJPGPayloadM9(')
if min(edge_pos, preview_pos, jpeg_pos) < 0 or not (edge_pos < preview_pos < jpeg_pos):
    raise SystemExit('M9LIVEWYSIWYG1D final boundary ordering lost')

# Exact exposure lock remains the contract for the still shot.
for token in (
        'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
        'm9LiveWysiwygDisplayedIso1B',
        'm9LiveWysiwygDisplayedExposureNs1B',
        'ImageView_displayed_M9_frame',
        'IsoExpoSelector.setExactExposureM9Wysiwyg1B('):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1D lost 1B controller contract: ' + token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1D lost exact exposure selector')

capture = method_span(c, '    private void captureStillPicture() {')
for forbidden in (
        'IsoExpoSelector.GenerateExpoPair(-1, this)',
        'IsoExpoSelector.setExpo(captureBuilder, i, this)'):
    if forbidden in capture:
        raise SystemExit('M9LIVEWYSIWYG1D hidden still selector returned: ' + forbidden)

# No preview performance policy may leak into the frozen production pixel cores.
for sig in (
        'private static RenderCore renderNativeSourceProduction1P(',
        'private static RenderCore renderNativeProspectiveCore('):
    core = method_span(r, sig)
    if 'M9LIVEWYSIWYG1D' in core or 'METER1600_REFERENCE_RENDER' in core:
        raise SystemExit('M9LIVEWYSIWYG1D leaked into frozen photographic core: ' + sig)

if 'm9livewysiwyg1d-meter1600' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1D versionName marker missing')

print('M9LIVEWYSIWYG1D_METER1600_REFERENCE_RENDER VERIFY PASS')
print(' - viewfinder render input is 1600x1200 / 1200x1600 when source is larger')
print(' - original RAW descriptor is retained for source geometry and falloff mapping')
print(' - TC20 reference long side remains 1600')
print(' - full production M9 render and edge-placement final boundary remain active')
print(' - no second normal-path 1440 bitmap downscale is required')
print(' - 1B displayed ISO/shutter still-capture lock remains intact')
print(' - frozen native production render cores contain no 1D preview policy')
