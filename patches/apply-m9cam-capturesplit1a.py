#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-capturesplit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CAPTURESPLIT1A missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
scene = read(scene_rel)
renderer = read(renderer_rel)

if 'm9cam.sceneexposure.v8.renderaware1h' not in scene:
    raise SystemExit('CAPTURESPLIT1A requires SCENEEXPOSURE1H first')
if 'diagnostic_only_no_exposure_mutation' not in scene:
    raise SystemExit('CAPTURESPLIT1A refuses a live/mutating scene-exposure baseline')
if 'm9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1' not in renderer:
    raise SystemExit('CAPTURESPLIT1A renderer baseline marker missing')

frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

coordinator_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
coordinator = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

import java.util.Arrays;

/**
 * CAPTUREMETER1A + TEMPORAL1A.
 *
 * Diagnostic-only coordinator that separates sensor-capture adequacy from the
 * SCENEEXPOSURE1H render-aware preview proxy. It never mutates Camera2, Photon,
 * FB1, shutter, ISO, motion policy, TC20 gain, or renderer pixels.
 *
 * The history is intentionally capture-step history for this first build. It
 * stabilizes burst-to-burst recommendations while leaving continuous-preview
 * temporal integration as a later isolated experiment.
 */
public final class M9CaptureRenderExposureCoordinator {
    public static final String SCHEMA = "m9cam.exposuresplit.v1.capturemeter1a.temporal1a";

    private static final int HISTORY = 5;
    private static final double DEADBAND_EV = 0.08;
    private static final double NORMAL_NEG_LIMIT_EV = -0.25;
    private static final double NORMAL_POS_LIMIT_EV = 0.40;
    private static final double STARVATION_POS_LIMIT_EV = 0.75;
    private static final double EXCEPTIONAL_POS_LIMIT_EV = 1.00;
    private static final double MAX_SLEW_EV_PER_CAPTURE = 0.35;

    private static final Sample[] samples = new Sample[HISTORY];
    private static int sampleCount = 0;
    private static int sampleWrite = 0;
    private static double lastStableEv = 0.0;
    private static boolean haveLastStable = false;

    private M9CaptureRenderExposureCoordinator() {}

    public static synchronized JSONObject evaluate(JSONObject scene1h) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("captureMeterRole", "raw_photon_headroom_motion_adequacy_not_jpeg_brightness");
            out.put("renderMeterRole", "separate_downstream_tonal_placement");
            out.put("temporalScope", "capture_step_history_first_build");

            if (scene1h == null || !scene1h.optBoolean("valid", false)) {
                out.put("valid", false);
                out.put("reason", "sceneexposure1h_invalid");
                out.put("stabilizedCaptureTargetEv", 0.0);
                return out;
            }

            JSONObject inputs = scene1h.optJSONObject("inputs");
            JSONObject positive = scene1h.optJSONObject("positiveBodyPressure");
            JSONObject negative = scene1h.optJSONObject("negativeHighlightPressure");
            if (inputs == null || positive == null || negative == null) {
                out.put("valid", false);
                out.put("reason", "missing_sceneexposure1h_components");
                out.put("stabilizedCaptureTargetEv", 0.0);
                return out;
            }

            double median = inputs.optDouble("globalMedian", Double.NaN);
            double center = inputs.optDouble("centerMedian", Double.NaN);
            double q99 = inputs.optDouble("globalQ99", Double.NaN);
            double positiveEv = positive.optDouble("sceneexposure1hPositiveCandidate",
                    scene1h.optDouble("positiveEvCandidate", 0.0));
            double captureNegativeEv = negative.optDouble("sceneexposure1cNegativeCandidate", 0.0);
            double renderProxyEv = negative.optDouble("renderAwareNegativeCandidate", 0.0);
            double positivePressure = positive.optDouble("positivePressure", 0.0);
            double starvation = positive.optDouble("spatialQualificationStarvationPressure",
                    positive.optDouble("luma24BacklightPressure", 0.0));
            double highlightSupport = positive.optDouble("absoluteHighlightSupportEvidence", 0.0);

            if (!finite(median) || !finite(center) || !finite(q99)
                    || !finite(positiveEv) || !finite(captureNegativeEv)) {
                out.put("valid", false);
                out.put("reason", "non_finite_capture_split_input");
                out.put("stabilizedCaptureTargetEv", 0.0);
                return out;
            }

            double rawCaptureCandidate = clamp(positiveEv + captureNegativeEv, -1.25, 1.25);
            if (Math.abs(rawCaptureCandidate) < DEADBAND_EV) rawCaptureCandidate = 0.0;

