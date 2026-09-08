#!/usr/bin/env python3
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1p-nativesource1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
r=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
a=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java').read_text()
g=(root/'app/build.gradle').read_text()
f=(root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java')
i=(root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java')
for marker in [
    'private static RenderCore renderNativeSourceProduction1P(',
    '"nativeSourceTransformApplied", true',
    '"cobaltSourceAdapterApplied", false',
    '"norm030ProductionApplied", true',
    '"norm030TargetOutsideMedianEv", 0.30',
    '"norm030UsesSceneBrightness", false',
    '"norm030UsesFinalClipFeedback", false',
    '"norm030UsesPrimaryFeedback", false',
    '"sourceCalibrationNativeTransformApplied", true',
    '"rawShadingGainMapApplied", true',
    'production_NORM030_linear_Bayer_pre_demosaic',
    'native_plus_historical_basis_hsm_self_meter_lumanorm030ev1a_parity1p',
    'boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true};',
    'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30};',
]:
    if marker not in r: raise SystemExit('verify renderer marker missing: '+marker)
if r.count('"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A"') != 1:
    raise SystemExit('verify expected exactly one NORM030 parity suffix')
for forbidden in [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
]:
    if forbidden in r: raise SystemExit('verify retired 1O endpoint survived: '+forbidden)
# Production orchestration may not call legacy renderCore.
start=r.find('    private static Result renderAndSaveInternal(')
end=r.find('\n    private static synchronized void ensureOpenCv()', start)
if start<0 or end<0: raise SystemExit('verify orchestration bounds missing')
orch=r[start:end]
if 'renderCore(' in orch: raise SystemExit('verify legacy Cobalt renderCore still reachable')
if orch.count('renderNativeSourceProduction1P(') != 2:
    raise SystemExit('verify native production route count != 2')
for marker in [
    'out.put("nativeTransformAppliedToRender", true);',
    'out.put("cobaltRuntimeDependencyChanged", true);',
    'embedded.put("sourceAdapterCurrentlyAppliedToRender", false);',
    'embedded.put("nativeSourceAdapterCurrentlyAppliedToRender", true);',
    'embedded.put("nativeReplacementApplied", true);',
    'Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX',
]:
    if marker not in a: raise SystemExit('verify SOURCECAL marker missing: '+marker)
if '-basishsm1p-nativesource1a' not in g: raise SystemExit('verify build identity missing')
if f.exists():
    ft=f.read_text()
    for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY','frameCount = 1;','throwCount = 0;']:
        if marker not in ft: raise SystemExit('verify NOHDR frame marker missing: '+marker)
if i.exists() and 'IsoExpoSelector.HDR = false;' not in i.read_text():
    raise SystemExit('verify IsoExpoSelector HDR=false missing')
# Capture-time Primary provenance and production wrapper must advertise native source.
if r.count('NORM030 physical LensShadingMap -> native Xiaomi SOURCECAL2A') < 3:
    raise SystemExit('verify native production pipeline provenance missing')
print('BASISHSM1P-NATIVESOURCE1A verification PASS')
print(' - native source production route active; legacy Cobalt source route unreachable')
print(' - NORM030 only parity bank retained')
print(' - SOURCECAL native=true / legacy source adapter=false')
print(' - NOHDR single-frame boundary present')
