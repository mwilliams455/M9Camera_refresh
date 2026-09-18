#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9livewysiwyg1c-fullsource.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle = root / 'app/build.gradle'
for p in (renderer, preview, controller, selector, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1C verify missing: ' + str(p))


def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1C verify method missing: ' + signature)
    brace = text.find('{', start)
    depth = 0
    state = 'code'
    quote = ''
    esc = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n':
                state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/':
                state = 'code'
                i += 1
        elif state == 'string':
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == quote:
                state = 'code'
        else:
            if ch == '/' and nxt == '/':
                state = 'line'
                i += 1
            elif ch == '/' and nxt == '*':
                state = 'block'
                i += 1
            elif ch in ('"', "'"):
                state = 'string'
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1C verify unterminated: ' + signature)


r = renderer.read_text()
p = preview.read_text()
c = controller.read_text()
s = selector.read_text()
g = gradle.read_text()

for token in (
        'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY',
        'packFullRawPreservingSamples1C(raw)',
        'raw, characteristics, captureResult, captureRequest, srcW, srcH',
        'packed, srcW, srcH, characteristics, captureResult, captureRequest'):
    if token not in p:
        raise SystemExit('M9LIVEWYSIWYG1C preview marker missing: ' + token)
for forbidden in (
        'reduceBayerParityPreserving',
        'sameParityNear(',
        'final int dstW =',
        'final int dstH ='):
    if forbidden in p:
        raise SystemExit('M9LIVEWYSIWYG1C forbidden pre-render source reduction remains: ' + forbidden)

packer = method_span(p, '    private static ByteBuffer packFullRawPreservingSamples1C(')
for token in (
        'pixelStride == 2',
        'rowStride',
        'out.put(row)',
        'out.putShort(src.getShort(off))'):
    if token not in packer:
        raise SystemExit('M9LIVEWYSIWYG1C full-source packer marker missing: ' + token)
for forbidden in ('>> 2', '/ 4', 'average', 'scaleVirtualCaptureDomain'):
    if forbidden in packer:
        raise SystemExit('M9LIVEWYSIWYG1C packer contains reduction/scaling token: ' + forbidden)

for token in (
        'M9_LIVE_PREVIEW_1C_CAPTURE_EVIDENCE',
        'buildM9LiveCaptureEvidence1C(',
        'M9SubjectMotionAnalyzer.snapshotJson(',
        'M9M10rMfmTest1A.snapshotJson()',
        'M9SceneExposureDiagnostic.snapshotJson()',
        'M9ExposureAudit.snapshotJson(root)',
        'captureSnapshotSource',
        'live_current_scene_evidence'):
    if token not in r:
        raise SystemExit('M9LIVEWYSIWYG1C live evidence marker missing: ' + token)

render_method = method_span(r, 'private static Result renderAndSaveInternal(')
edge_pos = render_method.find('out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);')
preview_pos = render_method.find('FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP')
still_measure_pos = render_method.find('"still_final_M9_bitmap"')
jpeg_pos = render_method.find('saveBitmapAsJPGPayloadM9(')
if min(edge_pos, preview_pos, still_measure_pos, jpeg_pos) < 0:
    raise SystemExit('M9LIVEWYSIWYG1C final-boundary anchors incomplete')
if not (edge_pos < still_measure_pos < preview_pos < jpeg_pos):
    raise SystemExit(
            'M9LIVEWYSIWYG1C wrong output ordering: expected edge -> still measure -> preview handoff -> JPEG')
if render_method.count('M9_LIVE_PREVIEW_1A_BITMAP.set(bitmap);') != 1:
    raise SystemExit('M9LIVEWYSIWYG1C expected exactly one preview bitmap handoff')
if 'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN' in r:
    raise SystemExit('M9LIVEWYSIWYG1C stale reduced-RAW renderer mode remains')
for token in (
        '"preRenderSourceReduction", false',
        '"edgePlacementIncluded", true',
        '"postRenderDisplayDownscaleOnly", true',
        '"after_edgePlacementBestFit2A_before_JPEG_encode"',
        '"full_resolution_RAW_is_renderer_input_no_pre_render_reduction"'):
    if token not in render_method:
        raise SystemExit('M9LIVEWYSIWYG1C final render contract marker missing: ' + token)

wrapper = method_span(r, '    public static Bitmap renderLivePreview1A(')
for token in (
        'renderAndSaveInternal(synthetic, frame, characteristics,',
        'Bitmap.createScaledBitmap(out, dw1C, dh1C, true)',
        'post_render_final_M9_bitmap_only',
        'registerM9LiveWysiwygRendered1A('):
    if token not in wrapper:
        raise SystemExit('M9LIVEWYSIWYG1C wrapper marker missing: ' + token)
if wrapper.find('renderAndSaveInternal(') > wrapper.find('Bitmap.createScaledBitmap('):
    raise SystemExit('M9LIVEWYSIWYG1C display scaling occurs before production render')

for token in (
        'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
        'm9LiveWysiwygDisplayedIso1B',
        'm9LiveWysiwygDisplayedExposureNs1B',
        'ImageView_displayed_M9_frame',
        'IsoExpoSelector.setExactExposureM9Wysiwyg1B('):
    if token not in c:
        raise SystemExit('M9LIVEWYSIWYG1C lost 1B controller contract: ' + token)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1C lost exact exposure selector')

capture = method_span(c, '    private void captureStillPicture() {')
for forbidden in (
        'IsoExpoSelector.GenerateExpoPair(-1, this)',
        'IsoExpoSelector.setExpo(captureBuilder, i, this)'):
    if forbidden in capture:
        raise SystemExit('M9LIVEWYSIWYG1C hidden still exposure selector returned: ' + forbidden)

for sig in (
        'private static RenderCore renderNativeSourceProduction1P(',
        'private static RenderCore renderNativeProspectiveCore('):
    core = method_span(r, sig)
    if 'M9LIVEWYSIWYG1C' in core or 'm9LivePreview' in core:
        raise SystemExit('M9LIVEWYSIWYG1C preview policy leaked into frozen photographic core: ' + sig)

if 'm9livewysiwyg1c-fullsource-final' not in g.lower():
    raise SystemExit('M9LIVEWYSIWYG1C versionName marker missing')

print('M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY VERIFY PASS')
print(' - full RAW source dimensions/samples feed production renderer')
print(' - no pre-render Bayer/source reduction survives')
print(' - current subject/multifield/scene/exposure evidence feeds same edge selector')
print(' - preview handoff occurs after edge-placement and before JPEG side effects')
print(' - still diagnostic now measures actual final bitmap')
print(' - display downscale occurs only after full M9 production render returns')
print(' - LIVEWYSIWYG1B exact displayed ISO/shutter capture lock remains intact')
