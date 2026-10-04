#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1c-fullsource.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
selector = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle = root / 'app/build.gradle'
for p in (renderer, preview, controller, selector, gradle):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1C missing assembled file: ' + str(p))


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEWYSIWYG1C {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)


def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1C method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('M9LIVEWYSIWYG1C opening brace missing: ' + signature)
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
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1C unterminated method: ' + signature)


# Preconditions: 1A current exposure + 1B displayed capture lock are both required.
c = controller.read_text()
s = selector.read_text()
for marker in (
        'M9LIVEWYSIWYG1A_CURRENTEXPOSURE',
        'M9LIVEWYSIWYG1B_DISPLAYEDCAPTURELOCK',
        'm9LiveWysiwygDisplayedIso1B',
        'm9LiveWysiwygDisplayedExposureNs1B'):
    if marker not in c:
        raise SystemExit('M9LIVEWYSIWYG1C requires controller marker: ' + marker)
if 'setExactExposureM9Wysiwyg1B(' not in s:
    raise SystemExit('M9LIVEWYSIWYG1C requires exact 1B exposure setter')

# ---------------------------------------------------------------------------
# 1) Preview facade: full RAW source in, no Bayer/source reduction before render.
# ---------------------------------------------------------------------------
p = preview.read_text()
for marker in (
        'M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN',
        'reduceBayerParityPreserving',
        'M9SensorDescriptor1A.fromPreviewImage(',
        'M9R35Renderer.renderLivePreview1A('):
    if marker not in p:
        raise SystemExit('M9LIVEWYSIWYG1C preview baseline marker missing: ' + marker)
if 'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY' in p:
    raise SystemExit('M9LIVEWYSIWYG1C already applied to preview facade')

rs, re_ = method_span(p, '    public static Bitmap render(Image raw,')
new_render = r'''    /**
     * M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY
     *
     * Feed every RAW_SENSOR sample to the exact production renderer. There is no Bayer/source
     * reduction before TC20, tone, colour, HSM/SAT2, shading/falloff or edge-placement logic.
     * Display scaling is performed only after the production renderer returns its final bitmap.
     */
    public static Bitmap render(Image raw,
                                CameraCharacteristics characteristics,
                                CaptureResult captureResult,
                                CaptureRequest captureRequest,
                                int cameraRotation) throws Exception {
        if (raw == null || raw.getFormat() != ImageFormat.RAW_SENSOR) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1C requires RAW_SENSOR image");
        }
        final int srcW = raw.getWidth();
        final int srcH = raw.getHeight();
        long started = System.nanoTime();
        final JSONObject sourceDescriptor1A = M9SensorDescriptor1A.fromPreviewImage(
                raw, characteristics, captureResult, captureRequest, srcW, srcH).toJson();
        ByteBuffer packed = packFullRawPreservingSamples1C(raw);
        long packedAt = System.nanoTime();
        Bitmap out = M9R35Renderer.renderLivePreview1A(
                packed, srcW, srcH, characteristics, captureResult, captureRequest,
                sourceDescriptor1A, cameraRotation);
        long finished = System.nanoTime();
        Log.d(TAG, "M9LIVEWYSIWYG1C FULLSOURCE raw=" + srcW + "x" + srcH
                + " renderInput=" + srcW + "x" + srcH
                + " preRenderSourceReduction=false"
                + " packMs=" + ((packedAt - started) / 1_000_000.0)
                + " renderAndPostScaleMs=" + ((finished - packedAt) / 1_000_000.0));
        return out;
    }'''
p = p[:rs] + new_render + p[re_:]

