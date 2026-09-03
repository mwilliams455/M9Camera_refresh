#!/usr/bin/env python3
from pathlib import Path
import math, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-virtualbv1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
virtual = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java').read_text()
meta = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java').read_text()
scene = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java').read_text()
coord = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java').read_text()
negative = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java').read_text()
render_meter = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java').read_text()
gradle = (root / 'app/build.gradle').read_text()
backlight = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java').read_text()

compact_version = '1.48-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1a-sc1a-vbv1a-cm1b'
checks = {
    'VIRTUALBV1A schema': 'm9cam.virtualbv.v1' in virtual,
    'diagnostic-only mode': 'diagnostic_only_no_exposure_mutation' in virtual,
    'live mutation forbidden': 'out.put("usedToMutateCaptureTarget", false)' in virtual,
    'jpeg not capture input': 'out.put("jpegBrightnessUsedForCapture", false)' in virtual,
    'architecture-only cross-generation rule': 'M10R_architecture_only_no_M10R_camera_specific_constants' in virtual,
    '70pct center scalar': 'PROVISIONAL_CENTER_WEIGHT = 0.70' in virtual,
    '30pct global scalar': 'PROVISIONAL_GLOBAL_WEIGHT = 0.30' in virtual,
    'corpus provisional Y120': 'PROVISIONAL_REFERENCE_Y = 120.0' in virtual,
    'Y120 explicitly not absolute M9 TTL': 'reference_y120_from_existing_m9cam_corpus_not_absolute_m9_ttl_calibration' in virtual,
    'raw signed delta unbounded': 'out.put("signedMeterDeltaUnbounded", true)' in virtual,
    'signed delta from BV difference': 'double signedMeterDeltaEv = photonEquivalentBvEv - virtualBvEv;' in virtual,
    'standard Photon APEX BV': 'double photonEquivalentBvEv = photonTvEv + photonAvEv - photonSvEv;' in virtual,
    'M9 base ISO160': 'M9_BASE_ISO = 160' in virtual,
    'M9 reduced APEX constant 5': 'M9_REDUCED_APEX_CONSTANT_EV = 5.0' in virtual,
    'M9 reduced TV equation': 'virtualBvEv + m9BaseSvEv\n                    - M9_REDUCED_APEX_CONSTANT_EV - M9_OVERRIDE_EV' in virtual,
    'Q8.8 conversion': 'Math.round(ev * 256.0)' in virtual,
    'lens TV threshold not invented': 'm9TvThresholdQ8_8", JSONObject.NULL' in virtual,
    'auto ISO activation not invented': 'autoIsoWouldActivate", JSONObject.NULL' in virtual,
    'actual target telemetry': 'actualTargetIso' in virtual and 'actualTargetExposureNs' in virtual,
    'actual capture telemetry': 'actualCaptureIso' in virtual and 'actualCaptureExposureNs' in virtual,
    'LUMA2.4 comparison telemetry': 'luma24RecommendedEv' in virtual and 'luma24AppliedEv' in virtual,
    'completed RAW teacher comparison telemetry': 'completedRawRecommendedCaptureDeltaEv' in virtual,
    'metadata publishes m9VirtualBv': 'root.put("m9VirtualBv", M9VirtualBv1A.evaluate(root));' in meta,
    'SCENEEXPOSURE1H frozen schema': 'm9cam.sceneexposure.v8.renderaware1h' in scene,
    'capture split SIGNEDCAL1A frozen schema': 'm9cam.exposuresplit.v4.capturemeter1b.m9negative1c.scenefingerprint1a.signedcal1a' in coord,
    'M9NEGATIVE1C frozen schema': 'm9cam.m9negative.v3.capturemeter1b.scenefingerprint1a.signedcal1a' in negative,
    'SCENEFINGERPRINT1A threshold frozen': 'SIMILAR_SCENE_DISTANCE = 1.0' in negative,
    'SCENEFINGERPRINT1A 60s gate frozen': 'MAX_FEEDBACK_AGE_MS = 60_000L' in negative,
    'SIGNEDCAL1A still diagnostic': 'm9cam.signedcal.v1.completedraw_coordinates1a' in negative,
    'RENDERMETER1C frozen': 'm9cam.rendermeter.v3.evidence1c' in render_meter,
    'compact Android versionName': ("versionName '" + compact_version + "'") in gradle,
    'compact version length safe': len(compact_version) < 96,
    'forensic marker contains VIRTUALBV1A': 'm9negative1csignedcal1avirtualbv1ascenefingerprint1acapturemeter1b' in backlight,
    'no M10R 59/256 calibration copied': '59 / 256' not in virtual and '59.0 / 256.0' not in virtual,
    'no M10R 25/256 hysteresis copied': '25 / 256' not in virtual and '25.0 / 256.0' not in virtual,
    'no percentile classifier drives BV': 'globalQ95' not in virtual and 'brightFractionGE' not in virtual,
    'no completed RAW drives BV': 'M9NegativeFeedback' not in virtual and 'rawUq99' not in virtual,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('VIRTUALBV1A structural self-check failed: ' + ', '.join(failed))

# Direction-first model regression. This intentionally validates only the simple
# scalar proxy and raw unbounded sign. It does NOT claim absolute M9 TTL calibration.
CENTER_W = 0.70
GLOBAL_W = 0.30
REF_Y = 120.0

def delta(global_y, center_y):
    proxy = CENTER_W * center_y + GLOBAL_W * global_y
    return math.log(REF_Y / proxy, 2.0)

# Existing 2026-09-03 field examples from the SCENEFINGERPRINT validation corpus.
# Bright-centre window should meter lower BV than Photon -> negative exposure correction.
# Dark/outdoor-centre examples should meter higher exposure need -> positive correction.
regressions = [
    ('ordinary_bike', 108.0, 115.0, +1, 0.08),
    ('bright_centre_window', 87.0, 199.0, -1, 0.20),
    ('ordinary_mug', 103.0, 139.0, -1, 0.05),
    ('dark_centre_outdoor', 123.0, 79.0, +1, 0.20),
    ('very_dark_transition', 20.0, 17.0, +1, 2.0),
]
for name, g, c, sign, minimum_abs in regressions:
    d = delta(g, c)
    print(f'VBV {name}: global={g:.1f} center={c:.1f} signedMeterDeltaEv={d:+.3f}')
    if sign > 0 and not d > 0.0:
        raise SystemExit(f'VIRTUALBV1A direction regression failed: {name} expected positive, got {d:+.3f}')
    if sign < 0 and not d < 0.0:
        raise SystemExit(f'VIRTUALBV1A direction regression failed: {name} expected negative, got {d:+.3f}')
    if abs(d) < minimum_abs:
        raise SystemExit(f'VIRTUALBV1A magnitude sanity failed: {name} only {d:+.3f}')

# Exact neutral proxy sanity.
if abs(delta(120.0, 120.0)) > 1e-12:
    raise SystemExit('VIRTUALBV1A neutral Y120 proxy does not produce zero delta')

# M9 baseline APEX sanity: ISO160 Sv in standard APEX; reduced M9 equation preserves
# one-EV response to one-EV BV change. This is an arithmetic check, not a calibration claim.
sv160 = math.log(160.0 / 3.125, 2.0)
tv_a = 6.0 + sv160 - 5.0
tv_b = 7.0 + sv160 - 5.0
if abs((tv_b - tv_a) - 1.0) > 1e-12:
    raise SystemExit('VIRTUALBV1A M9 reduced APEX one-EV invariance failed')
if round(6.0 * 256.0) != 1536:
    raise SystemExit('VIRTUALBV1A Q8.8 scale sanity failed')

print('M9Cam VIRTUALBV1A verification passed')
