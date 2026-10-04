#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
r=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
c=(root/'app/src/main/cpp/m9color_jni.cpp').read_text()
b=(root/'app/build.gradle').read_text()

def need(text, token, label):
    if token not in text: raise SystemExit('SKYDOWN1A verify failed: '+label)

def forbid(text, token, label):
    if token in text: raise SystemExit('SKYDOWN1A verify failed: '+label)

for s in ['_SKYDOWN_CONTROL_1P','_SKYDOWN_POSTGAIN_VECGAMUT','_SKYDOWN_SAT3_VECGAMUT','_SKYDOWN_SAT3_BYPASS','_SKYDOWN_BT601_BYPASS']:
    need(r,s,'missing bank '+s)
need(r,'int[] bridgeProbeModes = {40, 41, 42, 43, 44};','mode bank')
need(r,'boolean[] selfMeterFlags = {true, false, false, false, false};','only control self-meters')
need(r,'double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0, 1.0};','HSM V frozen')
need(r,'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30, 0.30};','NORM030 frozen')
need(r,'skyDownDiagnosticEncoded1A = bridgeProbeMode >= 40 && bridgeProbeMode <= 44','encoded isolation')
need(r,'bridgeProbeMode == 40 ? 0 : bridgeProbeMode - 36','downstream mode decode')
for t in ['case 5: return "POSTGAIN_VECGAMUT";','case 6: return "SAT3_VECGAMUT";','case 7: return "SAT3_BYPASS";','case 8: return "BT601_BYPASS";']:
    need(r,t,'mode name '+t)
need(r,'PP_TO_XYZ, XYZ2SRGB, cal.curve02, ctx.hueDivisions, ctx.satDivisions,\n                    0);','normal primary native context remains explicit mode 0')
need(r,'sameRawAsPrimary", true','same RAW diagnostic')
need(r,'skyDownControlEffectiveRenderGain','locked control gain metadata')
need(r,'skinLumaFinishedOutputAudit1A','finished bitmap audit retained')
need(r,'skyChromaFinishedAudit1A','pink proxy retained')

for t in ['ctx.skyChromaMode1A == 5','ctx.skyChromaMode1A == 6','ctx.skyChromaMode1A == 7','ctx.skyChromaMode1A == 8']:
    need(c,t,'native mode '+t)
need(c,'r = clipl(static_cast<int64_t>(std::rint(ur)), 0, RAW_MAX);','production 14-bit R clamp preserved')
need(c,'g = clipl(static_cast<int64_t>(std::rint(ug)), 0, RAW_MAX);','production 14-bit G clamp preserved')
need(c,'b = clipl(static_cast<int64_t>(std::rint(ub)), 0, RAW_MAX);','production 14-bit B clamp preserved')
need(c,'i0 = static_cast<int>(clipl(a0 >> 16, 0, LUT_MAX));','production SAT3 i0 clip preserved')
need(c,'i1 = static_cast<int>(clipl(a1 >> 16, 0, LUT_MAX));','production SAT3 i1 clip preserved')
need(c,'i2 = static_cast<int>(clipl(a2 >> 16, 0, LUT_MAX));','production SAT3 i2 clip preserved')
need(c,'const int cb = static_cast<int>((cbS + 128) & 0xff) - 128;','production BT601 signed byte path preserved')
need(c,'argb[p0] = packArgb(static_cast<int>(r0), static_cast<int>(g0), static_cast<int>(b0));','BT601 bypass only in mode 8')

need(b,'-basishsm1p-skydown1a-nativewpclip1a','version marker')
need(r,'public static final int JPEG_QUALITY = 95','JPEG Q95 frozen')
need(r,'public static final int SATURATION_BANK = 3','SAT3 bank frozen')
need(r,'private static final double HSM_H = 0.25','HSM H frozen')
need(r,'private static final double HSM_S = 0.85','HSM S frozen')
need(r,'private static final double HSM_V = 1.00','HSM V frozen')
forbid(r,'Ultra HDR','no Ultra HDR code')

print('SKYDOWN1A verification OK')
print(' - production primary context explicit mode 0')
print(' - same RAW / exact control-gain bank')
print(' - post-TC20, SAT3 vector, SAT3 bypass, BT601 bypass probes isolated')
print(' - Q95 / SAT3 / HSM / NORM030 frozen')