# Remove the entire old reduce helper and its helper methods, then install a 1:1 full-source packer.
red_start, red_end = method_span(p, '    private static ByteBuffer reduceBayerParityPreserving(')
# sameParityNear is the last old helper, so remove through its closing brace.
_, parity_end = method_span(p, '    private static int sameParityNear(')
full_packer = r'''    /** 1:1 RAW plane copy. No averaging, resampling, virtual exposure or CFA remapping. */
    private static ByteBuffer packFullRawPreservingSamples1C(Image raw) {
        Image.Plane[] planes = raw.getPlanes();
        if (planes == null || planes.length < 1) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1C RAW has no plane");
        }
        Image.Plane plane = planes[0];
        ByteBuffer src = plane.getBuffer().duplicate().order(ByteOrder.LITTLE_ENDIAN);
        final int width = raw.getWidth();
        final int height = raw.getHeight();
        final int rowStride = plane.getRowStride();
        final int pixelStride = plane.getPixelStride();
        if (width <= 0 || height <= 0 || rowStride <= 0 || pixelStride < 2) {
            throw new IllegalArgumentException("M9LIVEWYSIWYG1C unsupported RAW geometry row="
                    + rowStride + " pixel=" + pixelStride + " size=" + width + "x" + height);
        }
        ByteBuffer out = ByteBuffer.allocateDirect(Math.multiplyExact(Math.multiplyExact(width, height), 2))
                .order(ByteOrder.LITTLE_ENDIAN);

        // Fast path for normal RAW16-like Camera2 packing, while retaining row-padding removal.
        if (pixelStride == 2) {
            final int rowBytes = Math.multiplyExact(width, 2);
            for (int y = 0; y < height; y++) {
                int base = Math.multiplyExact(y, rowStride);
                if (base < 0 || base + rowBytes > src.capacity()) {
                    throw new IllegalArgumentException("M9LIVEWYSIWYG1C RAW row out of bounds y=" + y);
                }
                ByteBuffer row = src.duplicate();
                row.position(base);
                row.limit(base + rowBytes);
                out.put(row);
            }
        } else {
            for (int y = 0; y < height; y++) {
                int rowBase = Math.multiplyExact(y, rowStride);
                for (int x = 0; x < width; x++) {
                    int off = rowBase + Math.multiplyExact(x, pixelStride);
                    if (off < 0 || off + 1 >= src.capacity()) {
                        throw new IllegalArgumentException(
                                "M9LIVEWYSIWYG1C RAW sample out of bounds x=" + x + " y=" + y);
                    }
                    out.putShort(src.getShort(off));
                }
            }
        }
        out.flip();
        return out;
    }
'''
p = p[:red_start] + full_packer + p[parity_end:]
# Update legacy mode string only as a historical constant; active implementation is now explicitly 1C.
p = p.replace(
    'public static final String MODE_1B = "M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN";',
    'public static final String MODE_1B = "M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN";\n'
    '    public static final String MODE_1C = "M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY";',
    1)
preview.write_text(p)

# ---------------------------------------------------------------------------
# 2) Renderer: live route gets current scene evidence and reaches the SAME final bitmap
#    boundary as still, including EDGEPLACEMENTBESTFIT2A. Only then may display scaling occur.
# ---------------------------------------------------------------------------
r = renderer.read_text()
for marker in (
        'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN',
        'M9EdgePlacementBestFit2AController.evaluate(',
        'out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);',
        'M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR'):
    if marker not in r:
        raise SystemExit('M9LIVEWYSIWYG1C renderer baseline marker missing: ' + marker)
if 'M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY' in r:
    raise SystemExit('M9LIVEWYSIWYG1C already applied to renderer')

field_anchor = '    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR = new ThreadLocal<>();\n'
fields = field_anchor + '''    // M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY: read-only current scene evidence for the
    // same final JPEG exception/tone selector. The still route continues consuming its staged
    // capture snapshot exactly as before.
    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1C_CAPTURE_EVIDENCE = new ThreadLocal<>();
'''
r = replace_once(r, field_anchor, fields, 'live evidence ThreadLocal')

