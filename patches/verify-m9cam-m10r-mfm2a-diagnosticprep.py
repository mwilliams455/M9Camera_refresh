#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m10r-mfm2a-diagnosticprep.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('M10RMFM2A verify missing: ' + rel)
    return p.read_text()


def ok(name, cond):
    if not cond:
        raise SystemExit('FAIL ' + name)
    print('OK  ', name)

mfm = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9M10rMfmTest1A.java')
iso = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
meta = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
gradle = read('app/build.gradle')
renderer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')

ok('version 1.62 M10RMFM2A identity',
   "versionName '1.62-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a-pn1a-cn1a-ct1a-cfc1a-m10rmfm2a'" in gradle)
ok('M10RMFM2A schema', 'm9cam.m10r.mfmtest.v2a' in mfm)
ok('old MFM1 schema absent after promotion', 'm9cam.m10r.mfmtest.v1a' not in mfm)

# Capture-freeze semantics. The live allocator calls the evaluator many times, but only
# the exact step-0 decision is allowed to replace the metadata snapshot.
ok('evaluator has explicit freeze bit', 'boolean freezeCaptureDecision' in mfm)
ok('allocator freezes exact step-0 decision',
   'm9FeedbackEligibilityReason,\n                            step == 0);' in iso)
ok('capture and evaluation state separated',
   'lastEvaluation' in mfm and 'lastCaptureDecision' in mfm)
ok('capture snapshot returns frozen decision',
   'public static synchronized JSONObject snapshotJson()' in mfm and
   'return cloneJson(lastCaptureDecision);' in mfm)
ok('preflight/debug snapshot remains separately available',
   'evaluationSnapshotJson()' in mfm and 'return cloneJson(lastEvaluation);' in mfm)
ok('capture state only replaced on explicit freeze',
   'if (freezeCaptureDecision) {\n            lastCaptureDecision = cloneJson(out);\n        }' in mfm)
ok('metadata still publishes capture-frozen MFM object',
   'root.put("m9M10rMfmTest", M9M10rMfmTest1A.snapshotJson());' in meta)

# Absolute body and preview highlight evidence are diagnostic inputs only.
for field in [
    'previewGlobalMedianY', 'previewCenter50MedianY', 'previewGlobalQ95Y',
    'previewGlobalQ99Y', 'previewBrightFractionGE224', 'previewBrightFractionGE240',
    'previewDarkFractionLE64', 'bodyMinMedianCenterLowerY',
    'bodyMeanMedianCenterLowerY', 'bodyCenter50VsRegionalMedianEv']:
    ok('telemetry field ' + field, field in mfm)
ok('body level explicitly does not feed magnitude',
   'out.put("absoluteBodyLevelFeedsMagnitude", false);' in mfm)
ok('contract keeps body level telemetry-only',
   '"absoluteBodyLevelRole", "telemetry_only_not_positive_magnitude"' in mfm)

# Saturated-preview safety gate is narrow: it only suppresses a positive automatic
# recommendation at q95==255. It must not rewrite the underlying recommendation.
ok('q95 saturated-preview veto threshold is 255',
   'previewGlobalQ95Y >= 255.0' in mfm)
ok('veto applies only to positive recommendations',
   'recommendedEv > 0.0' in mfm and 'saturatedPreviewPositiveVeto' in mfm)
ok('veto records distinct reason',
   'm10r_mfm2a_saturated_preview_positive_veto' in mfm)
ok('veto zeros applied EV only',
   'else if (saturatedPreviewPositiveVeto) {\n                        appliedEv = 0.0;' in mfm)
ok('recommendation is still emitted for counterfactual analysis',
   'out.put("recommendedExposureCorrectionEv", recommendedEv);' in mfm)

# Most important regression gate: MFM1 magnitude equations must remain byte-for-byte
# equivalent in source form. MFM2A is not allowed to become an exposure retune.
positive_eq = '''double rawPositiveEv = Math.max(0.0,
                            0.55 * integralVsMedianEv
                            + 0.25 * integralVsCenterEv
                            + 0.20 * integralVsLowerEv);'''
