#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9livewysiwyg1a-currentexposure.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
preview = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java'
controller = root / 'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
gradle = root / 'app/build.gradle'
for p in (renderer, preview, controller):
    if not p.exists():
        raise SystemExit('M9LIVEWYSIWYG1A missing assembled file: ' + str(p))

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEWYSIWYG1A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9LIVEWYSIWYG1A method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('M9LIVEWYSIWYG1A opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
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
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
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
                escape = False
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1
        i += 1
    raise SystemExit('M9LIVEWYSIWYG1A unterminated method: ' + signature)

# ---------------------------------------------------------------------------
# CaptureController: exact current-exposure RAW/result pairing.
# ---------------------------------------------------------------------------
c = controller.read_text()
for marker in (
        'M9LIVEPREVIEW1A_FULLRENDER720P',
        'M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN',
        'm9LivePreviewProbeInFlight',
        'm9LivePreviewRenderBusy'):
    if marker not in c:
        raise SystemExit('M9LIVEWYSIWYG1A controller baseline marker missing: ' + marker)
if 'M9LIVEWYSIWYG1A_CURRENTEXPOSURE' in c:
    raise SystemExit('M9LIVEWYSIWYG1A already applied')

field_anchor = '''    private volatile CaptureResult m9LivePreviewProbeResult;
    private volatile CaptureRequest m9LivePreviewProbeRequest;
'''
field_new = field_anchor + '''    // M9LIVEWYSIWYG1A_CURRENTEXPOSURE
    // Pair the one-shot RAW probe to its exact TotalCaptureResult. The probe itself is
    // still the current repeating-preview request plus RAW output: no ISO/shutter/AE mutation.
    private final Object m9LiveWysiwygPairLock1A = new Object();
    private Image m9LiveWysiwygPendingImage1A = null;
    private TotalCaptureResult m9LiveWysiwygPendingResult1A = null;
    private CaptureRequest m9LiveWysiwygPendingRequest1A = null;
'''
c = replace_once(c, field_anchor, field_new, 'pair fields')

cb_start = c.find('    private final CameraCaptureSession.CaptureCallback m9LivePreviewCaptureCallback1A =')
if cb_start < 0:
    raise SystemExit('M9LIVEWYSIWYG1A callback start missing')
cb_end = c.find('    };', cb_start)
if cb_end < 0:
    raise SystemExit('M9LIVEWYSIWYG1A callback end missing')
cb_end += len('    };')
new_cb = r'''    private final CameraCaptureSession.CaptureCallback m9LivePreviewCaptureCallback1A =
            new CameraCaptureSession.CaptureCallback() {
        @Override
        public void onCaptureCompleted(@NonNull CameraCaptureSession session,
                                       @NonNull CaptureRequest request,
                                       @NonNull TotalCaptureResult result) {
            m9LivePreviewProbeRequest = request;
            m9LivePreviewProbeResult = result;
            synchronized (m9LiveWysiwygPairLock1A) {
                m9LiveWysiwygPendingResult1A = result;
                m9LiveWysiwygPendingRequest1A = request;
            }
            tryDispatchM9LiveWysiwygPair1A();
        }

        @Override
        public void onCaptureFailed(@NonNull CameraCaptureSession session,
                                    @NonNull CaptureRequest request,
                                    @NonNull android.hardware.camera2.CaptureFailure failure) {
            clearM9LiveWysiwygPair1A(true);
            Log.w(TAG, "M9LIVEWYSIWYG1A probe capture failed reason=" + failure.getReason());
        }
    };'''
c = c[:cb_start] + new_cb + c[cb_end:]

listener_start = c.find(
    '            if (M9LivePreview1A.ENABLED && !isZslMode()',
    c.find('mOnRawImageAvailableListener'))
if listener_start < 0:
    raise SystemExit('M9LIVEWYSIWYG1A RAW preview listener block missing')
listener_end = c.find('                return;\n            }', listener_start)
if listener_end < 0:
    raise SystemExit('M9LIVEWYSIWYG1A RAW preview listener end missing')
listener_end += len('                return;\n            }')
new_listener = r'''            if (M9LivePreview1A.ENABLED && !isZslMode()
                    && m9LivePreviewProbeInFlight.get()) {
                final Image previewRaw = reader.acquireLatestImage();
                if (previewRaw == null) return;
                synchronized (m9LiveWysiwygPairLock1A) {
                    Image old = m9LiveWysiwygPendingImage1A;
                    m9LiveWysiwygPendingImage1A = previewRaw;
                    if (old != null && old != previewRaw) {
                        try { old.close(); } catch (Throwable ignored) {}
                    }
                }
                tryDispatchM9LiveWysiwygPair1A();
                return;
            }'''
c = c[:listener_start] + new_listener + c[listener_end:]

# Ensure stop closes a RAW that is waiting for its metadata mate.
stop_start = c.find('    private void stopM9LivePreview1A() {')
req_start = c.find('    private void requestM9LivePreviewProbe1A() {', stop_start)
if stop_start < 0 or req_start < 0:
    raise SystemExit('M9LIVEWYSIWYG1A stop/request methods missing')
stop_block = c[stop_start:req_start]
stop_anchor = '''        m9LivePreviewProbeResult = null;
        m9LivePreviewProbeRequest = null;
'''
stop_block = replace_once(
    stop_block, stop_anchor,
    stop_anchor + '        clearM9LiveWysiwygPair1A(true);\n',
    'stop pair clear')
c = c[:stop_start] + stop_block + c[req_start:]

# Replace the probe request with an explicit current-exposure contract. This deliberately does
# NOT call GenerateExpoPair(), set AE mode, set SENSOR_SENSITIVITY, set SENSOR_EXPOSURE_TIME,
# or scale a RAW toward a hypothetical capture.
req_start = c.find('    private void requestM9LivePreviewProbe1A() {')
if req_start < 0:
    raise SystemExit('M9LIVEWYSIWYG1A request method missing')
_, req_end = method_span(c, '    private void requestM9LivePreviewProbe1A() {')
new_req = r'''    private void requestM9LivePreviewProbe1A() {
        if (!M9LivePreview1A.ENABLED || isZslMode() || burst || isProcessing
                || mState != STATE_PREVIEW || mCameraDevice == null || mCaptureSession == null
                || mPreviewRequestBuilder == null || mImageReaderRaw == null
                || m9LivePreviewRenderBusy.get()) return;
        if (!m9LivePreviewProbeInFlight.compareAndSet(false, true)) return;

        // Freeze only the pairing slots. Exposure remains whatever the photographer currently
        // sees through the normal preview request.
        clearM9LiveWysiwygPair1A(false);

        Surface rawSurface = mImageReaderRaw.getSurface();
        boolean targetAdded = false;
        try {
            m9LivePreviewProbeResult = null;
            m9LivePreviewProbeRequest = null;

            // CURRENT LIVE SENSOR EXPOSURE + RAW target. No exposure prediction or mutation.
            mPreviewRequestBuilder.addTarget(rawSurface);
            targetAdded = true;
            CaptureRequest probe = mPreviewRequestBuilder.build();
            mPreviewRequestBuilder.removeTarget(rawSurface);
            targetAdded = false;
            m9LivePreviewProbeRequest = probe;
            mCaptureSession.capture(probe, m9LivePreviewCaptureCallback1A, mBackgroundHandler);
        } catch (Throwable t) {
            if (targetAdded) {
                try { mPreviewRequestBuilder.removeTarget(rawSurface); } catch (Throwable ignored) {}
            }
            clearM9LiveWysiwygPair1A(true);
            Log.w(TAG, "M9LIVEWYSIWYG1A current-exposure RAW probe failed: " + t);
        }
    }'''
c = c[:req_start] + new_req + c[req_end:]

helper_anchor = '    private void showToast(String msg) {'
hi = c.find(helper_anchor)
if hi < 0:
    raise SystemExit('M9LIVEWYSIWYG1A helper insertion anchor missing')
helpers = r'''    private void clearM9LiveWysiwygPair1A(boolean clearInFlight) {
        Image image;
        synchronized (m9LiveWysiwygPairLock1A) {
            image = m9LiveWysiwygPendingImage1A;
            m9LiveWysiwygPendingImage1A = null;
            m9LiveWysiwygPendingResult1A = null;
            m9LiveWysiwygPendingRequest1A = null;
        }
        if (image != null) {
            try { image.close(); } catch (Throwable ignored) {}
        }
        if (clearInFlight) m9LivePreviewProbeInFlight.set(false);
    }

    private void tryDispatchM9LiveWysiwygPair1A() {
        final Image image;
        final TotalCaptureResult result;
        final CaptureRequest request;
        final long imageTs;
        final long resultTs;
        final long pairDeltaNs;

        synchronized (m9LiveWysiwygPairLock1A) {
            if (m9LiveWysiwygPendingImage1A == null
                    || m9LiveWysiwygPendingResult1A == null
                    || m9LiveWysiwygPendingRequest1A == null) {
                return;
            }
            image = m9LiveWysiwygPendingImage1A;
            result = m9LiveWysiwygPendingResult1A;
            request = m9LiveWysiwygPendingRequest1A;

            Long resultTsObj = result.get(CaptureResult.SENSOR_TIMESTAMP);
            imageTs = image.getTimestamp();
            resultTs = resultTsObj != null ? resultTsObj : Long.MIN_VALUE;
            pairDeltaNs = resultTsObj != null ? Math.abs(imageTs - resultTs) : Long.MAX_VALUE;

            // RAW Image timestamp and SENSOR_TIMESTAMP should normally be identical. Permit a
            // small vendor tolerance, but never pair adjacent frames separated by a frame interval.
            if (resultTsObj == null || pairDeltaNs > 2_000_000L) {
                Log.w(TAG, "M9LIVEWYSIWYG1A timestamp mismatch image=" + imageTs
                        + " result=" + resultTs + " deltaNs=" + pairDeltaNs);
                try { image.close(); } catch (Throwable ignored) {}
                m9LiveWysiwygPendingImage1A = null;
                m9LiveWysiwygPendingResult1A = null;
                m9LiveWysiwygPendingRequest1A = null;
                m9LivePreviewProbeInFlight.set(false);
                return;
            }

            m9LiveWysiwygPendingImage1A = null;
            m9LiveWysiwygPendingResult1A = null;
            m9LiveWysiwygPendingRequest1A = null;
            m9LivePreviewProbeInFlight.set(false);
        }

        if (!m9LivePreviewRenderBusy.compareAndSet(false, true)) {
            try { image.close(); } catch (Throwable ignored) {}
            return;
        }

        final CameraCharacteristics previewChars = mCameraCharacteristics;
        final int previewRotation = cameraRotation;
        m9LivePreviewExecutor.execute(() -> {
            android.graphics.Bitmap rendered = null;
            try {
                // Render the exposure that actually produced this RAW. No virtual capture domain.
                rendered = M9LivePreview1A.render(
                        image, previewChars, result, request, previewRotation);
                final android.graphics.Bitmap ready = rendered;
                rendered = null;
                activity.runOnUiThread(() -> {
                    if (m9LivePreviewImageView == null) {
                        if (ready != null && !ready.isRecycled()) ready.recycle();
                        return;
                    }
                    android.graphics.Bitmap old = m9LivePreviewDisplayedBitmap;
                    m9LivePreviewDisplayedBitmap = ready;
                    m9LivePreviewImageView.setImageBitmap(ready);
                    M9LivePreview1A.markDisplayedWysiwyg1A(
                            ready, imageTs, result, request, pairDeltaNs);
                    m9LivePreviewImageView.setVisibility(android.view.View.VISIBLE);
                    if (old != null && old != ready && !old.isRecycled()) old.recycle();
                });
            } catch (Throwable t) {
                Log.e(TAG, "M9LIVEWYSIWYG1A current-exposure frame failed", t);
            } finally {
                try { image.close(); } catch (Throwable ignored) {}
                if (rendered != null && !rendered.isRecycled()) rendered.recycle();
                m9LivePreviewRenderBusy.set(false);
            }
        });
    }

'''
c = c[:hi] + helpers + c[hi:]
controller.write_text(c)

# ---------------------------------------------------------------------------
# Preview facade: tell renderer which exact Bitmap reached ImageView.
# ---------------------------------------------------------------------------
p = preview.read_text()
class_anchor = '    private M9LivePreview1A() {}\n'
if p.count(class_anchor) != 1:
    raise SystemExit('M9LIVEWYSIWYG1A preview facade anchor count=' + str(p.count(class_anchor)))
p = p.replace(class_anchor, class_anchor + '''
    /** M9LIVEWYSIWYG1A: record the exact M9 Bitmap committed to the viewfinder. */
    public static void markDisplayedWysiwyg1A(Bitmap bitmap,
                                               long rawTimestampNs,
                                               CaptureResult captureResult,
                                               CaptureRequest captureRequest,
                                               long rawResultTimestampDeltaNs) {
        M9R35Renderer.markM9LiveWysiwygDisplayed1A(
                bitmap, rawTimestampNs, captureResult, captureRequest,
                rawResultTimestampDeltaNs);
    }
''', 1)
preview.write_text(p)

# ---------------------------------------------------------------------------
# Renderer: read-only displayed-preview/still diagnostics at actual Bitmap boundaries.
# ---------------------------------------------------------------------------
r = renderer.read_text()
for marker in (
        'M9_LIVE_PREVIEW_1A_ACTIVE',
        'M9_LIVE_PREVIEW_1A_BITMAP',
        'M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR',
        'FULL_PRODUCTION_RENDER_REDUCED_RAW_1440x1080_MAIN',
        'SAT2_M04_M05'):
    if marker not in r:
        raise SystemExit('M9LIVEWYSIWYG1A renderer baseline marker missing: ' + marker)

field_anchor_r = '    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR = new ThreadLocal<>();\n'
fields_r = field_anchor_r + '''    // M9LIVEWYSIWYG1A_CURRENTEXPOSURE: diagnostics only. Never read by photographic math.
    private static final Object M9_LIVE_WYSIWYG_1A_LOCK = new Object();
    private static final java.util.IdentityHashMap<Bitmap, JSONObject>
            M9_LIVE_WYSIWYG_1A_RENDERED = new java.util.IdentityHashMap<>();
    private static JSONObject M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED = null;
    private static long M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED_NS = 0L;
    private static long M9_LIVE_WYSIWYG_1A_SEQUENCE = 0L;
'''
r = replace_once(r, field_anchor_r, fields_r, 'renderer diagnostic fields')

# Register renderer diagnostics against the exact Bitmap identity before the wrapper returns it.
ws, we = method_span(r, '    public static Bitmap renderLivePreview1A(')
wrapper = r[ws:we]
return_anchor = '''            return out;
'''
if wrapper.count(return_anchor) != 1:
    raise SystemExit('M9LIVEWYSIWYG1A preview wrapper return anchor count=' + str(wrapper.count(return_anchor)))
wrapper = wrapper.replace(return_anchor, '''            registerM9LiveWysiwygRendered1A(
                    out, r.diagnostics, captureResult, captureRequest, width, height);
            return out;
''', 1)
r = r[:ws] + wrapper + r[we:]

# Snapshot the last actually DISPLAYED preview at still-render entry. No fallback to merely
# rendered frames: previewAvailable must mean the photographer could really see it.
entry_anchor = '''        long started = System.nanoTime();
        Path jpgPath = null;
'''
entry_new = '''        long started = System.nanoTime();
        final boolean m9LiveWysiwyg1ALiveRoute =
                Boolean.TRUE.equals(M9_LIVE_PREVIEW_1A_ACTIVE.get());
        final M9LiveWysiwygSnapshot1A m9LiveWysiwyg1AAtStillStart =
                (!m9LiveWysiwyg1ALiveRoute && primaryRoute)
                        ? snapshotM9LiveWysiwygDisplayed1A()
                        : M9LiveWysiwygSnapshot1A.none();
        Path jpgPath = null;
'''
r = replace_once(r, entry_anchor, entry_new, 'still-entry displayed snapshot')

# Measure the actual local final Bitmap immediately after renderer handoff and before JPEG
# encoding/recycling/file persistence.
rs, re_ = method_span(r, 'private static Result renderAndSaveInternal(')
method = r[rs:re_]
bitmap_anchor = '            bitmap = out.bitmap;\n'
if method.count(bitmap_anchor) != 1:
    raise SystemExit('M9LIVEWYSIWYG1A still bitmap anchor count=' + str(method.count(bitmap_anchor)))
still_diag = bitmap_anchor + r'''            if (!m9LiveWysiwyg1ALiveRoute && primaryRoute) {
                try {
                    JSONObject wysiwyg = new JSONObject();
                    wysiwyg.put("schema", "m9cam.livewysiwyg.v1a.current_exposure");
                    wysiwyg.put("revision", "M9LIVEWYSIWYG1A_CURRENTEXPOSURE");
                    wysiwyg.put("contract",
                            "current_live_sensor_exposure_through_M9_renderer");
                    wysiwyg.put("diagnosticOnly", true);
                    wysiwyg.put("previewExposurePrediction", false);
                    wysiwyg.put("previewSensorExposureMutation", false);
                    wysiwyg.put("virtualRawExposureScaling", false);
                    wysiwyg.put("captureExposureMutationByThisPatch", false);
                    wysiwyg.put("finalJpegPhotographicCoreChanged", false);
                    wysiwyg.put("previewPairingPolicy",
                            "RAW_Image_timestamp_exact_TotalCaptureResult_SENSOR_TIMESTAMP");
                    wysiwyg.put("previewReferencePolicy",
                            "last_actual_ImageView_displayed_M9_Bitmap_only");
                    wysiwyg.put("stillBitmapMeasurementBoundary",
                            "local_final_M9_Bitmap_immediately_before_JPEG_encode_or_recycle");
                    wysiwyg.put("previewAvailable",
                            m9LiveWysiwyg1AAtStillStart.json != null);
                    if (m9LiveWysiwyg1AAtStillStart.json != null) {
                        long ageNs = Math.max(
                                0L, started - m9LiveWysiwyg1AAtStillStart.displayedNs);
                        wysiwyg.put("previewDisplayedAgeAtStillRenderStartMs",
                                ageNs / 1_000_000.0);
                        wysiwyg.put("preview",
                                new JSONObject(m9LiveWysiwyg1AAtStillStart.json.toString()));
                    }
                    JSONObject stillSummary = buildM9LiveWysiwygSummary1A(
                            out.diagnostics, captureResult, captureRequest,
                            bitmap, frame.width, frame.height, "still_final_M9_bitmap");
                    wysiwyg.put("still", stillSummary);
                    if (m9LiveWysiwyg1AAtStillStart.json != null) {
                        putExposureAuditM9LiveWysiwyg1A(
                                wysiwyg, m9LiveWysiwyg1AAtStillStart.json, stillSummary);
                    }
                    out.diagnostics.put("m9LiveWysiwyg1A", wysiwyg);
                } catch (Throwable t) {
                    Log.w(TAG, "M9LIVEWYSIWYG1A still diagnostic failed: " + t);
                }
            }
'''
method = method.replace(bitmap_anchor, still_diag, 1)
r = r[:rs] + method + r[re_:]

helper_anchor_r = '    private static synchronized void ensureOpenCv() {\n'
if r.count(helper_anchor_r) != 1:
    raise SystemExit('M9LIVEWYSIWYG1A renderer helper anchor count=' + str(r.count(helper_anchor_r)))
renderer_helpers = r'''    private static final class M9LiveWysiwygSnapshot1A {
        final JSONObject json;
        final long displayedNs;

        M9LiveWysiwygSnapshot1A(JSONObject json, long displayedNs) {
            this.json = json;
            this.displayedNs = displayedNs;
        }

        static M9LiveWysiwygSnapshot1A none() {
            return new M9LiveWysiwygSnapshot1A(null, 0L);
        }
    }

    private static void registerM9LiveWysiwygRendered1A(
            Bitmap bitmap,
            JSONObject rendererDiag,
            CaptureResult result,
            CaptureRequest request,
            int width,
            int height) {
        if (bitmap == null || bitmap.isRecycled()) return;
        JSONObject summary = buildM9LiveWysiwygSummary1A(
                rendererDiag, result, request, bitmap, width, height,
                "preview_rendered_not_yet_displayed");
        synchronized (M9_LIVE_WYSIWYG_1A_LOCK) {
            M9_LIVE_WYSIWYG_1A_SEQUENCE++;
            safePutM9LiveWysiwyg1A(summary, "previewSequence",
                    M9_LIVE_WYSIWYG_1A_SEQUENCE);
            // Single-flight rendering means this normally contains one Bitmap. Bound it anyway.
            if (M9_LIVE_WYSIWYG_1A_RENDERED.size() > 4) {
                M9_LIVE_WYSIWYG_1A_RENDERED.clear();
            }
            M9_LIVE_WYSIWYG_1A_RENDERED.put(bitmap, summary);
        }
    }

    /** Called synchronously immediately after ImageView.setImageBitmap(ready). */
    public static void markM9LiveWysiwygDisplayed1A(
            Bitmap bitmap,
            long rawTimestampNs,
            CaptureResult result,
            CaptureRequest request,
            long rawResultTimestampDeltaNs) {
        long now = System.nanoTime();
        synchronized (M9_LIVE_WYSIWYG_1A_LOCK) {
            JSONObject summary = M9_LIVE_WYSIWYG_1A_RENDERED.remove(bitmap);
            if (summary == null) {
                summary = buildM9LiveWysiwygSummary1A(
                        null, result, request, bitmap,
                        bitmap != null ? bitmap.getWidth() : -1,
                        bitmap != null ? bitmap.getHeight() : -1,
                        "preview_display_failsafe");
            }
            safePutM9LiveWysiwyg1A(summary, "role", "preview_ImageView_displayed");
            safePutM9LiveWysiwyg1A(summary, "displayConfirmed", true);
            safePutM9LiveWysiwyg1A(summary, "displayConfirmedMonotonicNs", now);
            safePutM9LiveWysiwyg1A(summary, "rawImageTimestampNs", rawTimestampNs);
            safePutM9LiveWysiwyg1A(summary, "rawResultTimestampDeltaNs",
                    rawResultTimestampDeltaNs);
            // Re-measure at the actual ImageView commit boundary, not merely renderer return.
            safePutM9LiveWysiwyg1A(summary, "displayLuma1A",
                    measureM9LiveWysiwygBitmap1A(
                            bitmap, "actual_M9_Bitmap_at_ImageView_commit"));
            try {
                M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED =
                        new JSONObject(summary.toString());
                M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED_NS = now;
            } catch (Throwable t) {
                JSONObject core = new JSONObject();
                safePutM9LiveWysiwyg1A(core, "schema",
                        "m9cam.livewysiwyg.v1a.display_failsafe");
                safePutM9LiveWysiwyg1A(core, "displayConfirmed", true);
                safePutM9LiveWysiwyg1A(core, "displayConfirmedMonotonicNs", now);
                safePutM9LiveWysiwyg1A(core, "rawImageTimestampNs", rawTimestampNs);
                safePutM9LiveWysiwyg1A(core, "rawResultTimestampDeltaNs",
                        rawResultTimestampDeltaNs);
                safePutM9LiveWysiwyg1A(core, "serializationError", String.valueOf(t));
                M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED = core;
                M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED_NS = now;
            }
        }
    }

    private static M9LiveWysiwygSnapshot1A snapshotM9LiveWysiwygDisplayed1A() {
        synchronized (M9_LIVE_WYSIWYG_1A_LOCK) {
            if (M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED == null) {
                return M9LiveWysiwygSnapshot1A.none();
            }
            try {
                return new M9LiveWysiwygSnapshot1A(
                        new JSONObject(M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED.toString()),
                        M9_LIVE_WYSIWYG_1A_LAST_DISPLAYED_NS);
            } catch (Throwable t) {
                return M9LiveWysiwygSnapshot1A.none();
            }
        }
    }

    private static JSONObject buildM9LiveWysiwygSummary1A(
            JSONObject rendererDiag,
            CaptureResult result,
            CaptureRequest request,
            Bitmap bitmap,
            int width,
            int height,
            String role) {
        JSONObject out = new JSONObject();
        safePutM9LiveWysiwyg1A(out, "schema",
                "m9cam.livewysiwyg.v1a.render_summary");
        safePutM9LiveWysiwyg1A(out, "revision",
                "M9LIVEWYSIWYG1A_CURRENTEXPOSURE");
        safePutM9LiveWysiwyg1A(out, "role", role);
        safePutM9LiveWysiwyg1A(out, "rawWidth", width);
        safePutM9LiveWysiwyg1A(out, "rawHeight", height);

        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultSensorTimestampNs", result, CaptureResult.SENSOR_TIMESTAMP);
        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultIso", result, CaptureResult.SENSOR_SENSITIVITY);
        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultExposureTimeNs", result, CaptureResult.SENSOR_EXPOSURE_TIME);
        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultFrameDurationNs", result, CaptureResult.SENSOR_FRAME_DURATION);
        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultAeMode", result, CaptureResult.CONTROL_AE_MODE);
        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultAeExposureCompensation", result,
                CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION);
        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultAwbMode", result, CaptureResult.CONTROL_AWB_MODE);
        safeCaptureResultKeyM9LiveWysiwyg1A(
                out, "resultPostRawSensitivityBoost", result,
                CaptureResult.CONTROL_POST_RAW_SENSITIVITY_BOOST);

        safeCaptureRequestKeyM9LiveWysiwyg1A(
                out, "requestIso", request, CaptureRequest.SENSOR_SENSITIVITY);
        safeCaptureRequestKeyM9LiveWysiwyg1A(
                out, "requestExposureTimeNs", request, CaptureRequest.SENSOR_EXPOSURE_TIME);
        safeCaptureRequestKeyM9LiveWysiwyg1A(
                out, "requestFrameDurationNs", request, CaptureRequest.SENSOR_FRAME_DURATION);
        safeCaptureRequestKeyM9LiveWysiwyg1A(
                out, "requestAeMode", request, CaptureRequest.CONTROL_AE_MODE);
        safeCaptureRequestKeyM9LiveWysiwyg1A(
                out, "requestAeExposureCompensation", request,
                CaptureRequest.CONTROL_AE_EXPOSURE_COMPENSATION);
        safeCaptureRequestKeyM9LiveWysiwyg1A(
                out, "requestAwbMode", request, CaptureRequest.CONTROL_AWB_MODE);
        safeCaptureRequestKeyM9LiveWysiwyg1A(
                out, "requestPostRawSensitivityBoost", request,
                CaptureRequest.CONTROL_POST_RAW_SENSITIVITY_BOOST);

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
                if (!copyM9LiveWysiwygSafe1A(rendererDiag, out, key)
                        && rendererDiag.has(key)) {
                    omitted.put(key);
                }
            }
            safePutM9LiveWysiwyg1A(out, "optionalRendererFieldsOmitted", omitted);
        }

        safePutM9LiveWysiwyg1A(out, "displayLuma1A",
                measureM9LiveWysiwygBitmap1A(
                        bitmap, "actual_finished_M9_Bitmap_before_output_boundary"));
        return out;
    }

    private static void putExposureAuditM9LiveWysiwyg1A(
            JSONObject contract, JSONObject preview, JSONObject still) {
        Double actual = exposureDeltaEvM9LiveWysiwyg1A(
                preview, "resultIso", "resultExposureTimeNs",
                still, "resultIso", "resultExposureTimeNs");
        Double requested = exposureDeltaEvM9LiveWysiwyg1A(
                preview, "resultIso", "resultExposureTimeNs",
                still, "requestIso", "requestExposureTimeNs");
        safePutM9LiveWysiwyg1A(
                contract, "stillActualVsDisplayedPreviewExposureDeltaEv", actual);
        safePutM9LiveWysiwyg1A(
                contract, "stillRequestedVsDisplayedPreviewExposureDeltaEv", requested);
        safePutM9LiveWysiwyg1A(
                contract, "exposureDeltaDefinition",
                "log2((still_ISO*still_exposure_ns)/(displayed_preview_result_ISO*displayed_preview_result_exposure_ns))");
    }

    private static Double exposureDeltaEvM9LiveWysiwyg1A(
            JSONObject a, String aIsoKey, String aTimeKey,
            JSONObject b, String bIsoKey, String bTimeKey) {
        try {
            double aIso = a.optDouble(aIsoKey, Double.NaN);
            double aTime = a.optDouble(aTimeKey, Double.NaN);
            double bIso = b.optDouble(bIsoKey, Double.NaN);
            double bTime = b.optDouble(bTimeKey, Double.NaN);
            if (!Double.isFinite(aIso) || !Double.isFinite(aTime)
                    || !Double.isFinite(bIso) || !Double.isFinite(bTime)
                    || aIso <= 0.0 || aTime <= 0.0 || bIso <= 0.0 || bTime <= 0.0) {
                return null;
            }
            double ratio = (bIso * bTime) / (aIso * aTime);
            if (!Double.isFinite(ratio) || ratio <= 0.0) return null;
            return Math.log(ratio) / Math.log(2.0);
        } catch (Throwable t) {
            return null;
        }
    }

    private static void safePutM9LiveWysiwyg1A(
            JSONObject out, String key, Object value) {
        try {
            if (value instanceof Double && !Double.isFinite((Double) value)) {
                out.put(key, JSONObject.NULL);
            } else if (value instanceof Float && !Float.isFinite((Float) value)) {
                out.put(key, JSONObject.NULL);
            } else {
                out.put(key, value != null ? value : JSONObject.NULL);
            }
        } catch (Throwable ignored) {}
    }

    private static boolean copyM9LiveWysiwygSafe1A(
            JSONObject source, JSONObject dest, String key) {
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

    private static <T> void safeCaptureResultKeyM9LiveWysiwyg1A(
            JSONObject out, String name, CaptureResult result, CaptureResult.Key<T> key) {
        if (result == null) {
            safePutM9LiveWysiwyg1A(out, name, null);
            return;
        }
        try {
            safePutM9LiveWysiwyg1A(out, name, result.get(key));
        } catch (Throwable t) {
            safePutM9LiveWysiwyg1A(out, name, null);
            safePutM9LiveWysiwyg1A(out, name + "ReadError", String.valueOf(t));
        }
    }

    private static <T> void safeCaptureRequestKeyM9LiveWysiwyg1A(
            JSONObject out, String name, CaptureRequest request, CaptureRequest.Key<T> key) {
        if (request == null) {
            safePutM9LiveWysiwyg1A(out, name, null);
            return;
        }
        try {
            safePutM9LiveWysiwyg1A(out, name, request.get(key));
        } catch (Throwable t) {
            safePutM9LiveWysiwyg1A(out, name, null);
            safePutM9LiveWysiwyg1A(out, name + "ReadError", String.valueOf(t));
        }
    }

    private static JSONObject measureM9LiveWysiwygBitmap1A(
            Bitmap bitmap, String source) {
        JSONObject out = new JSONObject();
        safePutM9LiveWysiwyg1A(out, "schema",
                "m9cam.livewysiwyg.v1a.display_luma");
        safePutM9LiveWysiwyg1A(out, "source", source);
        safePutM9LiveWysiwyg1A(out, "lumaFormula",
                "BT601_integer_77R_150G_29B_div256");
        if (bitmap == null || bitmap.isRecycled()) {
            safePutM9LiveWysiwyg1A(out, "valid", false);
            safePutM9LiveWysiwyg1A(out, "reason", "bitmap_unavailable");
            return out;
        }
        try {
            int w = bitmap.getWidth();
            int h = bitmap.getHeight();
            int step = Math.max(
                    1, (int)Math.sqrt((w * (double)h) / 180000.0));
            long[] hist = new long[256];
            long[] centerHist = new long[256];
            long total = 0L;
            long centerTotal = 0L;
            long sum = 0L;
            long dark32 = 0L;
            long dark64 = 0L;
            long bright224 = 0L;
            long bright240 = 0L;
            int cx0 = w / 4;
            int cx1 = (3 * w) / 4;
            int cy0 = h / 4;
            int cy1 = (3 * h) / 4;
            int[] row = new int[w];
            for (int y = 0; y < h; y += step) {
                bitmap.getPixels(row, 0, w, 0, y, w, 1);
                for (int x = 0; x < w; x += step) {
                    int px = row[x];
                    int rr = (px >>> 16) & 255;
                    int gg = (px >>> 8) & 255;
                    int bb = px & 255;
                    int yy = (77 * rr + 150 * gg + 29 * bb + 128) >> 8;
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
            safePutM9LiveWysiwyg1A(out, "valid", total > 0);
            safePutM9LiveWysiwyg1A(out, "width", w);
            safePutM9LiveWysiwyg1A(out, "height", h);
            safePutM9LiveWysiwyg1A(out, "sampleStep", step);
            safePutM9LiveWysiwyg1A(out, "sampleCount", total);
            safePutM9LiveWysiwyg1A(
                    out, "meanY", total > 0 ? sum / (double) total : 0.0);
            safePutM9LiveWysiwyg1A(
                    out, "q10", quantileM9LiveWysiwyg1A(hist, total, 0.10));
            safePutM9LiveWysiwyg1A(
                    out, "q25", quantileM9LiveWysiwyg1A(hist, total, 0.25));
            safePutM9LiveWysiwyg1A(
                    out, "q50", quantileM9LiveWysiwyg1A(hist, total, 0.50));
            safePutM9LiveWysiwyg1A(
                    out, "q75", quantileM9LiveWysiwyg1A(hist, total, 0.75));
            safePutM9LiveWysiwyg1A(
                    out, "q90", quantileM9LiveWysiwyg1A(hist, total, 0.90));
            safePutM9LiveWysiwyg1A(
                    out, "q95", quantileM9LiveWysiwyg1A(hist, total, 0.95));
            safePutM9LiveWysiwyg1A(
                    out, "q99", quantileM9LiveWysiwyg1A(hist, total, 0.99));
            safePutM9LiveWysiwyg1A(
                    out, "centerMedian",
                    quantileM9LiveWysiwyg1A(centerHist, centerTotal, 0.50));
            safePutM9LiveWysiwyg1A(
                    out, "darkFractionLE32",
                    total > 0 ? dark32 / (double) total : 0.0);
            safePutM9LiveWysiwyg1A(
                    out, "darkFractionLE64",
                    total > 0 ? dark64 / (double) total : 0.0);
            safePutM9LiveWysiwyg1A(
                    out, "brightFractionGE224",
                    total > 0 ? bright224 / (double) total : 0.0);
            safePutM9LiveWysiwyg1A(
                    out, "brightFractionGE240",
                    total > 0 ? bright240 / (double) total : 0.0);
        } catch (Throwable t) {
            safePutM9LiveWysiwyg1A(out, "valid", false);
            safePutM9LiveWysiwyg1A(out, "reason", "measurement_failed");
            safePutM9LiveWysiwyg1A(out, "error", String.valueOf(t));
        }
        return out;
    }

    private static int quantileM9LiveWysiwyg1A(
            long[] hist, long total, double q) {
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
r = replace_once(
    r, helper_anchor_r, renderer_helpers + helper_anchor_r,
    'renderer helpers')
renderer.write_text(r)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'm9livewysiwyg1a' not in m.group(1).lower():
        old = m.group(0)
        quote = '"' if '"' in old else "'"
        g = g.replace(
            old,
            'versionName ' + quote + m.group(1)
            + '-m9livewysiwyg1a-currentexposure' + quote,
            1)
        gradle.write_text(g)

print('M9LIVEWYSIWYG1A_CURRENTEXPOSURE applied')
print(' - current preview request exposure is the only live RAW exposure')
print(' - exact RAW Image.timestamp <-> TotalCaptureResult SENSOR_TIMESTAMP pairing')
print(' - no GenerateExpoPair preview prediction')
print(' - no preview ISO/shutter/AE mutation')
print(' - no virtual RAW exposure-domain scaling')
print(' - exact ImageView-displayed Bitmap measured at commit boundary')
print(' - exact final still Bitmap measured before JPEG/recycle')
print(' - still actual/requested exposure audited against displayed preview exposure')
print(' - still photographic core unchanged')
