#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1f-shadedtailaudit1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A verify missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A verify method missing: ' + marker)
    brace = src.find('{', start)
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
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line_comment'; i += 1
            elif ch == '/' and nxt == '*': state = 'block_comment'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A verify unterminated: ' + marker)


if '-basishsm1f-shadedtailaudit1a' not in gradle:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A build provenance missing')

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A NOHDR freeze missing: ' + marker)

for marker in [
    'private static final class ShadedTailAudit1AStats',
    'm9cam.renderer.shadedtailaudit.v1a',
    'diagnosticOnly", true',
    'pixelMutation", false',
    'gainMutation", false',
    'private_clone_of_original_normalized_Bayer',
    'exact_existing_applyNativeProspectiveGainMap_helper',
    'lens_shading_corrected_linear_Bayer_pre_demosaic',
    'reuse_frozen_original_RAW_tail_q_no_reclassification_of_correction_above_one',
    'short[] correctedRepresented = originalNorm16.clone();',
    'applyNativeProspectiveGainMap(\n                correctedRepresented, width, height, map)',
    'originalCode >= 65535',
    'final double q = Math.max(0.0, Math.min(1.0, originalTail.q));',
    'correctedUq99',
    'correctedUq99_5',
    'correctedUq99_8',
    'correctedAdaptiveUqAtOriginalQ',
    'correctedTailCurvature',
    'correctedTailValueAtOriginalQ',
    'predictedGuardGainAtOriginalQ',
    'predictedMeterGainIfOnlyGuardDomainChanged',
    'predictedRenderBaseGainIfOnlyGuardDomainChanged',
    'predictedGainDeltaEvVsCurrent',
    'photographicDecisionMutation", false',
    'shadedTailAudit1AEnabled',
    'm9cam.renderer.basishsm.shadedtailaudit.v1a.main',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A diagnostic marker missing: ' + marker)

prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')
for marker in [
    'ShadedTailAudit1AStats shadedTailAuditStats = applyNativeShading',
    '? shadedTailAudit1A(norm16, width, height, nativeLiveGainMap, tail)',
    'NativeProspectiveShadingStats nativeShading = applyNativeShading',
    'applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap)',
    'Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);',
    'cam16.convertTo(cam16, -1, nativeShading.representationScale, 0.0);',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'restored_physical_shaded_camera_RGB',
    'shadingLateRepresentationScaleApplied", false',
    'final double effectiveRenderGain = meterParityRenderBaseGain;',
    'd.put("shadedTailAudit1A", shadedTailAuditJson);',
]:
    if marker not in prospective:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A prospective freeze/audit marker missing: ' + marker)

if 'meterParityRenderBaseGain * nativeShading.representationScale' in prospective:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A regressed to late representationScale exposure gain')

for forbidden in [
    'meter.gain = predictedMeterGainIfOnlyGuardDomainChanged',
    'effectiveRenderGain = predictedRenderBaseGainIfOnlyGuardDomainChanged',
    'meterParityRenderBaseGain = predictedRenderBaseGainIfOnlyGuardDomainChanged',
]:
    if forbidden in prospective:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A audit mutated photographic decision: ' + forbidden)

extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
for marker in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
    'boolean[] applyShadingFlags = {false, true};',
    'boolean[] selfMeterFlags = {true, true};',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A field-output freeze missing: ' + marker)

print('BASISHSM1F-SHADEDTAILAUDIT1A verify OK')
print(' - audit is ON-only and diagnostic-only')
print(' - corrected tail uses exact LensShadingMap helper on a private Bayer clone')
print(' - original sensor-clipped sites remain excluded and original TC20 q is reused')
print(' - predicted corrected-domain guard is logged but not applied')
print(' - SHADINGDOMAIN1A restore stage and effectiveRenderGain remain frozen')
print(' - field OFF/ON filenames and self-meter policy remain frozen')
print(' - single RAW / HDR=false boundary verified')
