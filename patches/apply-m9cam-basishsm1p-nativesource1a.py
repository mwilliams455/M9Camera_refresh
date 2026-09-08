#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1p-nativesource1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
audit_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
gradle_path = root / 'app/build.gradle'
for p in (renderer_path, audit_path, gradle_path):
    if not p.exists():
        raise SystemExit('BASISHSM1P-NATIVESOURCE1A missing: ' + str(p))
renderer = renderer_path.read_text()
audit = audit_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1P method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1P opening brace missing: ' + marker)
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
                if depth == 0: return start, i+1, src[start:i+1]
        i += 1
    raise SystemExit('BASISHSM1P unterminated method: ' + marker)


def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f'BASISHSM1P {label} anchor count={n}')
    return src.replace(old, new, 1)

for marker in [
    'BASISHSM1O-LUMANORM030ACCEPT1A',
    'SOURCECAL2A_CMFIX_DNG_dual_illuminant_math_CM_unchanged_FM_D50_normalized_live_neutral',
    'NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major',
    'historical_linear_basis_then_historical_HSM',
    '"shadingLumaNorm1AUsesSceneBrightness", false',
    '"shadingLumaNorm1AUsesFinalClipFeedback", false',
    '"shadingLumaNorm1AUsesPrimaryFeedback", false',
]:
    if marker not in renderer and marker not in audit:
        raise SystemExit('BASISHSM1P requires validated 1O/source marker: ' + marker)
if '-basishsm1o-lumanorm030accept1a' not in gradle:
    raise SystemExit('BASISHSM1P requires 1O build provenance')

