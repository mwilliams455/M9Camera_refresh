#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1j-shadedguardcap20ev1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n':
                state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/':
                state = 'code'
                i += 1
        elif state == 'string':
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                state = 'code'
        else:
            if ch == '/' and nxt == '/':
                state = 'line_comment'
                i += 1
            elif ch == '/' and nxt == '*':
                state = 'block_comment'
                i += 1
            elif ch in ('"', "'"):
                state = 'string'
                quote = ch
                escape = False
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A unterminated method: ' + marker)

def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1J-SHADEDGUARDCAP20EV1A {label} anchor count={count}')
    return src.replace(old, new, 1)

for marker in [
    'm9cam.renderer.basishsm.finalclipaudit.v1a.main',
    'finalClipAudit1AEnabled',
    'private static JSONObject finalClipAudit1A(',
    'shadedGuardAB1A',
    'shadedGuard1ARequested',
    'shading_on_unguarded_control',
    'shading_on_guarded',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    'boolean[] applyShadedGuard1AFlags = {false, false, true};',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A requires 1I marker: ' + marker)
if '-basishsm1i-finalclipaudit1a' not in gradle:
    raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A requires 1I build provenance')
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_before = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_before = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_before = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
_, _, clip_before = extract_method(renderer, '    private static JSONObject finalClipAudit1A(')
frozen_sha = {
    'primary': hashlib.sha256(primary_before.encode()).hexdigest(),
    'shading': hashlib.sha256(shading_before.encode()).hexdigest(),
    'residual': hashlib.sha256(residual_before.encode()).hexdigest(),
    'tail': hashlib.sha256(tail_before.encode()).hexdigest(),
    'clip': hashlib.sha256(clip_before.encode()).hexdigest(),
}

pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')

old_sig = '''                                         int bridgeProbeMode,
                                         boolean selfMeter,
                                         boolean applyShadedGuard1A) throws Exception {'''
new_sig = '''                                         int bridgeProbeMode,
                                         boolean selfMeter,
                                         boolean applyShadedGuard1A,
                                         boolean applyShadedGuardCap20Ev1A) throws Exception {'''
prospective = replace_once(prospective, old_sig, new_sig, 'prospective signature')

old_eligible = '''            final boolean shadedGuard1AEligible = applyShadedGuard1A
                    && meterParitySelfMeter'''
new_eligible = '''            final boolean shadedGuard1AEligible = (applyShadedGuard1A || applyShadedGuardCap20Ev1A)
                    && meterParitySelfMeter'''
prospective = replace_once(prospective, old_eligible, new_eligible, 'guard eligibility')

old_apply = '''            final boolean shadedGuard1AApplied = shadedGuard1AEligible
                    && shadedGuard1AMeterGain < shadedGuard1AOriginalMeterGain - 1.0e-12;

            final double meterParityRenderBaseGain = meterParitySelfMeter
                    ? shadedGuard1AMeterGain * Math.pow(2.0, edgePlacementGainEv)
                    : fixedPrimaryGain;'''
new_apply = '''            final boolean shadedGuard1AFullRequestWouldApply = shadedGuard1AEligible
                    && shadedGuard1AMeterGain < shadedGuard1AOriginalMeterGain - 1.0e-12;

            // BASISHSM1J-SHADEDGUARDCAP20EV1A. Bound only the newly added candidate.
            // Gain may still fall by less than 0.20 EV when the corrected-tail guard
            // itself requests less. It can never increase above the old shaded meter
            // decision and can never make a stronger cut than full SHADEDGUARD1A.
            final double shadedGuardCap20Ev1AMaxReductionEv = 0.20;
            final double shadedGuardCap20Ev1AMinGainRatio =
                    Math.pow(2.0, -shadedGuardCap20Ev1AMaxReductionEv);
            final double shadedGuardCap20Ev1AFloorGain =
                    shadedGuard1AOriginalMeterGain * shadedGuardCap20Ev1AMinGainRatio;
            final double shadedGuard1ARenderedMeterGain = applyShadedGuardCap20Ev1A
                    ? Math.max(shadedGuard1AMeterGain, shadedGuardCap20Ev1AFloorGain)
                    : shadedGuard1AMeterGain;
            final boolean shadedGuardCap20Ev1ABound =
                    applyShadedGuardCap20Ev1A
                    && shadedGuard1AMeterGain < shadedGuardCap20Ev1AFloorGain - 1.0e-12;
            final boolean shadedGuard1AApplied = shadedGuard1AEligible
                    && shadedGuard1ARenderedMeterGain
                    < shadedGuard1AOriginalMeterGain - 1.0e-12;

            final double meterParityRenderBaseGain = meterParitySelfMeter
                    ? shadedGuard1ARenderedMeterGain * Math.pow(2.0, edgePlacementGainEv)
                    : fixedPrimaryGain;'''
prospective = replace_once(prospective, old_apply, new_apply, 'cap render-gain seam')

prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.finalclipaudit.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.shadedguardcap20ev.finalclipaudit.v1a.main");',
    'prospective schema')

