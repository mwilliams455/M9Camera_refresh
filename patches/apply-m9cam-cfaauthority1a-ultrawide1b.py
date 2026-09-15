#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-cfaauthority1a-ultrawide1b.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
image_saver_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java'
queue_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java'

renderer = renderer_path.read_text()

probe_tail = '''                    captureResult,\n                    captureRequest);\n'''
authority = '''\n            // CFAAUTHORITY1A: Parameters.FillConstParameters permits Photon's global CFA\n            // setting to override Camera2. For the M9 portability path the active physical\n            // sensor characteristic is authoritative whenever it reports a conventional\n            // Bayer layout. Keep Photon's value only as a fail-closed fallback.\n            final int photonCfaPatternBeforeAuthority = params.cfaPattern & 0xff;\n            final Integer physicalCamera2CfaObj = characteristics != null\n                    ? characteristics.get(CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT)\n                    : null;\n            final int physicalCamera2CfaPattern = physicalCamera2CfaObj != null\n                    ? physicalCamera2CfaObj : -1;\n            final int sourceCfaPattern;\n            final String sourceCfaAuthority;\n            if (M9CfaResolver.isSupported(physicalCamera2CfaPattern)) {\n                sourceCfaPattern = physicalCamera2CfaPattern;\n                sourceCfaAuthority = "physical_camera2_characteristics";\n            } else if (M9CfaResolver.isSupported(photonCfaPatternBeforeAuthority)) {\n                sourceCfaPattern = photonCfaPatternBeforeAuthority;\n                sourceCfaAuthority = "photon_parameters_fallback";\n            } else {\n                throw new IllegalStateException(\n                        "CFAAUTHORITY1A no supported Bayer CFA; camera2="\n                                + physicalCamera2CfaPattern + "; photon="\n                                + photonCfaPatternBeforeAuthority);\n            }\n            // Synchronize M9-only downstream audits/source calibration with the same source\n            // lattice consumed by the renderer. This does not mutate global Photon settings.\n            params.cfaPattern = (byte) sourceCfaPattern;\n'''

if 'CFAAUTHORITY1A: Parameters.FillConstParameters' not in renderer:
    probe_anchor = renderer.find('            // DEVICEPORT1A/CFAABSTRACT1A: probe source RAW metadata')
    if probe_anchor < 0:
        raise SystemExit('DEVICEPORT probe anchor missing')
    probe_call = renderer.find('            M9DevicePortAudit1A.captureAndWrite(', probe_anchor)
    if probe_call < 0:
        raise SystemExit('DEVICEPORT probe call missing')
    end = renderer.find(probe_tail, probe_call)
    if end < 0:
        raise SystemExit('DEVICEPORT probe call tail missing')
    end += len(probe_tail)
    renderer = renderer[:end] + authority + renderer[end:]

old_decl = '            final int sourceCfaPattern = params.cfaPattern & 0xff;\n'
if old_decl in renderer:
    if renderer.count(old_decl) != 1:
        raise SystemExit('ambiguous sourceCfaPattern declaration count')
    renderer = renderer.replace(old_decl, '', 1)

render_elapsed = '            long renderCoreElapsedMs = (System.nanoTime() - renderCoreStartedNs) / 1_000_000L;\n'
diag = '''            out.diagnostics.put("cfaAuthority", sourceCfaAuthority);\n            out.diagnostics.put("camera2PhysicalCfaPattern", physicalCamera2CfaPattern);\n            out.diagnostics.put("photonCfaPatternBeforeAuthority", photonCfaPatternBeforeAuthority);\n            out.diagnostics.put("resolvedSourceCfaPattern", sourceCfaPattern);\n'''
if 'out.diagnostics.put("cfaAuthority"' not in renderer:
    if renderer.count(render_elapsed) < 1:
        raise SystemExit('render elapsed anchor missing')
    pos = renderer.find(render_elapsed) + len(render_elapsed)
    renderer = renderer[:pos] + diag + renderer[pos:]

renderer_path.write_text(renderer)

