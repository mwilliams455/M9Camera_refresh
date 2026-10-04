#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-deviceportspool1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
audit_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9DevicePortAudit1A.java'
spool_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not audit_path.exists():
    raise SystemExit('DEVICEPORTSPOOL1B missing M9DevicePortAudit1A.java')
if not spool_path.exists():
    raise SystemExit('DEVICEPORTSPOOL1B requires existing M9DiagnosticBurstSpool.java')
if not renderer_path.exists():
    raise SystemExit('DEVICEPORTSPOOL1B missing renderer')

spool = spool_path.read_text()
if 'public static boolean stage(' not in spool:
    raise SystemExit('DEVICEPORTSPOOL1B existing diagnostic spool has no stage() API')

renderer_before = hashlib.sha256(renderer_path.read_bytes()).hexdigest()
s = audit_path.read_text()

old_import = 'import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\n'
new_import = 'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;\n'
if new_import not in s:
    if old_import not in s:
        raise SystemExit('DEVICEPORTSPOOL1B transport import anchor missing')
    s = s.replace(old_import, new_import, 1)

old_block = '''                out.put("sidecarPath", sidecar.toString());
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean persisted = M9DiagnosticSidecarIO.persist(
                        sidecar, frozen, "deviceport1a_raw_sensor_probe");
                out.put("sidecarPersisted", persisted);
'''
new_block = '''                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticBurstSpool.SCHEMA);
                out.put("sidecarPersistencePolicy", "async_private_spool_no_render_worker_storage_wait");
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean staged = M9DiagnosticBurstSpool.stage(
                        sidecar, frozen, "deviceport1a_raw_sensor_probe");
                out.put("sidecarStaged", staged);
'''
if new_block not in s:
    if old_block not in s:
        raise SystemExit('DEVICEPORTSPOOL1B blocking persistence anchor missing')
    s = s.replace(old_block, new_block, 1)

if 'M9DiagnosticSidecarIO.persist(' in s:
    raise SystemExit('DEVICEPORTSPOOL1B blocking sidecar persistence still present')
if 'M9DiagnosticBurstSpool.stage(' not in s:
    raise SystemExit('DEVICEPORTSPOOL1B spool stage call missing')
if 'captureHotPathCameraManagerEnumeration", false' not in s:
    raise SystemExit('DEVICEPORTSPOOL1B requires DEVICEPORT-PERF1A inventory hot-path disable')

audit_path.write_text(s)
renderer_after = hashlib.sha256(renderer_path.read_bytes()).hexdigest()
if renderer_after != renderer_before:
    raise SystemExit('DEVICEPORTSPOOL1B unexpectedly changed renderer')

print('DEVICEPORTSPOOL1B applied')
print(' - DEVICEPORT JSON stages to existing asynchronous diagnostic spool')
print(' - direct/SAF persistence removed from render-worker DEVICEPORT call')
print(' - per-shot camera inventory enumeration remains disabled')
print(' - renderer bytes and all photographic arithmetic unchanged')
