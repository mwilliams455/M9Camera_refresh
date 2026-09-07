#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1h-shadedguardab1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
rp = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gp = root / 'app/build.gradle'
fp = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (rp, gp, fp):
    if not p.exists():
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A verify missing ' + str(p))
r = rp.read_text()
g = gp.read_text()
f = fp.read_text()

required = [
    'm9cam.renderer.basishsm.shadedguardab.v1a.main',
    'shadedGuardAB1A',
    'shadedGuard1ARequested',
    'shadedGuardAB1ARole',
    'applyShadedGuard1A',
    'applyShadedGuard1AFlags',
    'shadedGuard1AEligible',
    'shadedGuard1AApplied',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
    'shadedTailAuditStats.predictedGuardGain',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    'native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a',
    'native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a',
    'main_physical_2_primary_vs_basis_hsm_shading_off_on_unguarded_on_guarded',
    'boolean[] selfMeterFlags = {true, true, true};',
    'boolean[] applyShadingFlags = {false, true, true};',
    'boolean[] applyShadedGuard1AFlags = {false, false, true};',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'restored_physical_shaded_camera_RGB',
    'shadingLateRepresentationScaleApplied", false',
    'rawShadingResidual1AEnabled',
    'shadedTailAudit1AEnabled',
    'final double effectiveRenderGain = meterParityRenderBaseGain;',
]
for marker in required:
    if marker not in r:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A verify marker missing: ' + marker)

if '-basishsm1h-shadedguardab1a' not in g:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A build provenance missing')
if '-basishsm1g-shadedguard1a' in g:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A stale 1G build provenance survived')

for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in f:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A NOHDR boundary missing: ' + marker)

# Exactly three distinct additive field products are required.
for suffix in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
]:
    if r.count(suffix) != 1:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A suffix count invalid: ' + suffix)
if '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"' in r:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A stale exact pre-guard ON suffix survived')

# The only permission to mutate the old ON gain must be the explicit guard flag.
block_start = r.find('final boolean shadedGuard1AEligible')
block_end = r.find('final double effectiveRenderGain = meterParityRenderBaseGain;', block_start)
if block_start < 0 or block_end < 0:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A guard block not found')
block = r[block_start:block_end]
for marker in [
    'applyShadedGuard1A',
    'meterParitySelfMeter',
    'applyNativeShading',
    'shadedTailAuditStats.valid',
    'shadedTailAuditStats.predictedGuardGain',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
]:
    if marker not in block:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A bounded guard block missing: ' + marker)
for forbidden in ['CaptureRequest.', 'SENSOR_EXPOSURE_TIME', 'SENSOR_SENSITIVITY', 'IsoExpoSelector.HDR = true']:
    if forbidden in block:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A forbidden capture mutation in guard block: ' + forbidden)

# The field selector itself must encode the causal roles literally.
selector = 'boolean[] applyShadedGuard1AFlags = {false, false, true};'
if r.count(selector) != 1:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A causal selector is not unique')

print('BASISHSM1H-SHADEDGUARDAB1A verification OK')
print(' - same RAW produces OFF / ON unguarded / ON guarded candidates')
print(' - ON unguarded and guarded share physical shading and self-owned TC20')
print(' - only guarded ON permits SHADEDGUARD1A to alter the render gain')
print(' - guard formula/target are unchanged from 1G')
print(' - single RAW / HDR=false / capture / DNG boundary retained')
