#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1n-shadinglumanorm1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1N-SHADINGLUMANORM1A missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1N method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1N opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i+1] if i+1 < len(src) else ''
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
                if depth == 0:
                    return start, i + 1, src[start:i+1]
        i += 1
    raise SystemExit('BASISHSM1N unterminated method: ' + marker)

def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f'BASISHSM1N {label} anchor count={n}')
    return src.replace(old, new, 1)

# Require the validated 1M bank, 1L decomposition, and hard single-frame/no-HDR boundary.
for marker in [
    'm9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main',
    'm9cam.renderer.shadinglumadecomp.v1a',
    'private static JSONObject shadingLumaDecomp1AAudit(',
    'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA025_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA040_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA055_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA070_SHADING1A"',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.25, 0.40, 0.55, 0.70};',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1N requires validated 1M marker: ' + marker)
if '-basishsm1m-shadingalphasweep1a' not in gradle:
    raise SystemExit('BASISHSM1N requires 1M build provenance')
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in frames:
        raise SystemExit('BASISHSM1N NOHDR boundary missing: ' + marker)

# Everything photographic below the prospective orchestration remains frozen. 1N is allowed
# to derive the existing 1L alpha from the map itself, but may not alter the shading math.
frozen_markers = {
    'primary': '    private static RenderCore renderCore(',
    'full_shading': '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(',
    'decomp_shading': '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    'decomp_audit': '    private static JSONObject shadingLumaDecomp1AAudit(',
    'residual': '    private static JSONObject rawShadingResidualAudit1A(',
    'tail': '    private static ShadedTailAudit1AStats shadedTailAudit1A(',
    'clip': '    private static JSONObject finalClipAudit1A(',
    'spatial': '    private static JSONObject shadedTailSpatialAudit1A(',
}
frozen_sha = {}
for k, marker in frozen_markers.items():
    _, _, method = extract_method(renderer, marker)
    frozen_sha[k] = hashlib.sha256(method.encode()).hexdigest()

# Extend only the prospective experiment interface. Normalization is a scalar alpha derived
# from the LensShadingMap common-gain outside-center median; it never reads scene luma.
ps, pe, prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')
old_sig = '''                                         boolean applyShadedGuardCap20Ev1A,\n                                         boolean applyShadingLumaDecomp1A,\n                                         double shadingLumaAuthorityAlpha) throws Exception {'''
new_sig = '''                                         boolean applyShadedGuardCap20Ev1A,\n                                         boolean applyShadingLumaDecomp1A,\n                                         double shadingLumaAuthorityAlpha,\n                                         boolean normalizeShadingLumaOutsideMedian1A,\n                                         double shadingLumaTargetOutsideMedianEv1A) throws Exception {'''
prospective = replace_once(prospective, old_sig, new_sig, 'prospective normalization signature')

old_validation = '''        if (applyShadingLumaDecomp1A && (!applyNativeShading\n                || !Double.isFinite(shadingLumaAuthorityAlpha)\n                || shadingLumaAuthorityAlpha < 0.0 || shadingLumaAuthorityAlpha > 1.0)) {\n            throw new IllegalArgumentException("SHADINGLUMADECOMP1A invalid variant configuration");\n        }\n        final JSONObject shadingLumaDecomp1AJson = applyNativeShading\n                ? shadingLumaDecomp1AAudit(nativeLiveGainMap, shadingLumaAuthorityAlpha)\n                : shadingLumaDecomp1ASkipped("shading_off_reference");'''
new_validation = '''        if (applyShadingLumaDecomp1A && (!applyNativeShading\n                || !Double.isFinite(shadingLumaAuthorityAlpha)\n                || shadingLumaAuthorityAlpha < 0.0 || shadingLumaAuthorityAlpha > 1.0)) {\n            throw new IllegalArgumentException("SHADINGLUMADECOMP1A invalid variant configuration");\n        }\n        if (normalizeShadingLumaOutsideMedian1A && (!applyNativeShading\n                || !applyShadingLumaDecomp1A\n                || !Double.isFinite(shadingLumaTargetOutsideMedianEv1A)\n                || shadingLumaTargetOutsideMedianEv1A < 0.0)) {\n            throw new IllegalArgumentException("SHADINGLUMANORM1A invalid variant configuration");\n        }\n        double shadingLumaSourceOutsideMedianEv1A = Double.NaN;\n        double effectiveShadingLumaAuthorityAlpha = shadingLumaAuthorityAlpha;\n        if (normalizeShadingLumaOutsideMedian1A) {\n            // Alpha=0 makes suppression equal the full requested common-gain EV, so this\n            // reuses the validated 1L decomposition audit rather than duplicating its math.\n            JSONObject normProbe = shadingLumaDecomp1AAudit(nativeLiveGainMap, 0.0);\n            shadingLumaSourceOutsideMedianEv1A = normProbe\n                    .getJSONObject("commonLuminanceSuppressionByRegion")\n                    .getJSONObject("outsideCenter50")\n                    .getDouble("median");\n            if (!Double.isFinite(shadingLumaSourceOutsideMedianEv1A)\n                    || shadingLumaSourceOutsideMedianEv1A < 0.0) {\n                throw new IllegalStateException("SHADINGLUMANORM1A invalid source outside median EV");\n            }\n            if (shadingLumaTargetOutsideMedianEv1A <= 0.0) {\n                effectiveShadingLumaAuthorityAlpha = 0.0;\n            } else if (shadingLumaSourceOutsideMedianEv1A <= 1.0e-12) {\n                effectiveShadingLumaAuthorityAlpha = 1.0;\n            } else {\n                effectiveShadingLumaAuthorityAlpha = Math.max(0.0, Math.min(1.0,\n                        shadingLumaTargetOutsideMedianEv1A / shadingLumaSourceOutsideMedianEv1A));\n            }\n        }\n        final JSONObject shadingLumaDecomp1AJson = applyNativeShading\n                ? shadingLumaDecomp1AAudit(nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha)\n                : shadingLumaDecomp1ASkipped("shading_off_reference");'''
prospective = replace_once(prospective, old_validation, new_validation, 'map-normalized alpha derivation')

old_apply = '''                        ? applyNativeProspectiveGainMapLumaDecomp1A(\n                                norm16, width, height, nativeLiveGainMap, shadingLumaAuthorityAlpha)'''
new_apply = '''                        ? applyNativeProspectiveGainMapLumaDecomp1A(\n                                norm16, width, height, nativeLiveGainMap, effectiveShadingLumaAuthorityAlpha)'''
prospective = replace_once(prospective, old_apply, new_apply, 'effective alpha render')

old_diag = '''            d.put("lumaDecomp1ARenderApplied", applyShadingLumaDecomp1A);\n            d.put("lumaAuthorityAlpha", applyNativeShading ? shadingLumaAuthorityAlpha : JSONObject.NULL);\n            d.put("shadingLumaDecomp1A", shadingLumaDecomp1AJson);'''
new_diag = '''            d.put("lumaDecomp1ARenderApplied", applyShadingLumaDecomp1A);\n            d.put("lumaAuthorityAlphaRequested", applyNativeShading ? shadingLumaAuthorityAlpha : JSONObject.NULL);\n            d.put("lumaAuthorityAlpha", applyNativeShading ? effectiveShadingLumaAuthorityAlpha : JSONObject.NULL);\n            d.put("shadingLumaNorm1AEnabled", true);\n            d.put("shadingLumaNorm1AApplied", normalizeShadingLumaOutsideMedian1A);\n            d.put("shadingLumaNorm1ABasis", "LensShadingMap_common_gain_outsideCenter50_median_EV_only_no_scene_luma");\n            d.put("shadingLumaNorm1ATargetOutsideMedianEv", normalizeShadingLumaOutsideMedian1A\n                    ? shadingLumaTargetOutsideMedianEv1A : JSONObject.NULL);\n            d.put("shadingLumaNorm1ASourceOutsideMedianEv", normalizeShadingLumaOutsideMedian1A\n                    ? shadingLumaSourceOutsideMedianEv1A : JSONObject.NULL);\n            d.put("shadingLumaNorm1AEffectiveAlpha", normalizeShadingLumaOutsideMedian1A\n                    ? effectiveShadingLumaAuthorityAlpha : JSONObject.NULL);\n            d.put("shadingLumaNorm1AUsesSceneBrightness", false);\n            d.put("shadingLumaNorm1AUsesFinalClipFeedback", false);\n            d.put("shadingLumaNorm1AUsesPrimaryFeedback", false);\n            d.put("shadingLumaDecomp1A", shadingLumaDecomp1AJson);'''
prospective = replace_once(prospective, old_diag, new_diag, 'normalization diagnostics')
renderer = renderer[:ps] + prospective + renderer[pe:]

old_arrays = '''                        // BASISHSM1M-SHADINGALPHASWEEP1A: diagnostic same-RAW bank only.\n                        // OFF and exact full physical ON are endpoints. The remaining outputs\n                        // preserve physical per-channel shading ratios while varying only the\n                        // common geometric-mean luminance gain authority.\n                        String[] suffixes = {\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA025_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA040_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA055_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA070_SHADING1A"\n                        };\n                        String[] bridgeProbeNames = {\n                                "native_plus_historical_basis_hsm_self_meter_shading_off",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",\n                                "native_plus_historical_basis_hsm_self_meter_chroma_only_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma025_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma040_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma055_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma070_shading1a"\n                        };\n                        int[] bridgeProbeModes = {3, 3, 3, 3, 3, 3, 3};\n                        boolean[] selfMeterFlags = {true, true, true, true, true, true, true};\n                        boolean[] applyShadingFlags = {false, true, true, true, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false, false, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false, false, false};\n                        boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true, true, true, true};\n                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.25, 0.40, 0.55, 0.70};'''
new_arrays = '''                        // BASISHSM1N-SHADINGLUMANORM1A: same-RAW normalization test.\n                        // Normalized candidates preserve the 1L map shape and chroma ratios,\n                        // but choose alpha so the map's outside-center common-luma median applies\n                        // at most the requested EV. This is map calibration, not scene exposure.\n                        String[] suffixes = {\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM020EV1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM040EV1A"\n                        };\n                        String[] bridgeProbeNames = {\n                                "native_plus_historical_basis_hsm_self_meter_shading_off",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",\n                                "native_plus_historical_basis_hsm_self_meter_chroma_only_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_lumanorm020ev1a",\n                                "native_plus_historical_basis_hsm_self_meter_lumanorm030ev1a",\n                                "native_plus_historical_basis_hsm_self_meter_lumanorm040ev1a"\n                        };\n                        int[] bridgeProbeModes = {3, 3, 3, 3, 3, 3};\n                        boolean[] selfMeterFlags = {true, true, true, true, true, true};\n                        boolean[] applyShadingFlags = {false, true, true, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false, false};\n                        boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true, true, true};\n                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 1.0, 1.0, 1.0};\n                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {false, false, false, true, true, true};\n                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.0, 0.0, 0.20, 0.30, 0.40};'''
renderer = replace_once(renderer, old_arrays, new_arrays, 'normalized output bank')

old_selectors = '''                            double shadingLumaAuthorityAlpha =\n                                    shadingLumaAuthorityAlphaFlags[variantIndex];'''
new_selectors = '''                            double shadingLumaAuthorityAlpha =\n                                    shadingLumaAuthorityAlphaFlags[variantIndex];\n                            boolean normalizeShadingLumaOutsideMedian1A =\n                                    normalizeShadingLumaOutsideMedian1AFlags[variantIndex];\n                            double shadingLumaTargetOutsideMedianEv1A =\n                                    shadingLumaTargetOutsideMedianEv1AFlags[variantIndex];'''
renderer = replace_once(renderer, old_selectors, new_selectors, 'normalization selectors')

old_call = '''                                        applyShadedGuard1A, applyShadedGuardCap20Ev1A,\n                                        applyShadingLumaDecomp1A, shadingLumaAuthorityAlpha);'''
new_call = '''                                        applyShadedGuard1A, applyShadedGuardCap20Ev1A,\n                                        applyShadingLumaDecomp1A, shadingLumaAuthorityAlpha,\n                                        normalizeShadingLumaOutsideMedian1A, shadingLumaTargetOutsideMedianEv1A);'''
renderer = replace_once(renderer, old_call, new_call, 'normalization prospective call')
renderer = replace_once(
    renderer,
    '"main_physical_2_primary_vs_basis_hsm_shading_alpha_sweep1a"',
    '"main_physical_2_primary_vs_basis_hsm_shading_luma_norm1a"',
    'comparison identity')

gradle = gradle.replace('-basishsm1m-shadingalphasweep1a', '-basishsm1n-shadinglumanorm1a', 1)
if '-basishsm1n-shadinglumanorm1a' not in gradle:
    raise SystemExit('BASISHSM1N failed build provenance')

# Recheck all frozen photographic/decomposition helpers byte-for-byte.
for k, marker in frozen_markers.items():
    _, _, method = extract_method(renderer, marker)
    if hashlib.sha256(method.encode()).hexdigest() != frozen_sha[k]:
        raise SystemExit('BASISHSM1N changed frozen method: ' + k)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1N-SHADINGLUMANORM1A applied')
print(' - same RAW controls: SHADING_OFF, exact full SHADING_ON, CHROMA_ONLY')
print(' - normalized common-luma targets: outside-center median 0.20 / 0.30 / 0.40 EV')
print(' - effective alpha = min(1, targetEV / full-map outside-center median common EV)')
print(' - alpha derives only from LensShadingMap common-gain geometry; no scene-luma input')
print(' - validated 1L decomposition/render math and exact full-shading helper byte-frozen')
print(' - Primary / TC20 / HSM / tone / DNG / capture / JPEG math unchanged')
print(' - global shaded guards/caps and post-render vignette remain absent')
print(' - single RAW / HDR=false boundary preserved')
