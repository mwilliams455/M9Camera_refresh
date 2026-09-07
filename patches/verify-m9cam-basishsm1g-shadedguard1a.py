#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1g-shadedguard1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
rp = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gp = root / 'app/build.gradle'
fp = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (rp, gp, fp):
    if not p.exists():
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A verify missing ' + str(p))
r = rp.read_text()
g = gp.read_text()
f = fp.read_text()

required = [
    'm9cam.renderer.basishsm.shadedguard.v1a.main',
    'shadedGuard1AEligible',
    'shadedGuard1AApplied',
    'shadedGuard1AOriginalMeterGain',
    'shadedGuard1AOriginalUnshadedGuardGain',
    'shadedGuard1ACorrectedGuardGain',
    'shadedGuard1AMeterGain',
    'shadedGuard1AGainDeltaEvVsOldOn',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
    'shadedTailAuditStats.predictedGuardGain',
    'final double effectiveRenderGain = meterParityRenderBaseGain;',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    'native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'restored_physical_shaded_camera_RGB',
    'shadingLateRepresentationScaleApplied", false',
    'rawShadingResidual1AEnabled',
    'shadedTailAudit1AEnabled',
]
for marker in required:
    if marker not in r:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A verify marker missing: ' + marker)

if '-basishsm1g-shadedguard1a' not in g:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A build provenance missing')
if '-basishsm1f-shadedtailaudit1a' in g:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A stale build provenance survived')

for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in f:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A NOHDR boundary missing: ' + marker)

# The field experiment must still contain exactly one OFF product and one renamed ON product.
if r.count('"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"') != 1:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A OFF suffix count invalid')
if r.count('"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"') != 1:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A ON suffix count invalid')
if '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"' in r:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A stale exact 1F ON suffix survived')

# Promotion is deliberately bounded: the corrected guard may only reduce a self-metered
# shading-ON gain. It must not alter capture exposure or introduce HDR/multiframe logic.
block_start = r.find('final boolean shadedGuard1AEligible')
block_end = r.find('final double effectiveRenderGain = meterParityRenderBaseGain;', block_start)
if block_start < 0 or block_end < 0:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A guard block not found')
block = r[block_start:block_end]
for marker in ['meterParitySelfMeter', 'applyNativeShading', 'shadedTailAuditStats.valid',
               'shadedTailAuditStats.predictedGuardGain', 'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)']:
    if marker not in block:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A bounded guard block missing: ' + marker)
for forbidden in ['CaptureRequest.', 'SENSOR_EXPOSURE_TIME', 'SENSOR_SENSITIVITY', 'IsoExpoSelector.HDR = true']:
    if forbidden in block:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A forbidden capture mutation in guard block: ' + forbidden)

print('BASISHSM1G-SHADEDGUARD1A verification OK')
print(' - corrected tail guard applies only to eligible shading-ON self-meter branch')
print(' - OFF output retained; ON output distinctly renamed')
print(' - SHADINGDOMAIN1A + SHADEDTAILAUDIT1A provenance retained')
print(' - single RAW / HDR=false / capture / DNG boundary retained')
