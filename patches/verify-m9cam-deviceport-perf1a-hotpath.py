#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-deviceport-perf1a-hotpath.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9DevicePortAudit1A.java'
s = p.read_text()
start = s.index('    public static JSONObject captureAndWrite(')
end = s.index('\n    private static JSONArray enumerateRearRawCameras()', start)
hot = s[start:end]
checks = {
    'inventory_not_called_in_hot_path': 'enumerateRearRawCameras()' not in hot,
    'hot_path_enumeration_false': '"captureHotPathCameraManagerEnumeration", false' in hot,
    'inventory_policy_present': 'disabled_on_capture_hot_path' in hot,
    'active_descriptor_retained': 'M9RawSensorDescriptor.fromActive(' in hot,
    'inventory_helper_still_available_offline': 'private static JSONArray enumerateRearRawCameras()' in s,
}
failed = [k for k,v in checks.items() if not v]
if failed:
    for k in failed: print('FAIL', k)
    raise SystemExit('DEVICEPORT-PERF1A verification failed')
print('DEVICEPORT-PERF1A VERIFY PASS')
for k in checks: print('PASS', k)
