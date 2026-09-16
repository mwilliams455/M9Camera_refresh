#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-dngphysicalmeta1b-jsonexception1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists() or not renderer.exists():
    raise SystemExit('DNGPHYSICALMETA1B JSONEXCEPTION1A missing expected assembled source')

renderer_before = hashlib.sha256(renderer.read_bytes()).hexdigest()
text = p.read_text()
old_float = '        private static JSONArray floatArrayJson(float[] values) {\n'
new_float = '        private static JSONArray floatArrayJson(float[] values) throws org.json.JSONException {\n'
old_transform = '''        private static JSONArray transformJson(
                android.hardware.camera2.params.ColorSpaceTransform transform) {
'''
new_transform = '''        private static JSONArray transformJson(
                android.hardware.camera2.params.ColorSpaceTransform transform) throws org.json.JSONException {
'''
if old_float not in text:
    raise SystemExit('DNGPHYSICALMETA1B floatArrayJson signature anchor missing')
if old_transform not in text:
    raise SystemExit('DNGPHYSICALMETA1B transformJson signature anchor missing')
text = text.replace(old_float, new_float, 1)
text = text.replace(old_transform, new_transform, 1)
p.write_text(text)

post = p.read_text()
for marker in [
    'floatArrayJson(float[] values) throws org.json.JSONException',
    'ColorSpaceTransform transform) throws org.json.JSONException',
    'm9cam.dngphysicalmeta.v1b.writerinput',
    'writerPhysicalBindingPass',
    'M9DiagnosticBurstSpool.stage(',
]:
    if marker not in post:
        raise SystemExit('DNGPHYSICALMETA1B JSONEXCEPTION1A required marker missing: ' + marker)
if hashlib.sha256(renderer.read_bytes()).hexdigest() != renderer_before:
    raise SystemExit('DNGPHYSICALMETA1B JSONEXCEPTION1A unexpectedly changed renderer')

print('DNGPHYSICALMETA1B JSONEXCEPTION1A applied')
print(' - float-array and ColorSpaceTransform JSON helper signatures now propagate checked JSONException')
print(' - caller already catches Throwable; telemetry behavior is unchanged')
print(' - RAW/DNG pixel payload and JPEG renderer remain unchanged')