positive_conf = '''double positiveConfidence = smoothstep(sceneSpreadEv, 0.70, 2.20)
                            * smoothstep(brightRegionFraction, 0.08, 0.30)
                            * positiveGeometryConfidence;'''
negative_eq = '''double negativeCandidateEv = -0.70
                            * Math.max(0.0, centerOverIntegralEv - 0.10)
                            * negativeConfidence;'''
ok('positive raw magnitude equation unchanged', positive_eq in mfm)
ok('positive confidence thresholds unchanged', positive_conf in mfm)
ok('negative magnitude equation unchanged', negative_eq in mfm)
ok('positive bound unchanged +0.75 EV', 'MAX_POSITIVE_EV = 0.75' in mfm)
ok('negative bound unchanged -0.50 EV', 'MAX_NEGATIVE_EV = 0.50' in mfm)
ok('deadband unchanged 0.08 EV', 'DEAD_BAND_EV = 0.08' in mfm)
ok('contract states positive magnitude unchanged',
   '"positiveMagnitude", "unchanged_from_M10RMFMTEST1A"' in mfm)
ok('contract states negative path not forced',
   '"negativeMagnitude", "unchanged_not_forced"' in mfm)

# Preserve the recovered geometry and make no false numerical-parity claim.
ok('16x22/4x6 geometry retained', 'GRID_R = 16' in mfm and 'GRID_C = 22' in mfm and
   'REG_R = 4' in mfm and 'REG_C = 6' in mfm)
ok('exact recovered integral mask retained',
   'recoveredIntegralMask' in mfm and 'exact_0x4001349c_sum14160' in mfm)
ok('numerical M10-R parity still explicitly false',
   'o.put("m10rNumericalParity", false);' in mfm and
   'o.put("exact13FeatureGeneratorApplied", false);' in mfm)

# Live/manual authority and renderer freeze.
ok('signed live seam retained', 'Math.abs(m9Feedback.appliedEv) > 1.0e-9' in iso)
ok('manual EV bypass retained',
   'Math.abs(PhotonCamera.getSettings().exposureCompensation) < 1.0e-9' in iso)
ok('manual ISO and shutter bypass retained',
   'getCurrentExposureValue() == 0' in iso and 'getCurrentISOValue() == 0' in iso)
ok('TC20 intent normalization remains absent',
   '"tc20IntentNormalization", "unchanged_in_this_test_build"' in mfm)
ok('renderer JPEG quality still 95', 'public static final int JPEG_QUALITY = 95;' in renderer)
ok('renderer TC20 target frozen',
   'private static final double METER_TARGET = 0.107 * (8192.0 / 10000.0);' in renderer)
ok('renderer TC20 headroom target frozen',
   'private static final double TC_HEADROOM_TARGET = 0.95;' in renderer)
ok('renderer has no MFM2 dependency', 'M9M10rMfmTest1A' not in renderer)

# Behavioral truth table for the only new live policy.
def applied(recommended, q95, eligible=True):
    if not eligible:
        return 0.0
    if recommended > 0.0 and q95 >= 255.0:
        return 0.0
    return recommended

ok('synthetic +EV at q95 255 is vetoed', applied(+0.30, 255.0) == 0.0)
ok('synthetic +EV below saturation is unchanged', applied(+0.30, 254.0) == +0.30)
ok('synthetic negative EV at q95 255 is not force-vetoed', applied(-0.20, 255.0) == -0.20)
ok('ineligible decision stays zero', applied(+0.30, 200.0, False) == 0.0)

# Verify exact firmware Integral mask was not accidentally edited.
mm = re.search(r'INTEGRAL_MASK\s*=\s*new int\[\]\s*\{(.*?)\};', mfm, re.S)
ok('integral mask literal found', mm is not None)
vals = [int(x) for x in re.findall(r'-?\d+', mm.group(1))]
ok('integral mask has 352 entries', len(vals) == 352)
ok('integral mask exact sum 14160', sum(vals) == 14160)

print('PASS M10RMFM2A diagnostic/safety preparation verifier')