# Rewrite preview wrapper: build current evidence, run complete production renderer, then downscale
# only the finished M9 bitmap for display memory/bandwidth.
ws, we = method_span(r, '    public static Bitmap renderLivePreview1A(')
wrapper = r[ws:we]
set_anchor = '''        M9_LIVE_PREVIEW_1A_ACTIVE.set(Boolean.TRUE);
        M9_LIVE_PREVIEW_1A_BITMAP.remove();
        M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.set(sourceDescriptor1A);
'''
set_new = '''        M9_LIVE_PREVIEW_1A_ACTIVE.set(Boolean.TRUE);
        M9_LIVE_PREVIEW_1A_BITMAP.remove();
        M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.set(sourceDescriptor1A);
        M9_LIVE_PREVIEW_1C_CAPTURE_EVIDENCE.set(
                buildM9LiveCaptureEvidence1C(captureResult, captureRequest, cameraRotation));
'''
wrapper = replace_once(wrapper, set_anchor, set_new, 'preview evidence set')
old_return = '''            registerM9LiveWysiwygRendered1A(
                    out, r.diagnostics, captureResult, captureRequest, width, height);
            return out;
'''
new_return = '''            // The bitmap above is the exact final production M9 bitmap. Any size reduction from
            // this point forward is display transport only and cannot feed tone/TC20/colour decisions.
            final int maxLandscapeW1C = 1440;
            final int maxLandscapeH1C = 1080;
            int targetW1C = out.getWidth();
            int targetH1C = out.getHeight();
            double scale1C = Math.min(1.0, Math.min(
                    maxLandscapeW1C / (double)Math.max(1, targetW1C),
                    maxLandscapeH1C / (double)Math.max(1, targetH1C)));
            // Swap display bounds for portrait bitmaps.
            if (targetH1C > targetW1C) {
                scale1C = Math.min(1.0, Math.min(
                        maxLandscapeH1C / (double)Math.max(1, targetW1C),
                        maxLandscapeW1C / (double)Math.max(1, targetH1C)));
            }
            Bitmap display1C = out;
            if (scale1C < 0.999999) {
                int dw1C = Math.max(1, (int)Math.round(targetW1C * scale1C));
                int dh1C = Math.max(1, (int)Math.round(targetH1C * scale1C));
                display1C = Bitmap.createScaledBitmap(out, dw1C, dh1C, true);
                if (display1C == null) {
                    throw new IllegalStateException("M9LIVEWYSIWYG1C post-render display downscale failed");
                }
                if (display1C != out && !out.isRecycled()) out.recycle();
            }
            try {
                r.diagnostics.put("m9LivePreviewDisplayScalingBoundary",
                        "post_render_final_M9_bitmap_only");
                r.diagnostics.put("m9LivePreviewDisplayWidth", display1C.getWidth());
                r.diagnostics.put("m9LivePreviewDisplayHeight", display1C.getHeight());
                r.diagnostics.put("m9LivePreviewFullRenderedWidth", targetW1C);
                r.diagnostics.put("m9LivePreviewFullRenderedHeight", targetH1C);
                r.diagnostics.put("m9LivePreviewPostRenderDownscaleApplied", display1C != out);
            } catch (Throwable ignored) {}
            registerM9LiveWysiwygRendered1A(
                    display1C, r.diagnostics, captureResult, captureRequest, width, height);
            return display1C;
'''
wrapper = replace_once(wrapper, old_return, new_return, 'post-render display scaling')
cleanup_anchor = '''            M9_LIVE_PREVIEW_1A_BITMAP.remove();
            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
cleanup_new = '''            M9_LIVE_PREVIEW_1A_BITMAP.remove();
            M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.remove();
            M9_LIVE_PREVIEW_1C_CAPTURE_EVIDENCE.remove();
            M9_LIVE_PREVIEW_1A_ACTIVE.remove();
'''
wrapper = replace_once(wrapper, cleanup_anchor, cleanup_new, 'preview evidence cleanup')
r = r[:ws] + wrapper + r[we:]

# Skip staged DNG evidence consumption on the preview-only synthetic path; feed the current live
# evidence into the same selector instead. Still behavior is byte-for-byte equivalent here.
old_snapshot = '''            final byte[] edgePlacementCaptureBytes = M9DeferredMetadataStore.consumeRenderSnapshotForDng(dngPath);
'''
new_snapshot = '''            final byte[] edgePlacementCaptureBytes = m9LiveWysiwyg1ALiveRoute
                    ? null : M9DeferredMetadataStore.consumeRenderSnapshotForDng(dngPath);
            final JSONObject edgePlacementLiveEvidence1C = m9LiveWysiwyg1ALiveRoute
                    ? M9_LIVE_PREVIEW_1C_CAPTURE_EVIDENCE.get() : null;
'''
r = replace_once(r, old_snapshot, new_snapshot, 'edge capture evidence source')

old_evidence = '''                JSONObject captureEvidence = edgePlacementCaptureBytes != null
                        ? new JSONObject(new String(edgePlacementCaptureBytes, StandardCharsets.UTF_8)) : null;
                edgeDecision = M9EdgePlacementBestFit2AController.evaluate(captureEvidence, out.diagnostics, frozenDirectLuma);
