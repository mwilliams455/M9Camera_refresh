#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
R=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'; C=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'; CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'; B=ROOT/'app/build.gradle'
for p in (R,C,CPP,B):
    if not p.exists(): raise SystemExit('verify missing '+str(p))
r=R.read_text(); c=C.read_text(); cpp=CPP.read_text(); b=B.read_text()
def need(s,t):
    if t not in s: raise SystemExit('verify missing: '+t)
def forbid(s,t):
    if t in s: raise SystemExit('verify forbidden: '+t)
for t in ('_DEMOSAICNEUTRAL_MHCNB_SAT3','_DEMOSAICNEUTRAL_MHCPLAIN_SAT3_GAINLOCK','_DEMOSAICNEUTRAL_EA_SAT3_GAINLOCK','int[] bridgeProbeModes = {50, 55, 54};','boolean[] selfMeterFlags = {true, false, false};','demosaicPlainMhc1A = bridgeProbeMode == 55','demosaicNeutralEa1A = bridgeProbeMode == 54','skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 55','neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats','MHC_PLAIN_SAT3_GAINLOCK','MHC_NEUTRAL_SAT3_CONTROL','DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_plain_sameRAW_gainlocked','DEMOSAICMHCNEUTRAL1A_MalvarHeCutler5x5_RGGB_liveNeutral_balanced_restore','demosaicNeutralIntermediateClipping",false','SOURCECAL2A_owns_color_transform','reachabilityFence(mhcRgbBuffer)'): need(r,t)
for t in ('float neutralR, float neutralG, float neutralB,','boolean neutralAware,'): need(c,t)
for t in ('inline void mhcPixelNeutralRggb(','const uint16_t sm=u16(raw[y*w+x]);','neutralAware?static_cast<double>(neutralR)/static_cast<double>(neutralG):1.0','if(neutralAware) mhcPixelNeutralRggb','else mhcPixelRggb'): need(cpp,t)
for t in ('public static final int JPEG_QUALITY = 95','public static final int SATURATION_BANK = 3','private static final double HSM_H = 0.25','private static final double HSM_S = 0.85','private static final double HSM_V = 1.00'): need(r,t)
need(b,'-demosaicmhc1a-demosaicab1a-demosaicmhcneutral1a')
for t in ('isBlueSky1A(','applyMagentaSkyGuard1A(','SKY_CLASSIFIER_ENABLED = true','neutralBalancedRaw16'): forbid(r+cpp,t)
if r.count('Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);')!=2: raise SystemExit('EA call count')
if r.count('M9NativeColorCore.demosaicMhcRggb(')!=1: raise SystemExit('MHC JNI call count')
print('DEMOSAICMHCNEUTRAL1A verification OK')
print(' - neutral MHC primary, plain MHC + EA same-RAW gainlocked controls')
print(' - no intermediate neutral pre-scale/clipping; sampled CFA sites remain exact')
print(' - downstream M9 stages frozen; no sky/magenta classifier or suppressor')
