#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-edgeplacementgate1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('EDGEPLACEMENTGATE1A verify missing file: ' + rel)
    return p.read_text()

renderer = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
gradle = text('app/build.gradle')
native = text('app/src/main/cpp/m9color_jni.cpp')
policy = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
iso = text('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
back = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')

required = [
    'EDGEPLACEMENTGATE1A_RENDERGRID',
    'm9cam.edgeplacementgate.v1a.rendergrid',
    'diagnostic_only_finished_bitmap_no_pixel_mutation',
    'liveLiftEnabled", false',
    'gateDecisionAvailableInRenderer", false',
    'exact_bt601_q14_(4899R+9617G+1868B)>>14',
    'renderIntegralY',
    'renderIntegralVsMeanEv',
    'renderUpperVsLowerEv',
    'renderCellMedianP75',
    'renderGrid16x22',
    'renderMeanRegions4x6',
    'renderMedian4x6',
    'renderQ95_4x6',
    'bitmap.getPixels',
    '(4899 * r + 9617 * g + 1868 * b) >> 14',
    'integralMaskSum", 14160',
    'out.diagnostics.put("edgePlacementGate1A", edgePlacementGate1ARenderGrid(bitmap))',
    'JPEG_QUALITY = 95',
    'baselineExposureEv", 0.0',
    'METADATAFIX1A_PHYSICAL_ISO',
]
for token in required:
    if token not in renderer:
        raise SystemExit('EDGEPLACEMENTGATE1A verify missing renderer token: ' + token)

if '-metadatafix1a-edgeplacementgate1a' not in gradle:
    raise SystemExit('EDGEPLACEMENTGATE1A build identity missing expected suffix')

# The live correction must not exist in this diagnostic build.
for forbidden in [
    'effectiveRenderGain',
    'edgePlacementLiftEv',
    'EDGEPLACEMENTLIFT1A',
]:
    if forbidden in renderer:
        raise SystemExit('EDGEPLACEMENTGATE1A forbidden live-lift token present: ' + forbidden)

# No EDGEPLACEMENT code is allowed in native color, capture AE, ISO allocator or
# existing backlight feedback. The only changed production source is the Java
# finished-bitmap renderer diagnostics seam.
for rel, src in [
    ('m9color_jni.cpp', native),
    ('M9ModernExposurePolicy.java', policy),
    ('IsoExpoSelector.java', iso),
    ('M9BacklightDiagnostic.java', back),
]:
    if 'EDGEPLACEMENTGATE1A' in src or 'EDGEPLACEMENTLIFT1A' in src:
        raise SystemExit('EDGEPLACEMENTGATE1A leaked into frozen seam: ' + rel)

print('M9Cam EDGEPLACEMENTGATE1A verifier PASS')
print(' - telemetry is downstream of finished bitmap')
print(' - exact 16x22/4x6 BT601-Y evidence present')
print(' - live lift absent')
print(' - JPEG95 and METADATAFIX1A markers retained')
print(' - native color / capture AE / ISO allocator / backlight scorer remain EDGEPLACEMENT-free')
