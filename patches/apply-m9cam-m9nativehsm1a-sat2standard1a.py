#!/usr/bin/env python3
from pathlib import Path
import re, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9nativehsm1a-sat2standard1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit(f'M9NATIVEHSM1A SAT2STANDARD1A missing renderer: {p}')
s = p.read_text()

def method_span(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
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
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('unterminated method: ' + signature)

# 1) Firmware Standard sRGB state: nSaturation=2 -> signed matrix pair M04/M05.
pat = re.compile(r'(\bSATURATION_BANK\s*=\s*)3(\s*;)')
s, n = pat.subn(r'\g<1>2\g<2>', s, count=1)
if n != 1:
    raise SystemExit(f'M9NATIVEHSM1A SAT2STANDARD1A saturation-bank anchor count={n}')

# 2) Preserve TARGETINPUTADAPTER1A scene-domain basis, but replace only the
# historical Cobalt HueSatMap in production mode 4 with a topology-compatible
# 90x30 identity table.  The target-input algebra itself remains untouched.
start_token = '            } else if (bridgeProbeMode == 4) {'
end_token = '            } else if (bridgeProbeMode != 0) {'
a = s.find(start_token)
if a < 0:
    raise SystemExit('M9NATIVEHSM1A SAT2STANDARD1A mode4 start missing')
b = s.find(end_token, a)
if b < 0:
    raise SystemExit('M9NATIVEHSM1A SAT2STANDARD1A mode4 end missing')
seg = s[a:b]
old = '''                ctx.hsm = new double[cal.hsmA.length];
                for (int i = 0; i < ctx.hsm.length; i++) {
                    ctx.hsm[i] = targetInput.historical15.wA * cal.hsmA[i]
                            + (1.0 - targetInput.historical15.wA) * cal.hsmD65[i];
                }
                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
'''
new = '''                // M9NATIVEHSM1A: recovered firmware evidence does not establish an
                // Adobe ProfileHueSatMap-equivalent target stage.  Preserve the frozen
                // 90x30 evaluator geometry but make the operation an exact no-op.
                int identityHsmCells = Math.multiplyExact(cal.hueDivisions, cal.satDivisions);
                int identityHsmLength = Math.multiplyExact(identityHsmCells, 3);
                if (cal.hueDivisions != 90 || cal.satDivisions != 30
                        || cal.hsmA.length != identityHsmLength
                        || cal.hsmD65.length != identityHsmLength) {
                    throw new IllegalStateException(
                            "M9NATIVEHSM1A unexpected historical HSM geometry");
                }
                ctx.hsm = new double[identityHsmLength];
                for (int i = 0; i < ctx.hsm.length; i += 3) {
                    ctx.hsm[i] = 0.0;
                    ctx.hsm[i + 1] = 1.0;
                    ctx.hsm[i + 2] = 1.0;
                }
                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
'''
if seg.count(old) != 1:
    raise SystemExit(f'M9NATIVEHSM1A SAT2STANDARD1A historical HSM anchor count={seg.count(old)}')
seg = seg.replace(old, new, 1)
s = s[:a] + seg + s[b:]

# 3) Override production telemetry after the core returns so sidecars describe
# the actual candidate rather than the older TARGETHSM control state.
ps, pe = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
prod = s[ps:pe]
ret = prod.rfind('        return out;')
if ret < 0:
    raise SystemExit('M9NATIVEHSM1A SAT2STANDARD1A production return anchor missing')
telemetry = '''        d.put("architectureRevision", "TARGETINPUTADAPTER1A_M9NATIVEHSM1A_SAT2STANDARD1A");
        d.put("m9NativeHsm1A", true);
        d.put("m9NativeHsmOperation", "identity_90x30_no_Adobe_HueSatMap_target_stage");
        d.put("cobaltHueSatMapApplied", false);
        d.put("historicalBasisHsmTargetBehaviorApplied", false);
        d.put("identityHsmApplied", true);
        d.put("basisHsmHsmTableIdentity", "identity_90x30");
        d.put("m9SaturationBank", 2);
        d.put("m9SaturationState", "firmware_Standard_sRGB_nSaturation_2");
        d.put("m9SaturationMatrixPair", "M04_M05");
        d.put("cobaltRuntimeDependencyRole", "historical_target_input_coordinate_reference_only_no_HueSatMap");
        d.put("fullColorRenderStages", "active physical Camera2 SOURCECAL2A -> common scene -> TARGETINPUTADAPTER1A -> identity HSM -> M9 bridge -> TC20 -> SAT2 M04/M05 -> curve02 -> BT601 -> TG1");
        d.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene -> TARGETINPUTADAPTER1A -> identity HSM -> M9 bridge -> TC20 -> SAT2 M04/M05 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
'''
prod = prod[:ret] + telemetry + prod[ret:]
s = s[:ps] + prod + s[pe:]

p.write_text(s)
print('M9NATIVEHSM1A SAT2STANDARD1A applied')
print('production target input: retained')
print('production HSM: identity 90x30')
print('firmware saturation bank: 2 (M04/M05 Standard sRGB)')
