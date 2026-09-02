#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sceneexposure1e-live1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1E-LIVE1A missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'SCENEEXPOSURE1E-LIVE1A freeze guard missing expected file: {rel}')
    return hashlib.sha256(p.read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
iso_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
motion_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java'

scene = read(scene_rel)
if 'm9cam.sceneexposure.v5.aeefforttonal1e' not in scene:
    raise SystemExit('SCENEEXPOSURE1E-LIVE1A requires SCENEEXPOSURE1E first')
if 'diagnostic_only_no_exposure_mutation' not in scene:
    raise SystemExit('SCENEEXPOSURE1E-LIVE1A expected diagnostic-only 1E mode marker missing')

# Freeze the accepted renderer and motion policy. This overlay is exposure handoff only.
frozen_before = {
    renderer_rel: sha256(renderer_rel),
    motion_rel: sha256(motion_rel),
}

# Keep the exact 1E pressure math, but identify this branch as a live signed-exposure test.
scene = scene.replace(
    'out.put("mode", "diagnostic_only_no_exposure_mutation");',
    'out.put("mode", "live_test_signed_exposure_enabled");\n'
    '            out.put("liveTestTargetPolicy", "scene1e_total_signed_ev_replaces_fb1_total");\n'
    '            out.put("liveTestSignedLimitEv", 1.25);',
    1)

# Clear the live-application ledger whenever a new real step-0 diagnostic is evaluated.
eval_anchor = '''        if (step != 0) return;

        JSONObject out = new JSONObject();
'''
eval_insert = '''        if (step != 0) return;
        lastLiveApplication = new JSONObject();

        JSONObject out = new JSONObject();
'''
if eval_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E-LIVE1A evaluateStep0 anchor missing')
scene = scene.replace(eval_anchor, eval_insert, 1)

# Add a separate live ledger and accessors without touching any 1E scoring constants/math.
last_anchor = '    private static JSONObject last = new JSONObject();\n'
last_insert = '''    private static JSONObject last = new JSONObject();
    private static JSONObject lastLiveApplication = new JSONObject();
'''
if last_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E-LIVE1A last-result anchor missing')
scene = scene.replace(last_anchor, last_insert, 1)

snapshot_anchor = '''    public static synchronized JSONObject snapshotJson() {
        try {
            return new JSONObject(last.toString());
        } catch (Exception e) {
            return new JSONObject();
        }
    }
'''
snapshot_insert = '''    public static synchronized boolean hasValidRecommendation() {
        double ev = last.optDouble("recommendedSignedEv", Double.NaN);
        return last.optBoolean("valid", false) && finite(ev);
    }

    public static synchronized double getRecommendedSignedEv() {
        if (!hasValidRecommendation()) return 0.0;
        return clamp(last.optDouble("recommendedSignedEv", 0.0),
                -MAX_NEGATIVE_EV, MAX_POSITIVE_EV);
    }

    public static synchronized String getRecommendationReason() {
        return last.optString("reason", "scene1e_no_reason");
    }

    public static synchronized double getRecommendationConfidence() {
        return clamp01(last.optDouble("recommendationConfidence", 0.0));
    }

    public static synchronized void recordLiveApplication(
            boolean eligible,
            String eligibilityReason,
            double legacyFb1AppliedEv,
            double requestedScene1eEv,
            double appliedTotalScene1eEv,
            double appliedDeltaVsFb1Ev,
            long preDeltaExposureNs,
            int preDeltaIsoNormalized,
            long postDeltaExposureNs,
            int postDeltaIsoNormalized) {
        JSONObject o = new JSONObject();
        try {
            o.put("schema", "m9cam.sceneexposure.live1a");
            o.put("enabled", true);
            o.put("policy", "scene1e_total_signed_ev_replaces_fb1_total");
            o.put("eligible", eligible);
            o.put("eligibilityReason", eligibilityReason);
            o.put("recommendationValid", hasValidRecommendation());
            o.put("scene1eReason", getRecommendationReason());
            o.put("scene1eConfidence", getRecommendationConfidence());
            o.put("legacyFb1AppliedEv", legacyFb1AppliedEv);
            o.put("requestedScene1eSignedEv", requestedScene1eEv);
            o.put("appliedTotalSignedEv", appliedTotalScene1eEv);
            o.put("appliedDeltaVsFb1Ev", appliedDeltaVsFb1Ev);
            o.put("preDeltaExposureNs", preDeltaExposureNs);
            o.put("preDeltaIsoNormalized", preDeltaIsoNormalized);
            o.put("postDeltaExposureNs", postDeltaExposureNs);
            o.put("postDeltaIsoNormalized", postDeltaIsoNormalized);
            double preEnergy = (double) preDeltaExposureNs * (double) preDeltaIsoNormalized;
            double postEnergy = (double) postDeltaExposureNs * (double) postDeltaIsoNormalized;
            double ratio = preEnergy > 0.0 ? postEnergy / preEnergy : 1.0;
            o.put("actualDeltaEnergyRatio", ratio);
            o.put("actualDeltaEnergyEv", ratio > 0.0
                    ? Math.log(ratio) / Math.log(2.0) : 0.0);
        } catch (Exception ignored) {
        }
        lastLiveApplication = o;
    }

    public static synchronized JSONObject snapshotJson() {
        try {
            JSONObject out = new JSONObject(last.toString());
            out.put("liveApplication", new JSONObject(lastLiveApplication.toString()));
            return out;
        } catch (Exception e) {
            return new JSONObject();
        }
    }
'''
if snapshot_anchor not in scene:
    raise SystemExit('SCENEEXPOSURE1E-LIVE1A snapshot/accessor anchor missing')
scene = scene.replace(snapshot_anchor, snapshot_insert, 1)
write(scene_rel, scene)

# Replace the diagnostic-only call with a live delta handoff. Existing FB1 still runs
# first and remains the fallback. 1E is interpreted as the TOTAL desired signed EV;
# only the delta between 1E and the already-applied FB1 correction is added here.
iso = read(iso_rel)
old_block = '''            if (M9Config.isCaptureTest() && step == 0) {
                M9SceneExposureDiagnostic.evaluateStep0(
                        step, m9PreviewEnergyIsoSeconds, m9FeedbackRotationDegrees);
            }
'''
new_block = '''            if (M9Config.isCaptureTest() && step == 0) {
                M9SceneExposureDiagnostic.evaluateStep0(
                        step, m9PreviewEnergyIsoSeconds, m9FeedbackRotationDegrees);

                boolean m9SceneRecommendationValid =
                        M9SceneExposureDiagnostic.hasValidRecommendation();
                double m9SceneRequestedEv =
                        M9SceneExposureDiagnostic.getRecommendedSignedEv();
                double m9SceneAppliedTotalEv = m9Feedback.appliedEv;
                double m9SceneDeltaEv = 0.0;
                String m9SceneLiveEligibilityReason;

                long m9ScenePreDeltaExposureNs = pair.exposure;
                int m9ScenePreDeltaIsoNormalized = pair.iso;

                if (!m9FeedbackEligible) {
                    m9SceneLiveEligibilityReason =
                            "scene1e_live_bypassed_nonzero_ev_manual_or_tripod";
                } else if (!m9SceneRecommendationValid) {
                    m9SceneLiveEligibilityReason =
                            "scene1e_live_invalid_fallback_to_fb1";
                } else {
                    // Signed 1E is the TOTAL target relative to the original Photon
                    // metered energy. Existing FB1 has already changed pair, therefore
                    // apply only the residual delta. Clamp again at the live handoff.
                    m9SceneAppliedTotalEv = Math.max(-1.25,
                            Math.min(1.25, m9SceneRequestedEv));
                    m9SceneDeltaEv = m9SceneAppliedTotalEv - m9Feedback.appliedEv;
                    if (Math.abs(m9SceneDeltaEv) > 1.0e-9) {
                        double m9SceneDeltaFactor = Math.pow(2.0, m9SceneDeltaEv);
                        pair.ExpoCompensateLower(1.0 / m9SceneDeltaFactor);
                    }
                    m9SceneLiveEligibilityReason = "scene1e_live_applied_total_signed_ev";
                }

                M9SceneExposureDiagnostic.recordLiveApplication(
                        m9FeedbackEligible && m9SceneRecommendationValid,
                        m9SceneLiveEligibilityReason,
                        m9Feedback.appliedEv,
                        m9SceneRequestedEv,
                        m9SceneAppliedTotalEv,
                        m9SceneDeltaEv,
                        m9ScenePreDeltaExposureNs,
                        m9ScenePreDeltaIsoNormalized,
                        pair.exposure,
                        pair.iso);
            }
'''
if old_block not in iso:
    raise SystemExit('SCENEEXPOSURE1E-LIVE1A diagnostic call anchor missing from IsoExpoSelector')
iso = iso.replace(old_block, new_block, 1)
write(iso_rel, iso)

# Distinct test-build identity.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.38-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1e'"
new_v = "versionName '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1elive1a'"
if new_v not in g:
    if old_v not in g:
        raise SystemExit('SCENEEXPOSURE1E-LIVE1A expected 1E versionName missing')
    g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.38-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1e'
new_b = '1.39-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1elive1a'
if new_b not in b:
    if old_b not in b:
        raise SystemExit('SCENEEXPOSURE1E-LIVE1A build identity anchor missing')
    b = b.replace(old_b, new_b, 1)
write(back_rel, b)

# Assert exposure-only scope.
for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(
            f'SCENEEXPOSURE1E-LIVE1A quality freeze violated: {rel} changed '
            f'{before} -> {after}')

print('M9Cam SCENEEXPOSURE1E-LIVE1A applied')
print(' - exact SCENEEXPOSURE1E scoring math preserved')
print(' - 1E signed recommendation is now the TOTAL live target for auto PHOTO step0')
print(' - existing FB1 remains first-stage fallback; only delta-to-1E is applied')
print(' - manual EV/ISO, tripod, invalid 1E, and preflight behavior remain protected')
print(' - signed live range is bounded to -1.25..+1.25 EV')
print(' - renderer and frozen motion policy SHA-256 unchanged')
