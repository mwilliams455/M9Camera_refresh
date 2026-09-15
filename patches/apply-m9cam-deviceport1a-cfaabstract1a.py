#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-deviceport1a-cfaabstract1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
repo = Path(__file__).resolve().parents[1]
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

renderer_rel = Path('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
renderer_path = root / renderer_rel
renderer = renderer_path.read_text()

if 'params.FillDynamicParameters(captureResult, captureRequest, iso);' not in renderer:
    raise SystemExit('DEVICEPORT1A dynamic-parameter anchor missing')
if 'R3.5 v0.7 main-camera parity build expects RGGB CFA=0' not in renderer:
    raise SystemExit('DEVICEPORT1A expected frozen RGGB fail-closed gate missing')

payload_base = repo / 'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render'
target_base = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render'
for name in ('M9CfaResolver.java', 'M9RawSensorDescriptor.java', 'M9DevicePortAudit1A.java'):
    source = payload_base / name
    if not source.exists():
        raise SystemExit('DEVICEPORT1A missing payload source: ' + str(source))
    target_base.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target_base / name)

anchor = '''            params.FillDynamicParameters(captureResult, captureRequest, iso);
            params.cameraRotation = cameraRotation;

            // Frozen main-camera R3.5 reference is RGGB.  Fail loudly rather than
'''
insert = '''            params.FillDynamicParameters(captureResult, captureRequest, iso);
            params.cameraRotation = cameraRotation;

            // DEVICEPORT1A/CFAABSTRACT1A: probe source RAW metadata before the frozen
            // RGGB photographic gate. Diagnostic only; no descriptor value feeds pixels.
            M9DevicePortAudit1A.captureAndWrite(
                    dngPath,
                    frame.width,
                    frame.height,
                    frame.buffer != null ? frame.buffer.capacity() : -1,
                    params,
                    characteristics,
                    captureResult,
                    captureRequest);

            // Frozen main-camera R3.5 reference is RGGB.  Fail loudly rather than
'''

if 'M9DevicePortAudit1A.captureAndWrite(' not in renderer:
    if renderer.count(anchor) != 1:
        raise SystemExit('DEVICEPORT1A renderer hook anchor count != 1')
    renderer = renderer.replace(anchor, insert, 1)
    renderer_path.write_text(renderer)

print('DEVICEPORT1A/CFAABSTRACT1A applied')
print('photographic renderer remains on the frozen RGGB gate in this probe build')
