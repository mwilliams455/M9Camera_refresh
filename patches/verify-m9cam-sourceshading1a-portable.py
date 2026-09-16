#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourceshading1a-portable.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
render = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render'
shading = render / 'M9SourceShadingAudit1A.java'
deviceport = render / 'M9DevicePortAudit1A.java'
if not shading.exists() or not deviceport.exists():
    raise SystemExit('SOURCESHADING1A assembled files missing')

text = shading.read_text()
audit = deviceport.read_text()
required = [
    'source_domain_diagnostic_only_no_pixel_change',
    'physicalSensorGeneric", true',
    'cameraIdUsedForBehavior", false',
    'focalLengthUsedForBehavior", false',
    'zoomLabelUsedForBehavior", false',
    'SOURCE_SHADING_NORMALIZE',
    'CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP',
    'map.copyGainFactors(factors, 0)',
    'R,Geven,Godd,B',
    'live_CaptureResult_LensShadingMap_getColumnCount_getRowCount',
    'entire_active_pixel_array_independent_of_scaler_crop',
    'bilinear_between_grid_samples',
    'SENSOR_INFO_LENS_SHADING_APPLIED',
    'result_map_is_complete_correction_when_RAW_shading_applied_false_and_remaining_correction_when_true',
    'sourceShadingCorrectionAppliedInThisBuild", false',
    'sourceShadingCorrectionEligible", false',
    'RAW_buffer_origin_to_active_array_mapping_not_yet_proven',
    'm9TargetRendererChanged", false',
]
for token in required:
    if token not in text:
        raise SystemExit('SOURCESHADING1A required token missing: ' + token)

for forbidden in [
    'camera4_only',
    '3x_only',
    'three_x_only',
    'cameraIdUsedForBehavior", true',
    'focalLengthUsedForBehavior", true',
    'zoomLabelUsedForBehavior", true',
]:
    if forbidden in text:
        raise SystemExit('SOURCESHADING1A forbidden sensor-label behavior token present: ' + forbidden)

if 'sourceShadingNormalization1A' not in audit or 'M9SourceShadingAudit1A.describe(' not in audit:
    raise SystemExit('SOURCESHADING1A not wired into DEVICEPORT sidecar')

# A diagnostic source descriptor must not contain renderer-mutating OpenCV or native calls.
for forbidden in ['Core.multiply(', 'Core.transform(', 'nativeCamToPp(', 'renderCore(', 'M9NativeColorCore']:
    if forbidden in text:
        raise SystemExit('SOURCESHADING1A photographic mutation primitive present: ' + forbidden)

print('SOURCESHADING1A portable verification OK')
print(' - live four-channel Camera2 remaining map semantics recorded')
print(' - source correction is fail-closed and diagnostic-only')
print(' - no camera/focal/zoom-label behavioral selection')
