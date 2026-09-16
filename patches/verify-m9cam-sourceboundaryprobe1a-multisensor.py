#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourceboundaryprobe1a-multisensor.py <PhotonCamera-root>')
root = Path(sys.argv[1])
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
target_loader = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9TargetFirmwareCalibration.java'
target_asset = root / 'app/src/main/assets/m9/m9_curve02_firmware.bin'
for p in (renderer, target_loader, target_asset):
    if not p.exists(): raise SystemExit(f'missing required production file: {p}')
s = renderer.read_text()
required = [
    'SOURCEBOUNDARYPROBE1A: same-frame, read-only multi-sensor boundary audit.',
    'm9cam.renderer.sourceboundaryprobe.v1a',
    'POST_DEMOSAIC_SENSORRGB',
    'POST_DEMOSAIC_SENSORRGB_NEUTRALIZED_DIAGNOSTIC',
    'POST_SOURCECAL_LINEAR_UNCLIPPED',
    'POST_SOURCECAL_COMMONSCENE',
    'POST_M9_BRIDGE',
    'POST_TC20_GAIN',
    'POST_SAT3',
    'POST_CURVE02',
    'POST_BT601',
    'POST_TG1',
    'same_full_resolution_POST_DEMOSAIC_SENSORRGB_Mat_read_only_rows_no_resize_no_interpolation',
    'source_horizontal_even_x_adjacent_pairs_matches_frozen_BT601_pairing_space',
    '((R+B)/2)-G',
    'sourceBoundaryProbe1APixelMutation", false',
    'sourceBoundaryProbe1AGainMutation", false',
    'sourceBoundaryProbe1ATargetRendererMutation", false',
    'physicalSensorGeneric", true',
    'physical_RAW_characteristics_and_measured_sensor_parameters_not_zoom_or_lens_label',
    'cameraIdUsedForBehavior", false',
    'focalLengthUsedForBehavior", false',
    'zoomLabelUsedForBehavior", false',
    'geometryDerivedFromActiveInput", true',
    'any_supported_physical_Bayer_sensor',
    'locate_physical_sensor_domain_divergence_relative_to_SOURCECAL2A_common_scene_boundary',
    'for_any_physical_sensor_pair_first_stage_with_material_between_sensor_jump',
    'COBALTROLEPURGE1A_NATIVEFIRMWARE1A_SOURCEBOUNDARYPROBE1A',
    'research/sourceboundaryprobe1a-multisensor',
    'mixedCalibrationAssetUsage", "none_production"',
    'cobaltRuntimeProductionDependency", false',
    'identityHsmApplied", true',
    'm9TargetRendererLensIndependent", true',
]
for token in required:
    if token not in s: raise SystemExit('missing SOURCEBOUNDARYPROBE1A invariant: ' + token)

# Zoom/lens categories are test labels only. They must not survive as decision semantics.
for forbidden_label in ('3x_vs_main', 'three_x_vs_main', 'camera4_only', 'focalLengthUsedForBehavior", true',
                        'cameraIdUsedForBehavior", true', 'zoomLabelUsedForBehavior", true'):
    if forbidden_label in s:
        raise SystemExit('physical-sensor-generic invariant violated: ' + forbidden_label)

# Exact production call must remain source-only / identity-HSM mode 0 and self-metered.
prod_sig = 'private static RenderCore renderNativeSourceProduction1P('
start = s.index(prod_sig)
end = s.index('    private static RenderCore renderCore(', start)
prod = s[start:end]
call = '''                1.0,\n                true,\n                0,\n                true,\n                false, false,\n                true, 1.0,\n                true, 0.30,\n                1.0, false);'''
if call not in prod:
    raise SystemExit('production source-only renderNativeProspectiveCore call changed')
if 'historical basis/H25 target role' in prod:
    raise SystemExit('stale historical basis production comment survived probe patch')

# The probe must only read cam16 and build telemetry. No setter/mutation calls are allowed in its method.
probe_start = s.index('private static JSONObject sourceBoundaryProbe1A(')
probe_end = s.index('    // SKYCHROMA1A read-only audit.', probe_start)
probe = s[probe_start:probe_end]
for forbidden in ('cam16.put(', 'setPixels(', 'copyTo(cam16', 'ctx.camToPp =', 'ctx.ppToM9 =', 'meter.gain ='):
    if forbidden in probe: raise SystemExit('probe mutation forbidden: ' + forbidden)
if 'cam16.get(y, 0, row);' not in probe:
    raise SystemExit('probe must read demosaiced rows directly')
if 'Imgproc.resize' in probe:
    raise SystemExit('probe must not blur chroma noise through resize/interpolation')
if 'cam16.cols()' not in probe or 'cam16.rows()' not in probe:
    raise SystemExit('probe geometry must be derived from the active physical RAW input')

# Production target calibration remains dedicated curve02 only.
loader = target_loader.read_text()
if 'm9/m9_curve02_firmware.bin' not in loader:
    raise SystemExit('target-only curve02 loader changed')
if len(target_asset.read_bytes()) != 2048:
    raise SystemExit('target-only curve02 asset size changed')

print('SOURCEBOUNDARYPROBE1A_MULTISENSOR_VERIFY PASS')
print('diagnostic-only stage boundary telemetry present')
print('physical-sensor-generic selection invariant present; zoom/lens labels are diagnostic only')
print('active RAW geometry drives probe dimensions')
print('production source-only mode 0 / identity HSM preserved')
print('Cobalt production dependency remains disabled')
print('target-only curve02 remains 2048 bytes')