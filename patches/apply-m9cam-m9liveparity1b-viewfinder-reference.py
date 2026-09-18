#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9liveparity1b-viewfinder-reference.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
gradle = root / 'app/build.gradle'
for p in (renderer, preview, controller):
    if not p.exists():
        raise SystemExit('M9LIVEPARITY1B missing assembled file: ' + str(p))

def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEPARITY1B method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('M9LIVEPARITY1B opening brace missing: ' + signature)
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
    raise SystemExit('M9LIVEPARITY1B unterminated method: ' + signature)

def replace_method(text, signature, replacement):
    a, b = method_span(text, signature)
    return text[:a] + replacement + text[b:]

s = renderer.read_text()
for marker in (
        'M9LIVEPARITY1A_PREVIEWSTILL_DIAG',
        'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN',
        'M9_LIVE_PARITY_1A_LAST_PREVIEW',
        'M9SENSORPORT1A_ANYRAW_FALLOFFTGT1A',
        'SAT2_M04_M05'):
    if marker not in s:
        raise SystemExit('M9LIVEPARITY1B baseline marker missing: ' + marker)
if 'M9LIVEPARITY1B_VIEWFINDER_REFERENCE' in s:
    raise SystemExit('M9LIVEPARITY1B already applied')

# Add rendered-vs-actually-displayed state. The still snapshot will prefer DISPLAYED.
field_anchor = '    private static long M9_LIVE_PARITY_1A_LAST_PREVIEW_NS = 0L;\n'
if s.count(field_anchor) != 1:
    raise SystemExit('M9LIVEPARITY1B field anchor count=' + str(s.count(field_anchor)))
s = s.replace(field_anchor, field_anchor + '''    // M9LIVEPARITY1B_VIEWFINDER_REFERENCE: last frame actually committed to ImageView.
    private static JSONObject M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW = null;
    private static long M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW_NS = 0L;
    private static long M9_LIVE_PARITY_1B_RENDER_SEQUENCE = 0L;
    private static long M9_LIVE_PARITY_1B_LAST_RENDERED_SEQUENCE = 0L;
    private static long M9_LIVE_PARITY_1B_LAST_DISPLAYED_SEQUENCE = 0L;
''', 1)

# Preview call gets the actual finished Bitmap so its display-domain luma can be measured.
old_call = '''                    captureM9LiveParity1APreview(
                            previewDiag, captureResult, captureRequest, frame.width, frame.height);
'''
new_call = '''                    captureM9LiveParity1APreview(
                            previewDiag, captureResult, captureRequest, frame.width, frame.height,
                            M9_LIVE_PREVIEW_1A_BITMAP.get());
'''
if s.count(old_call) != 1:
    raise SystemExit('M9LIVEPARITY1B preview capture call anchor count=' + str(s.count(old_call)))
s = s.replace(old_call, new_call, 1)

# Pair block semantics: 1B purpose is viewfinder prediction only. The still remains authority.
s = s.replace('"m9cam.liveparity.v1a.previewstill"', '"m9cam.liveparity.v1b.viewfinder_reference"')
s = s.replace('"M9LIVEPARITY1A_PREVIEWSTILL_DIAG"', '"M9LIVEPARITY1B_VIEWFINDER_REFERENCE"')
s = s.replace(
        '"latest_completed_live_render_snapshotted_at_still_render_entry"',
        '"last_ImageView_displayed_M9_preview_snapshotted_at_still_render_entry"')
anchor = '                parity.put("diagnosticOnly", true);\n'
if s.count(anchor) != 1:
    raise SystemExit('M9LIVEPARITY1B parity purpose anchor count=' + str(s.count(anchor)))
s = s.replace(anchor, anchor + '''                parity.put("viewfinderPurpose", "predict_unchanged_final_JPEG");
                parity.put("finalJpegIsPhotographicAuthority", true);
                parity.put("viewfinderMayMutateCaptureExposure", false);
                parity.put("viewfinderMayMutateStillTone", false);
''', 1)

# Pass the final still Bitmap into the same display measurement. This measures only.
old_still = '''                parity.put("still", buildM9LiveParity1ASummary(
                        diag, captureResult, captureRequest,
                        frame.width, frame.height, "still_full_raw"));
'''
new_still = '''                parity.put("still", buildM9LiveParity1ASummary(
                        diag, captureResult, captureRequest,
                        frame.width, frame.height, "still_full_raw", out.bitmap));
'''
if s.count(old_still) != 1:
    raise SystemExit('M9LIVEPARITY1B still summary anchor count=' + str(s.count(old_still)))
