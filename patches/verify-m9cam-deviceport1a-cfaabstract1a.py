#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-deviceport1a-cfaabstract1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
base = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render'
renderer = (base / 'M9R35Renderer.java').read_text()
cfa = (base / 'M9CfaResolver.java').read_text()
desc = (base / 'M9RawSensorDescriptor.java').read_text()
audit = (base / 'M9DevicePortAudit1A.java').read_text()

checks = {
    'renderer_probe_hook': 'M9DevicePortAudit1A.captureAndWrite(' in renderer,
    'frozen_rggb_gate_retained': 'R3.5 v0.7 main-camera parity build expects RGGB CFA=0' in renderer,
    'frozen_opencv_rggb_retained': 'Imgproc.COLOR_BayerRG2BGR_EA' in renderer,
    'frozen_raw_max_retained': 'private static final int RAW_MAX = 16383;' in renderer,
    'frozen_jpeg_quality_retained': 'public static final int JPEG_QUALITY = 95;' in renderer,
    'four_bayer_patterns': all(x in cfa for x in ('RGGB(0)', 'GRBG(1)', 'GBRG(2)', 'BGGR(3)')),
    'unsupported_fail_closed': 'UNSUPPORTED(-1)' in cfa and 'throw new IllegalArgumentException("unsupported CFA pattern")' in cfa,
    'origin_phase_supported': 'localX + originX' in cfa and 'localY + originY' in cfa,
    'descriptor_origin_unproven': 'this.rawOriginProven = false;' in desc,
    'descriptor_black_level': 'SENSOR_BLACK_LEVEL_PATTERN' in desc,
    'descriptor_white_level': 'SENSOR_INFO_WHITE_LEVEL' in desc,
    'descriptor_lens_shading': 'SENSOR_INFO_LENS_SHADING_APPLIED' in desc and 'STATISTICS_LENS_SHADING_CORRECTION_MAP' in desc,
    'descriptor_arrays': 'SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE' in desc and 'SENSOR_INFO_ACTIVE_ARRAY_SIZE' in desc,
    'descriptor_matrices': 'SENSOR_FORWARD_MATRIX1' in desc and 'SENSOR_COLOR_TRANSFORM1' in desc and 'SENSOR_CALIBRATION_TRANSFORM1' in desc,
    'inventory_raw_capability': 'REQUEST_AVAILABLE_CAPABILITIES_RAW' in audit,
    'inventory_physical_ids': 'getPhysicalCameraIds()' in audit,
    'inventory_raw_sizes': 'ImageFormat.RAW_SENSOR' in audit,
    'sidecar_name': '_M9_DEVICEPORT1A.json' in audit,
    'diagnostic_only_marker': 'photographicPixelChange' in audit and 'false' in audit,
}

failed = [k for k, ok in checks.items() if not ok]
for key, ok in checks.items():
    print(('OK   ' if ok else 'FAIL ') + key)
if failed:
    raise SystemExit('DEVICEPORT1A verification failed: ' + ', '.join(failed))
print('DEVICEPORT1A/CFAABSTRACT1A verify PASS')
