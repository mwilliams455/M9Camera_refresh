#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1h-shadedguardab1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A opening brace missing: ' + marker)
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
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1H-SHADEDGUARDAB1A {label} anchor count={count}')
    return src.replace(old, new, 1)


# Start only from the field-tested 1G state. This experiment does not change the
# guard formula or any production/capture path. It only exposes the missing same-RAW
# unguarded shading-ON control alongside OFF and guarded ON.
for marker in [
    'm9cam.renderer.basishsm.shadedguard.v1a.main',
    'shadedGuard1AEligible',
    'shadedGuard1AApplied',
    'shadedGuard1ACorrectedGuardGain',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
    'shadedTailAuditStats.predictedGuardGain',
    'shadingDomain1A',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'shadingLateRepresentationScaleApplied", false',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    'native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a',
    'boolean[] selfMeterFlags = {true, true};',
    'boolean[] applyShadingFlags = {false, true};',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A requires 1G marker: ' + marker)
if '-basishsm1g-shadedguard1a' not in gradle:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A requires 1G build provenance')
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_before = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_before = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_before = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
primary_sha = hashlib.sha256(primary_before.encode()).hexdigest()
shading_sha = hashlib.sha256(shading_before.encode()).hexdigest()
residual_sha = hashlib.sha256(residual_before.encode()).hexdigest()
tail_sha = hashlib.sha256(tail_before.encode()).hexdigest()

# -----------------------------------------------------------------------------
# 1) Parameterize only whether the already-existing SHADEDGUARD1A decision is
#    allowed to bind. The unguarded control still runs the same shaded-tail audit,
#    but it cannot feed the render gain. This makes ON-unguarded vs ON-guarded a
#    clean same-RAW, same-shading, same-colour, same-TC20 causal comparison.
# -----------------------------------------------------------------------------
pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')

old_sig = '''                                         double fixedPrimaryGain,
                                         boolean applyNativeShading,
                                         int bridgeProbeMode,
                                         boolean selfMeter) throws Exception {'''
new_sig = '''                                         double fixedPrimaryGain,
                                         boolean applyNativeShading,
                                         int bridgeProbeMode,
                                         boolean selfMeter,
                                         boolean applyShadedGuard1A) throws Exception {'''
prospective = replace_once(prospective, old_sig, new_sig, 'prospective signature')

old_eligible = '''            final boolean shadedGuard1AEligible = meterParitySelfMeter
                    && applyNativeShading'''
new_eligible = '''            final boolean shadedGuard1AEligible = applyShadedGuard1A
                    && meterParitySelfMeter
                    && applyNativeShading'''
prospective = replace_once(prospective, old_eligible, new_eligible, 'guard request gate')

prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.shadedguard.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.shadedguardab.v1a.main");',
    'prospective schema')

prospective = replace_once(
    prospective,
    '            d.put("shadedTailAudit1AEnabled", applyNativeShading);',
    '''            d.put("shadedTailAudit1AEnabled", applyNativeShading);
            d.put("shadedGuardAB1A", true);
            d.put("shadedGuard1ARequested", applyShadedGuard1A);''',
    'top-level AB diagnostics')

prospective = replace_once(
    prospective,
    '            shadedTailAuditJson.put("shadedGuard1A", true);\n            shadedTailAuditJson.put("shadedGuard1AEligible", shadedGuard1AEligible);',
    '''            shadedTailAuditJson.put("shadedGuard1A", true);
            shadedTailAuditJson.put("shadedGuard1ARequested", applyShadedGuard1A);
            shadedTailAuditJson.put("shadedGuardAB1ARole", !applyNativeShading
                    ? "shading_off_control"
                    : (applyShadedGuard1A ? "shading_on_guarded" : "shading_on_unguarded_control"));
            shadedTailAuditJson.put("shadedGuard1AEligible", shadedGuard1AEligible);''',
    'tail AB diagnostics')

renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

# -----------------------------------------------------------------------------
# 2) Expand the field products from 2 variants to 3 variants:
#      OFF                  : no physical LensShadingMap
#      ON_UNGUARDED1A       : physical shading + SHADINGDOMAIN1A, old 1F meter gain
#      ON_SHADEDGUARD1A     : identical shaded path, corrected-tail guard permitted
#    Primary JPEG remains the frozen production output outside this experiment.
# -----------------------------------------------------------------------------
old_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_shading_off",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a"
                        };
                        int[] bridgeProbeModes = {3, 3};
                        boolean[] selfMeterFlags = {true, true};
                        boolean[] applyShadingFlags = {false, true};'''
new_arrays = '''                        String[] suffixes = {
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
renderer = replace_once(renderer, old_arrays, new_arrays, 'three-way field arrays')

old_loop = '''                            boolean selfMeter = selfMeterFlags[variantIndex];
                            boolean applyShading = applyShadingFlags[variantIndex];'''
new_loop = '''                            boolean selfMeter = selfMeterFlags[variantIndex];
                            boolean applyShading = applyShadingFlags[variantIndex];
                            boolean applyShadedGuard1A = applyShadedGuard1AFlags[variantIndex];'''
renderer = replace_once(renderer, old_loop, new_loop, 'field guard selector')

old_call = '''                                        cameraRotation, selfMeter ? primaryEdgeEv : 0.0,
                                        characteristics, physicalResult,
                                        fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter);'''
new_call = '''                                        cameraRotation, selfMeter ? primaryEdgeEv : 0.0,
                                        characteristics, physicalResult,
                                        fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter,
                                        applyShadedGuard1A);'''
renderer = replace_once(renderer, old_call, new_call, 'prospective call')

renderer = replace_once(
    renderer,
    '"main_physical_2_primary_vs_basis_hsm_selfmeter_shading_off_on"',
    '"main_physical_2_primary_vs_basis_hsm_shading_off_on_unguarded_on_guarded"',
    'comparison-set identity')

# Distinct build provenance; do not alter the existing 1G guard constants or helper.
gradle = gradle.replace('-basishsm1g-shadedguard1a', '-basishsm1h-shadedguardab1a', 1)
if '-basishsm1h-shadedguardab1a' not in gradle:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A failed to set build provenance')

# Frozen production renderer and physical/audit helpers remain source-byte identical.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_after = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_after = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_after = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
if hashlib.sha256(primary_after.encode()).hexdigest() != primary_sha:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A changed frozen Primary renderCore')
if hashlib.sha256(shading_after.encode()).hexdigest() != shading_sha:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A changed LensShadingMap helper')
if hashlib.sha256(residual_after.encode()).hexdigest() != residual_sha:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A changed RAW residual audit')
if hashlib.sha256(tail_after.encode()).hexdigest() != tail_sha:
    raise SystemExit('BASISHSM1H-SHADEDGUARDAB1A changed shaded-tail audit helper')

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1H-SHADEDGUARDAB1A applied')
print(' - Primary / LensShadingMap / residual audit / tail audit SHA preserved')
print(' - guard formula and TC_HEADROOM_TARGET unchanged')
print(' - outputs: shading OFF / shading ON unguarded / shading ON guarded')
print(' - ON unguarded and ON guarded differ only by permission for SHADEDGUARD1A to bind')
print(' - single RAW / HDR=false / capture exposure / DNG remain frozen')