s = s.replace(old_still, new_still, 1)

capture_method = r'''    private static void captureM9LiveParity1APreview(JSONObject rendererDiag,
                                                     CaptureResult result,
                                                     CaptureRequest request,
                                                     int width,
                                                     int height,
                                                     Bitmap finishedBitmap) {
        // 1B is deliberately fail-safe: commit a core preview record even if one optional
        // Camera2 key or renderer diagnostic is malformed/non-finite.
        JSONObject summary = buildM9LiveParity1ASummary(
                rendererDiag, result, request, width, height,
                "preview_reduced_raw", finishedBitmap);
        long completedNs = System.nanoTime();
        safePutM9LiveParity1B(summary, "completedMonotonicNs", completedNs);
        safePutM9LiveParity1B(summary, "recordPolicy",
                "core_record_always_committed_optional_fields_fail_individually");
        synchronized (M9_LIVE_PARITY_1A_LOCK) {
            try {
                M9_LIVE_PARITY_1B_RENDER_SEQUENCE++;
                safePutM9LiveParity1B(summary, "previewRenderSequence",
                        M9_LIVE_PARITY_1B_RENDER_SEQUENCE);
                M9_LIVE_PARITY_1A_LAST_PREVIEW = new JSONObject(summary.toString());
                M9_LIVE_PARITY_1A_LAST_PREVIEW_NS = completedNs;
                M9_LIVE_PARITY_1B_LAST_RENDERED_SEQUENCE =
                        M9_LIVE_PARITY_1B_RENDER_SEQUENCE;
            } catch (Throwable t) {
                // Last-resort tiny record: never allow previewAvailable to be lost merely
                // because optional diagnostics could not serialize.
                JSONObject core = new JSONObject();
                safePutM9LiveParity1B(core, "schema",
                        "m9cam.liveparity.v1b.fail_safe_core");
                safePutM9LiveParity1B(core, "role", "preview_reduced_raw");
                safePutM9LiveParity1B(core, "width", width);
                safePutM9LiveParity1B(core, "height", height);
                safePutM9LiveParity1B(core, "completedMonotonicNs", completedNs);
                safePutM9LiveParity1B(core, "serializationFallback", true);
                safePutM9LiveParity1B(core, "serializationError",
                        String.valueOf(t));
                M9_LIVE_PARITY_1A_LAST_PREVIEW = core;
                M9_LIVE_PARITY_1A_LAST_PREVIEW_NS = completedNs;
            }
        }
    }'''

snapshot_method = r'''    private static M9LiveParitySnapshot1A snapshotM9LiveParity1A() {
        synchronized (M9_LIVE_PARITY_1A_LOCK) {
            JSONObject chosen = M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW != null
                    ? M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW
                    : M9_LIVE_PARITY_1A_LAST_PREVIEW;
            long chosenNs = M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW != null
                    ? M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW_NS
                    : M9_LIVE_PARITY_1A_LAST_PREVIEW_NS;
            String source = M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW != null
                    ? "ImageView_displayed"
                    : (M9_LIVE_PARITY_1A_LAST_PREVIEW != null
                            ? "rendered_not_yet_display_confirmed" : "none");
            if (chosen == null) return M9LiveParitySnapshot1A.none();
            try {
                JSONObject copy = new JSONObject(chosen.toString());
                safePutM9LiveParity1B(copy, "pairingSource", source);
                safePutM9LiveParity1B(copy, "displayedSequence",
                        M9_LIVE_PARITY_1B_LAST_DISPLAYED_SEQUENCE);
                safePutM9LiveParity1B(copy, "lastRenderedSequence",
                        M9_LIVE_PARITY_1B_LAST_RENDERED_SEQUENCE);
                return new M9LiveParitySnapshot1A(copy, chosenNs);
            } catch (Throwable t) {
                JSONObject core = new JSONObject();
                safePutM9LiveParity1B(core, "schema",
                        "m9cam.liveparity.v1b.snapshot_fail_safe");
                safePutM9LiveParity1B(core, "pairingSource", source);
                safePutM9LiveParity1B(core, "snapshotError", String.valueOf(t));
                return new M9LiveParitySnapshot1A(core, chosenNs);
            }
        }
    }'''