'''
new_evidence = '''                JSONObject captureEvidence = m9LiveWysiwyg1ALiveRoute
                        ? edgePlacementLiveEvidence1C
                        : (edgePlacementCaptureBytes != null
                            ? new JSONObject(new String(edgePlacementCaptureBytes, StandardCharsets.UTF_8))
                            : null);
                edgeDecision = M9EdgePlacementBestFit2AController.evaluate(
                        captureEvidence, out.diagnostics, frozenDirectLuma);
'''
r = replace_once(r, old_evidence, new_evidence, 'edge selector evidence')
old_available = '            edgeDecision.put("captureSnapshotAvailable", edgePlacementCaptureBytes != null);\n'
new_available = '''            edgeDecision.put("captureSnapshotAvailable",
                    m9LiveWysiwyg1ALiveRoute
                            ? edgePlacementLiveEvidence1C != null
                            : edgePlacementCaptureBytes != null);
            edgeDecision.put("captureSnapshotSource",
                    m9LiveWysiwyg1ALiveRoute
                            ? "live_current_scene_evidence"
                            : "still_staged_capture_sidecar");
'''
r = replace_once(r, old_available, new_available, 'edge evidence diagnostics')

# Move the 1A still WYSIWYG measurement from the pre-edge bitmap to the true final bitmap.
# Also move preview interception to that exact same boundary.
pre_start = r.find('            if (!m9LiveWysiwyg1ALiveRoute && primaryRoute) {', r.find('            bitmap = out.bitmap;'))
if pre_start < 0:
    raise SystemExit('M9LIVEWYSIWYG1C pre-edge still diagnostic block missing')
preview_early = r.find('            if (Boolean.TRUE.equals(M9_LIVE_PREVIEW_1A_ACTIVE.get())) {', pre_start)
if preview_early < 0:
    raise SystemExit('M9LIVEWYSIWYG1C pre-edge preview return missing')
# Find end of preview early block by using the following RENDERMETER comment as stable boundary.
rendermeter = r.find('            // RENDERMETER1B read-only sparse sampling', preview_early)
if rendermeter < 0:
    raise SystemExit('M9LIVEWYSIWYG1C RENDERMETER boundary missing')
# Extract the still diagnostic block only (everything before preview early block) for re-use.
still_block = r[pre_start:preview_early]
r = r[:pre_start] + r[rendermeter:]

# After removing blocks, find final edge-placement handoff and insert true-final still diag + preview return.
final_anchor = '            out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);\n'
if r.count(final_anchor) != 1:
    raise SystemExit('M9LIVEWYSIWYG1C final edge anchor count=' + str(r.count(final_anchor)))
preview_final = r'''            // M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY
            // All photographic decisions are complete here. This is the same bitmap that the
            // still path will hand to quality-95 JPEG encoding below.
            if (m9LiveWysiwyg1ALiveRoute) {
                M9_LIVE_PREVIEW_1A_BITMAP.set(bitmap);
                bitmap = null;
                JSONObject previewDiag = out.diagnostics;
                try {
                    previewDiag.put("m9LivePreview1A", true);
                    previewDiag.put("m9LivePreviewMode",
                            "FULL_PRODUCTION_RENDER_FULL_SOURCE_FINAL_BITMAP");
                    previewDiag.put("m9LivePreviewNoFileSideEffects", true);
                    previewDiag.put("preRenderSourceReduction", false);
                    previewDiag.put("renderInputWidth", frame.width);
                    previewDiag.put("renderInputHeight", frame.height);
                    previewDiag.put("fullSourceRawWidth", frame.width);
                    previewDiag.put("fullSourceRawHeight", frame.height);
                    previewDiag.put("finalPhotographicBoundary",
                            "after_edgePlacementBestFit2A_before_JPEG_encode");
                    previewDiag.put("edgePlacementIncluded", true);
                    previewDiag.put("postRenderDisplayDownscaleOnly", true);
                    previewDiag.put("sensorDescriptor1A", M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR.get());
                    previewDiag.put("targetFalloff1A", M9TargetFalloff1A.describe());
                    previewDiag.put("sourceGeometryAuthority",
                            "full_resolution_RAW_is_renderer_input_no_pre_render_reduction");
                    previewDiag.put("liveCaptureEvidence1C", edgePlacementLiveEvidence1C);
                } catch (Throwable ignored) {}
                return new Result(true, null, null, null, previewDiag, null);
            }