top_diag = '''            d.put("shadedGuardAB1A", true);
            d.put("shadedGuard1ARequested", applyShadedGuard1A);'''
top_repl = '''            d.put("shadedGuardAB1A", true);
            d.put("shadedGuard1ARequested", applyShadedGuard1A);
            d.put("shadedGuardCap20Ev1AEnabled", true);
            d.put("shadedGuardCap20Ev1ARequested", applyShadedGuardCap20Ev1A);
            d.put("shadedGuardCap20Ev1AMaxReductionEv", 0.20);'''
prospective = replace_once(prospective, top_diag, top_repl, 'top cap diagnostics')

role_old = '''            shadedTailAuditJson.put("shadedGuard1ARequested", applyShadedGuard1A);
            shadedTailAuditJson.put("shadedGuardAB1ARole", !applyNativeShading
                    ? "shading_off_control"
                    : (applyShadedGuard1A ? "shading_on_guarded" : "shading_on_unguarded_control"));'''
role_new = '''            shadedTailAuditJson.put("shadedGuard1ARequested", applyShadedGuard1A);
            shadedTailAuditJson.put("shadedGuardCap20Ev1ARequested", applyShadedGuardCap20Ev1A);
            shadedTailAuditJson.put("shadedGuardAB1ARole", !applyNativeShading
                    ? "shading_off_control"
                    : (applyShadedGuardCap20Ev1A
                    ? "shading_on_guarded_cap20ev1a"
                    : (applyShadedGuard1A ? "shading_on_guarded" : "shading_on_unguarded_control")));'''
prospective = replace_once(prospective, role_old, role_new, 'cap role diagnostics')

diag_old = '''            shadedTailAuditJson.put("shadedGuard1AApplied", shadedGuard1AApplied);
            shadedTailAuditJson.put("shadedGuard1AOriginalMeterGain", shadedGuard1AOriginalMeterGain);
            shadedTailAuditJson.put("shadedGuard1AOriginalUnshadedGuardGain", shadedGuard1AOriginalUnshadedGuardGain);
            shadedTailAuditJson.put("shadedGuard1ACorrectedGuardGain", shadedGuard1ACorrectedGuardGain);
            shadedTailAuditJson.put("shadedGuard1AMeterGain", shadedGuard1AMeterGain);
            if (shadedGuard1AOriginalMeterGain > 0.0 && shadedGuard1AMeterGain > 0.0) {
                shadedTailAuditJson.put("shadedGuard1AGainDeltaEvVsOldOn",
                        Math.log(shadedGuard1AMeterGain / shadedGuard1AOriginalMeterGain) / Math.log(2.0));
            }'''
diag_new = '''            shadedTailAuditJson.put("shadedGuard1AApplied", shadedGuard1AApplied);
            shadedTailAuditJson.put("shadedGuard1AFullRequestWouldApply", shadedGuard1AFullRequestWouldApply);
            shadedTailAuditJson.put("shadedGuard1AOriginalMeterGain", shadedGuard1AOriginalMeterGain);
            shadedTailAuditJson.put("shadedGuard1AOriginalUnshadedGuardGain", shadedGuard1AOriginalUnshadedGuardGain);
            shadedTailAuditJson.put("shadedGuard1ACorrectedGuardGain", shadedGuard1ACorrectedGuardGain);
            shadedTailAuditJson.put("shadedGuard1AMeterGain", shadedGuard1AMeterGain);
            shadedTailAuditJson.put("shadedGuard1ARenderedMeterGain", shadedGuard1ARenderedMeterGain);
            shadedTailAuditJson.put("shadedGuardCap20Ev1AMaxReductionEv", shadedGuardCap20Ev1AMaxReductionEv);
            shadedTailAuditJson.put("shadedGuardCap20Ev1AMinGainRatio", shadedGuardCap20Ev1AMinGainRatio);
            shadedTailAuditJson.put("shadedGuardCap20Ev1AFloorGain", shadedGuardCap20Ev1AFloorGain);
            shadedTailAuditJson.put("shadedGuardCap20Ev1ABound", shadedGuardCap20Ev1ABound);
            if (shadedGuard1AOriginalMeterGain > 0.0 && shadedGuard1AMeterGain > 0.0) {
                shadedTailAuditJson.put("shadedGuard1AFullRequestedGainDeltaEvVsOldOn",
                        Math.log(shadedGuard1AMeterGain / shadedGuard1AOriginalMeterGain) / Math.log(2.0));
            }
            if (shadedGuard1AOriginalMeterGain > 0.0 && shadedGuard1ARenderedMeterGain > 0.0) {
                shadedTailAuditJson.put("shadedGuard1AGainDeltaEvVsOldOn",
                        Math.log(shadedGuard1ARenderedMeterGain / shadedGuard1AOriginalMeterGain) / Math.log(2.0));
            }'''
