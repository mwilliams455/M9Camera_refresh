#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-deviceportspool1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
device = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9DevicePortAudit1A.java').read_text()
spool = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java').read_text()
renderer = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()

# This verifier intentionally checks only invariants available immediately after
# DEVICEPORT/CFA assembly. SOURCESHADING1A and TARGETHSM1A are applied later and
# have their own dedicated post-assembly verifiers.
checks = {
    'existing_private_spool_schema': 'm9cam.sidecarspool.v1.privatebundle1b' in spool,
    'deviceport_uses_private_spool': 'M9DiagnosticBurstSpool.stage(' in device,
    'deviceport_records_spool_schema': 'M9DiagnosticBurstSpool.SCHEMA' in device,
    'deviceport_records_staged_state': 'sidecarStaged' in device,
    'blocking_public_persist_removed': 'M9DiagnosticSidecarIO.persist(' not in device,
    'camera_manager_inventory_still_disabled': 'captureHotPathCameraManagerEnumeration", false' in device,
    'offline_inventory_policy_retained': 'disabled_on_capture_hot_path_use_explicit_one_shot_inventory_if_needed' in device,
    'descriptor_retained': 'M9RawSensorDescriptor.fromActive(' in device,
    'jpeg_quality_95_retained': 'JPEG_QUALITY = 95' in renderer,
}
for name, ok in checks.items():
    print(('PASS ' if ok else 'FAIL ') + name)
if not all(checks.values()):
    raise SystemExit('DEVICEPORTSPOOL1A VERIFY FAILED')
print('DEVICEPORTSPOOL1A VERIFY PASS')
