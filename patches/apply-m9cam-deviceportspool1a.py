#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-deviceportspool1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9DevicePortAudit1A.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
p = root / rel
renderer = root / renderer_rel
if not p.exists() or not renderer.exists():
    raise SystemExit('DEVICEPORTSPOOL1A missing expected assembled source')

renderer_before = hashlib.sha256(renderer.read_bytes()).hexdigest()
text = p.read_text()
text = text.replace(
    'import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\n',
    'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;\n', 1)
old = '''                out.put("sidecarPath", sidecar.toString());
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean persisted = M9DiagnosticSidecarIO.persist(
                        sidecar, frozen, "deviceport1a_raw_sensor_probe");
                out.put("sidecarPersisted", persisted);
'''
new = '''                out.put("sidecarPath", sidecar.toString());
                out.put("sidecarTransport", M9DiagnosticBurstSpool.SCHEMA);
                byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
                boolean staged = M9DiagnosticBurstSpool.stage(
                        sidecar, frozen, "deviceport1a_raw_sensor_probe");
                out.put("sidecarStaged", staged);
'''
if old not in text:
    raise SystemExit('DEVICEPORTSPOOL1A blocking DEVICEPORT sidecar anchor missing')
text = text.replace(old, new, 1)
p.write_text(text)

post = p.read_text()
for marker in [
    'M9DiagnosticBurstSpool.stage(',
    'M9DiagnosticBurstSpool.SCHEMA',
    'sidecarStaged',
    'captureHotPathCameraManagerEnumeration", false',
    'disabled_on_capture_hot_path_use_explicit_one_shot_inventory_if_needed',
]:
    if marker not in post:
        raise SystemExit('DEVICEPORTSPOOL1A required marker missing: ' + marker)
if 'M9DiagnosticSidecarIO.persist(' in post:
    raise SystemExit('DEVICEPORTSPOOL1A blocking public sidecar persistence remains active')
if hashlib.sha256(renderer.read_bytes()).hexdigest() != renderer_before:
    raise SystemExit('DEVICEPORTSPOOL1A unexpectedly changed renderer')

print('DEVICEPORTSPOOL1A applied')
print(' - DEVICEPORT immutable JSON now stages to existing SIDECAR1B private spool')
print(' - legacy individual public export remains asynchronous through the spool')
print(' - all-camera CameraManager traversal remains disabled on capture hot path')
print(' - descriptor content, RAW bytes and photographic renderer unchanged')
