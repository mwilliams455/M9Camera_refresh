#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-deviceportspool1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9DevicePortAudit1A.java'
if not p.exists():
    raise SystemExit('DEVICEPORTSPOOL1B VERIFY missing audit helper')
s = p.read_text()

checks = {
    'async spool import': 'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;' in s,
    'async spool stage call': 'M9DiagnosticBurstSpool.stage(' in s,
    'spool schema telemetry': 'M9DiagnosticBurstSpool.SCHEMA' in s,
    'staged telemetry': 'sidecarStaged' in s,
    'nonblocking policy telemetry': 'async_private_spool_no_render_worker_storage_wait' in s,
    'blocking sidecar call absent': 'M9DiagnosticSidecarIO.persist(' not in s,
    'per-shot full inventory disabled': 'captureHotPathCameraManagerEnumeration", false' in s,
    'active descriptor retained': 'M9RawSensorDescriptor.fromActive(' in s,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('PASS ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('DEVICEPORTSPOOL1B VERIFY failed: ' + ', '.join(failed))
print('DEVICEPORTSPOOL1B VERIFY PASS')
print(' - active physical-source descriptor retained')
print(' - DEVICEPORT file persistence is staged, not blocking render-worker storage I/O')
