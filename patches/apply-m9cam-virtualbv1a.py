#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-virtualbv1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'VIRTUALBV1A missing expected file: {rel}')
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
coord_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
render_meter_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java'

if 'm9cam.sceneexposure.v8.renderaware1h' not in read(scene_rel):
    raise SystemExit('VIRTUALBV1A requires frozen SCENEEXPOSURE1H')
if 'm9cam.exposuresplit.v4.capturemeter1b.m9negative1c.scenefingerprint1a.signedcal1a' not in read(coord_rel):
    raise SystemExit('VIRTUALBV1A requires M9NEGATIVE1C / SIGNEDCAL1A coordinator')
if 'm9cam.m9negative.v3.capturemeter1b.scenefingerprint1a.signedcal1a' not in read(negative_rel):
    raise SystemExit('VIRTUALBV1A requires M9NEGATIVE1C / SIGNEDCAL1A')
if 'm9cam.rendermeter.v3.evidence1c' not in read(render_meter_rel):
    raise SystemExit('VIRTUALBV1A requires frozen RENDERMETER1C')

# VIRTUALBV1A is diagnostic-only. Freeze every photographic/capture seam and the
# completed-RAW teacher model. Only a new diagnostic class, metadata publication,
# build identity and CI are allowed to change.
frozen_rels = [
    scene_rel,
    coord_rel,
    negative_rel,
    render_meter_rel,
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

virtual_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'
virtual = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * VIRTUALBV1A: diagnostic-only Leica-like BV abstraction.
 *
 * Architectural basis:
 *  - recovered M9 APEX/Q8.8 exposure arithmetic remains the M9 authority;
 *  - M10-R reverse engineering independently supports meter -> BV -> APEX -> TV/SV
 *    separation, but NO M10-R camera-specific constants are imported here;
 *  - the Xiaomi preview is only a proxy for the M9 optical TTL meter.
 *
 * This first build intentionally keeps the uncertain part explicit:
 * phone preview scalar -> provisional virtual M9 BV.  It then reports the exact
 * recovered M9 reduced-form APEX baseline at ISO160.  No value from this class is
 * allowed to mutate Camera2, Photon, FB1, motion policy, renderer, DNG, or JPEG.
 */
public final class M9VirtualBv1A {
    public static final String SCHEMA = "m9cam.virtualbv.v1";

    // Research calibration only. These are NOT recovered Leica constants.
    private static final double PROVISIONAL_CENTER_WEIGHT = 0.70;
    private static final double PROVISIONAL_GLOBAL_WEIGHT = 0.30;
    private static final double PROVISIONAL_REFERENCE_Y = 100.0;
    private static final double PROVISIONAL_BV_CALIBRATION_OFFSET_EV = 0.0;
    private static final double DIRECTION_ANALYSIS_DEADBAND_EV = 0.08;

    // M9-side baseline already established by the M9 firmware investigation.
    private static final int M9_BASE_ISO = 160;
    private static final double M9_REDUCED_APEX_CONSTANT_EV = 5.0;
    private static final double M9_OVERRIDE_EV = 0.0;
    private static final double APEX_ISO_REFERENCE = 3.125;

    private M9VirtualBv1A() {}

    public static JSONObject evaluate(JSONObject root) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("jpegBrightnessUsedForCapture", false);
            out.put("architecture",
                    "preview_meter_proxy_to_virtual_bv_then_recovered_m9_apex_baseline");
            out.put("crossGenerationRule",
                    "M10R_architecture_only_no_M10R_camera_specific_constants");

            if (root == null) {
                invalid(out, "metadata_root_missing");
                return out;
            }
            JSONObject scene = root.optJSONObject("m9SceneExposureDiagnostic");
            JSONObject inputs = scene != null ? scene.optJSONObject("inputs") : null;
            if (scene == null || !scene.optBoolean("valid", false) || inputs == null) {
                invalid(out, "sceneexposure1h_missing_or_invalid");
                return out;
            }

            double globalMedian = inputs.optDouble("globalMedian", Double.NaN);
            double centerMedian = inputs.optDouble("centerMedian", Double.NaN);
            long previewFrames = scene.optLong("previewLumaFrames", 0L);
            if (!finite(globalMedian) || !finite(centerMedian)) {
                invalid(out, "virtual_meter_proxy_inputs_non_finite");
                return out;
            }

            // Deliberately simple scalar centre-weighted proxy. No histogram classifier,
            // q95/q99 highlight branch, scene labels or completed-RAW values enter BV.
            double meterProxyRaw = PROVISIONAL_CENTER_WEIGHT * centerMedian
                    + PROVISIONAL_GLOBAL_WEIGHT * globalMedian;
            double meterProxyTemporal = meterProxyRaw;
            double meterProxyRelativeEv = log2(Math.max(meterProxyTemporal, 1e-6)
                    / PROVISIONAL_REFERENCE_Y);

            JSONObject captureResult = root.optJSONObject("captureResult");
            double aperture = captureResult != null
                    ? captureResult.optDouble("aperture", Double.NaN) : Double.NaN;

            JSONObject audit = root.optJSONObject("m9ExposureAudit");
            JSONObject photonOnly = audit != null ? audit.optJSONObject("photonOnly") : null;
            double photonIso = photonOnly != null
                    ? photonOnly.optDouble("systemIsoExact", Double.NaN) : Double.NaN;
            long photonShutterNs = photonOnly != null
                    ? photonOnly.optLong("shutterNs", 0L) : 0L;

            if ((!finite(photonIso) || photonIso <= 0.0 || photonShutterNs <= 0L)) {
                JSONObject photon = root.optJSONObject("photonExposureDecision");
                JSONObject finalDecision = photon != null ? photon.optJSONObject("finalDecision") : null;
                if (finalDecision != null) {
                    photonIso = finalDecision.optDouble("iso", Double.NaN);
                    photonShutterNs = finalDecision.optLong("shutterNs", 0L);
                }
            }
            if (!finite(aperture) || aperture <= 0.0
                    || !finite(photonIso) || photonIso <= 0.0 || photonShutterNs <= 0L) {
                invalid(out, "photon_apex_reference_missing");
                return out;
            }

            // Photon-equivalent BV is a standard APEX coordinate derived from the
            // phone's photon-only exposure decision and physical fixed aperture.
            double photonTvEv = log2(1_000_000_000.0 / photonShutterNs);
            double photonAvEv = log2(aperture * aperture);
            double photonSvEv = svForIso(photonIso);
            double photonEquivalentBvEv = photonTvEv + photonAvEv - photonSvEv;

            // If the centre-weighted proxy lands below the provisional neutral Y,
            // virtual BV becomes lower than Photon-equivalent BV and signedMeterDeltaEv
            // naturally becomes positive. Above the reference it becomes negative.
            double virtualBvUncalibratedEv = photonEquivalentBvEv + meterProxyRelativeEv;
            double virtualBvEv = virtualBvUncalibratedEv
                    + PROVISIONAL_BV_CALIBRATION_OFFSET_EV;
            double signedMeterDeltaEv = photonEquivalentBvEv - virtualBvEv;

            int virtualBvQ8_8 = q8_8(virtualBvEv);
            int overrideQ8_8 = q8_8(M9_OVERRIDE_EV);
            double m9BaseSvEv = svForIso(M9_BASE_ISO);
            int m9BaseSvQ8_8 = q8_8(m9BaseSvEv);

            // Recovered M9 reduced-form baseline:
            // TV = BV + SV - 5 - Override.
            // The lens-dependent slowest-TV / Auto-ISO constraint is intentionally NOT
            // invented in VIRTUALBV1A, so threshold/activation fields remain unavailable.
            double m9TvBaseEv = virtualBvEv + m9BaseSvEv
                    - M9_REDUCED_APEX_CONSTANT_EV - M9_OVERRIDE_EV;
            int m9TvBaseQ8_8 = q8_8(m9TvBaseEv);
            double predictedM9ShutterSeconds = Math.pow(2.0, -m9TvBaseEv);

            out.put("valid", true);
            out.put("reason", "virtual_bv_diagnostic_recorded_no_live_exposure_change");

            out.put("meterProxyRaw", meterProxyRaw);
            out.put("meterProxyTemporal", meterProxyTemporal);
            out.put("meterProxyFramesUsed", previewFrames);
            out.put("meterProxyTemporalMethod",
                    "existing_preview_luma_snapshot_no_additional_sampling_or_capture_history");
            out.put("meterProxyCenterWeight", PROVISIONAL_CENTER_WEIGHT);
            out.put("meterProxyGlobalWeight", PROVISIONAL_GLOBAL_WEIGHT);
            out.put("meterProxyReferenceY", PROVISIONAL_REFERENCE_Y);
            out.put("meterProxyRelativeEv", meterProxyRelativeEv);

            out.put("virtualBvUncalibratedEv", virtualBvUncalibratedEv);
            out.put("virtualBvCalibrationOffsetEv", PROVISIONAL_BV_CALIBRATION_OFFSET_EV);
            out.put("virtualBvCalibrationState",
                    "provisional_zero_offset_reference_y100_not_absolute_m9_ttl_calibration");
            out.put("virtualBvQ8_8", virtualBvQ8_8);
            out.put("virtualBvEv", virtualBvEv);

            out.put("photonEquivalentBvEv", photonEquivalentBvEv);
            out.put("photonEquivalentTvEv", photonTvEv);
            out.put("photonEquivalentAvEv", photonAvEv);
            out.put("photonEquivalentSvEv", photonSvEv);
            out.put("photonReferenceIso", photonIso);
            out.put("photonReferenceExposureNs", photonShutterNs);
            out.put("signedMeterDeltaEv", signedMeterDeltaEv);
            out.put("signedMeterDeltaUnbounded", true);
            out.put("directionAnalysisDeadbandEv", DIRECTION_ANALYSIS_DEADBAND_EV);
            out.put("direction", direction(signedMeterDeltaEv));

            out.put("m9OverrideQ8_8", overrideQ8_8);
            out.put("m9OverrideEv", M9_OVERRIDE_EV);
            out.put("m9SelectedSvQ8_8", m9BaseSvQ8_8);
            out.put("m9SelectedSvEv", m9BaseSvEv);
            out.put("m9SelectedIso", M9_BASE_ISO);
            out.put("m9TvBaseQ8_8", m9TvBaseQ8_8);
            out.put("m9TvBaseEv", m9TvBaseEv);
            out.put("m9TvThresholdQ8_8", JSONObject.NULL);
            out.put("m9TvThresholdEv", JSONObject.NULL);
            out.put("autoIsoWouldActivate", JSONObject.NULL);
            out.put("autoIsoLowerBoundHit", JSONObject.NULL);
            out.put("autoIsoUpperBoundHit", JSONObject.NULL);
            out.put("autoIsoState",
                    "not_solved_in_1a_without_m9_lens_dependent_tv_threshold_context");

            out.put("predictedM9SvQ8_8", m9BaseSvQ8_8);
            out.put("predictedM9SvEv", m9BaseSvEv);
            out.put("predictedM9Iso", M9_BASE_ISO);
            out.put("predictedM9TvQ8_8", m9TvBaseQ8_8);
            out.put("predictedM9TvEv", m9TvBaseEv);
            out.put("predictedM9ShutterSeconds", predictedM9ShutterSeconds);
            out.put("predictedM9Assumption",
                    "base_iso160_reduced_m9_apex_baseline_only_auto_iso_threshold_not_yet_applied");

            JSONObject feedback = root.optJSONObject("m9ExposureFeedback");
            boolean lumaWouldApply = feedback != null && feedback.optBoolean("wouldApply", false);
            double lumaRecommendedEv = feedback != null
                    ? feedback.optDouble("recommendedExposureCorrectionEv", 0.0) : 0.0;
            double lumaAppliedEv = feedback != null
                    ? feedback.optDouble("appliedExposureCorrectionEv", 0.0) : 0.0;
            JSONObject auditFb1 = audit != null ? audit.optJSONObject("fb1") : null;
            if (auditFb1 != null && finite(auditFb1.optDouble("appliedEv", Double.NaN))) {
                lumaAppliedEv = auditFb1.optDouble("appliedEv", lumaAppliedEv);
            }
            out.put("luma24WouldApply", lumaWouldApply);
            out.put("luma24RecommendedEv", lumaRecommendedEv);
            out.put("luma24AppliedEv", lumaAppliedEv);

            JSONObject allocator = audit != null ? audit.optJSONObject("allocatorRequest") : null;
            if (allocator != null) {
                putFinite(out, "actualTargetIso", allocator.optDouble("iso", Double.NaN));
                long ns = allocator.optLong("shutterNs", 0L);
                out.put("actualTargetExposureNs", ns > 0L ? ns : JSONObject.NULL);
            } else {
                out.put("actualTargetIso", JSONObject.NULL);
                out.put("actualTargetExposureNs", JSONObject.NULL);
            }
            if (captureResult != null) {
                putFinite(out, "actualCaptureIso", captureResult.optDouble("iso", Double.NaN));
                long ns = captureResult.optLong("exposureTimeNs", 0L);
                out.put("actualCaptureExposureNs", ns > 0L ? ns : JSONObject.NULL);
            } else {
                out.put("actualCaptureIso", JSONObject.NULL);
                out.put("actualCaptureExposureNs", JSONObject.NULL);
            }

            JSONObject compare = new JSONObject();
            JSONObject split = scene.optJSONObject("captureRenderSplit");
            if (split != null) {
                putFinite(compare, "captureMeterStabilizedEv",
                        split.optDouble("stabilizedCaptureTargetEv", Double.NaN));
                JSONObject neg = split.optJSONObject("m9Negative1A");
                if (neg != null) {
                    compare.put("completedRawFeedbackAvailable",
                            neg.optBoolean("feedbackAvailable", false));
                    putFinite(compare, "completedRawRecommendedCaptureDeltaEv",
                            neg.optDouble("recommendedCaptureDeltaEv", Double.NaN));
                    putFinite(compare, "completedRawSceneDistance",
                            neg.optDouble("nearestCompletedSceneDistance", Double.NaN));
                }
            }
            compare.put("virtualBvSignedMeterDeltaEv", signedMeterDeltaEv);
            compare.put("luma24RecommendedEv", lumaRecommendedEv);
            compare.put("comparisonPurpose",
                    "direction_first_virtual_bv_vs_preview_classifier_vs_completed_raw_teacher");
            out.put("comparison", compare);
        } catch (Throwable t) {
            try {
                invalid(out, "virtual_bv_exception");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static String direction(double ev) {
        if (!finite(ev)) return "invalid";
        if (Math.abs(ev) < DIRECTION_ANALYSIS_DEADBAND_EV) return "neutral";
        return ev > 0.0 ? "increase" : "decrease";
    }

    private static double svForIso(double iso) {
        if (!finite(iso) || iso <= 0.0) return Double.NaN;
        return log2(iso / APEX_ISO_REFERENCE);
    }

    private static int q8_8(double ev) {
        if (!finite(ev)) return 0;
        return (int)Math.round(ev * 256.0);
    }

    private static void putFinite(JSONObject out, String key, double value) {
        try {
            out.put(key, finite(value) ? value : JSONObject.NULL);
        } catch (Exception ignored) {}
    }

    private static void invalid(JSONObject out, String reason) {
        try {
            out.put("valid", false);
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("signedMeterDeltaEv", JSONObject.NULL);
            out.put("reason", reason);
        } catch (Exception ignored) {}
    }

    private static double log2(double x) {
        return Math.log(x) / Math.log(2.0);
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }
}
'''
write(virtual_rel, virtual)

# Publish VIRTUALBV1A beside the existing capture/render diagnostics. It executes only
# while writing metadata, after the actual Camera2 request/result is known, and therefore
# cannot influence the exposure decision that produced the frame.
meta = read(meta_rel)
meta_anchor = '            root.put("m9SceneExposureDiagnostic", M9SceneExposureDiagnostic.snapshotJson());\n'
meta_insert = meta_anchor + '            root.put("m9VirtualBv", M9VirtualBv1A.evaluate(root));\n'
if 'root.put("m9VirtualBv"' not in meta:
    if meta_anchor not in meta:
        raise SystemExit('VIRTUALBV1A metadata scene diagnostic anchor missing')
    meta = meta.replace(meta_anchor, meta_insert, 1)
write(meta_rel, meta)

# Compact Android versionName avoids AGP/Linux output filename overflow.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_version = "versionName '1.47-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1a-sc1a-cm1b'"
new_version = "versionName '1.48-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1a-sc1a-vbv1a-cm1b'"
if old_version not in g:
    raise SystemExit('VIRTUALBV1A requires compact SIGNEDCAL1A 1.47 versionName')
write(gradle_rel, g.replace(old_version, new_version, 1))

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_marker = 'm9negative1csignedcal1ascenefingerprint1acapturemeter1b'
new_marker = 'm9negative1csignedcal1avirtualbv1ascenefingerprint1acapturemeter1b'
if old_marker not in b:
    raise SystemExit('VIRTUALBV1A forensic build marker anchor missing')
b = b.replace(old_marker, new_marker, 1)
if '1.47-' in b:
    b = b.replace('1.47-', '1.48-', 1)
write(back_rel, b)

# Verify photographic/capture implementation files are byte-identical.
for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'VIRTUALBV1A frozen seam changed unexpectedly: {rel}')

print('M9Cam VIRTUALBV1A diagnostic overlay applied')
print(' - M9 firmware remains authority for reduced APEX/Q8.8 baseline')
print(' - M10-R contributes architecture only; no M10-R camera-specific constants copied')
print(' - simple 70% center / 30% global preview scalar; provisional neutral Y=100')
print(' - absolute M9 TTL calibration explicitly remains provisional')
print(' - raw signedMeterDeltaEv is unbounded and diagnostic-only')
print(' - SCENEFINGERPRINT1A, SIGNEDCAL1A, RENDERMETER1C and current capture path frozen')
print(' - no Camera2, Photon, FB1, motion, renderer, DNG or JPEG mutation')
