#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-rawshading1a-gainmapaudit1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()


def require(rel, needle):
    p = root / rel
    if not p.exists():
        raise SystemExit('RAWSHADING1A verify missing file: ' + rel)
    text = p.read_text()
    if needle not in text:
        raise SystemExit('RAWSHADING1A verify missing marker in %s: %s' % (rel, needle))
    return text


audit_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
dng_rel = 'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java'

audit = require(audit_rel, 'm9cam.rawshading.v1a.gainmapaudit1a.multilens')
for marker in [
    'SENSOR_INFO_LENS_SHADING_APPLIED',
    'STATISTICS_LENS_SHADING_CORRECTION_MAP',
    'getColumnCount()',
    'getRowCount()',
    'advertisedShadingMapSizeSource',
    'not_exposed_by_CameraCharacteristics_use_live_CaptureResult_LensShadingMap_dimensions',
    'SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE',
    'SCALER_CROP_REGION',
    'SHADING_MODE',
    'STATISTICS_LENS_SHADING_MAP_MODE',
    'R,Geven,Godd,B',
    'cameraID',
    'logicalID',
    'physicalID',
    'focalLengthMm',
    'cfaPattern',
    'cfaPatternName',
    'gainMapMinPerChannel',
    'gainMapMaxPerChannel',
    'channelExtrema(factors, cols, rows, true)',
    'channelExtrema(factors, cols, rows, false)',
    'gainMapCenterPerChannel',
    'gainMapCornersPerChannel',
    'gainMapEdgeMidpointsPerChannel',
    'gainMapCentreToCornerApproxEv',
    '_M9_RAWSHADING1A.json',
    'gainMapApplicationEnabled", false',
    'fixedTc20ComparisonEnabled", false',
    'phase", "A_metadata_semantics_audit',
    'M9DiagnosticSidecarIO.persist(',
    'M9DiagnosticSidecarIO.SCHEMA',
    'raw_shading_audit',
    'sidecarPersisted',
]:
    if marker not in audit:
        raise SystemExit('RAWSHADING1A audit marker missing: ' + marker)
if 'CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE' in audit:
    raise SystemExit('RAWSHADING1A uses unsupported CameraCharacteristics.LENS_INFO_SHADING_MAP_SIZE')
if 'Files.write(sidecar' in audit:
    raise SystemExit('RAWSHADING1A must not depend on direct Files.write for public sidecar persistence')

renderer = require(renderer_rel, 'M9RawShadingAudit1A.captureAndWrite(')
for marker in [
    'rawShadingGainMapApplied", false',
    'rawShadingPhase", "A_metadata_semantics_audit',
    'rawShadingAudit1A',
]:
    if marker not in renderer:
        raise SystemExit('RAWSHADING1A renderer marker missing: ' + marker)

# BESTFIT2A already adds the final TC20-offset argument. Phase A must retain that
# exact baseline and must not wire the Camera2 GainMap into the renderer yet.
expected_render_call = '''RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0);'''
if expected_render_call not in renderer:
    raise SystemExit('RAWSHADING1A current BESTFIT2A baseline renderCore call changed')
for forbidden in ['params.gainMap', 'params.mapSize', 'params.hasGainMap']:
    if forbidden in renderer:
        raise SystemExit('RAWSHADING1A Phase A unexpectedly wires shading input into renderer: ' + forbidden)

dng = require(dng_rel, 'M9 DNGGAINMAPFIX1A')
for marker in [
    'parameters.sensorPix.left',
    'parameters.sensorPix.top',
    'parameters.sensorPix.right',
    'parameters.sensorPix.bottom',
]:
    if marker not in dng:
        raise SystemExit('RAWSHADING1A DNGGAINMAPFIX1A marker missing: ' + marker)

print('M9RAWSHADING1A GAINMAPAUDIT1A verification OK')
print(' - Camera2 lens-shading semantics and live GainMap audit present')
print(' - live LensShadingMap row/column counts are the map-size authority; no nonexistent characteristic key')
print(' - four-channel min/max, centre, edge and corner GainMap measurements present')
print(' - camera/physical IDs, focal length, CFA and sensor/crop geometry recorded for multi-lens mapping')
print(' - *_M9_RAWSHADING1A.json uses established direct-first/SAF-fallback diagnostic transport')
print(' - GainMap application remains OFF; current BESTFIT2A/TC20 photographic path unchanged')
