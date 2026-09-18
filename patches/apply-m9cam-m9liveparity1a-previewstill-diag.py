#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9liveparity1a-previewstill-diag.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle = root / 'app/build.gradle'
if not renderer.exists():
    raise SystemExit('M9LIVEPARITY1A renderer missing')

s = renderer.read_text()

required = [
    'M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN',
    'M9_LIVE_PREVIEW_1A_ACTIVE',
    'M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR',
    'M9SENSORTARGET1A',
    'm9cam.tonebound.v1a.050ev',
    'SAT2_M04_M05',
]
for marker in required:
    if marker not in s:
        raise SystemExit('M9LIVEPARITY1A baseline marker missing: ' + marker)
if 'M9LIVEPARITY1A_PREVIEWSTILL_DIAG' in s:
    raise SystemExit('M9LIVEPARITY1A already applied')

def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'M9LIVEPARITY1A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

# Diagnostic state only. This stores the last completed live-render summary, which is the
# frame most likely to be visible when the shutter is pressed. It never feeds rendering.
field_anchor = '    private static final ThreadLocal<JSONObject> M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR = new ThreadLocal<>();\n'
fields = field_anchor + '''    // M9LIVEPARITY1A_PREVIEWSTILL_DIAG: read-only pairing of the latest completed
    // 1080p live M9 render with the next full-resolution still render.
    private static final Object M9_LIVE_PARITY_1A_LOCK = new Object();
    private static JSONObject M9_LIVE_PARITY_1A_LAST_PREVIEW = null;
    private static long M9_LIVE_PARITY_1A_LAST_PREVIEW_NS = 0L;
'''
s = replace_once(s, field_anchor, fields, 'diagnostic state fields')

# Snapshot the last completed preview at still-render entry, before the full-resolution
# render can take seconds and a later preview update could otherwise contaminate pairing.
entry_anchor = '''        long started = System.nanoTime();
        Path jpgPath = null;
'''
entry_new = '''        long started = System.nanoTime();
        final boolean m9LiveParity1ALiveRoute =
                Boolean.TRUE.equals(M9_LIVE_PREVIEW_1A_ACTIVE.get());
        final M9LiveParitySnapshot1A m9LiveParity1AAtStillStart =
                (!m9LiveParity1ALiveRoute && primaryRoute)
                        ? snapshotM9LiveParity1A()
                        : M9LiveParitySnapshot1A.none();
        Path jpgPath = null;
'''
s = replace_once(s, entry_anchor, entry_new, 'still-entry snapshot')

# The early-return live-preview block already owns the exact diagnostics produced by the
# render shown in the ImageView. Capture a compact immutable copy immediately before return.
preview_anchor = '''                    previewDiag.put("sourceGeometryAuthority",
                            "original_full_resolution_RAW_descriptor_retained_before_preview_reduction");
'''
preview_new = preview_anchor + '''                    captureM9LiveParity1APreview(
                            previewDiag, captureResult, captureRequest, width, height);
'''
s = replace_once(s, preview_anchor, preview_new, 'preview completed-render capture')

# Pair the snapshotted live summary with this still's render diagnostics. This is added only
# to the full-resolution shutter route and does not modify any photographic decision.
diag_anchor = '''            JSONObject diag = out.diagnostics;
            diag.put("status", "success");
'''
diag_new = '''            JSONObject diag = out.diagnostics;
            if (!m9LiveParity1ALiveRoute && primaryRoute) {
                JSONObject parity = new JSONObject();
                parity.put("schema", "m9cam.liveparity.v1a.previewstill");
                parity.put("revision", "M9LIVEPARITY1A_PREVIEWSTILL_DIAG");
                parity.put("diagnosticOnly", true);
                parity.put("photographicPixelChange", false);
                parity.put("captureExposureMutation", false);
                parity.put("tc20Mutation", false);
                parity.put("toneBoundMutation", false);
                parity.put("curve02Mutation", false);
                parity.put("previewPairingPolicy",
                        "latest_completed_live_render_snapshotted_at_still_render_entry");
                parity.put("previewAvailable", m9LiveParity1AAtStillStart.json != null);
                if (m9LiveParity1AAtStillStart.json != null) {
                    long ageNs = Math.max(0L, started - m9LiveParity1AAtStillStart.completedNs);
                    parity.put("previewAgeAtStillRenderStartMs", ageNs / 1_000_000.0);
                    parity.put("preview", m9LiveParity1AAtStillStart.json);
                }
                parity.put("still", buildM9LiveParity1ASummary(
                        diag, captureResult, captureRequest, frame.width, frame.height, "still_full_raw"));
                diag.put("m9LiveParity1A", parity);
            }
            diag.put("status", "success");
'''
s = replace_once(s, diag_anchor, diag_new, 'still parity attachment')

