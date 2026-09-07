#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1e-shadingdomain1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n': state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/':
                state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/':
                state = 'line_comment'; i += 1
            elif ch == '/' and nxt == '*':
                state = 'block_comment'; i += 1
            elif ch in ('"', "'"):
                state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1E-SHADINGDOMAIN1A {label} anchor count={count}')
    return src.replace(old, new, 1)


# Requires the diagnostic-only RAW residual audit, which established that the live
# physical-camera map is real for this RAW stream. This stage changes only where the
# temporary headroom representation scale is restored.
for marker in [
    'rawShadingResidual1AEnabled',
    'm9cam.renderer.rawshadingresidual.v1a',
    'shadingParity1A',
    'meterParitySelfMeter',
    'normalized_linear_Bayer_pre_demosaic_headroom_preserved',
    'gainMapRepresentationScale',
    'gainMapPostScaleClipCount',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A requires RAWSHADINGRESIDUAL1A marker: ' + marker)
if '-basishsm1d-rawshadingresidual1a' not in gradle:
    raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A requires RAWSHADINGRESIDUAL1A build provenance')

# Single-frame / no-HDR capture boundary remains frozen.
frames = frames_path.read_text()
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_before = extract_method(
    renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_before = extract_method(
    renderer, '    private static JSONObject rawShadingResidualAudit1A(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()
shading_sha = hashlib.sha256(shading_before.encode('utf-8')).hexdigest()
residual_sha = hashlib.sha256(residual_before.encode('utf-8')).hexdigest()

pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')

# The map is still applied once on normalized Bayer and divided by max map gain only
# as a uint16 transport representation for EA demosaic. Restore that global scalar
# immediately after demosaic, before the native Camera2 white-point clamp, HSM, TC20,
# M9 bridge, or final tone stages. OpenCV CV_16U saturation at 1.0 is semantically
# equivalent to the existing downstream cameraToM9/cameraToSrgbLuma clamps because
# every context camera-white component is <= 1.0 (green is the unit channel).
# This removes the invalid late-scale assumption across nonlinear TC20/HSM/clamps.
demosaic_anchor = '''            Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);\n            rawMat.release();\n            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;'''
demosaic_replacement = '''            Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);\n            rawMat.release();\n            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;\n\n            // BASISHSM1E-SHADINGDOMAIN1A: restore the temporary Bayer transport scale\n            // in camera RGB before any nonlinear meter/HSM/white-point operation.\n            final boolean shadingDomainRestoreApplied = applyNativeShading\n                    && nativeShading.applied\n                    && Math.abs(nativeShading.representationScale - 1.0) > 1.0e-12;\n            if (shadingDomainRestoreApplied) {\n                cam16.convertTo(cam16, -1, nativeShading.representationScale, 0.0);\n            }'''
prospective = replace_once(
    prospective, demosaic_anchor, demosaic_replacement, 'post-demosaic representation restore')

old_gain = '''            final double effectiveRenderGain =\n                    meterParityRenderBaseGain * nativeShading.representationScale;'''
new_gain = '''            // SHADINGDOMAIN1A restored the representation scale before TC20/HSM,\n            // so the final render gain is now the photographic meter decision only.\n            final double effectiveRenderGain = meterParityRenderBaseGain;'''
prospective = replace_once(prospective, old_gain, new_gain, 'late representation-scale removal')

prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.rawshadingresidual.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.shadingdomain.v1a.main");',
    'prospective schema')

# Add explicit domain provenance next to the existing representation diagnostics.
diag_anchor = '            d.put("gainMapRepresentationScale", nativeShading.representationScale);'
diag_replacement = '''            d.put("gainMapRepresentationScale", nativeShading.representationScale);\n            d.put("shadingDomain1A", true);\n            d.put("shadingRepresentationRestoreApplied", shadingDomainRestoreApplied);\n            d.put("shadingRepresentationRestoreStage", shadingDomainRestoreApplied\n                    ? "post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20" : "none");\n            d.put("shadingMeterInputDomain", shadingDomainRestoreApplied\n                    ? "restored_physical_shaded_camera_RGB" : "native_unscaled_camera_RGB");\n            d.put("shadingRenderInputDomain", shadingDomainRestoreApplied\n                    ? "restored_physical_shaded_camera_RGB" : "native_unscaled_camera_RGB");\n            d.put("shadingLateRepresentationScaleApplied", false);\n            d.put("shadingDomainReason", "global headroom transport scale must be restored before nonlinear whitepoint_HSM_TC20 operations");'''
prospective = replace_once(prospective, diag_anchor, diag_replacement, 'domain diagnostics')

renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

gradle = gradle.replace(
    '-basishsm1d-rawshadingresidual1a',
    '-basishsm1e-shadingdomain1a', 1)
if '-basishsm1e-shadingdomain1a' not in gradle:
    raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A failed to set build provenance')

# Frozen Primary, the physical LensShadingMap interpolation itself, and the residual
# audit must remain source-byte identical. This stage owns only the prospective domain.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_after = extract_method(
    renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_after = extract_method(
    renderer, '    private static JSONObject rawShadingResidualAudit1A(')
if hashlib.sha256(primary_after.encode('utf-8')).hexdigest() != primary_sha:
    raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A changed frozen Primary renderCore')
if hashlib.sha256(shading_after.encode('utf-8')).hexdigest() != shading_sha:
    raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A changed LensShadingMap interpolation/application')
if hashlib.sha256(residual_after.encode('utf-8')).hexdigest() != residual_sha:
    raise SystemExit('BASISHSM1E-SHADINGDOMAIN1A changed RAW residual audit')

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9Cam BASISHSM1E-SHADINGDOMAIN1A applied')
print(' - frozen Primary renderCore sha256 preserved:', primary_sha)
print(' - LensShadingMap interpolation/application sha256 preserved:', shading_sha)
print(' - RAW residual audit sha256 preserved:', residual_sha)
print(' - shading transport scale now restored immediately after EA demosaic')
print(' - TC20/HSM/white-point clamp see physical shaded camera-RGB domain')
print(' - late render-gain representationScale multiplication removed')
print(' - OFF branch remains scale=1 and pixel-identical by construction')
print(' - single RAW / HDR=false / DNG / capture exposure remain frozen')