summary_method = r'''    private static JSONObject buildM9LiveParity1ASummary(JSONObject rendererDiag,
                                                          CaptureResult result,
                                                          CaptureRequest request,
                                                          int width,
                                                          int height,
                                                          String role,
                                                          Bitmap finishedBitmap) {
        JSONObject out = new JSONObject();
        safePutM9LiveParity1B(out, "schema",
                "m9cam.liveparity.v1b.render_summary");
        safePutM9LiveParity1B(out, "revision",
                "M9LIVEPARITY1B_VIEWFINDER_REFERENCE");
        safePutM9LiveParity1B(out, "role", role);
        safePutM9LiveParity1B(out, "width", width);
        safePutM9LiveParity1B(out, "height", height);
        safePutM9LiveParity1B(out, "photographicPixelChange", false);
        safePutM9LiveParity1B(out, "captureExposureMutation", false);
        safePutM9LiveParity1B(out, "stillToneMutation", false);

        // Camera2 keys are independent: one unsupported key must not invalidate the record.
        safeCaptureResultKeyM9LiveParity1B(out, "resultIso", result,
                CaptureResult.SENSOR_SENSITIVITY);
        safeCaptureResultKeyM9LiveParity1B(out, "resultExposureTimeNs", result,
                CaptureResult.SENSOR_EXPOSURE_TIME);
        safeCaptureResultKeyM9LiveParity1B(out, "resultFrameDurationNs", result,
                CaptureResult.SENSOR_FRAME_DURATION);
        safeCaptureResultKeyM9LiveParity1B(out, "resultPostRawSensitivityBoost", result,
                CaptureResult.CONTROL_POST_RAW_SENSITIVITY_BOOST);
        safeCaptureResultKeyM9LiveParity1B(out, "resultShadingMode", result,
                CaptureResult.SHADING_MODE);
        safeCaptureResultKeyM9LiveParity1B(out, "resultLensShadingMapMode", result,
                CaptureResult.STATISTICS_LENS_SHADING_MAP_MODE);
        safeCaptureResultKeyM9LiveParity1B(out, "resultColorCorrectionMode", result,
                CaptureResult.COLOR_CORRECTION_MODE);

        safeCaptureRequestKeyM9LiveParity1B(out, "requestIso", request,
                CaptureRequest.SENSOR_SENSITIVITY);
        safeCaptureRequestKeyM9LiveParity1B(out, "requestExposureTimeNs", request,
                CaptureRequest.SENSOR_EXPOSURE_TIME);
        safeCaptureRequestKeyM9LiveParity1B(out, "requestFrameDurationNs", request,
                CaptureRequest.SENSOR_FRAME_DURATION);
        safeCaptureRequestKeyM9LiveParity1B(out, "requestPostRawSensitivityBoost", request,
                CaptureRequest.CONTROL_POST_RAW_SENSITIVITY_BOOST);
        safeCaptureRequestKeyM9LiveParity1B(out, "requestShadingMode", request,
                CaptureRequest.SHADING_MODE);
        safeCaptureRequestKeyM9LiveParity1B(out, "requestLensShadingMapMode", request,
                CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE);
        safeCaptureRequestKeyM9LiveParity1B(out, "requestColorCorrectionMode", request,
                CaptureRequest.COLOR_CORRECTION_MODE);

        if (rendererDiag != null) {
            String[] keys = new String[] {
                    "gain",
                    "edgePlacementRenderGainEv",
                    "edgePlacementEffectiveGain",
                    "baseMedianGain",
                    "legacyR31Gain",
                    "legacyP98Proxy",
                    "tc20GuardGain",
                    "rawHardClipFraction",
                    "rawUq25",
                    "rawUq50",
                    "rawUq99",
                    "rawUq99_5",
                    "rawUq99_8",
                    "tc20Q",
                    "tc20AdaptiveUq",
                    "tc20TailCurvature",
                    "tc20TailIsolated",
                    "tc20TailValue",
                    "rgb8ClipFraction",
                    "renderNearWhiteFraction",
                    "baselineExposureEv",
                    "satBank",
                    "nativeSaturationBankActuallySelected",
                    "nativeSaturationMatrixPairActuallySelected",
                    "contrastCurve",
                    "gainMapAppliedToRender",
                    "gainMapApplicationCount",
                    "gainMapRepresentationScale",
                    "lumaDecomp1ARenderApplied",
                    "lumaAuthorityAlpha",
                    "shadingLumaNorm1AApplied",
                    "shadingLumaNorm1ATargetOutsideMedianEv",
                    "shadingLumaNorm1ASourceOutsideMedianEv",
                    "shadingLumaNorm1AEffectiveAlpha",
                    "sourceRawOriginX",
                    "sourceRawOriginY",
                    "sourceRawOriginEvidence",
                    "m9LivePreviewMode",
                    "toneForensics1A",
                    "toneBound1A",
                    "shadingLumaDecomp1A",
                    "sensorDescriptor1A",
                    "targetFalloff1A"
            };
            org.json.JSONArray omitted = new org.json.JSONArray();
            for (String key : keys) {
                if (!copyM9LiveParitySafe1B(rendererDiag, out, key)) {
                    if (rendererDiag.has(key)) omitted.put(key);
                }
            }
            safePutM9LiveParity1B(out, "optionalRendererFieldsOmitted", omitted);
        }

        safePutM9LiveParity1B(out, "displayLuma1B",
                measureM9LiveParityBitmap1B(finishedBitmap));
        return out;
    }'''

