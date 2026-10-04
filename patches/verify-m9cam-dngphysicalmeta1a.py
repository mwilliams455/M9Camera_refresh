#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-dngphysicalmeta1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
params_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/render/Parameters.java'
saver_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java'
queue_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java'
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
for p in (params_path, saver_path, queue_path, renderer_path):
    if not p.exists(): raise SystemExit(f'missing: {p}')

params = params_path.read_text()
saver = saver_path.read_text()
queue = queue_path.read_text()
renderer = renderer_path.read_text()

checks = {
    'legacy_recalc_delegates_global': 'ReCalcColorPhysical(customNeutr, result, CaptureController.mCameraCharacteristics);' in params,
    'physical_recalc_overload': 'public void ReCalcColorPhysical(boolean customNeutr, CaptureResult result,' in params,
    'physical_recalc_null_guard': 'DNGPHYSICALMETA1A missing physical CameraCharacteristics' in params,
    'm9_dng_physical_recalc': 'parameters.ReCalcColorPhysical(false, captureResult, characteristics);' in saver,
    'm9_dng_physical_black': 'characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN)' in saver,
    'dynamic_black_preserved': 'if (!parameters.usedDynamic)' in saver,
    'm9_physical_cfa_helper_retained': 'saveSingleRawM9PhysicalCfa' in saver,
    'ordinary_dng_helper_retained': 'return saveSingleRawInternal(dngFilePath, image, characteristics, captureResult,' in saver,
    'async_m9_dng_uses_physical_helper': 'ImageSaver.Util.saveSingleRawM9PhysicalCfa(' in queue,
    'renderer_not_rewired_to_dng_fix': 'ReCalcColorPhysical(false, captureResult, characteristics)' not in renderer,
}
for name, ok in checks.items():
    if not ok: raise SystemExit('FAIL ' + name)
    print('PASS ' + name)

# The explicit physical method must not silently fall back to the global camera.
start = params.index('public void ReCalcColorPhysical(boolean customNeutr')
# ReCalcColorPhysical is the last color-recalc body in the baseline; limit to a generous
# region ending at the next public method if present.
next_public = params.find('\n    public ', start + 20)
physical_body = params[start: next_public if next_public > start else len(params)]
if 'CaptureController.mCameraCharacteristics' in physical_body:
    raise SystemExit('FAIL physical_recalc_reads_global_camera')
print('PASS physical_recalc_does_not_read_global_camera')

# DNG metadata correction is post-capture metadata only; do not add any RAW-buffer or JPEG mutation.
segment_start = saver.index('private static boolean saveSingleRawInternal(')
segment_end = saver.find('\n        }\n', segment_start)
segment = saver[segment_start:segment_end]
for forbidden in ('image.buffer.put(', 'saveBitmapAsJPG', 'M9R35Renderer'):
    if forbidden in segment:
        raise SystemExit('FAIL DNG helper unexpected mutation/dependency: ' + forbidden)
print('PASS raw_bytes_and_jpeg_path_untouched')
print('DNGPHYSICALMETA1A VERIFY PASS')