            double starvationEvidence = clamp01(smoothstep(starvation, 0.55, 0.85));
            double absoluteCenterDarkEvidence = 1.0 - smoothstep(center, 52.0, 64.0);
            double exceptionalStarvationEvidence = clamp01(starvationEvidence
                    * absoluteCenterDarkEvidence
                    * smoothstep(highlightSupport, 0.35, 0.75));

            double positiveLimit = NORMAL_POS_LIMIT_EV;
            if (starvationEvidence >= 0.55) positiveLimit = STARVATION_POS_LIMIT_EV;
            if (exceptionalStarvationEvidence >= 0.60) positiveLimit = EXCEPTIONAL_POS_LIMIT_EV;
            double boundedCaptureCandidate = clamp(rawCaptureCandidate,
                    NORMAL_NEG_LIMIT_EV, positiveLimit);

            double captureNegativePressure = clamp01(Math.abs(captureNegativeEv) / 1.25);
            double captureConfidence = clamp01(Math.max(positivePressure,
                    Math.max(captureNegativePressure, 0.85 * starvationEvidence)));

            Sample previous = newest();
            double sceneDistance = previous == null ? 0.0 : sceneDistance(
                    previous, median, center, q99, starvation);
            boolean sceneChanged = previous != null && sceneDistance >= 1.0;
            if (sceneChanged) {
                clearHistory();
            }

            add(new Sample(boundedCaptureCandidate, median, center, q99, starvation));
            double temporalMedian = medianEv();
            int agreementCount = agreementCount(temporalMedian, 0.20);

            double proposedStable;
            String temporalReason;
            if (!haveLastStable || sceneChanged) {
                proposedStable = clamp(boundedCaptureCandidate,
                        NORMAL_NEG_LIMIT_EV, NORMAL_POS_LIMIT_EV);
                temporalReason = sceneChanged
                        ? "scene_change_reset_first_capture_normal_envelope"
                        : "first_capture_normal_envelope";
            } else {
                double delta = temporalMedian - lastStableEv;
                double absDelta = Math.abs(delta);
                boolean gatePass;
                if (absDelta <= 0.20) {
                    gatePass = true;
                    temporalReason = "small_change_immediate";
                } else if (absDelta <= 0.40) {
                    gatePass = agreementCount >= 2;
                    temporalReason = gatePass ? "medium_change_two_capture_agreement"
                            : "medium_change_waiting_for_agreement";
                } else if (absDelta <= 0.70) {
                    gatePass = agreementCount >= 3;
                    temporalReason = gatePass ? "large_change_three_capture_agreement"
                            : "large_change_waiting_for_agreement";
                } else {
                    gatePass = agreementCount >= 3 && exceptionalStarvationEvidence >= 0.60;
                    temporalReason = gatePass ? "exceptional_starvation_large_change_confirmed"
                            : "very_large_change_waiting_for_exceptional_starvation_confirmation";
                }

                double desired = gatePass ? temporalMedian
                        : lastStableEv + clamp(delta, -0.20, 0.20);
                proposedStable = lastStableEv + clamp(desired - lastStableEv,
                        -MAX_SLEW_EV_PER_CAPTURE, MAX_SLEW_EV_PER_CAPTURE);
            }

            proposedStable = clamp(proposedStable, NORMAL_NEG_LIMIT_EV, positiveLimit);
            if (Math.abs(proposedStable) < DEADBAND_EV) proposedStable = 0.0;
            lastStableEv = proposedStable;
            haveLastStable = true;

            JSONObject captureMeter = new JSONObject();
            captureMeter.put("scene1hPositiveEv", positiveEv);
            captureMeter.put("captureNegativeEv", captureNegativeEv);
            captureMeter.put("scene1hRenderProxyEvExcludedFromCapture", renderProxyEv);
            captureMeter.put("rawCaptureCandidateEv", rawCaptureCandidate);
            captureMeter.put("boundedCaptureCandidateEv", boundedCaptureCandidate);
            captureMeter.put("normalNegativeLimitEv", NORMAL_NEG_LIMIT_EV);
            captureMeter.put("normalPositiveLimitEv", NORMAL_POS_LIMIT_EV);
            captureMeter.put("activePositiveLimitEv", positiveLimit);
            captureMeter.put("starvationEvidence", starvationEvidence);
            captureMeter.put("exceptionalStarvationEvidence", exceptionalStarvationEvidence);
            captureMeter.put("captureConfidence", captureConfidence);
            out.put("captureMeter", captureMeter);

