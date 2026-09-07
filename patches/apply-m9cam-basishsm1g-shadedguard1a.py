#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1g-shadedguard1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A opening brace missing: ' + marker)
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
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1G-SHADEDGUARD1A {label} anchor count={count}')
    return src.replace(old, new, 1)


for marker in [
    'shadedTailAudit1AEnabled',
    'm9cam.renderer.shadedtailaudit.v1a',
    'predictedGuardGainAtOriginalQ',
    'predictedGainDeltaEvVsCurrent',
    'photographicDecisionMutation", false',
    'shadingDomain1A',
    'final double effectiveRenderGain = meterParityRenderBaseGain;',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A requires SHADEDTAILAUDIT1A marker: ' + marker)
if '-basishsm1f-shadedtailaudit1a' not in gradle:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A requires SHADEDTAILAUDIT1A build provenance')
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1G-SHADEDGUARD1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_before = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_before = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_before = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
primary_sha = hashlib.sha256(primary_before.encode()).hexdigest()
shading_sha = hashlib.sha256(shading_before.encode()).hexdigest()
residual_sha = hashlib.sha256(residual_before.encode()).hexdigest()
tail_sha = hashlib.sha256(tail_before.encode()).hexdigest()

pros_start, pros_end, prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')
old_gain = '''            final double meterParityRenderBaseGain = meterParitySelfMeter
                    ? meter.gain * Math.pow(2.0, edgePlacementGainEv)
                    : fixedPrimaryGain;
            // SHADINGDOMAIN1A restored the representation scale before TC20/HSM,
            // so the final render gain is now the photographic meter decision only.
            final double effectiveRenderGain = meterParityRenderBaseGain;'''
new_gain = '''            // BASISHSM1G-SHADEDGUARD1A: field audit showed that the corrected-tail
            // headroom guard is non-binding in ordinary scenes and binds only the true
            // highlight-limited shading-ON case. Keep the frozen TC20 weighted-median
            // base gain, but replace only its RAW-tail guard domain for shading ON.
            final double shadedGuard1AOriginalMeterGain = meter.gain;
            final double shadedGuard1AOriginalUnshadedGuardGain = meter.guardGain;
            final boolean shadedGuard1AEligible = meterParitySelfMeter
                    && applyNativeShading
                    && shadedTailAuditStats.valid
                    && Double.isFinite(shadedTailAuditStats.predictedGuardGain)
                    && shadedTailAuditStats.predictedGuardGain > 0.0;
            final double shadedGuard1ACorrectedGuardGain = shadedGuard1AEligible
                    ? shadedTailAuditStats.predictedGuardGain
                    : meter.guardGain;
            final double shadedGuard1AMeterGain = shadedGuard1AEligible
                    ? Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)
                    : meter.gain;
            final boolean shadedGuard1AApplied = shadedGuard1AEligible
                    && shadedGuard1AMeterGain < shadedGuard1AOriginalMeterGain - 1.0e-12;

            final double meterParityRenderBaseGain = meterParitySelfMeter
                    ? shadedGuard1AMeterGain * Math.pow(2.0, edgePlacementGainEv)
                    : fixedPrimaryGain;
            // SHADINGDOMAIN1A restored the representation scale before TC20/HSM,
            // so the final render gain is now the photographic meter decision only.
            final double effectiveRenderGain = meterParityRenderBaseGain;'''
prospective = replace_once(prospective, old_gain, new_gain, 'render gain guard seam')

# Promote schema and make the prior audit truthful now that its prediction is applied.
prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.shadedtailaudit.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.shadedguard.v1a.main");',
    'prospective schema')

diag_anchor = '''            shadedTailAuditJson.put("photographicDecisionMutation", false);
            d.put("shadedTailAudit1A", shadedTailAuditJson);'''
diag_replacement = '''            shadedTailAuditJson.put("photographicDecisionMutation", shadedGuard1AApplied);
            shadedTailAuditJson.put("shadedGuard1A", true);
            shadedTailAuditJson.put("shadedGuard1AEligible", shadedGuard1AEligible);
            shadedTailAuditJson.put("shadedGuard1AApplied", shadedGuard1AApplied);
            shadedTailAuditJson.put("shadedGuard1AOriginalMeterGain", shadedGuard1AOriginalMeterGain);
            shadedTailAuditJson.put("shadedGuard1AOriginalUnshadedGuardGain", shadedGuard1AOriginalUnshadedGuardGain);
            shadedTailAuditJson.put("shadedGuard1ACorrectedGuardGain", shadedGuard1ACorrectedGuardGain);
            shadedTailAuditJson.put("shadedGuard1AMeterGain", shadedGuard1AMeterGain);
            if (shadedGuard1AOriginalMeterGain > 0.0 && shadedGuard1AMeterGain > 0.0) {
                shadedTailAuditJson.put("shadedGuard1AGainDeltaEvVsOldOn",
                        Math.log(shadedGuard1AMeterGain / shadedGuard1AOriginalMeterGain) / Math.log(2.0));
            }
            d.put("shadedTailAudit1A", shadedTailAuditJson);'''
prospective = replace_once(prospective, diag_anchor, diag_replacement, 'guard diagnostics')

renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

# Rename only the experimental ON output so field images cannot be confused with 1F.
renderer = replace_once(
    renderer,
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    'ON suffix')
renderer = replace_once(
    renderer,
    '"native_plus_historical_basis_hsm_self_meter_shading_on"',
    '"native_plus_historical_basis_hsm_self_meter_shading_on_shadedguard1a"',
    'ON diagnostic name')

gradle = gradle.replace('-basishsm1f-shadedtailaudit1a', '-basishsm1g-shadedguard1a', 1)

_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_after = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_after = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_after = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
if hashlib.sha256(primary_after.encode()).hexdigest() != primary_sha:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A changed frozen Primary renderCore')
if hashlib.sha256(shading_after.encode()).hexdigest() != shading_sha:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A changed LensShadingMap helper')
if hashlib.sha256(residual_after.encode()).hexdigest() != residual_sha:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A changed RAW residual audit')
if hashlib.sha256(tail_after.encode()).hexdigest() != tail_sha:
    raise SystemExit('BASISHSM1G-SHADEDGUARD1A changed shaded-tail audit helper')

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1G-SHADEDGUARD1A applied')
print(' - Primary / shading helper / residual audit / tail audit SHA preserved')
print(' - only shading-ON TC20 headroom guard domain is promoted from audit to render decision')
print(' - weighted-median base gain remains unchanged')
print(' - OFF path remains byte-equivalent by construction')
print(' - single RAW / HDR=false / capture exposure / DNG remain frozen')
