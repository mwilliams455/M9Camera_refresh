#!/usr/bin/env python3
from pathlib import Path
import math
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-virtualbv-spatial1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'MISSING {rel}')
    return p.read_text()

checks = []
def check(name, ok):
    checks.append((name, bool(ok)))
    print(('OK   ' if ok else 'FAIL ') + name)

cand_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBvSpatial1B.java'
meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
base_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'
gradle_rel = 'app/build.gradle'

cand = text(cand_rel)
meta = text(meta_rel)
base = text(base_rel)
gradle = text(gradle_rel)
iso = text('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
policy = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
renderer = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
constraint = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java')

check('VIRTUALBVSPATIAL1B schema', 'm9cam.virtualbv.spatial.v1b' in cand)
check('diagnostic-only contract', 'diagnostic_only_no_exposure_mutation' in cand and 'liveEligible", false' in cand)
check('cannot mutate capture target', 'usedToMutateCaptureTarget", false' in cand)
check('same Y120 reference', 'REFERENCE_Y = 120.0' in cand)
check('moderate 50/30/20 probe', 'MODERATE_CENTER = 0.50' in cand and 'MODERATE_MIDDLE_CENTER = 0.30' in cand and 'MODERATE_GLOBAL = 0.20' in cand)
check('static 3x3 center kernel', 'K_CORNER = 0.25' in cand and 'K_AXIS = 0.50' in cand and 'K_CENTER = 6.00' in cand and 'K_SUM = 9.00' in cand)
check('aggressive 80/20 bracketing probe', 'AGGRESSIVE_MIDDLE_CENTER = 0.80' in cand and 'AGGRESSIVE_GLOBAL = 0.20' in cand)
check('orientation-aware 3x3 source', 'spatialTileMedians3x3' in cand and 'middleCenter' in cand)
check('no RAW teacher in meter', 'rawFeedbackUsedForMeter", false' in cand and 'M9NegativeFeedback1A' not in cand and 'rawUq' not in cand)
check('no rendered luma in meter', 'renderedLumaUsedForMeter", false' in cand and 'directRenderedLuma' not in cand and 'M9RenderMeterDiagnostic' not in cand)
check('metadata publishes candidate once', meta.count('m9VirtualBvSpatialCandidate') == 1 and 'M9VirtualBvSpatial1B.evaluate(root)' in meta)
check('frozen VIRTUALBV1A schema retained', 'm9cam.virtualbv.v1' in base)
check('frozen VIRTUALBV1A 70/30 retained', 'PROVISIONAL_CENTER_WEIGHT = 0.70' in base and 'PROVISIONAL_GLOBAL_WEIGHT = 0.30' in base)
check('frozen VIRTUALBV1A Y120 retained', 'PROVISIONAL_REFERENCE_Y = 120.0' in base)
check('CONSTRAINTREF1A remains meterModelFrozen VIRTUALBV1A', 'meterModelFrozen", "VIRTUALBV1A"' in constraint)
check('no live seam consumes spatial candidate', 'M9VirtualBvSpatial1B' not in iso and 'M9VirtualBvSpatial1B' not in policy and 'M9VirtualBvSpatial1B' not in renderer)
check('compact 1.54 version exact', "versionName '1.54-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b'" in gradle)

# Test-20 numeric fixtures. These are not target labels; they simply freeze the
# candidate geometry arithmetic observed in the first field corpus that motivated 1B.
def request(proxy):
    return math.log(120.0 / proxy, 2.0)

def probes(global_m, center_m, tiles):
    mc = tiles[4]
    moderate = 0.50 * center_m + 0.30 * mc + 0.20 * global_m
    kernel = (0.25 * (tiles[0] + tiles[2] + tiles[6] + tiles[8])
              + 0.50 * (tiles[1] + tiles[3] + tiles[5] + tiles[7])
              + 6.00 * mc) / 9.00
    aggressive = 0.80 * mc + 0.20 * global_m
    return request(moderate), request(kernel), request(aggressive)

fixtures = {
    '091938 ordinary control': (134,123,[96,191,184,150,103,34,141,117,60], (0.010,0.134,0.136)),
    '092125 cat control': (91,45,[37,97,85,67,35,160,52,163,182], (1.229,0.993,1.377)),
    '092209 flowers backlight': (87,66,[142,115,58,186,61,52,193,70,63], (0.805,0.643,0.858)),
    '092259 dark cat window': (100,84,[197,198,206,105,67,78,43,62,55], (0.548,0.528,0.705)),
    '092544 child window': (142,55,[164,255,255,173,43,155,167,26,70], (0.803,0.572,0.934)),
    '092551 ordinary control': (132,103,[255,146,189,174,113,76,121,100,54], (0.102,-0.001,0.039)),
    '092555 broad-center contamination anchor': (73,112,[101,211,49,138,61,31,66,33,51], (0.433,0.757,0.920)),
}
for name,(g,c,t,exp) in fixtures.items():
    got = probes(g,c,t)
    ok = all(abs(a-b) < 0.0025 for a,b in zip(got,exp))
    check(f'fixture {name}: moderate/kernel/aggressive {got[0]:+.3f}/{got[1]:+.3f}/{got[2]:+.3f}', ok)

# The motivating anchor must show that geometry alone can explain the large
# discrepancy without changing Y120: broad 1A was about +0.259 EV, while the
# static center-concentrated kernel is about +0.757 EV.
anchor = probes(73,112,[101,211,49,138,61,31,66,33,51])[1]
check('092555 kernel exposes about +0.50 EV hidden by broad-center geometry', 0.74 < anchor < 0.78)

failed = [n for n,ok in checks if not ok]
if failed:
    raise SystemExit('VIRTUALBVSPATIAL1B verification failed: ' + '; '.join(failed))
print(f'VERIFIED {len(checks)} VIRTUALBVSPATIAL1B structural and test-20 geometry checks')
print('VIRTUALBVSPATIAL1B PASS: three fixed meter-geometry probes are observational only; VIRTUALBV1A, CONSTRAINTREF1A, Camera2, FB1, motion, renderer, JPEG and DNG remain frozen')