#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1l-shadinglumadecomp1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1L-SHADINGLUMADECOMP1A missing: ' + str(p))
renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1L method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1L opening brace missing: ' + marker)
    depth = 0; i = brace; state = 'code'; quote = ''; escape = False
    while i < len(src):
        ch = src[i]; nxt = src[i+1] if i+1 < len(src) else ''
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
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1, src[start:i+1]
        i += 1
    raise SystemExit('BASISHSM1L unterminated method: ' + marker)

def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f'BASISHSM1L {label} anchor count={n}')
    return src.replace(old, new, 1)

for marker in [
    'm9cam.renderer.basishsm.shadedtailspatial.finalclipaudit.v1a.main',
    'm9cam.renderer.shadedtailspatial.v1a',
    'private static JSONObject shadedTailSpatialAudit1A(',
    'private static JSONObject finalClipAudit1A(',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"',
    'boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, true};',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1L requires validated 1K marker: ' + marker)
if '-basishsm1k-shadedtailspatial1a' not in gradle:
    raise SystemExit('BASISHSM1L requires 1K build provenance')
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY','frameCount = 1;','throwCount = 0;','IsoExpoSelector.HDR = false;']:
    if marker not in frames:
        raise SystemExit('BASISHSM1L NOHDR boundary missing: ' + marker)

frozen_markers = {
    'primary': '    private static RenderCore renderCore(',
    'full_shading': '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(',
    'residual': '    private static JSONObject rawShadingResidualAudit1A(',
    'tail': '    private static ShadedTailAudit1AStats shadedTailAudit1A(',
    'clip': '    private static JSONObject finalClipAudit1A(',
    'spatial': '    private static JSONObject shadedTailSpatialAudit1A(',
}
frozen_sha = {}
for k, marker in frozen_markers.items():
    _,_,m = extract_method(renderer, marker); frozen_sha[k] = hashlib.sha256(m.encode()).hexdigest()

P = Path(__file__).resolve().parent
helper = (P / 'fragments/basishsm1l-shadinglumadecomp1a-a.javafrag').read_text() + (P / 'fragments/basishsm1l-shadinglumadecomp1a-b.javafrag').read_text()
class_marker='    private static final class NativeProspectiveShadingStats {'
if renderer.count(class_marker)!=1: raise SystemExit('BASISHSM1L shading class anchor ambiguous')
if 'applyNativeProspectiveGainMapLumaDecomp1A(' in renderer: raise SystemExit('BASISHSM1L already applied')
renderer=renderer.replace(class_marker,helper+class_marker,1)

ps,pe,prospective=extract_method(renderer,'    private static RenderCore renderNativeProspectiveCore(')
old_sig='''                                         boolean selfMeter,\n                                         boolean applyShadedGuard1A,\n                                         boolean applyShadedGuardCap20Ev1A) throws Exception {'''
new_sig='''                                         boolean selfMeter,\n                                         boolean applyShadedGuard1A,\n                                         boolean applyShadedGuardCap20Ev1A,\n                                         boolean applyShadingLumaDecomp1A,\n                                         double shadingLumaAuthorityAlpha) throws Exception {'''
prospective=replace_once(prospective,old_sig,new_sig,'prospective signature')
old_block='''        ShadedTailAudit1AStats shadedTailAuditStats = applyNativeShading\n                ? shadedTailAudit1A(norm16, width, height, nativeLiveGainMap, tail)\n                : ShadedTailAudit1AStats.skipped();\n        final boolean shadedTailSpatial1ARun = applyNativeShading\n                && !applyShadedGuard1A\n                && !applyShadedGuardCap20Ev1A;\n        final JSONObject shadedTailSpatial1AJson = shadedTailSpatial1ARun\n                ? shadedTailSpatialAudit1A(\n                        norm16, width, height, nativeLiveGainMap, tail, cameraRotation)\n                : shadedTailSpatialAudit1ASkipped(\n                        !applyNativeShading\n                                ? "shading_off_control"\n                                : "shared_same_raw_audit_emitted_on_shading_on_unguarded_control");\n        NativeProspectiveShadingStats nativeShading = applyNativeShading\n                ? applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap)\n                : NativeProspectiveShadingStats.none();'''
new_block='''        if (applyShadingLumaDecomp1A && (!applyNativeShading\n                || !Double.isFinite(shadingLumaAuthorityAlpha)\n                || shadingLumaAuthorityAlpha < 0.0 || shadingLumaAuthorityAlpha > 1.0)) {\n            throw new IllegalArgumentException("SHADINGLUMADECOMP1A invalid variant configuration");\n        }\n        final JSONObject shadingLumaDecomp1AJson = applyNativeShading\n                ? shadingLumaDecomp1AAudit(nativeLiveGainMap, shadingLumaAuthorityAlpha)\n                : shadingLumaDecomp1ASkipped("shading_off_reference");\n        final boolean fullPhysicalShadingControl = applyNativeShading && !applyShadingLumaDecomp1A;\n        ShadedTailAudit1AStats shadedTailAuditStats = fullPhysicalShadingControl\n                ? shadedTailAudit1A(norm16, width, height, nativeLiveGainMap, tail)\n                : ShadedTailAudit1AStats.skipped();\n        final boolean shadedTailSpatial1ARun = fullPhysicalShadingControl\n                && !applyShadedGuard1A\n                && !applyShadedGuardCap20Ev1A;\n        final JSONObject shadedTailSpatial1AJson = shadedTailSpatial1ARun\n                ? shadedTailSpatialAudit1A(\n                        norm16, width, height, nativeLiveGainMap, tail, cameraRotation)\n                : shadedTailSpatialAudit1ASkipped(\n                        !applyNativeShading ? "shading_off_control"\n                                : (applyShadingLumaDecomp1A\n                                ? "decomposed_variant_uses_final_spatial_audits"\n                                : "shared_same_raw_audit_emitted_on_shading_on_unguarded_control"));\n        NativeProspectiveShadingStats nativeShading = applyNativeShading\n                ? (applyShadingLumaDecomp1A\n                        ? applyNativeProspectiveGainMapLumaDecomp1A(\n                                norm16, width, height, nativeLiveGainMap, shadingLumaAuthorityAlpha)\n                        : applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap))\n                : NativeProspectiveShadingStats.none();'''
prospective=replace_once(prospective,old_block,new_block,'decomposition render seam')
prospective=replace_once(prospective,'            d.put("schema", "m9cam.renderer.basishsm.shadedtailspatial.finalclipaudit.v1a.main");','            d.put("schema", "m9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main");','schema')
prospective=replace_once(prospective,'            d.put("shadedTailAudit1AEnabled", applyNativeShading);','''            d.put("shadedTailAudit1AEnabled", fullPhysicalShadingControl);\n            d.put("lumaDecomp1AEnabled", true);\n            d.put("lumaDecomp1ARenderApplied", applyShadingLumaDecomp1A);\n            d.put("lumaAuthorityAlpha", applyNativeShading ? shadingLumaAuthorityAlpha : JSONObject.NULL);\n            d.put("shadingLumaDecomp1A", shadingLumaDecomp1AJson);\n            d.put("shadingLumaDecomp1APreDemosaicOnly", true);\n            d.put("shadingLumaDecomp1APostRenderVignette", false);\n            d.put("shadingLumaDecomp1AGlobalGuardFeedbackIntoGain", false);\n            d.put("shadingLumaDecomp1AFinalClipFeedbackIntoGain", false);\n            d.put("shadingLumaDecomp1APrimaryMutation", false);''','decomp diagnostics')
renderer=renderer[:ps]+prospective+renderer[pe:]

old_arrays='''                        String[] suffixes = {\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"\n                        };\n                        String[] bridgeProbeNames = {\n                                "native_plus_historical_basis_hsm_self_meter_shading_off",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_shadedguardcap20ev1a"\n                        };\n                        int[] bridgeProbeModes = {3, 3, 3, 3};\n                        boolean[] selfMeterFlags = {true, true, true, true};\n                        boolean[] applyShadingFlags = {false, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, true, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, true};'''
new_arrays='''                        String[] suffixes = {\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_PARTIAL_LUMA_SHADING1A"\n                        };\n                        String[] bridgeProbeNames = {\n                                "native_plus_historical_basis_hsm_self_meter_shading_off",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",\n                                "native_plus_historical_basis_hsm_self_meter_chroma_only_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_partial_luma_shading1a"\n                        };\n                        int[] bridgeProbeModes = {3, 3, 3, 3};\n                        boolean[] selfMeterFlags = {true, true, true, true};\n                        boolean[] applyShadingFlags = {false, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, false, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false};\n                        boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true};\n                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.5};'''
renderer=replace_once(renderer,old_arrays,new_arrays,'four-way output arrays')
old_loop='''                            boolean applyShadedGuardCap20Ev1A =\n                                    applyShadedGuardCap20Ev1AFlags[variantIndex];'''
new_loop='''                            boolean applyShadedGuardCap20Ev1A =\n                                    applyShadedGuardCap20Ev1AFlags[variantIndex];\n                            boolean applyShadingLumaDecomp1A =\n                                    applyShadingLumaDecomp1AFlags[variantIndex];\n                            double shadingLumaAuthorityAlpha =\n                                    shadingLumaAuthorityAlphaFlags[variantIndex];'''
renderer=replace_once(renderer,old_loop,new_loop,'variant selectors')
old_call='''                                        fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter,\n                                        applyShadedGuard1A, applyShadedGuardCap20Ev1A);'''
new_call='''                                        fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter,\n                                        applyShadedGuard1A, applyShadedGuardCap20Ev1A,\n                                        applyShadingLumaDecomp1A, shadingLumaAuthorityAlpha);'''
renderer=replace_once(renderer,old_call,new_call,'prospective call')
renderer=replace_once(renderer,'"main_physical_2_primary_vs_basis_hsm_shading_off_on_unguarded_on_guarded_on_cap20ev"','"main_physical_2_primary_vs_basis_hsm_shading_luma_decomp1a"','comparison identity')

gradle=gradle.replace('-basishsm1k-shadedtailspatial1a','-basishsm1l-shadinglumadecomp1a',1)
if '-basishsm1l-shadinglumadecomp1a' not in gradle: raise SystemExit('BASISHSM1L failed build provenance')

for k,marker in frozen_markers.items():
    _,_,m=extract_method(renderer,marker)
    if hashlib.sha256(m.encode()).hexdigest()!=frozen_sha[k]: raise SystemExit('BASISHSM1L changed frozen helper: '+k)

renderer_path.write_text(renderer); gradle_path.write_text(gradle)
print('M9Cam BASISHSM1L-SHADINGLUMADECOMP1A applied')
print(' - OFF and exact full physical SHADING_ON controls retained')
print(' - CHROMA_ONLY alpha=0 and PARTIAL_LUMA alpha=0.5 candidates added')
print(' - geometric-mean common gain decomposition occurs pre-demosaic only')
print(' - full physical shading helper remains byte-identical')
print(' - global SHADEDGUARD/CAP20 requests disabled for all 1L outputs')
print(' - Primary / TC20 / HSM / tone / DNG / capture / JPEG quality unchanged')
print(' - single RAW / HDR=false boundary preserved')
