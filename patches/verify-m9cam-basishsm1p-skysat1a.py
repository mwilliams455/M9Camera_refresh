#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('.')
r=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java').read_text()
c=(root/'app/src/main/cpp/m9color_jni.cpp').read_text()
b=(root/'app/build.gradle').read_text()
def need(s,t,label):
    if t not in s: raise SystemExit('SKYSAT1A verify missing '+label+': '+t)
def forbid(s,t,label):
    if t in s: raise SystemExit('SKYSAT1A verify forbidden '+label+': '+t)
for t in ['_SKYSAT_CONTROL_SAT3','_SKYSAT_SAT2_STANDARD','_SKYSAT_SAT4_HIGH','_SKYSAT_SAT3_BYPASS']:
    need(r,t,'bank suffix')
need(r,'int[] bridgeProbeModes = {50, 51, 52, 53};','mode bank')
need(r,'boolean[] selfMeterFlags = {true, false, false, false};','gain lock')
need(r,'double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0};','HSM V frozen')
need(r,'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30};','NORM030 frozen')
need(r,'skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 53','SKYSAT encoding')
need(r,'bridgeProbeMode == 51 ? 9','SAT2 decode')
need(r,'bridgeProbeMode == 52 ? 10 : 7','SAT4/bypass decode')
need(r,'case 9: return "SAT2_STANDARD_M04_M05";','SAT2 mode name')
need(r,'case 10: return "SAT4_HIGH_M08_M09";','SAT4 mode name')
need(r,'d.put("skySat1A", skySatDiagnosticEncoded1A);','diag flag')
for t in ['13659, -4457, -1004','14811, -5604, -1004','19850, -10808, -840','21509, -12464, -840']:
    need(c,t,'exact recovered saturation matrix')
need(c,'if (ctx.skyChromaMode1A == 9) qPtr = &(evenBranch ? Q2E : Q2O);','SAT2 selector')
need(c,'else if (ctx.skyChromaMode1A == 10) qPtr = &(evenBranch ? Q4E : Q4O);','SAT4 selector')
need(c,'skyChromaMode1A > 10','native mode contract')
for t in ['16754, -7632, -922','18160, -9034, -922']:
    need(c,t,'production SAT3 matrix')
need(c,'const std::array<int64_t, 9>* qPtr = &(evenBranch ? QE : QO);','production SAT3 default selector')
need(b,'-basishsm1p-skysat1a-nativewpclip1a','version provenance')
for t in ['public static final int JPEG_QUALITY = 95','public static final int SATURATION_BANK = 3','private static final double HSM_H = 0.25','private static final double HSM_S = 0.85','private static final double HSM_V = 1.00']:
    need(r,t,'frozen production boundary')
forbid(r,'Ultra HDR','HDR')
for bad in ['isBlueSky1A(', 'applyMagentaSkyGuard1A(', 'SKY_CLASSIFIER_ENABLED = true']:
    forbid(r,bad,'scene-specific correction')
print('SKYSAT1A verification OK')
print(' - exact current SAT3 remains default/native mode 0')
print(' - exact SAT2 M04/M05 and SAT4 M08/M09 added as same-RAW gain-locked diagnostics')
print(' - existing SAT3 bypass retained as identity anchor')
print(' - Q95 / HSM / NORM030 / no-HDR frozen')
