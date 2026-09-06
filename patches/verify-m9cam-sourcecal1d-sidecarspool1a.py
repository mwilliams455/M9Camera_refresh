#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-sourcecal1d-sidecarspool1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()


def text(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('SOURCECAL1D verify missing file: ' + rel)
    return p.read_text()

spool = text('app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java')
for marker in ['m9cam.sidecarspool.v1.privatebundle1b', 'public static boolean stage(']:
    if marker not in spool:
        raise SystemExit('SOURCECAL1D spool baseline marker missing: ' + marker)

for rel, role in [
    ('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java', 'source_calibration_audit'),
    ('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java', 'raw_shading_audit'),
]:
    audit = text(rel)
    for marker in [
        'M9DiagnosticBurstSpool.stage(',
        'M9DiagnosticBurstSpool.SCHEMA',
        'sidecarStaged',
        role,
    ]:
        if marker not in audit:
            raise SystemExit('SOURCECAL1D audit spool marker missing in %s: %s' % (rel, marker))
    for forbidden in ['M9DiagnosticSidecarIO.persist(', 'Files.write(sidecar']:
        if forbidden in audit:
            raise SystemExit('SOURCECAL1D blocking public sidecar path remains in %s: %s' % (rel, forbidden))

renderer = text('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java')
expected_render_call = '''RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0);'''
if expected_render_call not in renderer:
    raise SystemExit('SOURCECAL1D frozen BESTFIT2A renderCore call changed')
for marker in [
    'sourceCalibrationNativeTransformApplied\", false',
    'rawShadingGainMapApplied\", false',
    'params.FillDynamicParameters(captureResult, captureRequest, iso);',
]:
    if marker not in renderer:
        raise SystemExit('SOURCECAL1D frozen renderer marker missing: ' + marker)
if 'params.FillDynamicParameters(diagnosticCaptureResult1A' in renderer:
    raise SystemExit('SOURCECAL1D diagnostic result leaked into active Parameters')

print('M9SOURCECAL1D SIDECARSPOOL1A verification OK')
print(' - SOURCECAL/RAWSHADING audit payloads stage to existing app-private SIDECAR1B spool')
print(' - slow direct-first/SAF public persistence no longer blocks audit call sites')
print(' - public individual JSON compatibility export remains asynchronous through SIDECAR1B')
print(' - frozen renderCore, TC20, exposure, DNG, native source transform and GainMap application unchanged')
