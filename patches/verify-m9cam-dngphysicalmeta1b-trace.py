#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-dngphysicalmeta1b-trace.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
saver = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java').read_text()
params = (root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/render/Parameters.java').read_text()
renderer = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
spool = (root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java').read_text()

checks = {
    'dngphysicalmeta1a_recalc_retained': 'ReCalcColorPhysical(boolean customNeutr' in params,
    'm9_dng_physical_recalc_retained': 'parameters.ReCalcColorPhysical(false, captureResult, characteristics);' in saver,
    'writer_trace_schema': 'm9cam.dngphysicalmeta.v1b.writerinput' in saver,
    'writer_binding_pass': 'writerPhysicalBindingPass' in saver,
    'writer_cfa_compare': 'writerCfaMatchesPhysical' in saver,
    'writer_black_compare': 'writerStaticBlackMatchesPhysical' in saver,
    'writer_neutral_compare': 'writerNeutralMatchesPhysicalCapture' in saver,
    'writer_calibration_compare': 'writerCalibrationTransform1MatchesPhysical' in saver and 'writerCalibrationTransform2MatchesPhysical' in saver,
    'writer_cm_compare': 'writerColorMatrix1MatchesPhysical' in saver and 'writerColorMatrix2MatchesPhysical' in saver,
    'writer_fm_compare': 'writerForwardMatrix1MatchesPhysical' in saver and 'writerForwardMatrix2MatchesPhysical' in saver,
    'writer_trace_private_spool': 'M9DiagnosticBurstSpool.stage(' in saver,
    'writer_trace_no_blocking_public_io': 'M9DiagnosticSidecarIO.persist(' not in saver,
    'existing_spool_schema': 'm9cam.sidecarspool.v1.privatebundle1b' in spool,
    'ordinary_photon_dng_helper_retained': 'public static boolean saveSingleRaw(Path dngFilePath,' in saver,
    'm9_physical_cfa_helper_retained': 'saveSingleRawM9PhysicalCfa' in saver,
    'raw_writer_unchanged': 'dngCreator.writeBuffer(outputStream, buffer, parameters.rawSize.x, parameters.rawSize.y);' in saver,
    'renderer_not_dependent_on_dng_trace': 'DNGPHYSICALMETA1B' not in renderer,
    'jpeg_quality_95_retained': 'JPEG_QUALITY = 95' in renderer,
    'target_hsm_retained': 'TARGETHSM1A' in renderer,
}
for name, ok in checks.items():
    print(('PASS ' if ok else 'FAIL ') + name)
if not all(checks.values()):
    raise SystemExit('DNGPHYSICALMETA1B VERIFY FAILED')
print('DNGPHYSICALMETA1B VERIFY PASS')