image_saver = image_saver_path.read_text()
old_method = '''        public static boolean saveSingleRaw(Path dngFilePath,\n                                            ImageFrame image,\n                                            CameraCharacteristics characteristics,\n                                            CaptureResult captureResult,\n                                            int cameraRotation) {\n            Parameters parameters = new Parameters();\n\n            parameters.FillConstParameters(characteristics, new Point(image.width, image.height));\n            int iso = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);\n            parameters.FillDynamicParameters(captureResult, null, iso);\n            parameters.cameraRotation = cameraRotation;\n            Log.d(TAG, "Camera rotation: " + parameters.cameraRotation);\n            Log.d(TAG, "activearr:" + characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE));\n            Log.d(TAG, "precorr:" + characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE));\n            return saveSingleRaw(dngFilePath, image.buffer, parameters);\n        }\n'''
new_method = '''        public static boolean saveSingleRaw(Path dngFilePath,\n                                            ImageFrame image,\n                                            CameraCharacteristics characteristics,\n                                            CaptureResult captureResult,\n                                            int cameraRotation) {\n            return saveSingleRawInternal(dngFilePath, image, characteristics, captureResult,\n                    cameraRotation, false);\n        }\n\n        /**\n         * CFAAUTHORITY1A M9-only DNG path. Camera2 physical CFA wins over Photon's\n         * optional global CFA override so the DNG tag describes the actual RAW mosaic.\n         * The ordinary Photon saveSingleRaw behavior above remains unchanged.\n         */\n        public static boolean saveSingleRawM9PhysicalCfa(Path dngFilePath,\n                                                         ImageFrame image,\n                                                         CameraCharacteristics characteristics,\n                                                         CaptureResult captureResult,\n                                                         int cameraRotation) {\n            return saveSingleRawInternal(dngFilePath, image, characteristics, captureResult,\n                    cameraRotation, true);\n        }\n\n        private static boolean saveSingleRawInternal(Path dngFilePath,\n                                                     ImageFrame image,\n                                                     CameraCharacteristics characteristics,\n                                                     CaptureResult captureResult,\n                                                     int cameraRotation,\n                                                     boolean physicalCfaAuthority) {\n            Parameters parameters = new Parameters();\n\n            parameters.FillConstParameters(characteristics, new Point(image.width, image.height));\n            if (physicalCfaAuthority && characteristics != null) {\n                Integer physicalCfa = characteristics.get(\n                        CameraCharacteristics.SENSOR_INFO_COLOR_FILTER_ARRANGEMENT);\n                if (physicalCfa != null && physicalCfa >= 0 && physicalCfa <= 3) {\n                    parameters.cfaPattern = (byte) (int) physicalCfa;\n                }\n            }\n            int iso = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);\n            parameters.FillDynamicParameters(captureResult, null, iso);\n            parameters.cameraRotation = cameraRotation;\n            Log.d(TAG, "Camera rotation: " + parameters.cameraRotation);\n            Log.d(TAG, "activearr:" + characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE));\n            Log.d(TAG, "precorr:" + characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE));\n            return saveSingleRaw(dngFilePath, image.buffer, parameters);\n        }\n'''

if 'saveSingleRawM9PhysicalCfa' not in image_saver:
    if image_saver.count(old_method) != 1:
        raise SystemExit('exact ImageSaver single-raw method anchor missing/ambiguous')
    image_saver = image_saver.replace(old_method, new_method, 1)
image_saver_path.write_text(image_saver)

queue = queue_path.read_text()
old_queue_call = '''            dngSaved = ImageSaver.Util.saveSingleRaw(\n                    job.dngPath,\n                    job.ownedFrame,\n                    job.characteristics,\n                    job.captureResult,\n                    job.cameraRotation);\n'''
new_queue_call = '''            dngSaved = ImageSaver.Util.saveSingleRawM9PhysicalCfa(\n                    job.dngPath,\n                    job.ownedFrame,\n                    job.characteristics,\n                    job.captureResult,\n                    job.cameraRotation);\n'''
if 'saveSingleRawM9PhysicalCfa(' not in queue:
    if queue.count(old_queue_call) != 1:
        raise SystemExit('exact M9 DNG async call anchor missing/ambiguous')
    queue = queue.replace(old_queue_call, new_queue_call, 1)
queue_path.write_text(queue)

print('CFAAUTHORITY1A/ULTRAWIDE1B applied')
print(' - M9 renderer uses physical Camera2 CFA with Photon fallback')
print(' - M9 source/shading audits share resolved CFA')
print(' - M9 async DNG writer tags physical CFA')
print(' - ordinary Photon CFA override behavior remains unchanged')