            JSONObject temporal = new JSONObject();
            temporal.put("historyCount", sampleCount);
            temporal.put("temporalMedianEv", temporalMedian);
            temporal.put("agreementCountWithin0p20Ev", agreementCount);
            temporal.put("sceneDistance", sceneDistance);
            temporal.put("sceneChanged", sceneChanged);
            temporal.put("maxSlewEvPerCapture", MAX_SLEW_EV_PER_CAPTURE);
            temporal.put("reason", temporalReason);
            out.put("temporal", temporal);

            JSONObject renderSplit = new JSONObject();
            renderSplit.put("scene1hRenderAwarePreviewProxyEv", renderProxyEv);
            renderSplit.put("usedForCaptureTarget", false);
            renderSplit.put("reason", "jpeg_tonal_placement_must_be_evaluated_separately_from_raw_capture");
            out.put("renderSplit", renderSplit);

            out.put("valid", true);
            out.put("stabilizedCaptureTargetEv", proposedStable);
            out.put("direction", proposedStable > 0.0 ? "increase"
                    : proposedStable < 0.0 ? "decrease" : "neutral");
            out.put("reason", "capture_render_split_temporally_stabilized_diagnostic");
        } catch (Exception ignored) {
            try {
                out.put("valid", false);
                out.put("liveEligible", false);
                out.put("stabilizedCaptureTargetEv", 0.0);
                out.put("reason", "capture_render_split_exception");
            } catch (Exception ignoredAgain) {}
        }
        return out;
    }

    private static void add(Sample s) {
        samples[sampleWrite] = s;
        sampleWrite = (sampleWrite + 1) % HISTORY;
        if (sampleCount < HISTORY) sampleCount++;
    }

    private static Sample newest() {
        if (sampleCount == 0) return null;
        int idx = (sampleWrite - 1 + HISTORY) % HISTORY;
        return samples[idx];
    }

    private static void clearHistory() {
        Arrays.fill(samples, null);
        sampleCount = 0;
        sampleWrite = 0;
        haveLastStable = false;
        lastStableEv = 0.0;
    }

    private static double medianEv() {
        double[] values = new double[sampleCount];
        int n = 0;
        for (int i = 0; i < HISTORY; i++) {
            Sample s = samples[i];
            if (s != null) values[n++] = s.ev;
        }
        if (n == 0) return 0.0;
        values = Arrays.copyOf(values, n);
        Arrays.sort(values);
        return (n & 1) == 1 ? values[n / 2] : 0.5 * (values[n / 2 - 1] + values[n / 2]);
    }

    private static int agreementCount(double centerEv, double tolerance) {
        int count = 0;
        for (int i = 0; i < HISTORY; i++) {
            Sample s = samples[i];
            if (s != null && Math.abs(s.ev - centerEv) <= tolerance) count++;
        }
        return count;
    }

    private static double sceneDistance(Sample p, double median, double center,
                                        double q99, double starvation) {
        return Math.max(Math.abs(median - p.median) / 40.0,
                Math.max(Math.abs(center - p.center) / 40.0,
                Math.max(Math.abs(q99 - p.q99) / 50.0,
                        Math.abs(starvation - p.starvation) / 0.50)));
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

    private static final class Sample {
        final double ev;
        final double median;
        final double center;
        final double q99;
        final double starvation;

        Sample(double ev, double median, double center, double q99, double starvation) {
            this.ev = ev;
            this.median = median;
            this.center = center;
            this.q99 = q99;
            this.starvation = starvation;
        }
    }
}
'''
write(coordinator_rel, coordinator)

render_meter_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java'
render_meter = r'''package com.particlesdevs.photoncamera.m9.render;

import org.json.JSONObject;

/**
 * RENDERMETER1A: observational-only downstream exposure diagnostics.
 *
 * It consumes statistics the frozen renderer already computes. It does not read
 * or modify pixels and does not change TC20 gain. A live correction remains
 * deliberately disabled until rendered-image luminance placement is measured
 * directly and validated against paired DNG/JPEG scenes.
 */
public final class M9RenderMeterDiagnostic {
    public static final String SCHEMA = "m9cam.rendermeter.v1.observational1a";

    private M9RenderMeterDiagnostic() {}

    public static JSONObject evaluate(JSONObject renderer) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_renderer_mutation");
            out.put("liveEligible", false);
            out.put("correctionAppliedEv", 0.0);
            out.put("correctionCandidateEv", 0.0);
            out.put("state", "awaiting_direct_rendered_luma_measurement");

