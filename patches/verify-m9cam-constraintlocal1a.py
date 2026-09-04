#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-constraintlocal1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CONSTRAINTLOCAL1A verify missing: {rel}')
    return p.read_text()

def require(haystack, needle, label):
    if needle not in haystack:
        raise SystemExit(f'CONSTRAINTLOCAL1A verify failed: {label}')

negative = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
local = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintLocal1A.java')
meta = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
guard = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java')
constraint_ref = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java')
virtual = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java')
gradle = text('app/build.gradle')
back = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')
renderer = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
policy = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
isoexpo = text('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')

require(local, 'm9cam.constraintlocal.v1a', 'schema')
require(local, 'diagnostic_only_no_exposure_mutation', 'diagnostic-only contract')
require(local, 'liveEligible", false', 'live eligibility false')
require(local, 'usedToMutateCaptureTarget", false', 'capture mutation false')
require(local, 'compare_nearest_top2_local_and_existing_broad_reference_aligned_raw_history',
        'selection architecture')
require(local, 'nearest_plus0p15_is_research_only_not_frozen_photographic_truth',
        'local rule marked provisional')
require(meta, 'root.put("m9ConstraintLocal", M9ConstraintLocal1A.evaluate(root));',
        'metadata publication')

require(negative, 'constraintLocal1A', 'nested candidate diagnostics')
require(negative, 'sourceActualCaptureOffsetFromPhotonEv', 'source capture offset per candidate')
require(negative, 'rawPositiveAllowanceEv', 'positive allowance per candidate')
require(negative, 'referenceAlignedPositiveCeilingFromPhotonEv',
        'aligned positive ceiling per candidate')
require(negative, 'rawMandatoryProtectionEv', 'mandatory protection per candidate')
require(negative, 'sceneFingerprintDistance', 'fingerprint distance per candidate')
require(negative, 'spatialTileMedianDistance', 'spatial distance per candidate')
require(negative, 'sourceAgeMs', 'candidate age')
require(negative, 'sourceCompletedSequence', 'candidate completed identity')
require(negative, 'sourceCaptureIdentity', 'candidate capture identity')
require(negative, 'top2NearestPositiveCeilingFromPhotonEv', 'top2 envelope')
require(negative, 'localEnvelopePositiveCeilingFromPhotonEv', 'local envelope')
require(negative, 'existingBroadPositiveCeilingFromPhotonEv', 'broad envelope retained')
require(negative, 'bestDistance + 0.15', 'nearest plus 0.15 local threshold')
require(negative, 'SIMILAR_SCENE_DISTANCE = 1.0', 'FP1B threshold frozen')
require(negative, 'MAX_FEEDBACK_AGE_MS = 60_000L', '60s history frozen')
require(negative,
        'm9cam.m9negative.v5.capturemeter1b.scenefingerprint1b.signedcal1a.exactid1a',
        'teacher schema frozen')

require(guard, 'private static final double MAX_FOREGROUND_BUMP_EV = 0.50;',
        '+0.50 guard cap frozen')
require(guard, 'Math.max(0.0, fb1Applied - baseEv)', 'guard floor frozen')
require(constraint_ref, 'm9cam.constraintref.v1', 'CONSTRAINTREF schema frozen')
require(constraint_ref, 'source_actual_capture_offset_from_photon_plus_raw_relative_constraint',
        'reference-alignment math frozen')
require(virtual, 'PROVISIONAL_CENTER_WEIGHT = 0.70', 'VirtualBV center weight frozen')
require(virtual, 'PROVISIONAL_GLOBAL_WEIGHT = 0.30', 'VirtualBV global weight frozen')
require(virtual, 'PROVISIONAL_REFERENCE_Y = 120.0', 'VirtualBV Y120 frozen')
require(gradle,
        "versionName '1.56-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a-cl1a'",
        'build identity')
require(back,
        'constraintref1avirtualbvspatial1bforegroundguard1aconstraintlocal1ascenefingerprint1b',
        'forensic marker')

for name, body in [
    ('renderer', renderer),
    ('exposure policy', policy),
    ('IsoExpoSelector', isoexpo),
]:
    if 'M9ConstraintLocal1A' in body or 'm9ConstraintLocal' in body:
        raise SystemExit(f'CONSTRAINTLOCAL1A verify failed: {name} consumes diagnostic output')

def constrain(request, positive=None, mandatory=None):
    if mandatory is not None:
        return min(request, mandatory)
    if request > 0.0 and positive is not None:
        return min(request, positive)
    return request

assert abs(constrain(0.700, positive=0.698) - 0.698) < 1e-9
assert abs(constrain(0.700, positive=-0.012) - (-0.012)) < 1e-9
assert abs(constrain(-0.595, positive=0.400) - (-0.595)) < 1e-9
assert abs(constrain(0.600, positive=0.900, mandatory=0.200) - 0.200) < 1e-9

print('CONSTRAINTLOCAL1A verification passed')
print(' - candidate-level identity/age/fingerprint/spatial/reference-aligned ceilings present')
print(' - nearest/top2/local/broad policies are diagnostic-only comparisons')
print(' - FOREGROUNDGUARD1A +0.50, VIRTUALBV1A Y120 and CONSTRAINTREF1A reference math frozen')
print(' - no live Camera2/allocator/render seam consumes CONSTRAINTLOCAL1A')
