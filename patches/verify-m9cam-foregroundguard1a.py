#!/usr/bin/env python3
from pathlib import Path
import math
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-foregroundguard1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()


def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'FOREGROUNDGUARD1A verify missing file: {rel}')
    return p.read_text()


def require(haystack, needle, label):
    if needle not in haystack:
        raise SystemExit(f'FOREGROUNDGUARD1A verify failed: {label}: {needle!r}')
    print(f'OK   {label}')


guard_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java'
meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
gradle_rel = 'app/build.gradle'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'

guard = text(guard_rel)
meta = text(meta_rel)
gradle = text(gradle_rel)
back = text(back_rel)

require(guard, 'm9cam.foregroundguard.v1a', 'schema')
require(guard, 'diagnostic_only_no_exposure_mutation', 'diagnostic-only contract')
require(guard, 'liveEligible", false', 'live eligibility false')
require(guard, 'usedToMutateCaptureTarget", false', 'capture mutation false')
require(guard, 'private static final double MAX_FOREGROUND_BUMP_EV = 0.50;', 'provisional +0.50 EV maximum bump')
require(guard, 'Math.max(0.0, fb1Applied - baseEv)', 'FB1 used as floor gap rather than additive EV')
require(guard, 'Math.min(MAX_FOREGROUND_BUMP_EV, requestedGap)', 'foreground gap bounded')
require(guard, 'double preSensorTarget = baseEv + boundedBump;', 'bounded floor applied to VirtualBV base')
require(guard, 'boolean fb1WouldApply = base.optBoolean("luma24WouldApply", false);', 'FB1 classifier gate retained')
require(guard, 'double fb1Applied = base.optDouble("luma24AppliedEv", Double.NaN);', 'field-tested FB1 applied target used')
require(guard, 'legacy_FB1_applied_target_as_bounded_floor_signal', 'architecture identity')
require(guard, 'CONSTRAINTREF1A_reference_aligned_RAW_ceiling', 'sensor authority identity')
require(guard, 'spatialProbeAuthority", "none_observation_only', 'spatial probe remains observation-only')
require(guard, 'conservativeEnvelopePositiveCeilingFromPhotonEv', 'conservative aligned positive ceiling consumed')
require(guard, 'conservativeEnvelopeMandatoryCeilingFromPhotonEv', 'conservative aligned mandatory ceiling consumed')
require(guard, 'matchedSensorPositiveCeilingFromPhotonEv', 'nearest aligned positive ceiling fallback consumed')
require(guard, 'matchedSensorMandatoryCeilingFromPhotonEv', 'nearest aligned mandatory ceiling fallback consumed')
require(guard, 'Math.min(requestEv, c.mandatoryCeilingEv)', 'mandatory sensor ceiling remains hard upper bound')
require(guard, 'requestEv > 0.0 && finite(c.positiveCeilingEv)', 'positive ceiling only constrains positive requests')
require(guard, 'retainedForegroundBumpAfterSensorEv', 'post-sensor retained bump telemetry')
require(guard, 'sensorConstrainedBaseFromPhotonEv', 'base sensor counterfactual telemetry')
require(guard, 'sensorConstrainedGuardedTargetFromPhotonEv', 'guarded sensor counterfactual telemetry')
require(meta, 'root.put("m9ForegroundGuard", M9ForegroundGuard1A.evaluate(root));', 'metadata publication')
require(gradle, "versionName '1.55-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a'", 'version identity')
require(back, 'constraintref1avirtualbvspatial1bforegroundguard1ascenefingerprint1b', 'forensic marker')

# The spatial experiment may coexist in metadata but must not enter guard math.
if 'M9VirtualBvSpatial1B' in guard or 'm9VirtualBvSpatialCandidate' in guard:
    raise SystemExit('FOREGROUNDGUARD1A verify failed: spatial candidate entered guard decision path')
print('OK   spatial candidate not consumed by guard math')

