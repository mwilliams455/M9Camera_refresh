#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourceshading1a-portable.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
repo = Path(__file__).resolve().parents[1]
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

render_rel = Path('app/src/main/java/com/particlesdevs/photoncamera/m9/render')
audit_path = root / render_rel / 'M9DevicePortAudit1A.java'
payload = repo / 'payload' / render_rel / 'M9SourceShadingAudit1A.java'
target = root / render_rel / 'M9SourceShadingAudit1A.java'

if not audit_path.exists():
    raise SystemExit('SOURCESHADING1A requires DEVICEPORT1A assembled audit')
if not payload.exists():
    raise SystemExit('SOURCESHADING1A payload missing: ' + str(payload))

target.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(payload, target)

audit = audit_path.read_text()
anchor = '            out.put("activeRawSensorDescriptor", descriptor.toJson());\n'
insertion = '''            out.put("activeRawSensorDescriptor", descriptor.toJson());
            out.put("sourceShadingNormalization1A", M9SourceShadingAudit1A.describe(
                    rawWidth, rawHeight, activeCharacteristics, captureResult, captureRequest));
'''
if 'sourceShadingNormalization1A' not in audit:
    if audit.count(anchor) != 1:
        raise SystemExit('SOURCESHADING1A DEVICEPORT insertion anchor count != 1')
    audit = audit.replace(anchor, insertion, 1)
    audit_path.write_text(audit)

print('SOURCESHADING1A portable source descriptor applied')
print(' - Camera2 live remaining lens-shading map recorded without pixel mutation')
print(' - source adapter behavior remains independent of camera ID, focal length and zoom label')
print(' - RAW-to-active-array mapping remains fail-closed until proven')
print(' - shared M9 target renderer unchanged')
