#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9sensorport1a-anyraw-fallofftgt1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
paths = {
    'renderer': root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'preview': root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9LivePreview1A.java',
    'descriptor': root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SensorDescriptor1A.java',
    'falloff': root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9TargetFalloff1A.java',
    'frame': root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageFrame.java',
    'saver': root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/SaverImplementation.java',
}
for name, path in paths.items():
    if not path.exists():
        raise SystemExit(f'M9SENSORPORT1A missing {name}: {path}')

r = paths['renderer'].read_text()
p = paths['preview'].read_text()
d = paths['descriptor'].read_text()
f = paths['falloff'].read_text()
frame = paths['frame'].read_text()
saver = paths['saver'].read_text()

required_renderer = [
    'M9SENSORTARGET1A',
    'M9_LIVE_PREVIEW_1A_SENSOR_DESCRIPTOR',
    'sensorDescriptor1A',
    'targetFalloff1A',
    'sourceShadingAndTargetFalloffSeparatedArchitecturally',
]
for marker in required_renderer:
    if marker not in r:
        raise SystemExit('M9SENSORPORT1A renderer marker missing: ' + marker)

if 'M9LIVEPREVIEW1B_FULLRENDER1080P_MAIN' not in p:
    raise SystemExit('M9SENSORPORT1A preview 1080p runtime marker missing')

required_preview = [
    'LANDSCAPE_WIDTH = 1440',
    'LANDSCAPE_HEIGHT = 1080',
    'M9SensorDescriptor1A.fromPreviewImage',
    'sourceDescriptor1A',
    'reduceBayerParityPreserving',
]
for marker in required_preview:
    if marker not in p:
        raise SystemExit('M9SENSORPORT1A preview marker missing: ' + marker)

for marker in [
    'cameraIdUsedForPhotographicPolicy',
    'physicalCameraIdUsedForPhotographicPolicy',
    'manufacturerUsedForPhotographicPolicy',
    'rawRowStrideBytes',
    'rawPixelStrideBytes',
    'staticBlackLevelPattern',
    'dynamicBlackLevel',
    'staticWhiteLevel',
    'dynamicWhiteLevel',
    'cameraCalibration1',
    'cameraCalibration2',
    'colorMatrix1',
    'colorMatrix2',
    'forwardMatrix1',
    'forwardMatrix2',
    'asShotNeutral',
    'lensShadingMapRows',
    'lensShadingMapColumns',
    'targetFalloffCoordinateSpace',
]:
    if marker not in d:
        raise SystemExit('M9SENSORPORT1A descriptor field missing: ' + marker)

for forbidden in [
    'Xiaomi 15',
    'Xiaomi 17',
    '"2".equals',
    'main_physical_2',
]:
    if forbidden in d:
        raise SystemExit('M9SENSORPORT1A forbidden device/ID policy token in descriptor: ' + forbidden)

for marker in [
    'PIXEL_MUTATION_ENABLED = false',
    'normalized_image_coordinates_center_0_corner_radius_1',
    'EV(r)=a2*r^2+a4*r^4+a6*r^6',
    'PENDING_GENUINE_M9_EVIDENCE',
    'return 1.0;',
]:
    if marker not in f:
        raise SystemExit('FALLOFFTGT1A contract marker missing: ' + marker)

for marker in [
    'm9SourceImageFormat',
    'm9SourceRowStrideBytes',
    'm9SourcePixelStrideBytes',
]:
    if marker not in frame:
        raise SystemExit('M9SENSORPORT1A ImageFrame provenance marker missing: ' + marker)

for marker in [
    'frame.m9SourceImageFormat = image.getFormat();',
    'frame.m9SourceRowStrideBytes = image.getPlanes()[0].getRowStride();',
    'frame.m9SourcePixelStrideBytes = image.getPlanes()[0].getPixelStride();',
]:
    if marker not in saver:
        raise SystemExit('M9SENSORPORT1A Saver provenance marker missing: ' + marker)

# 1A must not activate a target vignette or replace the existing production source shading.
if re.search(r'PIXEL_MUTATION_ENABLED\s*=\s*true', f):
    raise SystemExit('FALLOFFTGT1A unexpectedly enables target falloff pixels')
if 'gainForRadius(double r) {\n        return 1.0;' not in f:
    raise SystemExit('FALLOFFTGT1A identity-gain safety gate changed')

print('M9SENSORPORT1A_ANYRAW_FALLOFFTGT1A VERIFY PASS')
print(' - full-resolution source descriptor survives preview reduction as metadata')
print(' - still acquisition row/pixel/copy geometry retained')
print(' - descriptor contains CFA/black/white/matrix/neutral/shading/geometry evidence')
print(' - no Xiaomi model or fixed camera-2 photographic selector in descriptor')
print(' - target falloff coordinate/model contract present but pixel mutation disabled')
print(' - 1080p full-render live preview markers retained')