# No live/capture/render seam may reference the diagnostic class.
frozen_live = [
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
for rel in frozen_live:
    if 'M9ForegroundGuard1A' in text(rel) or 'm9ForegroundGuard' in text(rel):
        raise SystemExit(f'FOREGROUNDGUARD1A verify failed: live seam consumes guard: {rel}')
print('OK   no live exposure/capture/render seam consumes FOREGROUNDGUARD1A')

# Preserve the frozen meter, identity and sensor models exactly by schema/constant anchors.
virtual = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java')
constraint = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java')
negative = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
require(virtual, 'm9cam.virtualbv.v1', 'VIRTUALBV1A schema frozen')
require(virtual, 'PROVISIONAL_CENTER_WEIGHT = 0.70', 'VIRTUALBV1A 70% center frozen')
require(virtual, 'PROVISIONAL_GLOBAL_WEIGHT = 0.30', 'VIRTUALBV1A 30% global frozen')
require(virtual, 'PROVISIONAL_REFERENCE_Y = 120.0', 'VIRTUALBV1A Y120 frozen')
require(constraint, 'm9cam.constraintref.v1', 'CONSTRAINTREF1A schema frozen')
require(constraint, 'referenceFrame", "photon_pre_fb1_exposure_baseline', 'CONSTRAINTREF common reference frozen')
require(negative, 'm9cam.m9negative.v5.capturemeter1b.scenefingerprint1b.signedcal1a.exactid1a', 'EXACTID/SIGNEDCAL/FP1B teacher frozen')
require(negative, 'SIMILAR_SCENE_DISTANCE = 1.0', 'FP1B similarity threshold frozen')
require(negative, 'MAX_HISTORY_AGE_MS = 60_000L', 'FP1B history age frozen')

# Numerical architecture fixtures from test 902 and boundary cases.
MAX_BUMP = 0.50

def floor_target(base, fb1, would_apply=True):
    gap = max(0.0, fb1 - base) if would_apply else 0.0
    bump = min(MAX_BUMP, gap)
    return base + bump, bump

def constrain(req, pos=None, mand=None):
    if mand is not None:
        return min(req, mand)
    if req > 0.0 and pos is not None:
        return min(req, pos)
    return req

def close(a, b, eps=1e-9):
    return abs(a - b) <= eps

fixtures = [
    # test 902 moving black dog: +0.50 max lift toward legacy +0.75 target.
    (0.243, 0.750, True, 0.743, 0.500, 'test902 moving dog capped floor'),
    # test 902 off-centre black dog: preserve Leica-like negative base, lift only +0.50.
    (-0.148, 0.619, True, 0.352, 0.500, 'test902 off-centre dog capped floor'),
    # small gap: floor reaches FB1 without additive overshoot.
    (0.680, 0.750, True, 0.750, 0.070, 'test902 small floor gap'),
    # base already above FB1: Leica-like meter remains authority.
    (0.905, 0.750, True, 0.905, 0.000, 'test902 base above FB1 preserved'),
    # inactive FB1: signed negative base survives unchanged.
    (-0.141, 0.750, False, -0.141, 0.000, 'inactive guard preserves negative base'),
]
for base, fb1, active, expected_target, expected_bump, label in fixtures:
    target, bump = floor_target(base, fb1, active)
    if not close(target, expected_target) or not close(bump, expected_bump):
        raise SystemExit(f'FOREGROUNDGUARD1A fixture failed: {label}: target={target} bump={bump}')
    print(f'OK   {label}')

# Sensor ceilings constrain the guarded target after floor composition.
target, _ = floor_target(0.418, 0.750, True)
if not close(target, 0.750) or not close(constrain(target, pos=0.600), 0.600):
    raise SystemExit('FOREGROUNDGUARD1A fixture failed: positive sensor ceiling after floor')
print('OK   positive RAW ceiling caps guarded target after floor')

target, _ = floor_target(0.100, 0.750, True)
if not close(target, 0.600) or not close(constrain(target, pos=1.2, mand=0.200), 0.200):
    raise SystemExit('FOREGROUNDGUARD1A fixture failed: mandatory sensor ceiling after floor')
print('OK   mandatory RAW ceiling overrides positive floor')

# A negative request below a positive ceiling is never pulled upward by the sensor stage.
if not close(constrain(-0.500, pos=0.300), -0.500):
    raise SystemExit('FOREGROUNDGUARD1A fixture failed: signed negative request preservation')
print('OK   signed negative base is not raised by positive RAW ceiling')

print('FOREGROUNDGUARD1A verification passed')
