#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourcecal1c-physicalresult1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()


def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('SOURCECAL1C verify missing file: ' + rel)
    return p.read_text()

resolver = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PhysicalCaptureResult1A.java')
for marker in [
    'TotalCaptureResult',
    'getPhysicalCameraTotalResults()',
    'getPhysicalCameraResults()',
    'requestedPhysicalCameraId',
    'resultMatchesRequestedPhysical',
    'Build.VERSION_CODES.S',
    'Build.VERSION_CODES.P',
]:
    if marker not in resolver:
        raise SystemExit('SOURCECAL1C resolver marker missing: ' + marker)

renderer = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
for marker in [
    'params.FillDynamicParameters(captureResult, captureRequest, iso);',
    'CaptureResult diagnosticCaptureResult1A = M9PhysicalCaptureResult1A.resolve(',
    'diagnosticCaptureResult1A, captureRequest);',
    'dngPath, params, characteristics, diagnosticCaptureResult1A);',
    'sourceCalibrationNativeTransformApplied", false',
    'rawShadingGainMapApplied", false',
]:
    if marker not in renderer:
        raise SystemExit('SOURCECAL1C renderer marker missing: ' + marker)
if 'params.FillDynamicParameters(diagnosticCaptureResult1A' in renderer:
    raise SystemExit('SOURCECAL1C audit result leaked into active Parameters')

expected_render_call = '''RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0);'''
if expected_render_call not in renderer:
    raise SystemExit('SOURCECAL1C frozen renderCore baseline changed')

for rel in [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java',
]:
    audit = text(rel)
    for marker in [
        'captureResultResolutionPolicy',
        'physicalCaptureResultRequested',
        'requestedPhysicalCameraId',
        'captureResultCameraId',
        'captureResultMatchesRequestedPhysicalCamera',
    ]:
        if marker not in audit:
            raise SystemExit('SOURCECAL1C sidecar marker missing in %s: %s' % (rel, marker))

print('M9SOURCECAL1C PHYSICALRESULT1A verification OK')
print(' - per-physical TotalCaptureResult is selected for diagnostic metadata when available')
print(' - SOURCECAL and RAWSHADING sidecars expose physical-result provenance/match status')
print(' - active Parameters and frozen M9 render path still consume the original top-level result')
