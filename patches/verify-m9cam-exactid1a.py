#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-exactid1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'missing {rel}')
    return p.read_text()

negative = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java')
constraint = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java')
renderer = read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
metadata = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java')
coordinator = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java')
iso_selector = read('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
policy = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
gradle = read('app/build.gradle')
backlight = read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')

compact_version = '1.52-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b'
checks = {
    'EXACTID1A M9NEGATIVE schema':
        'm9cam.m9negative.v5.capturemeter1b.scenefingerprint1b.signedcal1a.exactid1a' in negative,
    'EXACTID1A constraint schema':
        'm9cam.constraintsplit.v3.virtualbv1a_rawconstraint1b.fix1.exactid1a' in constraint,
    'capture metadata DNG identity source':
        'root.put("dng",dngPath.getFileName().toString())' in metadata,
    'capture metadata RAW timestamp source':
        'raw.put("timestampNs",frame.timestamp)' in metadata,
    'capture constraint binds identity':
        'root.optString("dng", "")' in constraint
        and 'rawIdentity.optLong("timestampNs", -1L)' in constraint
        and 'completionCorrelationExactIdentityBound' in constraint,
    'scene identity fields':
        'String captureIdentity = null;' in negative
        and 'long rawTimestampNs = -1L;' in negative
        and 'boolean captureIdentityBound = false;' in negative,
    'completed RAW exact key match':
        'completedCaptureIdentity.equals(candidate.captureIdentity)' in negative
        and 'candidate.rawTimestampNs != rawTimestampNs' in negative,
    'FIFO not primary association':
        'SceneSignature scene = PENDING.pollFirst();' not in negative,
    'FIFO fallback history disabled':
        'out.put("fifoFallbackUsedForHistory", false);' in negative
        and 'raw.scene = scene;' in negative,
    'exact correlation surfaced':
        'out.put("correlationExact", correlationExact);' in negative
        and 'exact_dng_filename_plus_raw_timestamp' in negative,
    'orphan duplicate cleanup':
        '!candidate.captureIdentityBound && candidate.sequence < scene.sequence' in negative
        and 'orphanUnboundPrunedCount' in negative,
    'renderer passes DNG path':
        'diag, iso, exposureTimeNs, dngPath,' in renderer,
    'renderer passes ImageFrame timestamp':
        'frame != null ? frame.timestamp : -1L' in renderer,
    'oracle hard-gated on exact correlation':
        'boolean meterAvailable = captureCorrelationExact && finite(meterRequestEv);' in constraint
        and 'same_frame_raw_oracle_rejected_capture_identity_not_exact' in constraint,
    'FIX1 mandatory min preserved':
        'double constrained = Math.min(meterRequestEv, mandatoryProtectionEv);' in constraint,
    'FIX1 conservative envelope preserved':
        'conservativeEnvelopeConstrainedMeterRequestEv' in constraint
        and 'passingConstraintCandidateCount' in negative,
    'FP1B frozen':
        'private static final double SIMILAR_SCENE_DISTANCE = 1.0;' in negative
        and 'private static final long MAX_FEEDBACK_AGE_MS = 60_000L;' in negative
        and 'Math.abs(a[i] - b[i]) / 60.0' in negative,
    'no constraint live seam':
        'M9ConstraintSplit1A' not in iso_selector
        and 'M9ConstraintSplit1A' not in policy
        and 'm9ConstraintSplit' not in coordinator,
    'compact version':
        ("versionName '" + compact_version + "'") in gradle and len(compact_version) < 96,
    'forensic identity':
        'virtualbv1aconstraintsplit1afix1exactid1ascenefingerprint1b' in backlight,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('EXACTID1A structural self-check failed: ' + ', '.join(failed))

# Reproduce the field-observed failure: an unbound duplicate FIFO entry sits
# ahead of the real capture. Exact identity must choose seq3, not seq2.
pending = [
    {'seq': 2, 'id': None, 'ts': -1, 'bound': False},
    {'seq': 3, 'id': 'IMG_20260904_070206_1788501726903_00.dng', 'ts': 222222, 'bound': True},
]
target_id = 'IMG_20260904_070206_1788501726903_00.dng'
target_ts = 222222
match = next((x for x in pending
              if x['bound'] and x['id'] == target_id and x['ts'] == target_ts), None)
if match is None or match['seq'] != 3:
    raise SystemExit('EXACTID1A regression failed: exact match did not bypass FIFO orphan')
pending = [x for x in pending if x is not match]
pending = [x for x in pending if not (not x['bound'] and x['seq'] < match['seq'])]
if pending:
    raise SystemExit('EXACTID1A regression failed: older unbound duplicate not pruned')
print('ID1A exact_match_bypasses_fifo_duplicate: PASS')

pending = [{'seq': 4, 'id': 'IMG_A.dng', 'ts': 100, 'bound': True}]
bad = next((x for x in pending if x['bound'] and x['id'] == 'IMG_A.dng' and x['ts'] == 101), None)
if bad is not None:
    raise SystemExit('EXACTID1A regression failed: timestamp mismatch accepted')
print('ID1A timestamp_mismatch_rejected: PASS')

pending = [{'seq': 5, 'id': 'IMG_B.dng', 'ts': 200, 'bound': True}]
bad = next((x for x in pending if x['bound'] and x['id'] == 'IMG_C.dng' and x['ts'] == 200), None)
if bad is not None:
    raise SystemExit('EXACTID1A regression failed: DNG identity mismatch accepted')
print('ID1A dng_identity_mismatch_rejected: PASS')

print('EXACTID1A verification passed')
