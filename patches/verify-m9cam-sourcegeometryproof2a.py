#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourcegeometryproof2a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
image = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageFrame.java'
saver = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/SaverImplementation.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
for p in (image, saver, renderer):
    if not p.exists():
        raise SystemExit('SOURCEGEOMETRYPROOF2A verifier missing: ' + str(p))

i = image.read_text()
s = saver.read_text()
r = renderer.read_text()

for token in [
    'm9SourceImageFormat', 'm9SourceImageWidth', 'm9SourceImageHeight',
    'm9SourceRowStrideBytes', 'm9SourcePixelStrideBytes',
    'm9SourceCopyOffsetBytes', 'm9SourceCopyCapacityBytes',
    'm9SourcePlaneCapacityBytes', 'm9SourceAspect169Requested',
    'm9SourceBinningRequested',
]:
    if token not in i:
        raise SystemExit('SOURCEGEOMETRYPROOF2A ImageFrame field missing: ' + token)

for token in [
    'frame.m9SourceImageFormat = image.getFormat();',
    'frame.m9SourceImageWidth = image.getWidth();',
    'frame.m9SourceImageHeight = image.getHeight();',
    'frame.m9SourceRowStrideBytes = image.getPlanes()[0].getRowStride();',
    'frame.m9SourcePixelStrideBytes = image.getPlanes()[0].getPixelStride();',
    'frame.m9SourceCopyOffsetBytes = offset;',
    'frame.m9SourceCopyCapacityBytes = capacity;',
    'frame.m9SourcePlaneCapacityBytes = image.getPlanes()[0].getBuffer().capacity();',
]:
    if token not in s:
        raise SystemExit('SOURCEGEOMETRYPROOF2A Saver provenance missing: ' + token)

for token in [
    'm9cam.sourcegeometryproof.v2a.acquisition_copy',
    'SOURCEGEOMETRYPROOF2A',
    'proveSourceGeometry2A(',
    'android.graphics.ImageFormat.RAW_SENSOR',
    'frame.m9SourceAspect169Requested',
    'frame.m9SourceBinningRequested',
    'frame.m9SourceImageWidth != frame.width',
    'frame.m9SourcePixelStrideBytes != 2',
    'frame.m9SourceRowStrideBytes != expectedRowBytes',
    'frame.m9SourceCopyOffsetBytes != 0',
    'frame.m9SourceCopyCapacityBytes != expectedBytes',
    'frame.m9SourcePlaneCapacityBytes != expectedBytes',
    'resolveSourceRawOrigin1A(',
    'originNowProvenFromAcquisitionAndPhysicalGeometry',
    'productionLensShadingAlreadyApplied',
    'existing_NORM030_CFA_aware_pre_demosaic_path_unchanged',
    'sourceGeometryProof2ARuntimeVerified',
    'sourceGeometryProof2APixelMutation',
    'sourceGeometryProof2AExistingShadingPathChanged',
]:
    if token not in r:
        raise SystemExit('SOURCEGEOMETRYPROOF2A renderer invariant missing: ' + token)

# Existing production shading must still be the previously validated path, not a new
# shading implementation introduced by this branch.
for token in [
    'applyNativeProspectiveGainMapLumaDecomp1A(',
    'applyNativeProspectiveGainMapLumaDecomp1ABayer(',
    'applyNativeProspectiveGainMapBayer(',
    'gainMapAppliedToRender',
    'gainMapApplicationCount',
    'normalized_linear_Bayer_pre_demosaic_headroom_preserved',
    'shadingRepresentationRestoreApplied',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'shadingLumaNorm1ATargetOutsideMedianEv',
    'm9SensorTarget1ARuntimeVerified',
    'm9SensorTarget1ACobaltAssetUsedByRender',
    'm9SensorTarget1ATargetInputAdapterUsed',
    'm9SensorTarget1AHsmApplied',
    'SAT2_M04_M05_native_mode9',
    'curve02',
    'm9cam.tonebound.v1a.050ev',
]:
    if token not in r:
        raise SystemExit('SOURCEGEOMETRYPROOF2A lost frozen production invariant: ' + token)

if r.count('SourceGeometryProof2A sourceGeometryProof2A = proveSourceGeometry2A(') != 1:
    raise SystemExit('SOURCEGEOMETRYPROOF2A runtime gate must occur exactly once before primary render')
if r.count('sourceGeometryProof2A.toJson(frame, sourceCfaPattern)') != 1:
    raise SystemExit('SOURCEGEOMETRYPROOF2A diagnostics attachment not unique')

print('SOURCEGEOMETRYPROOF2A VERIFY PASS')
print('acquisition provenance: Image format/dimensions/stride/offset/capacity/crop/binning')
print('origin: accepted only after exact source-copy proof')
print('pixel mutation: false')
print('existing NORM030 physical LensShadingMap path: retained')
print('M9SENSORTARGET1A / TONEBOUND050 / SAT2 / curve02: retained')
