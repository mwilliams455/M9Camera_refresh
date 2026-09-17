#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourceshading2a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()

files = {
    'ImageFrame': root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageFrame.java',
    'SaverImplementation': root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/SaverImplementation.java',
    'Renderer': root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'Helper': root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceShadingApply2A.java',
}
for name, p in files.items():
    if not p.exists():
        raise SystemExit(f'SOURCESHADING2A missing {name}: {p}')

image = files['ImageFrame'].read_text()
saver = files['SaverImplementation'].read_text()
renderer = files['Renderer'].read_text()
helper = files['Helper'].read_text()

required_image = [
    'm9SourceImageFormat', 'm9SourceImageWidth', 'm9SourceImageHeight',
    'm9SourceRowStrideBytes', 'm9SourcePixelStrideBytes',
    'm9SourceCopyOffsetBytes', 'm9SourceCopyCapacityBytes',
    'm9SourcePlaneCapacityBytes', 'm9SourceAspect169Requested',
    'm9SourceBinningRequested',
]
for token in required_image:
    if token not in image:
        raise SystemExit('SOURCESHADING2A ImageFrame provenance missing: ' + token)

required_saver = [
    'frame.m9SourceImageFormat = image.getFormat();',
    'frame.m9SourceImageWidth = image.getWidth();',
    'frame.m9SourceImageHeight = image.getHeight();',
    'frame.m9SourceRowStrideBytes = image.getPlanes()[0].getRowStride();',
    'frame.m9SourcePixelStrideBytes = image.getPlanes()[0].getPixelStride();',
    'frame.m9SourceCopyOffsetBytes = offset;',
    'frame.m9SourceCopyCapacityBytes = capacity;',
    'frame.m9SourcePlaneCapacityBytes = image.getPlanes()[0].getBuffer().capacity();',
]
for token in required_saver:
    if token not in saver:
        raise SystemExit('SOURCESHADING2A Saver provenance missing: ' + token)

required_helper = [
    'SOURCESHADING2A_ACQUISITIONPROOF_SAMERAW_GAINLOCK',
    'ImageFormat.RAW_SENSOR',
    'frame.m9SourceCopyOffsetBytes == 0',
    'frame.m9SourceRowStrideBytes == Math.multiplyExact(width, 2)',
    'frame.m9SourcePixelStrideBytes == 2',
    'SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE',
    'SENSOR_INFO_LENS_SHADING_APPLIED',
    'STATISTICS_LENS_SHADING_CORRECTION_MAP',
    '(out.mapColumns - 1) / (double)Math.max(1, width - 1)',
    '(out.mapRows - 1) / (double)Math.max(1, height - 1)',
    'channelFor(cfa, x, y)',
    'normalizedCfa[i] = (short)(q & 0xffffL);',
    'applied_live_Camera2_map_exactly_once',
    'deviceSpecificAestheticLogic',
    'm9TargetMutation',
]
for token in required_helper:
    if token not in helper:
        raise SystemExit('SOURCESHADING2A helper invariant missing: ' + token)

required_renderer = [
    'M9SourceShadingApply2A.applyInPlace(',
    'sourceShading2ARequested',
    'sourceShading2AForcedTc20Gain',
    'sourceShading2AComputedTc20Gain',
    'sourceShading2ATc20GainLockedToControl',
    'm9cam.sourceshading.v2a.sameraw.bank',
    '_SOURCESHADING2A_SAMERAW_GAINLOCK.jpg',
    'controlPixelMutation',
    'onlyIntendedVariant',
    'm9SensorTarget1ARuntimeVerified',
    'm9cam.tonebound.v1a.050ev',
    'saveSourceShading2AJpeg',
]
for token in required_renderer:
    if token not in renderer:
        raise SystemExit('SOURCESHADING2A renderer invariant missing: ' + token)

# The ordinary primary call must explicitly keep shading disabled. The second call
# must explicitly enable it and reuse the control TC20 decision.
if renderer.count('false, Double.NaN, frame, characteristics, captureResult, params.cfaPattern') != 1:
    raise SystemExit('SOURCESHADING2A primary control call is not unique/frozen')
if renderer.count('true, controlOriginalTc20, frame, characteristics, captureResult, params.cfaPattern') != 1:
    raise SystemExit('SOURCESHADING2A same-RAW variant call is not unique')

# Cobalt remains a retained control only; current M9SENSORTARGET runtime assertions
# must still exist and the historical adapter must remain forbidden in production.
for token in [
    'M9SENSORTARGET1A historical Cobalt calibration reached production context',
    'm9SensorTarget1ACobaltAssetUsedByRender',
    'm9SensorTarget1ATargetInputAdapterUsed',
    'm9SensorTarget1AHsmApplied',
    'SAT2_M04_M05_native_mode9',
    'curve02',
]:
    if token not in renderer:
        raise SystemExit('SOURCESHADING2A lost frozen M9SENSORTARGET invariant: ' + token)

print('SOURCESHADING2A VERIFY PASS')
print('PRIMARY control shading requested: false')
print('same-RAW variant shading requested: true')
print('TC20 gain-lock: control original decision -> variant before TONEBOUND')
print('RAW provenance gate: format/dimensions/stride/offset/capacity/crop/binning')
print('Camera2 map: exact endpoint grid + bilinear + R/Geven/Godd/B')
print('M9SENSORTARGET1A runtime assertions retained')