copy_method = r'''    private static void copyM9LiveParityIfPresent(JSONObject source, JSONObject dest, String key)
            throws Exception {
        copyM9LiveParitySafe1B(source, dest, key);
    }'''

nullable_method = r'''    private static void putM9LiveParityNullable(JSONObject dest, String key, Object value)
            throws Exception {
        safePutM9LiveParity1B(dest, key, value);
    }'''

s = replace_method(s, 'private static void captureM9LiveParity1APreview(', capture_method)
s = replace_method(s, 'private static M9LiveParitySnapshot1A snapshotM9LiveParity1A(', snapshot_method)
s = replace_method(s, 'private static JSONObject buildM9LiveParity1ASummary(', summary_method)
s = replace_method(s, 'private static void copyM9LiveParityIfPresent(', copy_method)
s = replace_method(s, 'private static void putM9LiveParityNullable(', nullable_method)

# Add public display confirmation + safe serializers + actual rendered-bitmap luma measurement.
helper_anchor = '    private static synchronized void ensureOpenCv() {\n'
if s.count(helper_anchor) != 1:
    raise SystemExit('M9LIVEPARITY1B helper anchor count=' + str(s.count(helper_anchor)))
helpers = r'''    /** Called only after the M9 preview Bitmap has been committed to the ImageView. */
    public static void markM9LivePreviewDisplayed1B() {
        synchronized (M9_LIVE_PARITY_1A_LOCK) {
            if (M9_LIVE_PARITY_1A_LAST_PREVIEW == null) return;
            try {
                JSONObject copy = new JSONObject(M9_LIVE_PARITY_1A_LAST_PREVIEW.toString());
                long now = System.nanoTime();
                safePutM9LiveParity1B(copy, "displayConfirmed", true);
                safePutM9LiveParity1B(copy, "displayConfirmedMonotonicNs", now);
                safePutM9LiveParity1B(copy, "previewRenderSequence",
                        M9_LIVE_PARITY_1B_LAST_RENDERED_SEQUENCE);
                M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW = copy;
                M9_LIVE_PARITY_1B_LAST_DISPLAYED_PREVIEW_NS =
                        M9_LIVE_PARITY_1A_LAST_PREVIEW_NS;
                M9_LIVE_PARITY_1B_LAST_DISPLAYED_SEQUENCE =
                        M9_LIVE_PARITY_1B_LAST_RENDERED_SEQUENCE;
            } catch (Throwable t) {
                Log.w(TAG, "M9LIVEPARITY1B display confirmation failed: " + t);
            }
        }
    }

    private static void safePutM9LiveParity1B(JSONObject out, String key, Object value) {
        try {
            if (value instanceof Double && !Double.isFinite((Double) value)) {
                out.put(key, JSONObject.NULL);
                return;
            }
            if (value instanceof Float && !Float.isFinite((Float) value)) {
                out.put(key, JSONObject.NULL);
                return;
            }
            out.put(key, value != null ? value : JSONObject.NULL);
        } catch (Throwable ignored) {}
    }

    private static boolean copyM9LiveParitySafe1B(JSONObject source,
                                                   JSONObject dest,
                                                   String key) {
        if (source == null || dest == null) return false;
        try {
            if (!source.has(key) || source.isNull(key)) return true;
            Object value = source.get(key);
            if (value instanceof Double && !Double.isFinite((Double) value)) {
                dest.put(key, JSONObject.NULL);
                return true;
            }
            if (value instanceof Float && !Float.isFinite((Float) value)) {
                dest.put(key, JSONObject.NULL);
                return true;
            }
            if (value instanceof JSONObject) {
                value = new JSONObject(value.toString());
            } else if (value instanceof org.json.JSONArray) {
                value = new org.json.JSONArray(value.toString());
            }
            dest.put(key, value);
            return true;
        } catch (Throwable ignored) {
            return false;
        }
    }

    private static <T> void safeCaptureResultKeyM9LiveParity1B(
            JSONObject out, String name, CaptureResult result, CaptureResult.Key<T> key) {
        if (result == null) {
            safePutM9LiveParity1B(out, name, null);
            return;
        }
        try {
            safePutM9LiveParity1B(out, name, result.get(key));
        } catch (Throwable t) {
            safePutM9LiveParity1B(out, name, null);
            safePutM9LiveParity1B(out, name + "ReadError", String.valueOf(t));
        }
    }

    private static <T> void safeCaptureRequestKeyM9LiveParity1B(
            JSONObject out, String name, CaptureRequest request, CaptureRequest.Key<T> key) {
        if (request == null) {
            safePutM9LiveParity1B(out, name, null);
            return;
        }
        try {
            safePutM9LiveParity1B(out, name, request.get(key));
        } catch (Throwable t) {
            safePutM9LiveParity1B(out, name, null);
            safePutM9LiveParity1B(out, name + "ReadError", String.valueOf(t));
        }
    }

    private static JSONObject measureM9LiveParityBitmap1B(Bitmap bitmap) {
        JSONObject out = new JSONObject();
        safePutM9LiveParity1B(out, "schema", "m9cam.liveparity.v1b.display_luma");
        safePutM9LiveParity1B(out, "source", "actual_finished_M9_Bitmap_before_ImageView");
        safePutM9LiveParity1B(out, "lumaFormula", "BT601_integer_77R_150G_29B_div256");
        if (bitmap == null || bitmap.isRecycled()) {
            safePutM9LiveParity1B(out, "valid", false);
            safePutM9LiveParity1B(out, "reason", "bitmap_unavailable");
            return out;
        }
        try {
            int w = bitmap.getWidth();
            int h = bitmap.getHeight();
            int step = Math.max(1, (int)Math.sqrt((w * (double)h) / 180000.0));
            long[] hist = new long[256];
            long[] centerHist = new long[256];
            long total = 0L;
            long centerTotal = 0L;
            long sum = 0L;
            long dark32 = 0L, dark64 = 0L, bright224 = 0L, bright240 = 0L;
            int cx0 = w / 4, cx1 = (3 * w) / 4;
            int cy0 = h / 4, cy1 = (3 * h) / 4;
            int[] row = new int[w];
            for (int y = 0; y < h; y += step) {
                bitmap.getPixels(row, 0, w, 0, y, w, 1);
                for (int x = 0; x < w; x += step) {
                    int p = row[x];
                    int r = (p >>> 16) & 255;
                    int g = (p >>> 8) & 255;
                    int b = p & 255;
                    int yy = (77 * r + 150 * g + 29 * b + 128) >> 8;
                    hist[yy]++;
                    total++;
                    sum += yy;
                    if (yy <= 32) dark32++;
                    if (yy <= 64) dark64++;
                    if (yy >= 224) bright224++;
                    if (yy >= 240) bright240++;
                    if (x >= cx0 && x < cx1 && y >= cy0 && y < cy1) {
                        centerHist[yy]++;
                        centerTotal++;
                    }
                }
            }
            safePutM9LiveParity1B(out, "valid", total > 0);
            safePutM9LiveParity1B(out, "width", w);
            safePutM9LiveParity1B(out, "height", h);
            safePutM9LiveParity1B(out, "sampleStep", step);
            safePutM9LiveParity1B(out, "sampleCount", total);
            safePutM9LiveParity1B(out, "meanY", total > 0 ? sum / (double)total : 0.0);
            safePutM9LiveParity1B(out, "q10", quantileM9LiveParity1B(hist, total, 0.10));
            safePutM9LiveParity1B(out, "q25", quantileM9LiveParity1B(hist, total, 0.25));
            safePutM9LiveParity1B(out, "median", quantileM9LiveParity1B(hist, total, 0.50));
            safePutM9LiveParity1B(out, "q75", quantileM9LiveParity1B(hist, total, 0.75));
            safePutM9LiveParity1B(out, "q90", quantileM9LiveParity1B(hist, total, 0.90));
            safePutM9LiveParity1B(out, "q95", quantileM9LiveParity1B(hist, total, 0.95));
            safePutM9LiveParity1B(out, "q99", quantileM9LiveParity1B(hist, total, 0.99));
            safePutM9LiveParity1B(out, "centerMedian",
                    quantileM9LiveParity1B(centerHist, centerTotal, 0.50));
            safePutM9LiveParity1B(out, "darkFractionLE32",
                    total > 0 ? dark32 / (double)total : 0.0);
            safePutM9LiveParity1B(out, "darkFractionLE64",
                    total > 0 ? dark64 / (double)total : 0.0);
            safePutM9LiveParity1B(out, "brightFractionGE224",
                    total > 0 ? bright224 / (double)total : 0.0);
            safePutM9LiveParity1B(out, "brightFractionGE240",
                    total > 0 ? bright240 / (double)total : 0.0);
        } catch (Throwable t) {
            safePutM9LiveParity1B(out, "valid", false);
            safePutM9LiveParity1B(out, "reason", "measurement_failed");
            safePutM9LiveParity1B(out, "error", String.valueOf(t));
        }
        return out;
    }

    private static int quantileM9LiveParity1B(long[] hist, long total, double q) {
        if (hist == null || total <= 0) return 0;
        long target = Math.max(1L, (long)Math.ceil(total * q));
        long acc = 0L;
        for (int i = 0; i < hist.length; i++) {
            acc += hist[i];
            if (acc >= target) return i;
        }
        return hist.length - 1;
    }

'''
s = s.replace(helper_anchor, helpers + helper_anchor, 1)
renderer.write_text(s)

