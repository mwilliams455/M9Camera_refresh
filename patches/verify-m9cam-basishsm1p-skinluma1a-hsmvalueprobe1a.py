#!/usr/bin/env python3
from pathlib import Path
import re, sys
if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-basishsm1p-skinluma1a-hsmvalueprobe1a.py <PhotonCamera-root>')
root=Path(sys.argv[1]).resolve()
rp=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gp=root/'app/build.gradle'
fp=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
ip=root/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
for p in (rp,gp):
    if not p.exists(): raise SystemExit('SKINLUMA verify missing '+str(p))
r=rp.read_text(); g=gp.read_text()

def need(s, marker, label):
    if marker not in s: raise SystemExit('SKINLUMA verify missing '+label+': '+marker)

def count(s, marker, n, label):
    c=s.count(marker)
    if c!=n: raise SystemExit(f'SKINLUMA verify {label} count={c} expected={n}')

need(g,'-basishsm1p-skinluma1a-hsmvalueprobe1a','build provenance')
for marker in [
 'm9cam.renderer.basishsm.v1p.nativesource1a.production',
 'SOURCECAL2A_CMFIX_DNG_dual_illuminant_math_CM_unchanged_FM_D50_normalized_live_neutral',
 'NORM030 physical LensShadingMap -> native Xiaomi SOURCECAL2A -> BASISHSM1A historical working-basis/H25 target role -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1',
 'JPEG_QUALITY = 95', 'SATURATION_BANK = 3', 'HSM_H = 0.25', 'HSM_S = 0.85', 'HSM_V = 1.00',
 '"shadingLumaNorm1AUsesSceneBrightness", false',
 '"shadingLumaNorm1AUsesFinalClipFeedback", false',
 '"shadingLumaNorm1AUsesPrimaryFeedback", false',
 'true, 0.30,\n                1.0, false);',
]: need(r,marker,'frozen production boundary')

for marker in [
 '"_SKINLUMA_CONTROL_1P"', '"_SKINLUMA_HSM_VALUE_OFF"',
 '"_SKINLUMA_HSM_VALUE_050"', '"_SKINLUMA_TC20_GAINLOCK"',
 'boolean[] selfMeterFlags = {true, false, false, false};',
 'double[] hsmValueStrengthFlags = {1.0, 0.0, 0.50, 1.0};',
 'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30};',
 'skinLumaControlEffectiveRenderGain',
 'variantFixedGain = skinLumaControlEffectiveRenderGain;',
 'd2\' = 1 + authority * (d2 - 1)',
 'ctx.hsm[i] = 1.0 + hsmValueStrengthProbe1A * (ctx.hsm[i] - 1.0);',
 'SKINLUMA_AUDIT_LONG_SIDE = 256',
 '"native_SOURCECAL2A_output"', '"after_historical_BASIS"', '"after_HSM"',
 '"after_M9_bridge"', '"after_TC20_gain"', '"after_SAT3_M06_M07"',
 '"after_curve02_pre_BT601"', '"final_BT601_TG1_finished_bitmap"',
 '"grid3x3"', '"q90Y"', '"q95Y"', '"q99Y"',
 '"skinChromaProxyApplied", false',
 '"skinLumaExactBitmapParityWithControl"',
 '"inputDngPath", dngPath.toString()',
 '"productionBehaviorChanged", false',
]: need(r,marker,'SKINLUMA diagnostic')

count(r,'"_SKINLUMA_CONTROL_1P"',1,'control suffix')
count(r,'"_SKINLUMA_TC20_GAINLOCK"',1,'gainlock suffix')
if '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A"' in r:
    raise SystemExit('SKINLUMA verify retired 1P parity JPEG still present')
if r.count('renderNativeProspectiveCore(') != 3:
    raise SystemExit('SKINLUMA verify unexpected prospective declaration/call count')

# Native source must remain the production adapter; no Cobalt source dependency may be reactivated.
for bad in [
 'cobaltSourceAdapterApplied", true',
 'cobaltSourceColorMatrixApplied", true',
 'cobaltSourceForwardMatrixApplied", true',
]:
    if bad in r: raise SystemExit('SKINLUMA verify forbidden legacy source reactivation: '+bad)

# This experiment is read-only JPEG-side diagnostics. Re-check hard single-frame/no-HDR boundary.
if fp.exists():
    f=fp.read_text()
    for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY','frameCount = 1;','throwCount = 0;']:
        need(f,marker,'NOHDR single-frame boundary')
if ip.exists():
    iso=ip.read_text()
    if not re.search(r'\bHDR\s*=\s*false\s*;', iso):
        raise SystemExit('SKINLUMA verify HDR=false boundary missing')

# No photographic constant is parameterized by the stage audit. Audit calls are gated and production passes false.
need(r,'final JSONObject skinLumaStageAudit1AJson = skinLumaStageAuditEnabled1A','audit gate')
need(r,'out.put("pixelMutation", false);','read-only audit')
need(r,'out.put("gainMutation", false);','read-only audit')

print('SKINLUMA1A verify OK')
print(' - production wrapper retains 1P V=1 / audit=false and NORM030 0.30')
print(' - A=self-meter control; B/C/D exact effective-gain locked to A')
print(' - HSM value only: V 1.0 / 0.0 / 0.50 / 1.0; H=.25 and S=.85 frozen')
print(' - stage 1-7 aggregate sampler + finished bitmap stage 8/hash present')
print(' - no skin classifier, Cobalt source reactivation, HDR, or multi-frame change')