helper_anchor = '    private static synchronized void ensureOpenCv() {\n'
helpers = r'''    private static final class M9LiveParitySnapshot1A {
        final JSONObject json;
        final long completedNs;
        M9LiveParitySnapshot1A(JSONObject json, long completedNs) {
            this.json = json;
            this.completedNs = completedNs;
        }
        static M9LiveParitySnapshot1A none() {
            return new M9LiveParitySnapshot1A(null, 0L);
        }
    }

    private static void captureM9LiveParity1APreview(JSONObject rendererDiag,
                                                     CaptureResult result,
                                                     CaptureRequest request,
                                                     int width,
                                                     int height) {
        try {
            JSONObject summary = buildM9LiveParity1ASummary(
                    rendererDiag, result, request, width, height, "preview_reduced_raw");
            summary.put("completedMonotonicNs", System.nanoTime());
            synchronized (M9_LIVE_PARITY_1A_LOCK) {
                M9_LIVE_PARITY_1A_LAST_PREVIEW = new JSONObject(summary.toString());
                M9_LIVE_PARITY_1A_LAST_PREVIEW_NS = summary.getLong("completedMonotonicNs");
            }
        } catch (Throwable t) {
            Log.w(TAG, "M9LIVEPARITY1A preview diagnostic capture failed: " + t);
        }
    }

    private static M9LiveParitySnapshot1A snapshotM9LiveParity1A() {
        synchronized (M9_LIVE_PARITY_1A_LOCK) {
            if (M9_LIVE_PARITY_1A_LAST_PREVIEW == null) {
                return M9LiveParitySnapshot1A.none();
            }
            try {
                return new M9LiveParitySnapshot1A(
                        new JSONObject(M9_LIVE_PARITY_1A_LAST_PREVIEW.toString()),
                        M9_LIVE_PARITY_1A_LAST_PREVIEW_NS);
            } catch (Throwable ignored) {
                return M9LiveParitySnapshot1A.none();
            }
        }
    }

    private static JSONObject buildM9LiveParity1ASummary(JSONObject rendererDiag,
                                                          CaptureResult result,
                                                          CaptureRequest request,
                                                          int width,
                                                          int height,
                                                          String role) throws Exception {
        JSONObject out = new JSONObject();
        out.put("schema", "m9cam.liveparity.v1a.render_summary");
        out.put("role", role);
        out.put("width", width);
        out.put("height", height);

        if (result != null) {
            putNullable(out, "resultIso", result.get(CaptureResult.SENSOR_SENSITIVITY));
            putNullable(out, "resultExposureTimeNs", result.get(CaptureResult.SENSOR_EXPOSURE_TIME));
            putNullable(out, "resultFrameDurationNs", result.get(CaptureResult.SENSOR_FRAME_DURATION));
            putNullable(out, "resultPostRawSensitivityBoost",
                    result.get(CaptureResult.CONTROL_POST_RAW_SENSITIVITY_BOOST));
            putNullable(out, "resultShadingMode", result.get(CaptureResult.SHADING_MODE));
            putNullable(out, "resultLensShadingMapMode",
                    result.get(CaptureResult.STATISTICS_LENS_SHADING_MAP_MODE));
            putNullable(out, "resultColorCorrectionMode",
                    result.get(CaptureResult.COLOR_CORRECTION_MODE));
        }
        if (request != null) {
            putNullable(out, "requestIso", request.get(CaptureRequest.SENSOR_SENSITIVITY));
            putNullable(out, "requestExposureTimeNs", request.get(CaptureRequest.SENSOR_EXPOSURE_TIME));
            putNullable(out, "requestFrameDurationNs", request.get(CaptureRequest.SENSOR_FRAME_DURATION));
            putNullable(out, "requestPostRawSensitivityBoost",
                    request.get(CaptureRequest.CONTROL_POST_RAW_SENSITIVITY_BOOST));
            putNullable(out, "requestShadingMode", request.get(CaptureRequest.SHADING_MODE));
            putNullable(out, "requestLensShadingMapMode",
                    request.get(CaptureRequest.STATISTICS_LENS_SHADING_MAP_MODE));
            putNullable(out, "requestColorCorrectionMode",
                    request.get(CaptureRequest.COLOR_CORRECTION_MODE));
        }

        if (rendererDiag != null) {
            String[] scalarKeys = new String[] {
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
                    "m9LivePreviewMode"
            };
            for (String key : scalarKeys) copyIfPresent(rendererDiag, out, key);
            copyIfPresent(rendererDiag, out, "toneForensics1A");
            copyIfPresent(rendererDiag, out, "toneBound1A");
            copyIfPresent(rendererDiag, out, "shadingLumaDecomp1A");
            copyIfPresent(rendererDiag, out, "sensorDescriptor1A");
            copyIfPresent(rendererDiag, out, "targetFalloff1A");
        }
        return out;
    }

    private static void copyIfPresent(JSONObject source, JSONObject dest, String key)
            throws Exception {
        if (source != null && source.has(key) && !source.isNull(key)) {
            Object value = source.get(key);
            if (value instanceof JSONObject) {
                value = new JSONObject(value.toString());
            } else if (value instanceof org.json.JSONArray) {
                value = new org.json.JSONArray(value.toString());
            }
            dest.put(key, value);
        }
    }

    private static void putNullable(JSONObject dest, String key, Object value)
            throws Exception {
        dest.put(key, value != null ? value : JSONObject.NULL);
    }

'''
s = replace_once(s, helper_anchor, helpers + helper_anchor, 'diagnostic helpers')

renderer.write_text(s)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'm9liveparity1a' not in m.group(1).lower():
        old = m.group(0)
        quote = '"' if '"' in old else "'"
        g = g.replace(old, 'versionName ' + quote + m.group(1)
                      + '-m9liveparity1a-previewstilldiag' + quote, 1)
        gradle.write_text(g)

print('M9LIVEPARITY1A_PREVIEWSTILL_DIAG applied')
print(' - latest completed 1080p M9 preview diagnostics retained in memory')
print(' - snapshot taken at full-resolution still render entry')
print(' - preview/still exposure, TC20, tonebound, tail and shading state paired in _M9_PRIMARY')
print(' - no capture request, source processing or photographic pixel mutation')
