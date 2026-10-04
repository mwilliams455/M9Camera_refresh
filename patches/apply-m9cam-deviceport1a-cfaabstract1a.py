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

gate_token = 'if (params.cfaPattern != 0)'
gate = renderer.find(gate_token)
if gate < 0:
    raise SystemExit('DEVICEPORT1A expected frozen RGGB fail-closed gate missing')

fill_token = 'params.FillDynamicParameters(captureResult, captureRequest, iso);'
rotation_token = '            params.cameraRotation = cameraRotation;\n'
rotation = renderer.rfind(rotation_token, 0, gate)
fill = renderer.rfind(fill_token, 0, rotation if rotation >= 0 else gate)
if rotation < 0 or fill < 0:
    raise SystemExit('DEVICEPORT1A could not resolve dynamic-parameter block immediately before CFA gate')
if gate - rotation > 1600 or rotation - fill > 800:
    raise SystemExit('DEVICEPORT1A resolved anchors are too far apart; refusing ambiguous insertion')

payload_base = repo / 'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render'
target_base = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render'
for name in ('M9CfaResolver.java', 'M9RawSensorDescriptor.java', 'M9DevicePortAudit1A.java'):
    source = payload_base / name
    if not source.exists():
        raise SystemExit('DEVICEPORT1A missing payload source: ' + str(source))
    target_base.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target_base / name)

probe = '''
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
'''

if 'M9DevicePortAudit1A.captureAndWrite(' not in renderer:
    insert_at = rotation + len(rotation_token)
    renderer = renderer[:insert_at] + probe + renderer[insert_at:]
    renderer_path.write_text(renderer)

print('DEVICEPORT1A/CFAABSTRACT1A applied')
print(' - active probe anchored immediately before the existing RGGB fail-closed gate')
print(' - photographic renderer remains frozen in this probe build')
