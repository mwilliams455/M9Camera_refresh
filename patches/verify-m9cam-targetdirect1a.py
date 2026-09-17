#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-targetdirect1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
rp = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
cp = root / 'app/src/main/cpp/m9color_jni.cpp'
if not rp.exists() or not cp.exists():
    raise SystemExit('TARGETDIRECT1A assembled sources missing')
s = rp.read_text()
c = cp.read_text()


def method_span(text, signature):
    start = text.find(signature)
    if start < 0: return ''
    brace = text.find('{', start)
    if brace < 0: return ''
    depth = 0; state = 'code'; quote = ''; escape = False; i = brace
    while i < len(text):
        ch = text[i]; nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return text[start:i + 1]
        i += 1
    return ''

prod = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
mode0 = '                0,\n                true,\n                false, false,'
mode4 = '                4,\n                true,\n                false, false,'
checks = {
    'production_method_found': bool(prod),
    'production_mode0_exactly_once': prod.count(mode0) == 1,
    'production_mode4_absent': mode4 not in prod,
    'targetdirect_marker': 'd.put("targetDirect1A", true);' in prod,
    'targetdirect_schema': 'm9cam.targetdirect.v1a.common_scene_direct' in prod,
    'direct_common_scene_domain': 'common_scene_ProPhoto_D50_direct_to_M9_bridge' in prod,
    'targetinput_adapter_false': 'd.put("targetInputAdapter1AApplied", false);' in prod,
    'adapter_basis_identity_diag': 'd.put("targetInputAdapterBasisMaxAbsFromIdentity", 0.0);' in prod,
    'cobalt_runtime_false': 'd.put("cobaltRuntimeProductionDependency", false);' in prod,
    'cobalt_role_none': 'd.put("cobaltRuntimeDependencyRole", "none_production");' in prod,
    'cobalt_linear_basis_false': 'd.put("cobaltHistoricalLinearBasisApplied", false);' in prod,
    'cobalt_hsm_false': 'd.put("cobaltHueSatMapApplied", false);' in prod,
    'mixed_calibration_false': 'd.put("mixedCalibrationAssetUsedByProduction", false);' in prod,
    'identity_hsm_true': 'd.put("identityHsmApplied", true);' in prod,
    'identity_hsm_90x30': 'd.put("basisHsmHsmTableIdentity", "identity_90x30");' in prod,
    'historical_calibration_gated_off_for_mode0': 'final boolean historicalProbeCalibrationRequired = bridgeProbeMode != 0;' in s,
    'targetdomaintrace_retained': 'm9cam.targetdomaintrace.v1a.readonly' in s and 'd.put("targetDomainTrace1A", targetDomainTrace1AJson);' in s,
    'targetdomaintrace_readonly': 'targetDomainTrace1APixelMutation", false' in s,
    'tonebound050_retained': 'm9cam.tonebound.v1a.050ev' in s,
    'sat2_selector_retained': 'SATURATION_BANK == 2 ? 9' in s,
    'sat2_state_retained': 'firmware_Standard_sRGB_nSaturation_2' in s,
}
expected = [13659,-4457,-1004,-2244,13469,-3033,-199,-6014,14398,
            14811,-5604,-1004,-2455,13688,-3033,393,-6588,14398]
checks['sat2_coefficients_present'] = all(str(x) in s or str(x) in c for x in expected)

# TARGETDIRECT1A intentionally leaves the historical probe implementation in source
# for controlled research, but production mode 0 must not request that calibration.
checks['historical_adapter_not_called_by_production_wrapper'] = 'buildTargetInputAdapter1A(' not in prod

failed = [k for k, v in checks.items() if not v]
for k, v in checks.items():
    print(k, 'PASS' if v else 'FAIL')
if failed:
    raise SystemExit('TARGETDIRECT1A VERIFY FAIL: ' + ', '.join(failed))
print('TARGETDIRECT1A VERIFY PASS')
