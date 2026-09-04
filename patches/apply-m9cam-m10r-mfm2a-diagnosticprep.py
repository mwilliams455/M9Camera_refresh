#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m10r-mfm2a-diagnosticprep.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

mfm_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9M10rMfmTest1A.java'
iso_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
gradle_rel = 'app/build.gradle'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('M10RMFM2A missing expected file: ' + rel)
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

m = read(mfm_rel)
if 'm9cam.m10r.mfmtest.v1a' not in m:
    raise SystemExit('M10RMFM2A requires M10RMFMTEST1A baseline')
if 'Diagnostic telemetry must never affect capture or rendering.' not in m:
    raise SystemExit('M10RMFM2A requires JSONARRAY1A compile fix first')

frozen_rels = [
    renderer_rel,
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintNearest1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintTie1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CurrentFrameCeiling1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

# Schema/contract marker only; class name remains stable so downstream metadata anchors do not move.
m = m.replace('m9cam.m10r.mfmtest.v1a', 'm9cam.m10r.mfmtest.v2a', 1)

old_state = '    private static JSONObject lastLive = new JSONObject();\n'
new_state = '''    private static JSONObject lastEvaluation = new JSONObject();
    private static JSONObject lastCaptureDecision = new JSONObject();
'''
if old_state not in m:
    raise SystemExit('M10RMFM2A state anchor missing')
m = m.replace(old_state, new_state, 1)

old_sig = '''    public static synchronized M9BacklightDiagnostic.LiveFeedbackDecision evaluateLiveFeedback(
            double previewEnergyIsoSeconds, int cameraRotationDegrees, boolean eligible,
            String eligibilityReason) {
'''
new_sig = '''    public static synchronized M9BacklightDiagnostic.LiveFeedbackDecision evaluateLiveFeedback(
            double previewEnergyIsoSeconds, int cameraRotationDegrees, boolean eligible,
            String eligibilityReason, boolean freezeCaptureDecision) {
'''
if old_sig not in m:
    raise SystemExit('M10RMFM2A method signature anchor missing')
m = m.replace(old_sig, new_sig, 1)

old_luma = '''            JSONObject luma = subject.optJSONObject("previewLuma");
            long frames = luma != null ? luma.optLong("framesAnalyzed", 0L) : 0L;
            JSONObject grid = luma != null ? luma.optJSONObject("m10rAeGrid16x22") : null;
'''
new_luma = '''            JSONObject luma = subject.optJSONObject("previewLuma");
            long frames = luma != null ? luma.optLong("framesAnalyzed", 0L) : 0L;
            JSONObject grid = luma != null ? luma.optJSONObject("m10rAeGrid16x22") : null;
            JSONObject global = luma != null ? luma.optJSONObject("global") : null;
            JSONObject center50 = luma != null ? luma.optJSONObject("center50") : null;
            double previewGlobalMedianY = global != null
                    ? global.optDouble("median", Double.NaN) : Double.NaN;
            double previewGlobalQ95Y = global != null
                    ? global.optDouble("q95", Double.NaN) : Double.NaN;
            double previewGlobalQ99Y = global != null
                    ? global.optDouble("q99", Double.NaN) : Double.NaN;
            double previewBrightFractionGE224 = global != null
                    ? global.optDouble("brightFractionGE224", Double.NaN) : Double.NaN;
            double previewBrightFractionGE240 = global != null
                    ? global.optDouble("brightFractionGE240", Double.NaN) : Double.NaN;
            double previewDarkFractionLE64 = global != null
                    ? global.optDouble("darkFractionLE64", Double.NaN) : Double.NaN;
            double previewCenter50MedianY = center50 != null
                    ? center50.optDouble("median", Double.NaN) : Double.NaN;
'''
if old_luma not in m:
    raise SystemExit('M10RMFM2A preview-luma anchor missing')
m = m.replace(old_luma, new_luma, 1)

old_pregrid = '''            out.put("legacyLuma24WouldApply", legacy.wouldApply);
            out.put("legacyLuma24RecommendedEv", legacy.recommendedEv);

            if (frames < 3L || grid == null || !grid.optBoolean("valid", false)) {
'''
new_pregrid = '''            out.put("legacyLuma24WouldApply", legacy.wouldApply);
            out.put("legacyLuma24RecommendedEv", legacy.recommendedEv);
            out.put("previewGlobalMedianY", previewGlobalMedianY);
            out.put("previewCenter50MedianY", previewCenter50MedianY);
            out.put("previewGlobalQ95Y", previewGlobalQ95Y);
            out.put("previewGlobalQ99Y", previewGlobalQ99Y);
            out.put("previewBrightFractionGE224", previewBrightFractionGE224);
            out.put("previewBrightFractionGE240", previewBrightFractionGE240);
            out.put("previewDarkFractionLE64", previewDarkFractionLE64);
            out.put("saturatedPreviewPositiveVetoThresholdQ95", 255.0);

            if (frames < 3L || grid == null || !grid.optBoolean("valid", false)) {
'''
if old_pregrid not in m:
    raise SystemExit('M10RMFM2A pre-grid telemetry anchor missing')
m = m.replace(old_pregrid, new_pregrid, 1)

old_body = '''                    double edge16Y = regionEdgeMean(regions, true);
                    double inner8Y = regionEdgeMean(regions, false);

                    double integralVsMedianEv = log2(safe(integralY) / safe(regionalMedianY));
'''
new_body = '''                    double edge16Y = regionEdgeMean(regions, true);
                    double inner8Y = regionEdgeMean(regions, false);
                    // MFM2A absolute body-level telemetry. These are measurements only;
                    // they do not change the positive magnitude in this preparation branch.
                    double bodyMinMedianCenterLowerY = Math.min(regionalMedianY,
                            Math.min(center8Y, lower12Y));
                    double bodyMeanMedianCenterLowerY = (regionalMedianY + center8Y + lower12Y) / 3.0;
                    double bodyCenter50VsRegionalMedianEv = finite(previewCenter50MedianY)
                            ? log2(safe(previewCenter50MedianY) / safe(regionalMedianY))
                            : Double.NaN;

                    double integralVsMedianEv = log2(safe(integralY) / safe(regionalMedianY));
'''
if old_body not in m:
    raise SystemExit('M10RMFM2A body-level anchor missing')
m = m.replace(old_body, new_body, 1)

old_decision = '''                    if (!eligible) {
                        appliedEv = 0.0;
                        reason = eligibilityReason != null && !eligibilityReason.isEmpty()
                                ? eligibilityReason : "m10r_mfmtest_not_eligible";
                    } else if (!valid) {
                        appliedEv = 0.0;
                        reason = "m10r_mfmtest_invalid";
                    } else if (!wouldApply) {
                        appliedEv = 0.0;
                        reason = "m10r_mfmtest_neutral_deadband";
                    } else {
                        appliedEv = recommendedEv;
                        reason = recommendedEv > 0.0
                                ? "m10r_multifield_positive_capture_assist"
                                : "m10r_multifield_negative_capture_moderation";
                    }
'''
new_decision = '''                    boolean saturatedPreviewPositiveVeto = valid
                            && recommendedEv > 0.0
                            && finite(previewGlobalQ95Y)
                            && previewGlobalQ95Y >= 255.0;
                    if (!eligible) {
                        appliedEv = 0.0;
                        reason = eligibilityReason != null && !eligibilityReason.isEmpty()
                                ? eligibilityReason : "m10r_mfmtest_not_eligible";
                    } else if (!valid) {
                        appliedEv = 0.0;
                        reason = "m10r_mfmtest_invalid";
                    } else if (!wouldApply) {
                        appliedEv = 0.0;
                        reason = "m10r_mfmtest_neutral_deadband";
                    } else if (saturatedPreviewPositiveVeto) {
                        appliedEv = 0.0;
                        reason = "m10r_mfm2a_saturated_preview_positive_veto";
                    } else {
                        appliedEv = recommendedEv;
                        reason = recommendedEv > 0.0
                                ? "m10r_multifield_positive_capture_assist"
                                : "m10r_multifield_negative_capture_moderation";
                    }
                    out.put("saturatedPreviewPositiveVeto", saturatedPreviewPositiveVeto);
'''
if old_decision not in m:
    raise SystemExit('M10RMFM2A decision anchor missing')
m = m.replace(old_decision, new_decision, 1)

old_metrics = '''                    out.put("edge16Y", edge16Y);
                    out.put("inner8Y", inner8Y);
                    out.put("integralVsMedianEv", integralVsMedianEv);
'''
new_metrics = '''                    out.put("edge16Y", edge16Y);
                    out.put("inner8Y", inner8Y);
                    out.put("bodyMinMedianCenterLowerY", bodyMinMedianCenterLowerY);
                    out.put("bodyMeanMedianCenterLowerY", bodyMeanMedianCenterLowerY);
                    out.put("bodyCenter50VsRegionalMedianEv", bodyCenter50VsRegionalMedianEv);
                    out.put("absoluteBodyLevelFeedsMagnitude", false);
                    out.put("integralVsMedianEv", integralVsMedianEv);
'''
if old_metrics not in m:
    raise SystemExit('M10RMFM2A metrics anchor missing')
m = m.replace(old_metrics, new_metrics, 1)

old_tail = '''        lastLive = cloneJson(out);
        return new M9BacklightDiagnostic.LiveFeedbackDecision(
                valid, wouldApply, recommendedEv, appliedEv, reason, cloneJson(out));
    }

    public static synchronized JSONObject snapshotJson() {
        return cloneJson(lastLive);
    }
'''
new_tail = '''        try {
            out.put("captureDecisionFreezeRequested", freezeCaptureDecision);
            out.put("captureDecisionFrozen", freezeCaptureDecision);
            out.put("captureFreezeRule", "IsoExpoSelector_step_equals_0");
        } catch (Exception ignored) {}
        lastEvaluation = cloneJson(out);
        if (freezeCaptureDecision) {
            lastCaptureDecision = cloneJson(out);
        }
        return new M9BacklightDiagnostic.LiveFeedbackDecision(
                valid, wouldApply, recommendedEv, appliedEv, reason, cloneJson(out));
    }

    public static synchronized JSONObject snapshotJson() {
        return cloneJson(lastCaptureDecision);
    }

    public static synchronized JSONObject evaluationSnapshotJson() {
        return cloneJson(lastEvaluation);
    }
'''
if old_tail not in m:
    raise SystemExit('M10RMFM2A capture-freeze anchor missing')
m = m.replace(old_tail, new_tail, 1)

m = m.replace('"mode", "live_bounded_m10r_architecture_proxy"',
              '"mode", "live_bounded_m10r_architecture_proxy_mfm2a_safetyprep"', 1)
contract_anchor = '            o.put("tc20IntentNormalization", "unchanged_in_this_test_build");\n'
contract_insert = contract_anchor + '''            o.put("captureDecisionSnapshot", "frozen_on_IsoExpoSelector_step0_only");
            o.put("absoluteBodyLevelRole", "telemetry_only_not_positive_magnitude");
            o.put("highlightRiskRole", "telemetry_plus_q95_255_positive_veto_only");
            o.put("positiveMagnitude", "unchanged_from_M10RMFMTEST1A");
            o.put("negativeMagnitude", "unchanged_not_forced");
'''
if contract_anchor not in m:
    raise SystemExit('M10RMFM2A contract anchor missing')
m = m.replace(contract_anchor, contract_insert, 1)
write(mfm_rel, m)

# Pass an explicit step-0 freeze bit. This fixes the 16/27 field-side snapshot overwrite
# without guessing whether a later evaluation is preflight from eligibility reason strings.
i = read(iso_rel)
old_call = '''                    M9M10rMfmTest1A.evaluateLiveFeedback(
                            m9PreviewEnergyIsoSeconds,
                            m9FeedbackRotationDegrees,
                            m9FeedbackEligible,
                            m9FeedbackEligibilityReason);
'''
new_call = '''                    M9M10rMfmTest1A.evaluateLiveFeedback(
                            m9PreviewEnergyIsoSeconds,
                            m9FeedbackRotationDegrees,
                            m9FeedbackEligible,
                            m9FeedbackEligibilityReason,
                            step == 0);
'''
if old_call not in i:
    raise SystemExit('M10RMFM2A IsoExpoSelector call anchor missing')
i = i.replace(old_call, new_call, 1)
write(iso_rel, i)

# Build identity only. No renderer/photo pipeline changes.
g = read(gradle_rel)
old_v = "versionName '1.61-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a-m10rmfm1a'"
new_v = "versionName '1.62-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a-m10rmfm2a'"
if old_v not in g:
    raise SystemExit('M10RMFM2A version anchor missing')
write(gradle_rel, g.replace(old_v, new_v, 1))

b = read(back_rel)
if 'currentframeceiling1am10rmfmtest1ascenefingerprint1b' not in b:
    raise SystemExit('M10RMFM2A build marker anchor missing')
b = b.replace('currentframeceiling1am10rmfmtest1ascenefingerprint1b',
              'currentframeceiling1am10rmfm2ascenefingerprint1b', 1)
if '1.61-' not in b:
    raise SystemExit('M10RMFM2A backlight version anchor missing')
write(back_rel, b.replace('1.61-', '1.62-', 1))

for rel, before in frozen_before.items():
    if sha(rel) != before:
        raise SystemExit('M10RMFM2A changed frozen photographic seam: ' + rel)

print('M10RMFM2A diagnostic/safety preparation applied')
print(' - step-0 MFM decision is capture-frozen; later preflight cannot overwrite metadata')
print(' - absolute body-level and q95/q99/GE224/GE240 highlight telemetry added')
print(' - preview q95==255 vetoes positive automatic assist only')
print(' - positive magnitude equation unchanged')
print(' - negative equation unchanged/not forced')
print(' - TC20, R3.8-H25/TG1, Cobalt, SAT3, curve02, BT601, JPEG95 and DNG unchanged')