'''
r = replace_once(r, final_anchor, final_anchor + still_block + preview_final, 'final bitmap handoff')

# Install live evidence builder before existing WYSIWYG helper section.
helper_anchor = '    private static final class M9LiveWysiwygSnapshot1A {'
hi = r.find(helper_anchor)
if hi < 0:
    raise SystemExit('M9LIVEWYSIWYG1C WYSIWYG helper anchor missing')
evidence_helper = r'''    /**
     * Snapshot the same CURRENT live scene/exposure evidence families consumed by the still
     * EDGEPLACEMENTBESTFIT2A selector. This is read-only: it changes neither capture exposure
     * nor any photographic setting. Camera2 request/result values are from this exact RAW pair.
     */
    private static JSONObject buildM9LiveCaptureEvidence1C(
            CaptureResult result, CaptureRequest request, int cameraRotation) {
        JSONObject root = new JSONObject();
        try {
            root.put("schema", "m9cam.livewysiwyg.v1c.current_scene_evidence");
            root.put("revision", "M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY");
            JSONObject capture = new JSONObject();
            Integer resultIso = result != null ? result.get(CaptureResult.SENSOR_SENSITIVITY) : null;
            Long resultExposure = result != null ? result.get(CaptureResult.SENSOR_EXPOSURE_TIME) : null;
            if (resultIso != null) capture.put("iso", resultIso);
            if (resultExposure != null) capture.put("exposureTimeNs", resultExposure);
            root.put("captureResult", capture);

            JSONObject requested = new JSONObject();
            Integer requestIso = request != null ? request.get(CaptureRequest.SENSOR_SENSITIVITY) : null;
            Long requestExposure = request != null ? request.get(CaptureRequest.SENSOR_EXPOSURE_TIME) : null;
            if (requestIso != null) requested.put("iso", requestIso);
            if (requestExposure != null) requested.put("exposureTimeNs", requestExposure);
            root.put("captureRequest", requested);

            root.put("subjectMotion",
                    com.particlesdevs.photoncamera.m9.M9SubjectMotionAnalyzer.snapshotJson(
                            cameraRotation));
            root.put("m9M10rMfmTest",
                    com.particlesdevs.photoncamera.m9.M9M10rMfmTest1A.snapshotJson());
            root.put("m9SceneExposureDiagnostic",
                    com.particlesdevs.photoncamera.m9.M9SceneExposureDiagnostic.snapshotJson());
            root.put("m9ExposureAudit",
                    com.particlesdevs.photoncamera.m9.M9ExposureAudit.snapshotJson(root));
            root.put("evidenceRole",
                    "current_live_inputs_for_same_final_still_edge_placement_selector");
        } catch (Throwable t) {
            try { root.put("liveEvidenceError", String.valueOf(t)); } catch (Throwable ignored) {}
        }
        return root;
    }

'''
r = r[:hi] + evidence_helper + r[hi:]
renderer.write_text(r)

# ---------------------------------------------------------------------------
# 3) Build identity. Exposure-lock implementation is deliberately not modified.
# ---------------------------------------------------------------------------
g = gradle.read_text()
m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
if not m:
    raise SystemExit('M9LIVEWYSIWYG1C versionName missing')
if 'm9livewysiwyg1c' not in m.group(1).lower():
    old = m.group(0)
    quote = '"' if '"' in old else "'"
    g = g.replace(old,
                  'versionName ' + quote + m.group(1)
                  + '-m9livewysiwyg1c-fullsource-final' + quote,
                  1)
    gradle.write_text(g)

print('M9LIVEWYSIWYG1C_FULLSOURCE_FINALBOUNDARY applied')
print(' - every live RAW sample is preserved into the production renderer')
print(' - no pre-render Bayer/source downsampling remains')
print(' - current live scene/exposure evidence feeds the same edge-placement selector')
print(' - preview bitmap handoff moved after edge-placement/final photographic decisions')
print(' - still WYSIWYG measurement moved to the actual final bitmap boundary')
print(' - optional 1440x1080-class scaling occurs only after full M9 render completion')
print(' - LIVEWYSIWYG1B exact displayed ISO/shutter capture lock retained untouched')