frozen_methods = {
    'legacy_core': '    private static RenderCore renderCore(',
    'native_core': '    private static RenderCore renderNativeProspectiveCore(',
    'luma_decomp': '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    'native_source': '    private static NativeProspectiveSource buildNativeProspectiveSource(',
}
frozen_sha = {}
for name, marker in frozen_methods.items():
    _, _, method = extract_method(renderer, marker)
    frozen_sha[name] = hashlib.sha256(method.encode()).hexdigest()

old_pipeline = 'Cobalt main DCP H25/S85/V100 -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1'
new_pipeline = 'NORM030 physical LensShadingMap -> native Xiaomi SOURCECAL2A -> BASISHSM1A historical working-basis/H25 target role -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1'
if renderer.count(old_pipeline) != 4:
    raise SystemExit('BASISHSM1P expected four legacy pipeline provenance strings, got ' + str(renderer.count(old_pipeline)))
renderer = renderer.replace(old_pipeline, new_pipeline, 2)

renderer = renderer.replace(
    '// M9SOURCECAL1A/1C: native Camera2/DNG source characterization only; never feeds renderCore.',
    '// BASISHSM1P-NATIVESOURCE1A: native Camera2/DNG source characterization is now the production source transform.',
    1)

insert_marker = '    private static RenderCore renderCore(ByteBuffer rawBuffer,'
insert_at = renderer.find(insert_marker)
if insert_at < 0:
    raise SystemExit('BASISHSM1P production wrapper insertion marker missing')
if 'private static RenderCore renderNativeSourceProduction1P(' in renderer:
    raise SystemExit('BASISHSM1P wrapper already present')
wrapper = r'''    // BASISHSM1P-NATIVESOURCE1A production route.
    // Photographic math is the validated 1O middle candidate exactly:
    // native SOURCECAL2A + historical basis/H25 target role + self-meter TC20 + NORM030.
    // The old Cobalt-source renderCore remains only as a dormant forensic reference.
    private static RenderCore renderNativeSourceProduction1P(ByteBuffer rawBuffer,
                                         int width,
                                         int height,
                                         float[] black,
                                         int whiteLevel,
                                         float[] neutralF,
                                         int cameraRotation,
                                         double edgePlacementGainEv,
                                         CameraCharacteristics nativeCharacteristics,
                                         CaptureResult nativeCaptureResult) throws Exception {
        RenderCore out = renderNativeProspectiveCore(
                rawBuffer, width, height, black, whiteLevel, neutralF,
                cameraRotation, edgePlacementGainEv,
                nativeCharacteristics, nativeCaptureResult,
                1.0,
                true,
                3,
                true,
                false, false,
                true, 1.0,
                true, 0.30);
        JSONObject d = out.diagnostics;
        d.put("schema", "m9cam.renderer.basishsm.v1p.nativesource1a.production");
        d.put("nativeSourceProduction1A", true);
        d.put("nativeSourceTransformApplied", true);
        d.put("sourceAdapterProvider", "Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX");
        d.put("sourceTransformFamily", "SOURCECAL2A_CMFIX_DNG_dual_illuminant_math_CM_unchanged_FM_D50_normalized_live_neutral");
        d.put("cobaltSourceAdapterApplied", false);
        d.put("cobaltSourceColorMatrixApplied", false);
        d.put("cobaltSourceForwardMatrixApplied", false);
        d.put("cobaltSourceHsmRoleApplied", false);
        d.put("historicalBasisHsmTargetBehaviorApplied", true);
        d.put("historicalBasisHsmRole", "frozen_BASISHSM1A_target_behavior_not_source_transform");
        d.put("historicalBasisDataProvenance", "legacy_profile_role_reconstruction_retained_only_after_native_scene_transform");
        d.put("m9FirmwareCurve02Retained", true);
        d.put("norm030ProductionApplied", true);
        d.put("norm030TargetOutsideMedianEv", 0.30);
        d.put("norm030UsesSceneBrightness", false);
        d.put("norm030UsesFinalClipFeedback", false);
        d.put("norm030UsesPrimaryFeedback", false);
        d.put("productionSelfMeter", true);
        d.put("fixedPrimaryGainReferenceRole", "diagnostic_placeholder_only_not_render_gain_when_selfMeter_true");
        d.remove("meterParityGainRatioVsPrimary");
        d.remove("meterParityGainDeltaEvVsPrimary");
        d.put("pipeline", "NORM030 physical LensShadingMap -> native Xiaomi SOURCECAL2A -> BASISHSM1A historical working-basis/H25 target role -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
        return out;
    }

'''
renderer = renderer[:insert_at] + wrapper + renderer[insert_at:]

old_base_call = '''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0);'''
new_base_call = '''            RenderCore out = renderNativeSourceProduction1P(
                    frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0,
                    characteristics, diagnosticCaptureResult1A);'''
renderer = replace_once(renderer, old_base_call, new_base_call, 'production baseline route')

old_dark_call = '''                        candidateCore = renderCore(frame.buffer, frame.width, frame.height,
                                encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, candidateEv);'''
new_dark_call = '''                        candidateCore = renderNativeSourceProduction1P(
                                frame.buffer, frame.width, frame.height,
                                encodedBlack, params.whiteLevel, params.whitePoint,
                                cameraRotation, candidateEv,
                                characteristics, diagnosticCaptureResult1A);'''
renderer = replace_once(renderer, old_dark_call, new_dark_call, 'dark exact rerender route')

renderer = replace_once(renderer,
    '            diag.put("sourceCalibrationNativeTransformApplied", false);',
    '            diag.put("sourceCalibrationNativeTransformApplied", true);',
    'primary sourcecal truth')
renderer = replace_once(renderer,
    '            diag.put("rawShadingGainMapApplied", false);',
    '            diag.put("rawShadingGainMapApplied", true);',
    'primary shading truth')
renderer = replace_once(renderer,
    '            diag.put("rawShadingPhase", "A_metadata_semantics_audit");',
    '            diag.put("rawShadingPhase", "production_NORM030_linear_Bayer_pre_demosaic");',
    'primary shading phase')

old_bank = '''                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_shading_off",
                                "native_plus_historical_basis_hsm_self_meter_lumanorm030ev1a",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a"
                        };
                        int[] bridgeProbeModes = {3, 3, 3};
                        boolean[] selfMeterFlags = {true, true, true};
                        boolean[] applyShadingFlags = {false, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {false, true, false};
                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {false, true, false};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.30, 0.0};'''
new_bank = '''                        // BASISHSM1P-NATIVESOURCE1A: retain exactly one NORM030 same-RAW
                        // parity JPEG during first production validation. The 1O OFF/full-ON
                        // endpoints are retired; no shading parameter is retuned here.
                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_lumanorm030ev1a_parity1p"
                        };
                        int[] bridgeProbeModes = {3};
                        boolean[] selfMeterFlags = {true};
                        boolean[] applyShadingFlags = {true};
                        boolean[] applyShadedGuard1AFlags = {false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false};
                        boolean[] applyShadingLumaDecomp1AFlags = {true};
                        double[] shadingLumaAuthorityAlphaFlags = {1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30};'''
renderer = replace_once(renderer, old_bank, new_bank, 'single NORM030 parity bank')
renderer = renderer.replace(
    'nativeAb1A.put("scope", "main_physical_2_primary_vs_basis_hsm_lumanorm030_accept1a");',
    'nativeAb1A.put("scope", "main_physical_2_native_source_production_vs_same_math_norm030_parity1p");', 1)
renderer = renderer.replace(
    'nativeAb1A.put("primaryOutputPreserved", true);',
    'nativeAb1A.put("primaryOutputPreserved", true);\n                    nativeAb1A.put("primaryIsNativeSourceProduction1P", true);', 1)
renderer = renderer.replace(
    'nativeAb1A.put("status", "completed_isolated_experiment");',
    'nativeAb1A.put("status", "completed_single_norm030_production_parity");', 1)

audit = replace_once(audit,
    '            out.put("nativeTransformAppliedToRender", false);',
    '            out.put("nativeTransformAppliedToRender", true);',
    'audit native applied')
audit = replace_once(audit,
    '            out.put("cobaltRuntimeDependencyChanged", false);',
    '            out.put("cobaltRuntimeDependencyChanged", true);',
    'audit runtime role changed')
audit = replace_once(audit,
    '            out.put("phase", "A_native_metadata_and_transform_audit_plus_embedded_calibration_role_split");',
    '            out.put("phase", "B_native_SOURCECAL2A_production_source_replacement");',
    'audit phase')
audit = replace_once(audit,
    '            embedded.put("sourceAdapterCurrentlyAppliedToRender", true);',
    '            embedded.put("sourceAdapterCurrentlyAppliedToRender", false);\n'
    '            embedded.put("nativeSourceAdapterCurrentlyAppliedToRender", true);\n'
    '            embedded.put("productionSourceAdapterProvider", "Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX");\n'
    '            embedded.put("historicalBasisHsmRetainedRole", "frozen_target_behavior_after_native_scene_transform");',
    'embedded source role')
audit = replace_once(audit,
    '            embedded.put("nativeReplacementApplied", false);',
    '            embedded.put("nativeReplacementApplied", true);',
    'embedded replacement truth')
audit = replace_once(audit,
    '            embedded.put("comparisonMeaning", "embedded_Cobalt_source_profile_logged_beside_native_Camera2_source_characterization");',
    '            embedded.put("comparisonMeaning", "legacy_mixed_asset_logged_for_role_forensics_native_SOURCECAL2A_is_production_source_transform");',
    'embedded comparison meaning')

gradle = gradle.replace('-basishsm1o-lumanorm030accept1a', '-basishsm1p-nativesource1a', 1)
if '-basishsm1p-nativesource1a' not in gradle:
    raise SystemExit('BASISHSM1P failed build provenance')

_, _, orchestration = extract_method(renderer, '    private static Result renderAndSaveInternal(')
if 'renderCore(' in orchestration:
    raise SystemExit('BASISHSM1P legacy renderCore call survived production orchestration')
if orchestration.count('renderNativeSourceProduction1P(') != 2:
    raise SystemExit('BASISHSM1P expected baseline + DARK native production calls')

for name, marker in frozen_methods.items():
    _, _, method = extract_method(renderer, marker)
    after = hashlib.sha256(method.encode()).hexdigest()
    if after != frozen_sha[name]:
        raise SystemExit(f'BASISHSM1P changed frozen {name} math: {frozen_sha[name]} -> {after}')

renderer_path.write_text(renderer)
audit_path.write_text(audit)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1P-NATIVESOURCE1A applied')
print(' - production baseline + DARK rerenders now use native SOURCECAL2A + BASISHSM1A + self-meter + NORM030')
print(' - legacy Cobalt-source renderCore remains dormant and unreachable from renderAndSaveInternal')
print(' - SOURCECAL sidecar reports native transform applied=true / legacy source adapter applied=false')
print(' - one NORM030 parity JPEG retained for first field validation; OFF/full-ON bank retired')
print(' - no TC20/NORM030/HSM/curve02/BT601/TG1/JPEG math changed')
for k,v in frozen_sha.items(): print(' - frozen', k, v)
