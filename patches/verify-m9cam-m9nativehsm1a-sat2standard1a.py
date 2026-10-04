#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-m9nativehsm1a-sat2standard1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = p.read_text()

def method(text, signature):
    start = text.index(signature); brace = text.index('{', start)
    depth = 0; state = 'code'; quote = ''; esc = False; i = brace
    while i < len(text):
        ch = text[i]; nxt = text[i+1] if i+1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return text[start:i+1]
        i += 1
    raise SystemExit('unterminated method')

prod = method(s, 'private static RenderCore renderNativeSourceProduction1P(')
core = method(s, 'private static RenderCore renderNativeProspectiveCore(')
mode4_start = core.index('} else if (bridgeProbeMode == 4) {')
mode4_end = core.index('} else if (bridgeProbeMode != 0) {', mode4_start)
mode4 = core[mode4_start:mode4_end]

sat2 = len(re.findall(r'\bSATURATION_BANK\s*=\s*2\s*;', s)) == 1
sat3_const = re.search(r'\bSATURATION_BANK\s*=\s*3\s*;', s) is not None
checks = {
    'production_mode4_targetinput_retained': '                4,\n                true,\n                false, false,' in prod,
    'targetinput_basis_retained': 'ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);' in mode4,
    'targetinput_formula_telemetry_retained': 'T_scene=C15_historical_scene*inverse(N15_native_scene); output=T_scene*N_active' in prod,
    'mode4_identity_geometry_90x30': 'cal.hueDivisions != 90 || cal.satDivisions != 30' in mode4,
    'mode4_identity_hue': 'ctx.hsm[i] = 0.0;' in mode4,
    'mode4_identity_saturation': 'ctx.hsm[i + 1] = 1.0;' in mode4,
    'mode4_identity_value': 'ctx.hsm[i + 2] = 1.0;' in mode4,
    'mode4_historical_hsm_removed': 'targetInput.historical15.wA * cal.hsmA[i]' not in mode4,
    'sat2_constant': sat2,
    'sat3_constant_removed': not sat3_const,
    'sat2_telemetry': 'd.put("m9SaturationBank", 2);' in prod,
    'sat2_matrix_pair_telemetry': 'M04_M05' in prod,
    'identity_hsm_telemetry': 'd.put("m9NativeHsm1A", true);' in prod and 'identity_90x30' in prod,
    'cobalt_huesatmap_false': 'd.put("cobaltHueSatMapApplied", false);' in prod,
    'curve02_retained': 'curve02' in core and 'curve02' in prod,
    'bt601_retained': 'BT601' in core and 'BT601' in prod,
    'tg1_retained': 'TG1' in core and 'TG1' in prod,
    'norm030_retained': 'NORM030' in prod,
    'mhc_retained': 'DEMOSAICMHCNEUTRAL1A' in prod,
    'active_physical_source_retained': 'active_physical_Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX' in prod,
}
failed = [k for k,v in checks.items() if not v]
for k,v in checks.items(): print(('PASS' if v else 'FAIL'), k)
if failed:
    raise SystemExit('M9NATIVEHSM1A SAT2STANDARD1A verification failed: ' + ','.join(failed))
print('M9NATIVEHSM1A SAT2STANDARD1A VERIFY PASS')
print('target_input_adapter', 'retained')
print('hsm', 'identity 90x30')
print('firmware_saturation', 'SAT2 M04/M05 Standard sRGB')
print('tone_exposure_demosaic_sharpening', 'unchanged by this patch')
