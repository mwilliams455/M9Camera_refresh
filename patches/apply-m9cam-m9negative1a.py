#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9negative1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'M9NEGATIVE1A missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

coord_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
spool_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
render_meter_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java'
scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'

if 'm9cam.exposuresplit.v1.capturemeter1a.temporal1a' not in read(coord_rel):
    raise SystemExit('M9NEGATIVE1A requires CAPTUREMETER1A/TEMPORAL1A baseline')
if 'm9cam.rendermeter.v3.evidence1c' not in read(render_meter_rel):
    raise SystemExit('M9NEGATIVE1A requires RENDERMETER1C')
if 'm9cam.sidecarspool.v1.privatebundle1b' not in read(spool_rel):
    raise SystemExit('M9NEGATIVE1A requires SIDECAR1B')
if "versionName '1.44-m9modern7r38luma24fb1primary25perf3i" not in read('app/build.gradle'):
    raise SystemExit('M9NEGATIVE1A requires version 1.44 CAPTURESPLIT1C baseline')

# Photographic controls remain frozen. Renderer source is changed only to expose additional
# statistics from the histogram it already computes and to publish completed-RAW feedback.
frozen_rels = [
    scene_rel,
    render_meter_rel,
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

# -----------------------------------------------------------------------------
# M9NEGATIVE1A: completed-RAW feedback store + CAPTUREMETER1B diagnostic model.
# It never mutates Camera2. Scene signatures are queued at capture-step evaluation and
# paired FIFO with the primary render completion, matching PRIMARY2.5's ordered queue.
# -----------------------------------------------------------------------------
negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
negative = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;

/**
 * M9NEGATIVE1A / CAPTUREMETER1B diagnostic-only completed-RAW feedback.
 *
 * The current capture decision remains untouched. This class answers a different question:
 * did a recent similar completed RAW collect enough useful lower-distribution signal while
 * preserving meaningful highlight headroom? JPEG brightness is never an input.
 */
public final class M9NegativeFeedback1A {
    public static final String SCHEMA = "m9cam.m9negative.v1.capturemeter1b.completedraw1a";
    private static final int MAX_PENDING = 24;
    private static final int MAX_COMPLETED = 10;
    private static final double SIMILAR_SCENE_DISTANCE = 1.0;
    private static final double MAX_POSITIVE_DELTA_EV = 0.50;
    private static final double MAX_NEGATIVE_DELTA_EV = -0.50;

    private static final Deque<SceneSignature> PENDING = new ArrayDeque<>();
    private static final Deque<CompletedRaw> COMPLETED = new ArrayDeque<>();
    private static long captureSequence = 0L;
    private static long completedSequence = 0L;

    private M9NegativeFeedback1A() {}

    /** Called once by the capture-step diagnostic after its recommendation has been evaluated. */
    public static synchronized JSONObject noteCaptureScene(JSONObject scene1h) {
        JSONObject out = new JSONObject();
        try {
            SceneSignature s = SceneSignature.from(scene1h, ++captureSequence);
            if (s == null) {
                out.put("valid", false);
                out.put("reason", "capture_scene_signature_missing");
                return out;
            }
            while (PENDING.size() >= MAX_PENDING) PENDING.removeFirst();
            PENDING.addLast(s);
            out.put("valid", true);
            out.put("captureSequence", s.sequence);
            out.put("pendingSceneCount", PENDING.size());
            out.put("associationMode", "capture_step_fifo_to_primary_render_completion");
        } catch (Exception e) {
            try {
                out.put("valid", false);
                out.put("reason", "capture_scene_queue_exception");
            } catch (Exception ignored) {}
        }
        return out;
    }

    /** Called only for the completed primary RAW/JPEG render. No pixels or exposure state are changed. */
    public static synchronized JSONObject recordCompletedRaw(JSONObject renderer,
                                                             int iso,
                                                             long exposureTimeNs) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_completed_raw_feedback_only");
            out.put("liveEligible", false);
            SceneSignature scene = PENDING.pollFirst();
            if (renderer == null) {
                out.put("valid", false);
                out.put("reason", "renderer_diagnostics_missing");
                return out;
            }
            double q25 = renderer.optDouble("rawUq25", Double.NaN);
            double q50 = renderer.optDouble("rawUq50", Double.NaN);
            double q99 = renderer.optDouble("rawUq99", Double.NaN);
            double q995 = renderer.optDouble("rawUq99_5", Double.NaN);
            double q998 = renderer.optDouble("rawUq99_8", Double.NaN);
            double clip = renderer.optDouble("rawHardClipFraction", Double.NaN);
            if (!finite(q25) || !finite(q50) || !finite(q99) || !finite(q995)
                    || !finite(q998) || !finite(clip)) {
                out.put("valid", false);
                out.put("reason", "completed_raw_distribution_missing");
                out.put("sceneAssociationPresent", scene != null);
                return out;
            }

            CompletedRaw raw = new CompletedRaw();
            raw.completedSequence = ++completedSequence;
            raw.scene = scene;
            raw.q25 = q25;
            raw.q50 = q50;
            raw.q99 = q99;
            raw.q995 = q995;
            raw.q998 = q998;
            raw.clip = clip;
            raw.iso = Math.max(0, iso);
            raw.exposureTimeNs = Math.max(0L, exposureTimeNs);
            raw.energyIsoSeconds = raw.iso > 0 && raw.exposureTimeNs > 0
                    ? raw.iso * (raw.exposureTimeNs / 1_000_000_000.0) : Double.NaN;
            raw.completedEpochMs = System.currentTimeMillis();
            while (COMPLETED.size() >= MAX_COMPLETED) COMPLETED.removeFirst();
            COMPLETED.addLast(raw);

            out.put("valid", true);
            out.put("completedSequence", raw.completedSequence);
            out.put("captureSequence", scene != null ? scene.sequence : JSONObject.NULL);
            out.put("sceneAssociationPresent", scene != null);
            out.put("associationMode", "capture_step_fifo_to_primary_render_completion");
            out.put("rawUq25", q25);
            out.put("rawUq50", q50);
            out.put("rawUq99", q99);
            out.put("rawUq99_5", q995);
            out.put("rawUq99_8", q998);
            out.put("rawHardClipFraction", clip);
            out.put("captureIso", raw.iso);
            out.put("captureExposureTimeNs", raw.exposureTimeNs);
            if (finite(raw.energyIsoSeconds)) out.put("captureExposureEnergyIsoSeconds", raw.energyIsoSeconds);
            out.put("pendingSceneCount", PENDING.size());
            out.put("completedRawHistoryCount", COMPLETED.size());
            out.put("reason", scene != null
                    ? "completed_raw_recorded_with_capture_scene_signature"
                    : "completed_raw_recorded_without_scene_signature");
        } catch (Exception e) {
            try {
                out.put("valid", false);
                out.put("liveEligible", false);
                out.put("reason", "completed_raw_feedback_record_exception");
            } catch (Exception ignored) {}
        }
        return out;
    }

    /** Evaluate current preview scene against the most similar recent completed RAW. */
    public static synchronized JSONObject evaluate(JSONObject currentScene1h,
                                                   double legacyCaptureMeterEv) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("jpegBrightnessUsedForCapture", false);
            out.put("legacyCaptureMeterCandidateEv", legacyCaptureMeterEv);
            out.put("pendingSceneCount", PENDING.size());
            out.put("completedRawHistoryCount", COMPLETED.size());

            SceneSignature current = SceneSignature.from(currentScene1h, -1L);
            if (current == null) {
                out.put("valid", false);
                out.put("recommendedCaptureDeltaEv", 0.0);
                out.put("reason", "current_scene_signature_missing");
                return out;
            }

            CompletedRaw best = null;
            double bestDistance = Double.POSITIVE_INFINITY;
            List<CompletedRaw> history = new ArrayList<>(COMPLETED);
            for (int i = history.size() - 1; i >= 0; i--) {
                CompletedRaw candidate = history.get(i);
                if (candidate.scene == null) continue;
                double d = current.distance(candidate.scene);
                if (d < bestDistance) {
                    bestDistance = d;
                    best = candidate;
                }
            }
            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);
            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);
            if (best == null || !finite(bestDistance) || bestDistance > SIMILAR_SCENE_DISTANCE) {
                out.put("valid", true);
                out.put("feedbackAvailable", false);
                out.put("recommendedCaptureDeltaEv", 0.0);
                out.put("reason", best == null
                        ? "no_completed_raw_with_scene_signature_yet"
                        : "completed_raw_not_scene_similar_enough");
                return out;
            }

            double highlightStressFromTail = smoothstep(best.q998, 0.88, 0.98);
            double clipRisk = smoothstep(best.clip, 0.005, 0.030);
            double meaningfulClipRiskEvidence = clamp01(clipRisk
                    * Math.max(0.35, smoothstep(best.q998, 0.72, 0.96)));
            double negativeHighlightStressEvidence = clamp01(Math.max(
                    highlightStressFromTail * (0.35 + 0.65 * meaningfulClipRiskEvidence),
                    meaningfulClipRiskEvidence));
            double negativeHighlightProtectionEvidence = clamp01(
                    smoothstep(best.q998, 0.58, 0.90)
                    * (1.0 - 0.70 * meaningfulClipRiskEvidence));

            // These provisional lower-distribution bands are deliberately broad. The values are
            // emitted for calibration and are NOT allowed to alter the camera in this build.
            double q50Adequacy = smoothstep(best.q50, 0.025, 0.080);
            double q25Adequacy = smoothstep(best.q25, 0.006, 0.025);
            double lowerBodyAdequacy = clamp01(0.68 * q50Adequacy + 0.32 * q25Adequacy);
            double negativeShadowStarvationEvidence = clamp01(1.0 - lowerBodyAdequacy);
            double negativeRecoverabilityEvidence = clamp01(
                    smoothstep(best.q50, 0.012, 0.055)
                    * (1.0 - 0.35 * meaningfulClipRiskEvidence));
            double negativeExposureAdequacyEvidence = clamp01(
                    (1.0 - negativeShadowStarvationEvidence)
                    * (1.0 - 0.55 * negativeHighlightStressEvidence));

            double rawHeadroomEv = log2(0.92 / Math.max(best.q998, 1e-6));
            double additionalCaptureHeadroomEv = clamp(rawHeadroomEv, 0.0, MAX_POSITIVE_DELTA_EV);
            additionalCaptureHeadroomEv *= (1.0 - 0.80 * meaningfulClipRiskEvidence);

            double positiveDelta = additionalCaptureHeadroomEv
                    * negativeShadowStarvationEvidence
                    * (1.0 - 0.65 * negativeHighlightStressEvidence);
            double negativeDelta = 0.0;
            if (meaningfulClipRiskEvidence > 0.45 && negativeShadowStarvationEvidence < 0.55) {
                negativeDelta = -0.35 * meaningfulClipRiskEvidence
                        * (1.0 - negativeShadowStarvationEvidence);
            }
            double recommendation = clamp(positiveDelta + negativeDelta,
                    MAX_NEGATIVE_DELTA_EV, MAX_POSITIVE_DELTA_EV);
            if (Math.abs(recommendation) < 0.05) recommendation = 0.0;

            out.put("valid", true);
            out.put("feedbackAvailable", true);
            out.put("sourceCompletedSequence", best.completedSequence);
            if (best.scene != null) out.put("sourceCaptureSequence", best.scene.sequence);
            out.put("sourceAgeMs", Math.max(0L, System.currentTimeMillis() - best.completedEpochMs));
            out.put("rawUq25", best.q25);
            out.put("rawUq50", best.q50);
            out.put("rawUq99", best.q99);
            out.put("rawUq99_5", best.q995);
            out.put("rawUq99_8", best.q998);
            out.put("rawHardClipFraction", best.clip);
            out.put("captureIso", best.iso);
            out.put("captureExposureTimeNs", best.exposureTimeNs);
            if (finite(best.energyIsoSeconds)) out.put("captureExposureEnergyIsoSeconds", best.energyIsoSeconds);
            out.put("negativeHighlightProtectionEvidence", negativeHighlightProtectionEvidence);
            out.put("negativeHighlightStressEvidence", negativeHighlightStressEvidence);
            out.put("negativeShadowStarvationEvidence", negativeShadowStarvationEvidence);
            out.put("negativeRecoverabilityEvidence", negativeRecoverabilityEvidence);
            out.put("negativeExposureAdequacyEvidence", negativeExposureAdequacyEvidence);
            out.put("meaningfulClipRiskEvidence", meaningfulClipRiskEvidence);
            out.put("rawHeadroomTo0p92Ev", rawHeadroomEv);
            out.put("additionalCaptureHeadroomEv", additionalCaptureHeadroomEv);
            out.put("recommendedCaptureDeltaEv", recommendation);
            out.put("recommendationBoundNegativeEv", MAX_NEGATIVE_DELTA_EV);
            out.put("recommendationBoundPositiveEv", MAX_POSITIVE_DELTA_EV);
            out.put("reason", recommendation > 0.0
                    ? "similar_completed_raw_shadow_starved_with_remaining_headroom"
                    : recommendation < 0.0
                    ? "similar_completed_raw_highlight_stressed_with_adequate_lower_body"
                    : "similar_completed_raw_no_material_capture_delta_supported");
            out.put("calibrationState",
                    "provisional_raw_distribution_thresholds_collect_regression_labels_before_live_promotion");
        } catch (Exception e) {
            try {
                out.put("valid", false);
                out.put("liveEligible", false);
                out.put("usedToMutateCaptureTarget", false);
                out.put("recommendedCaptureDeltaEv", 0.0);
                out.put("reason", "m9negative1a_evaluation_exception");
            } catch (Exception ignored) {}
        }
        return out;
    }

    public static synchronized JSONObject snapshotJson() {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("pendingSceneCount", PENDING.size());
            out.put("completedRawHistoryCount", COMPLETED.size());
            JSONArray completed = new JSONArray();
            for (CompletedRaw r : COMPLETED) {
                JSONObject item = new JSONObject();
                item.put("completedSequence", r.completedSequence);
                item.put("captureSequence", r.scene != null ? r.scene.sequence : JSONObject.NULL);
                item.put("rawUq25", r.q25);
                item.put("rawUq50", r.q50);
                item.put("rawUq99_8", r.q998);
                item.put("rawHardClipFraction", r.clip);
                item.put("captureIso", r.iso);
                item.put("captureExposureTimeNs", r.exposureTimeNs);
                completed.put(item);
            }
            out.put("completed", completed);
        } catch (Exception ignored) {}
        return out;
    }

    private static final class SceneSignature {
        long sequence;
        double median;
        double center;
        double q99;
        double starvation;

        static SceneSignature from(JSONObject scene, long sequence) {
            if (scene == null || !scene.optBoolean("valid", false)) return null;
            JSONObject inputs = scene.optJSONObject("inputs");
            JSONObject positive = scene.optJSONObject("positiveBodyPressure");
            if (inputs == null || positive == null) return null;
            double median = inputs.optDouble("globalMedian", Double.NaN);
            double center = inputs.optDouble("centerMedian", Double.NaN);
            double q99 = inputs.optDouble("globalQ99", Double.NaN);
            double starvation = positive.optDouble("spatialQualificationStarvationPressure",
                    positive.optDouble("luma24BacklightPressure", Double.NaN));
            if (!finite(median) || !finite(center) || !finite(q99) || !finite(starvation)) return null;
            SceneSignature s = new SceneSignature();
            s.sequence = sequence;
            s.median = median;
            s.center = center;
            s.q99 = q99;
            s.starvation = starvation;
            return s;
        }

        double distance(SceneSignature other) {
            if (other == null) return Double.POSITIVE_INFINITY;
            return Math.max(Math.abs(median - other.median) / 40.0,
                    Math.max(Math.abs(center - other.center) / 40.0,
                    Math.max(Math.abs(q99 - other.q99) / 50.0,
                            Math.abs(starvation - other.starvation) / 0.50)));
        }
    }

    private static final class CompletedRaw {
        long completedSequence;
        SceneSignature scene;
        double q25, q50, q99, q995, q998, clip;
        int iso;
        long exposureTimeNs;
        double energyIsoSeconds;
        long completedEpochMs;
    }

    private static double smoothstep(double x, double lo, double hi) {
        if (!finite(x)) return 0.0;
        if (hi <= lo) return x >= hi ? 1.0 : 0.0;
        double t = clamp01((x - lo) / (hi - lo));
        return t * t * (3.0 - 2.0 * t);
    }

    private static double clamp01(double x) {
        return clamp(x, 0.0, 1.0);
    }

    private static double clamp(double x, double lo, double hi) {
        return Math.max(lo, Math.min(hi, x));
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }

    private static double log2(double x) {
        return Math.log(Math.max(x, 1e-12)) / Math.log(2.0);
    }
}
'''
write(negative_rel, negative)

# CAPTUREMETER1B: preserve CAPTUREMETER1A output exactly, append completed-RAW diagnostic
# recommendation and queue the current scene signature for later primary-render association.
coord = read(coord_rel)
coord = coord.replace('m9cam.exposuresplit.v1.capturemeter1a.temporal1a',
                      'm9cam.exposuresplit.v2.capturemeter1b.m9negative1a', 1)
insert_anchor = '''            out.put("renderSplit", renderSplit);

            out.put("valid", true);
