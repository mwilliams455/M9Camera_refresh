#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-nativeprospective1b-review1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
helper_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeProspective1A.java'
renderer_p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not helper_p.exists() or not renderer_p.exists():
    raise SystemExit('NATIVEPROSPECTIVE1B verify missing helper/renderer')
helper = helper_p.read_text()
renderer = renderer_p.read_text()

required = [
    'sourceFrameCount", 1',
    'captureMode", "single_frame_raw"',
    'hdrEnabled", false',
    'multiFrameFusion", false',
    'androidHdrGainmapUsed", false',
    'cobaltColorMatrixApplied", false',
    'cobaltForwardMatrixApplied", false',
    'cobaltHsmApplied", false',
    'leicaM9Curve02Applied", true',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'tc20Recomputed", false',
    'tc20ComparisonEligible", false',
    'frozen primary TC20 gain unavailable; prospective comparison refused',
    'nativeColorMatrixConvention", "DNG_XYZ_to_reference_camera_unmodified"',
    'nativeColorMatrixRowNormalizationApplied", false',
    'nativeForwardMatrixNormalizationApplied", true',
    'lensShadingHeadroomPolicy',
    'lensShadingStorageClipFraction',
    'cfaScope", "RGGB_main_only_until_CFA_aware_shading_and_demosaic_are_validated"',
    'fourRearCameraRendererClaimed", false',
    '_M9_NATIVEPROSPECTIVE.jpg',
]
for marker in required:
    if marker not in helper:
        raise SystemExit('NATIVEPROSPECTIVE1B verify missing marker: ' + marker)

for forbidden in [
    'Converter.normalizeFM(ncm1)',
    'Converter.normalizeFM(ncm2)',
    'HdrxProcessor',
    'UltraHDR',
    'UltraHdr',
    'mergeFrames(',
    'mergeRaw',
]:
    if forbidden in helper:
        raise SystemExit('NATIVEPROSPECTIVE1B verify forbidden helper marker: ' + forbidden)

# Primary control still encodes before the prospective sidecar hook and remains the
# ordinary Photon finished image.
primary_save = 'ImageSaver.Util.saveBitmapAsJPGPayloadM9(jpgPath, bitmap, JPEG_QUALITY, exif);'
prospective_hook = 'M9NativeProspective1A.renderAndSave('
if primary_save not in renderer or prospective_hook not in renderer:
    raise SystemExit('NATIVEPROSPECTIVE1B primary/prospective renderer anchors missing')
if renderer.index(primary_save) > renderer.index(prospective_hook):
    raise SystemExit('NATIVEPROSPECTIVE1B prospective hook occurs before frozen primary JPEG save')

print('M9 NATIVEPROSPECTIVE1B REVIEW1A verified')
print(' - corrected CM convention')
print(' - fixed primary TC20/edge-placement comparison')
print(' - single-frame LensShadingMap headroom policy recorded')
print(' - explicit RGGB main-only scientific scope')
print(' - primary JPEG remains encoded before nonfatal prospective sidecar')
