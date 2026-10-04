#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
C = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
B = ROOT / 'app/build.gradle'
for p in (R, C, CPP, B):
    if not p.exists():
        raise SystemExit('FROZEN1A verify missing ' + str(p))
r, c, cpp, b = R.read_text(), C.read_text(), CPP.read_text(), B.read_text()

def one(text, token, name):
    n = text.count(token)
    if n != 1:
        raise SystemExit(f'FROZEN1A verify {name} count={n}')

one(r, 'private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = false;', 'bank disabled')
one(r, 'if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED) {', 'bank gate')
one(r, '"MHC_NEUTRAL_SAT3_PRODUCTION"', 'production variant telemetry')
one(r, '"production_frozen_liveNeutral_balanced_MHC"', 'frozen control telemetry')
one(r, '"DEMOSAICMHCNEUTRAL1A_FROZEN1A"', 'foundation telemetry')
if r.count('DEMOSAICMHCNEUTRAL1A live-neutral balanced 5x5 MHC -> native Xiaomi SOURCECAL2A') != 3:
    raise SystemExit('FROZEN1A verify primary pipeline order count=' + str(r.count('DEMOSAICMHCNEUTRAL1A live-neutral balanced 5x5 MHC -> native Xiaomi SOURCECAL2A')))

# Keep rollback controls compiled but dormant.
one(r, 'final boolean demosaicNeutralEa1A = bridgeProbeMode == 54;', 'EA control')
one(r, 'final boolean demosaicPlainMhc1A = bridgeProbeMode == 55;', 'plain MHC control')
one(r, 'int[] bridgeProbeModes = {50, 55, 54};', 'diagnostic modes retained')

# Primary non-control path must still invoke neutral-aware MHC.
one(r, 'neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats', 'neutral MHC JNI call')
one(c, 'boolean neutralAware,', 'JNI Java neutral-aware signature')
one(cpp, 'inline void mhcPixelNeutralRggb(', 'native neutral MHC kernel definition')

# Frozen downstream anchors.
one(cpp, '16754, -7632, -922', 'SAT3 M06 anchor')
one(cpp, '18160, -9034, -922', 'SAT3 M07 anchor')
if '-demosaicmhcneutral1a-frozen1a' not in b:
    raise SystemExit('FROZEN1A verify version suffix missing')

print('DEMOSAICMHCNEUTRAL1A-FROZEN1A verify OK: one production JPEG path, neutral MHC frozen, controls dormant, downstream anchors retained')