prospective = replace_once(prospective, diag_old, diag_new, 'cap tail diagnostics')
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

old_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_shading_off",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a"
                        };
                        int[] bridgeProbeModes = {3, 3, 3};
                        boolean[] selfMeterFlags = {true, true, true};
                        boolean[] applyShadingFlags = {false, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, true};'''
new_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_shading_off",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_shadedguardcap20ev1a"
                        };
                        int[] bridgeProbeModes = {3, 3, 3, 3};
                        boolean[] selfMeterFlags = {true, true, true, true};
                        boolean[] applyShadingFlags = {false, true, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, true, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, true};'''
renderer = replace_once(renderer, old_arrays, new_arrays, 'four-way field arrays')

old_loop = '''                            boolean applyShading = applyShadingFlags[variantIndex];
                            boolean applyShadedGuard1A = applyShadedGuard1AFlags[variantIndex];'''
new_loop = '''                            boolean applyShading = applyShadingFlags[variantIndex];
                            boolean applyShadedGuard1A = applyShadedGuard1AFlags[variantIndex];
                            boolean applyShadedGuardCap20Ev1A =
                                    applyShadedGuardCap20Ev1AFlags[variantIndex];'''
renderer = replace_once(renderer, old_loop, new_loop, 'field cap selector')

old_call = '''                                        fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter,
                                        applyShadedGuard1A);'''
new_call = '''                                        fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter,
                                        applyShadedGuard1A, applyShadedGuardCap20Ev1A);'''
renderer = replace_once(renderer, old_call, new_call, 'prospective cap call')

renderer = replace_once(
    renderer,
    '"main_physical_2_primary_vs_basis_hsm_shading_off_on_unguarded_on_guarded"',
    '"main_physical_2_primary_vs_basis_hsm_shading_off_on_unguarded_on_guarded_on_cap20ev"',
    'comparison-set identity')

gradle = gradle.replace(
    '-basishsm1i-finalclipaudit1a',
    '-basishsm1j-shadedguardcap20ev1a',
    1)
if '-basishsm1j-shadedguardcap20ev1a' not in gradle:
    raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A failed to set build provenance')

_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_after = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_after = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_after = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
_, _, clip_after = extract_method(renderer, '    private static JSONObject finalClipAudit1A(')
after = {
    'primary': hashlib.sha256(primary_after.encode()).hexdigest(),
    'shading': hashlib.sha256(shading_after.encode()).hexdigest(),
    'residual': hashlib.sha256(residual_after.encode()).hexdigest(),
    'tail': hashlib.sha256(tail_after.encode()).hexdigest(),
    'clip': hashlib.sha256(clip_after.encode()).hexdigest(),
}
for key in frozen_sha:
    if after[key] != frozen_sha[key]:
        raise SystemExit('BASISHSM1J-SHADEDGUARDCAP20EV1A changed frozen helper: ' + key)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1J-SHADEDGUARDCAP20EV1A applied')
print(' - adds fourth shaded candidate capped to <=0.20 EV whole-frame reduction')
print(' - retains OFF / ON unguarded / ON full SHADEDGUARD1A controls')
print(' - FINALCLIPAUDIT1A remains byte-identical and runs on all four products')
print(' - Primary / LensShadingMap / residual audit / tail audit remain frozen')
print(' - TC_HEADROOM_TARGET / capture exposure / DNG / single RAW / HDR=false unchanged')
