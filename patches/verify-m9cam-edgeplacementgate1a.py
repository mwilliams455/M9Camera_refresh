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
luma = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderedLumaDiagnostic.java')
edge = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9EdgePlacementGate1ADiagnostic.java')
gradle = text('app/build.gradle')
native = text('app/src/main/cpp/m9color_jni.cpp')
policy = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java')
iso = text('app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
back = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java')

for token in [
    'm9cam.edgeplacementgate.v1a.rendergrid',
    'diagnostic_only_finished_bitmap_no_pixel_mutation',
    'liveLiftEnabled", false',
    'usedToMutateRenderer", false',
    'usedToMutateCapture", false',
    'gateDecisionAvailableInRenderer", false',
    'exact_bt601_q14_(4899R+9617G+1868B)>>14',
    'integer_floor_cell_boundaries_match_offline_rendergrid',
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
    'maskSum != 14160L',
    'elapsedMs',
]:
    if token not in edge:
        raise SystemExit('EDGEPLACEMENTGATE1A verify missing helper token: ' + token)

if 'out.put("edgePlacementGate1A", M9EdgePlacementGate1ADiagnostic.measure(bitmap));' not in luma:
    raise SystemExit('EDGEPLACEMENTGATE1A not attached to existing rendered-luma diagnostic')
if 'm9cam.renderedluma.v1.grid64' not in luma or 'read_only_finished_bitmap_sampling' not in luma:
    raise SystemExit('EDGEPLACEMENTGATE1A lost CAPTURESPLIT1B rendered-luma identity')

# Renderer must still contain the one pre-existing CAPTURESPLIT1B hook and no new EDGEPLACEMENT call.
if 'out.diagnostics.put("directRenderedLuma", M9RenderedLumaDiagnostic.measure(bitmap));' not in renderer:
    raise SystemExit('EDGEPLACEMENTGATE1A existing directRenderedLuma renderer hook missing')
if 'M9EdgePlacementGate1ADiagnostic' in renderer or 'edgePlacementGate1A' in renderer:
    raise SystemExit('EDGEPLACEMENTGATE1A leaked a second hook into renderer')
for token in ['JPEG_QUALITY = 95', 'baselineExposureEv", 0.0', 'METADATAFIX1A_PHYSICAL_ISO']:
    if token not in renderer:
        raise SystemExit('EDGEPLACEMENTGATE1A frozen renderer marker missing: ' + token)

if '-metadatafix1a-edgeplacementgate1a' not in gradle:
    raise SystemExit('EDGEPLACEMENTGATE1A build identity missing expected suffix')

for forbidden in ['effectiveRenderGain', 'edgePlacementLiftEv', 'EDGEPLACEMENTLIFT1A']:
    if forbidden in edge or forbidden in luma or forbidden in renderer:
        raise SystemExit('EDGEPLACEMENTGATE1A forbidden live-lift token present: ' + forbidden)

for rel, src in [
    ('m9color_jni.cpp', native),
    ('M9ModernExposurePolicy.java', policy),
    ('IsoExpoSelector.java', iso),
    ('M9BacklightDiagnostic.java', back),
]:
    if 'EDGEPLACEMENTGATE1A' in src or 'EDGEPLACEMENTLIFT1A' in src or 'M9EdgePlacementGate1ADiagnostic' in src:
        raise SystemExit('EDGEPLACEMENTGATE1A leaked into frozen seam: ' + rel)

# Structural sanity of recovered geometry.
start = edge.find('private static final int[] INTEGRAL_MASK')
end = edge.find('};', start)
if start < 0 or end < 0:
    raise SystemExit('EDGEPLACEMENTGATE1A Integral mask literal missing')
import re
nums = [int(x) for x in re.findall(r'-?\d+', edge[edge.find('{', start)+1:end])]
if len(nums) != 352 or sum(nums) != 14160:
    raise SystemExit(f'EDGEPLACEMENTGATE1A Integral mask invalid: n={len(nums)} sum={sum(nums)}')

print('M9Cam EDGEPLACEMENTGATE1A verifier PASS')
print(' - reuses exactly one existing CAPTURESPLIT1B renderer hook')
print(' - renderer itself remains EDGEPLACEMENT-free')
print(' - exact all-pixel BT601-Q14 16x22/4x6 evidence present')
print(' - recovered Integral mask 352 cells / sum 14160 verified')
print(' - live lift absent; JPEG95 and METADATAFIX1A markers retained')
print(' - native color / capture AE / ISO allocator / backlight scorer remain EDGEPLACEMENT-free')