'''
insert_new = '''            out.put("renderSplit", renderSplit);

            JSONObject m9Negative = M9NegativeFeedback1A.evaluate(scene1h, proposedStable);
            out.put("m9Negative1A", m9Negative);
            out.put("m9Negative1AUsedToMutateCaptureTarget", false);
            out.put("m9NegativeCaptureSceneQueue", M9NegativeFeedback1A.noteCaptureScene(scene1h));

            out.put("valid", true);
'''
if insert_anchor not in coord:
    raise SystemExit('M9NEGATIVE1A coordinator output anchor missing')
coord = coord.replace(insert_anchor, insert_new, 1)
coord = coord.replace('capture_render_split_temporally_stabilized_diagnostic',
                      'capturemeter1a_preserved_plus_m9negative1a_completed_raw_diagnostic', 1)
write(coord_rel, coord)

# Renderer: extend existing RawTail histogram diagnostics with q25/q50 (same bins, no new RAW scan),
# record actual Camera2 exposure energy, and publish completed primary RAW into feedback store.
renderer = read(renderer_rel)
import_anchor = 'import com.particlesdevs.photoncamera.app.PhotonCamera;\n'
if 'import com.particlesdevs.photoncamera.m9.M9NegativeFeedback1A;' not in renderer:
    if import_anchor not in renderer:
        raise SystemExit('M9NEGATIVE1A renderer import anchor missing')
    renderer = renderer.replace(import_anchor,
                                import_anchor + 'import com.particlesdevs.photoncamera.m9.M9NegativeFeedback1A;\n', 1)

iso_anchor = '''            Integer isoObj = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);
            int iso = isoObj != null ? isoObj : 100;
            params.FillDynamicParameters(captureResult, captureRequest, iso);
