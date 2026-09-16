#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-dngphysicalmeta1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
params_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/render/Parameters.java'
saver_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java'
for p in (params_path, saver_path):
    if not p.exists():
        raise SystemExit(f'missing required file: {p}')

# Photon ReCalcColor historically reads CaptureController.mCameraCharacteristics.
# Preserve that behavior for all ordinary Photon callers, but expose an explicit
# characteristics-bound overload for the M9 DNG path so rapid physical-camera
# switching cannot attach the previous sensor's matrices to the current RAW.
params = params_path.read_text()
old_head = '''    public void ReCalcColor(boolean customNeutr, CaptureResult result) {\n        CameraCharacteristics characteristics = CaptureController.mCameraCharacteristics;\n'''
new_head = '''    public void ReCalcColor(boolean customNeutr, CaptureResult result) {\n        ReCalcColorPhysical(customNeutr, result, CaptureController.mCameraCharacteristics);\n    }\n\n    // DNGPHYSICALMETA1A: explicit physical-sensor color authority. Ordinary Photon\n    // behavior above remains unchanged; only M9 callers opt into this overload.\n    public void ReCalcColorPhysical(boolean customNeutr, CaptureResult result,\n                                    CameraCharacteristics characteristics) {\n        if (characteristics == null) {\n            throw new IllegalArgumentException("DNGPHYSICALMETA1A missing physical CameraCharacteristics");\n        }\n'''
if 'ReCalcColorPhysical(boolean customNeutr' not in params:
    if params.count(old_head) != 1:
        raise SystemExit('Parameters ReCalcColor anchor missing/ambiguous')
    params = params.replace(old_head, new_head, 1)
params_path.write_text(params)

saver = saver_path.read_text()
method_sig = '        private static boolean saveSingleRawInternal(Path dngFilePath,'
start = saver.find(method_sig)
if start < 0:
    raise SystemExit('CFAAUTHORITY1A saveSingleRawInternal missing; apply after CFA authority patch')
end = saver.find('\n        }\n', start)
if end < 0:
    raise SystemExit('saveSingleRawInternal end missing')
segment = saver[start:end]
anchor = '''            int iso = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);\n            parameters.FillDynamicParameters(captureResult, null, iso);\n            parameters.cameraRotation = cameraRotation;\n'''
insert = '''            int iso = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);\n            parameters.FillDynamicParameters(captureResult, null, iso);\n            if (physicalCfaAuthority) {\n                // FillDynamicParameters/ReCalcColor use Photon's global current-camera\n                // characteristics. Recompute only the M9 DNG metadata from the immutable\n                // physical characteristics carried with this RAW job. RAW bytes are untouched.\n                parameters.ReCalcColorPhysical(false, captureResult, characteristics);\n\n                // Photon defaults to static black level unless dynamic black was explicitly\n                // selected. If dynamic black was not used, replace the potentially stale\n                // global-camera black pattern with this RAW sensor's physical pattern.\n                if (!parameters.usedDynamic) {\n                    android.hardware.camera2.params.BlackLevelPattern physicalBlack =\n                            characteristics.get(CameraCharacteristics.SENSOR_BLACK_LEVEL_PATTERN);\n                    if (physicalBlack != null) {\n                        int[] physicalBlackValues = new int[4];\n                        physicalBlack.copyTo(physicalBlackValues, 0);\n                        for (int i = 0; i < 4; i++) {\n                            parameters.blackLevel[i] = physicalBlackValues[i];\n                        }\n                    }\n                }\n            }\n            parameters.cameraRotation = cameraRotation;\n'''
if 'parameters.ReCalcColorPhysical(false, captureResult, characteristics);' not in segment:
    if segment.count(anchor) != 1:
        raise SystemExit('M9 DNG dynamic-parameter anchor missing/ambiguous')
    segment = segment.replace(anchor, insert, 1)
    saver = saver[:start] + segment + saver[end:]
saver_path.write_text(saver)

print('DNGPHYSICALMETA1A applied')
print(' - ordinary Photon ReCalcColor keeps global-current-camera behavior')
print(' - M9 DNG color matrices/illuminants/neutral are recomputed from job physical characteristics + capture result')
print(' - M9 DNG static black pattern is rebound to physical characteristics when dynamic black is not active')
print(' - RAW bytes and JPEG renderer are unchanged')
