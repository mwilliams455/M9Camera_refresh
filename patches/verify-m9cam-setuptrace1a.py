#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-setuptrace1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not renderer.exists(): raise SystemExit(f'missing renderer: {renderer}')
s = renderer.read_text()
required = [
    'm9cam.setuptrace.v1a.readonly',
    'setupEnsureOpenCvElapsedMs',
    'setupSnapshotLookupElapsedMs',
    'setupFillConstElapsedMs',
    'setupFillDynamicElapsedMs',
    'setupDevicePortAuditElapsedMs',
    'setupPhysicalResultResolveElapsedMs',
    'setupRawShadingAuditElapsedMs',
    'setupSourceCalibrationAuditElapsedMs',
    'setupFinalBookkeepingElapsedMs',
    'accountedElapsedMs',
    'unaccountedElapsedMs',
    'diagnosticOnly", true',
]
for token in required:
    if token not in s: raise SystemExit('FAIL missing SETUPTRACE1A token: ' + token)
    print('PASS ' + token)

# Existing total setup and render timing must remain present.
for token in ('setupParametersElapsedMs', 'renderCoreElapsedMs', 'jpegEncodeWriteElapsedMs'):
    if token not in s: raise SystemExit('FAIL existing timing removed: ' + token)
    print('PASS retained_' + token)

# Instrumentation is timing/JSON only. The established native production call and JPEG quality stay intact.
for token in ('renderNativeSourceProduction1P(', 'JPEG_QUALITY = 95', 'M9TargetFirmwareCalibration.get().curve02'):
    if token not in s: raise SystemExit('FAIL photographic anchor missing: ' + token)
    print('PASS photographic_anchor_' + token.replace(' ', '_'))

# No SETUPTRACE result is allowed to feed gains, pixels, capture exposure or target selection.
for forbidden in (
    'setupTrace1A.getDouble',
    'setupTrace1A.optDouble',
    'setupTraceAccountedMs *',
    'setupTraceAccountedMs /',
):
    if forbidden in s:
        raise SystemExit('FAIL setup trace feeds photographic behavior: ' + forbidden)
print('PASS setup_trace_readonly')
print('SETUPTRACE1A VERIFY PASS')