'''
iso_new = '''            Integer isoObj = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);
            int iso = isoObj != null ? isoObj : 100;
            Long exposureObj = captureResult.get(CaptureResult.SENSOR_EXPOSURE_TIME);
            if (exposureObj == null && captureRequest != null) {
                exposureObj = captureRequest.get(CaptureRequest.SENSOR_EXPOSURE_TIME);
            }
            long exposureTimeNs = exposureObj != null ? Math.max(0L, exposureObj) : 0L;
            params.FillDynamicParameters(captureResult, captureRequest, iso);
'''
if iso_anchor not in renderer:
    raise SystemExit('M9NEGATIVE1A Camera2 exposure anchor missing')
renderer = renderer.replace(iso_anchor, iso_new, 1)

rawtail_class_old = '''    private static final class RawTail {
        double clipFraction, uq99, uq995, uq998, q, adaptiveUq, curvature, tailValue;
        boolean isolated;
    }
'''
rawtail_class_new = '''    private static final class RawTail {
        double clipFraction, uq25, uq50, uq99, uq995, uq998, q, adaptiveUq, curvature, tailValue;
        boolean isolated;
    }
'''
if rawtail_class_old not in renderer:
    raise SystemExit('M9NEGATIVE1A RawTail class anchor missing')
renderer = renderer.replace(rawtail_class_old, rawtail_class_new, 1)

empty_anchor = '''        if (total <= 0) {
            o.uq99 = o.uq995 = o.uq998 = o.adaptiveUq = o.tailValue = 1.0;
            o.q = .95;
'''
empty_new = '''        if (total <= 0) {
            o.uq25 = o.uq50 = o.uq99 = o.uq995 = o.uq998 = o.adaptiveUq = o.tailValue = 1.0;
            o.q = .95;
'''
if empty_anchor not in renderer:
    raise SystemExit('M9NEGATIVE1A RawTail empty anchor missing')
renderer = renderer.replace(empty_anchor, empty_new, 1)

quant_anchor = '''        o.uq99 = quantileBins(bins, total, .99);
        o.uq995 = quantileBins(bins, total, .995);
        o.uq998 = quantileBins(bins, total, .998);
'''
quant_new = '''        o.uq25 = quantileBins(bins, total, .25);
        o.uq50 = quantileBins(bins, total, .50);
        o.uq99 = quantileBins(bins, total, .99);
        o.uq995 = quantileBins(bins, total, .995);
        o.uq998 = quantileBins(bins, total, .998);
'''
if quant_anchor not in renderer:
    raise SystemExit('M9NEGATIVE1A RawTail quantile anchor missing')
renderer = renderer.replace(quant_anchor, quant_new, 1)

raw_diag_anchor = '''            d.put("rawHardClipFraction", tail.clipFraction);
            d.put("rawUq99", tail.uq99);
'''
raw_diag_new = '''            d.put("rawHardClipFraction", tail.clipFraction);
            d.put("rawUq25", tail.uq25);
            d.put("rawUq50", tail.uq50);
            d.put("rawUq99", tail.uq99);
'''
if raw_diag_anchor not in renderer:
    raise SystemExit('M9NEGATIVE1A renderer RAW diagnostic anchor missing')
renderer = renderer.replace(raw_diag_anchor, raw_diag_new, 1)

final_anchor = '''            diag.put("primaryPhotonFinishedImage", primaryRoute);
            diag.put("renderMeterDiagnostic", M9RenderMeterDiagnostic.evaluate(diag));
'''
final_new = '''            diag.put("primaryPhotonFinishedImage", primaryRoute);
            diag.put("captureIso", iso);
            diag.put("captureExposureTimeNs", exposureTimeNs);
            if (iso > 0 && exposureTimeNs > 0L) {
                diag.put("captureExposureEnergyIsoSeconds", iso * (exposureTimeNs / 1_000_000_000.0));
            }
            if (primaryRoute) {
                diag.put("m9NegativeCompletedRawFeedback",
                        M9NegativeFeedback1A.recordCompletedRaw(diag, iso, exposureTimeNs));
            }
            diag.put("renderMeterDiagnostic", M9RenderMeterDiagnostic.evaluate(diag));
'''
if final_anchor not in renderer:
    raise SystemExit('M9NEGATIVE1A renderer completion anchor missing')
renderer = renderer.replace(final_anchor, final_new, 1)
write(renderer_rel, renderer)

# SIDECAR1B storage-only adjustment from handoff: give active processing bursts 3 s idle before
# public bundle flush. Private staging and JPEG/DNG persistence are unchanged.
spool = read(spool_rel)
if 'private static final long BUNDLE_IDLE_MS = 1500L;' not in spool:
    raise SystemExit('M9NEGATIVE1A SIDECAR1B idle anchor missing')
spool = spool.replace('private static final long BUNDLE_IDLE_MS = 1500L;',
                      'private static final long BUNDLE_IDLE_MS = 3000L;', 1)
write(spool_rel, spool)

# Distinct diagnostic identity.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.44-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1crendermeter1csidecar1b'"
new_v = "versionName '1.45-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1crendermeter1csidecar1bm9negative1acapturemeter1b'"
if old_v not in g:
    raise SystemExit('M9NEGATIVE1A expected 1.44 versionName missing')
g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.44-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1crendermeter1csidecar1b'
new_b = '1.45-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1crendermeter1csidecar1bm9negative1acapturemeter1b'
if old_b not in b:
    raise SystemExit('M9NEGATIVE1A build identity anchor missing')
b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'M9NEGATIVE1A frozen photographic-control violation: {rel} changed')

print('M9Cam M9NEGATIVE1A/CAPTUREMETER1B applied: completed-RAW q25/q50/q99/q99.5/q99.8 + hard-clip/Camera2 energy feedback, scene-similar diagnostic recommendation only; RENDERMETER1C/SceneExposure/Camera2/motion/TC20/color/JPEG-DNG outputs frozen; SIDECAR bundle idle 3000 ms')
