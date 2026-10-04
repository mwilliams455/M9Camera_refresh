#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-targetdirect1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit('TARGETDIRECT1A missing renderer')
s = p.read_text()


def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('TARGETDIRECT1A method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('TARGETDIRECT1A opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
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
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('TARGETDIRECT1A unterminated method: ' + signature)

# This patch is intentionally narrow. The assembled baseline already has:
# SOURCECAL2A -> common scene, identity_90x30 HSM, M9 bridge, SAT2 M04/M05,
# curve02, TC20/TONEBOUND050, TTL and TARGETDOMAINTRACE1A.  Mode 4 inserts
# the historical Xiaomi-15U TARGETINPUTADAPTER1A between common scene and the
# M9 bridge; mode 0 is the already-validated direct common-scene path.
ps, pe = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
prod = s[ps:pe]
mode4 = '                4,\n                true,\n                false, false,'
mode0 = '                0,\n                true,\n                false, false,'
if prod.count(mode4) != 1:
    raise SystemExit('TARGETDIRECT1A expected exactly one production mode-4 anchor, found ' + str(prod.count(mode4)))
prod = prod.replace(mode4, mode0, 1)

ret = prod.rfind('        return out;')
if ret < 0:
    raise SystemExit('TARGETDIRECT1A production return anchor missing')
telemetry = '''        // TARGETDIRECT1A: production now consumes the universal common-scene
        // coordinates directly. No historical Xiaomi/Cobalt target-input basis is
        // evaluated or applied. Identity HSM and every downstream M9 stage remain frozen.
        d.put("targetDirect1A", true);
        d.put("targetDirect1ASchema", "m9cam.targetdirect.v1a.common_scene_direct");
        d.put("targetDirect1AProductionBridgeMode", 0);
        d.put("targetDirect1AInputDomain", "common_scene_ProPhoto_D50_direct_to_M9_bridge");
        d.put("targetDirect1AOnlyIntendedPixelChange", "remove_TARGETINPUTADAPTER1A_historical_15U_linear_basis");
        d.put("targetInputAdapter1AApplied", false);
        d.put("targetInputAdapterBasisMaxAbsFromIdentity", 0.0);
        d.put("cobaltRuntimeProductionDependency", false);
        d.put("cobaltRuntimeDependencyRole", "none_production");
        d.put("cobaltHistoricalLinearBasisApplied", false);
        d.put("historicalLinearBasisDiagnosticApplied", false);
        d.put("historicalLinearBasisDerivedFromCobaltSourceProfile", false);
        d.put("mixedCalibrationAssetUsedByProduction", false);
        d.put("mixedCalibrationAssetUsage", "none_production");
        d.put("cobaltHueSatMapApplied", false);
        d.put("historicalBasisHsmTargetBehaviorApplied", false);
        d.put("identityHsmApplied", true);
        d.put("basisHsmHsmTableIdentity", "identity_90x30");
        d.put("architectureRevision", "TARGETDIRECT1A_M9NATIVEHSM1A_SAT2STANDARD1B_TONEBOUND050");
        d.put("fullColorRenderStages", "active physical Camera2 SOURCECAL2A -> common scene -> identity HSM -> M9 bridge -> TC20/TONEBOUND050 -> SAT2 M04/M05 -> curve02 -> BT601 -> TG1");
        d.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene -> identity HSM -> M9 bridge -> TC20/TONEBOUND050 -> SAT2 M04/M05 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
'''
prod = prod[:ret] + telemetry + prod[ret:]
s = s[:ps] + prod + s[pe:]

p.write_text(s)
print('TARGETDIRECT1A applied')
print('production bridge mode: 4 -> 0')
print('pixel change: TARGETINPUTADAPTER1A historical 15U basis removed only')