# Expose ImageView-display confirmation through the existing preview facade.
p = preview.read_text()
class_anchor = '    private M9LivePreview1A() {}\n'
if p.count(class_anchor) != 1:
    raise SystemExit('M9LIVEPARITY1B preview facade anchor count=' + str(p.count(class_anchor)))
p = p.replace(class_anchor, class_anchor + '''
    /** M9LIVEPARITY1B: confirms that the most recent rendered frame reached the user display. */
    public static void markDisplayed1B() {
        M9R35Renderer.markM9LivePreviewDisplayed1B();
    }
''', 1)
preview.write_text(p)

# Confirm only after setImageBitmap(), i.e. after the frame chosen for the viewfinder is known.
c = controller.read_text()
ui_anchor = '''                            m9LivePreviewImageView.setImageBitmap(ready);
                            m9LivePreviewImageView.setVisibility(android.view.View.VISIBLE);
'''
if c.count(ui_anchor) != 1:
    raise SystemExit('M9LIVEPARITY1B ImageView commit anchor count=' + str(c.count(ui_anchor)))
c = c.replace(ui_anchor, '''                            m9LivePreviewImageView.setImageBitmap(ready);
                            M9LivePreview1A.markDisplayed1B();
                            m9LivePreviewImageView.setVisibility(android.view.View.VISIBLE);
''', 1)
controller.write_text(c)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'm9liveparity1b' not in m.group(1).lower():
        old = m.group(0)
        quote = '"' if '"' in old else "'"
        g = g.replace(old, 'versionName ' + quote + m.group(1)
                      + '-m9liveparity1b-viewfinderref' + quote, 1)
        gradle.write_text(g)

print('M9LIVEPARITY1B_VIEWFINDER_REFERENCE applied')
print(' - final JPEG remains photographic authority')
print(' - no exposure, TC20, tone, curve02, saturation or still-render mutation')
print(' - preview record is fail-safe against malformed/non-finite optional diagnostics')
print(' - pairing prefers the M9 preview frame actually committed to the ImageView')
print(' - preview and still actual rendered Bitmap luma distributions recorded')
