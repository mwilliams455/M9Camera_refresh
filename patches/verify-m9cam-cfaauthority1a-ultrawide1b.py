#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-cfaauthority1a-ultrawide1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
image_saver = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java').read_text()
queue = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java').read_text()
params = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/Parameters.java').read_text()
dng = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java').read_text()

checks = {
    'renderer Camera2 physical CFA authority': 'sourceCfaAuthority = "physical_camera2_characteristics"' in renderer,
    'renderer Photon fallback retained': 'sourceCfaAuthority = "photon_parameters_fallback"' in renderer,
    'renderer synchronizes M9 params CFA': 'params.cfaPattern = (byte) sourceCfaPattern;' in renderer,
    'authority before raw shading audit': renderer.find('params.cfaPattern = (byte) sourceCfaPattern;') < renderer.find('M9RawShadingAudit1A.captureAndWrite('),
    'authority before source calibration audit': renderer.find('params.cfaPattern = (byte) sourceCfaPattern;') < renderer.find('M9SourceCalibrationAudit1A.captureAndWrite('),
    'renderer authority diagnostic': 'out.diagnostics.put("cfaAuthority", sourceCfaAuthority);' in renderer,
    'generic four-CFA native path retained': 'M9NativeColorCore.demosaicMhcBayer(' in renderer,
    'legacy RGGB MHC path retained': 'M9NativeColorCore.demosaicMhcRggb(' in renderer,
    'legacy CFA0 dispatch retained': 'if (sourceCfaPattern == 0 && RAW_ORIGIN_X == 0 && RAW_ORIGIN_Y == 0)' in renderer,
    'M9-specific DNG helper added': 'saveSingleRawM9PhysicalCfa(' in image_saver,
    'ordinary Photon saveSingleRaw remains non-authoritative': 'cameraRotation, false);' in image_saver,
    'M9 DNG helper requests physical authority': 'cameraRotation, true);' in image_saver,
    'DNG helper reads Camera2 CFA': 'CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT' in image_saver,
    'M9 async queue uses physical-CFA DNG helper': 'ImageSaver.Util.saveSingleRawM9PhysicalCfa(' in queue,
    'old M9 async queue call removed': 'dngSaved = ImageSaver.Util.saveSingleRaw(\n                    job.dngPath' not in queue,
    'DngCreator still tags Parameters CFA': 'setCFAPattern(parameters.cfaPattern);' in dng,
    'global Photon manual CFA semantics preserved': 'PhotonCamera.getSettings().cfaPattern >= 0' in params,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('PASS ' if ok else 'FAIL ') + name)
if failed:
    raise SystemExit('CFAAUTHORITY1A verification failed: ' + ', '.join(failed))
print('CFAAUTHORITY1A/ULTRAWIDE1B PASS')
