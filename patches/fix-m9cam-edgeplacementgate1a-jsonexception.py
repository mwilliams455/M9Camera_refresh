#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-edgeplacementgate1a-jsonexception.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9EdgePlacementGate1ADiagnostic.java'
p = root / rel
if not p.exists():
    raise SystemExit('EDGEPLACEMENTGATE1A JSONEXCEPTION fix missing generated helper')

s = p.read_text()
repls = {
    'private static JSONArray arrayJson(double[] values) {':
        'private static JSONArray arrayJson(double[] values) throws org.json.JSONException {',
    'private static JSONArray gridJson(double[] grid) {':
        'private static JSONArray gridJson(double[] grid) throws org.json.JSONException {',
}
for old, new in repls.items():
    if new in s:
        continue
    if old not in s:
        raise SystemExit('EDGEPLACEMENTGATE1A JSONEXCEPTION anchor missing: ' + old)
    s = s.replace(old, new, 1)

p.write_text(s)
print('M9Cam EDGEPLACEMENTGATE1A JSONEXCEPTION compile fix applied')
print(' - only generated diagnostic helper signatures changed')
print(' - renderer/capture/TC20/JPEG paths untouched')