            double gain = renderer != null ? renderer.optDouble("gain", Double.NaN) : Double.NaN;
            double baseGain = renderer != null ? renderer.optDouble("baseMedianGain", Double.NaN) : Double.NaN;
            double guardGain = renderer != null ? renderer.optDouble("tc20GuardGain", Double.NaN) : Double.NaN;
            double rawQ99 = renderer != null ? renderer.optDouble("rawUq99", Double.NaN) : Double.NaN;
            double rawClip = renderer != null ? renderer.optDouble("rawHardClipFraction", Double.NaN) : Double.NaN;
            double rgbClip = renderer != null ? renderer.optDouble("rgb8ClipFraction", Double.NaN) : Double.NaN;
            double nearWhite = renderer != null ? renderer.optDouble("renderNearWhiteFraction", Double.NaN) : Double.NaN;

            JSONObject observations = new JSONObject();
            if (finite(gain)) {
                observations.put("tc20Gain", gain);
                observations.put("tc20GainEv", log2(Math.max(gain, 1e-12)));
            }
            if (finite(baseGain)) observations.put("baseMedianGain", baseGain);
            if (finite(guardGain)) observations.put("tc20GuardGain", guardGain);
            if (finite(rawQ99)) observations.put("rawUq99", rawQ99);
            if (finite(rawClip)) observations.put("rawHardClipFraction", rawClip);
            if (finite(rgbClip)) observations.put("renderRgbChannelClipFraction", rgbClip);
            if (finite(nearWhite)) observations.put("renderNearWhiteFraction", nearWhite);
            out.put("observations", observations);

            out.put("captureRenderDecouplingEvidence",
                    "tc20_gain_and_raw_placement_logged_together_without_reinterpreting_jpeg_brightness_as_capture_ev");
            out.put("nextRequiredSignal",
                    "direct_render_global_center_subject_luma_statistics_before_nonzero_render_correction");
            out.put("valid", finite(gain) || finite(rawQ99) || finite(nearWhite));
        } catch (Exception ignored) {
            try {
                out.put("valid", false);
                out.put("liveEligible", false);
                out.put("correctionAppliedEv", 0.0);
                out.put("reason", "render_meter_diagnostic_exception");
            } catch (Exception ignoredAgain) {}
        }
        return out;
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }

    private static double log2(double x) {
        return Math.log(x) / Math.log(2.0);
    }
}
'''
write(render_meter_rel, render_meter)

scene_before = scene
scene_anchor = '''            out.put("direction", signedEv > 0.0 ? "increase" : signedEv < 0.0 ? "decrease" : "neutral");
'''
scene_call = '            out.put("captureRenderSplit", M9CaptureRenderExposureCoordinator.evaluate(out));\n'
if scene_anchor not in scene:
    raise SystemExit('CAPTURESPLIT1A scene output anchor missing')
scene = scene.replace(scene_anchor, scene_anchor + scene_call, 1)
if scene.replace(scene_call, '', 1) != scene_before:
    raise SystemExit('CAPTURESPLIT1A scene structural guard failed')
write(scene_rel, scene)

renderer_before = renderer
renderer_anchor = '''            diag.put("primaryPhotonFinishedImage", primaryRoute);
            diag.put("outputRole", primaryRoute ? "primary_photon_jpeg" : "legacy_m9_sidecar");
'''
renderer_insert = '''            diag.put("primaryPhotonFinishedImage", primaryRoute);
            diag.put("renderMeterDiagnostic", M9RenderMeterDiagnostic.evaluate(diag));
            diag.put("outputRole", primaryRoute ? "primary_photon_jpeg" : "legacy_m9_sidecar");
'''
if renderer_anchor not in renderer:
    raise SystemExit('CAPTURESPLIT1A renderer diagnostic anchor missing')
renderer = renderer.replace(renderer_anchor, renderer_insert, 1)
renderer_call = '            diag.put("renderMeterDiagnostic", M9RenderMeterDiagnostic.evaluate(diag));\n'
if renderer.replace(renderer_call, '', 1) != renderer_before:
    raise SystemExit('CAPTURESPLIT1A renderer structural guard failed: non-diagnostic renderer source changed')
write(renderer_rel, renderer)

gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.41-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1h'"
new_v = "versionName '1.42-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1a'"
if old_v not in g:
    raise SystemExit('CAPTURESPLIT1A expected 1H versionName missing')
g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.41-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1h'
new_b = '1.42-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1a'
if old_b not in b:
    raise SystemExit('CAPTURESPLIT1A build identity anchor missing')
b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'CAPTURESPLIT1A quality-freeze violation: {rel} changed')

print('M9Cam CAPTURESPLIT1A applied: CAPTUREMETER1A + TEMPORAL1A + observational RENDERMETER1A; SCENEEXPOSURE1H math, Camera2/FB1/motion policy, native colour math and renderer pixels remain unchanged')
