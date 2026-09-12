#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists():
    raise SystemExit('CLOSURETEST1B missing ' + str(CPP))
s = CPP.read_text()

# 1B is deliberately a one-variable delta over the already verified 1A source.
# Keep 1A intact as the 1x diagnostic, but correct Leica Standard at manual
# ISO160 / slot0 to its proven internal mode 4: signed LUT coefficient x2,
# clamped to [-2048,+2048].
if 'SHARPNESS_CLOSURETEST1A' not in s or 'm9ClosureSlot0Coeff' not in s:
    raise SystemExit('CLOSURETEST1B requires assembled CLOSURETEST1A parent')
if 'SHARPNESS_CLOSURETEST1B' in s:
    raise SystemExit('CLOSURETEST1B already applied')

old_header = '// SHARPNESS_CLOSURETEST1A -- RESEARCH ONLY, fixed ISO160 slot0 / Standard 1x.'
new_header = ('// SHARPNESS_CLOSURETEST1A base + SHARPNESS_CLOSURETEST1B mode4 override -- '
              'RESEARCH ONLY, fixed ISO160 slot0 / Standard mode4 x2.')
if s.count(old_header) != 1:
    raise SystemExit('CLOSURETEST1B 1A header anchor count=' + str(s.count(old_header)))
s = s.replace(old_header, new_header, 1)

old = '''            const int corr=m9ClosureSlot0Coeff(1024+r); // Standard == 1x base LUT.
            dst[p]=m9ClosureClamp14(a11+corr);'''
new = '''            // SHARPNESS_CLOSURETEST1B: Leica Standard slot0 selects internal mode 4.
            // Firmware mode4 is signed coefficient x2 followed by [-2048,+2048] clamp.
            // Use multiplication rather than left-shifting a negative signed value in C++.
            const int baseCorr=m9ClosureSlot0Coeff(1024+r);
            const int doubledCorr=baseCorr*2;
            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);
            dst[p]=m9ClosureClamp14(a11+corr);'''
if s.count(old) != 1:
    raise SystemExit('CLOSURETEST1B 1x correction anchor count=' + str(s.count(old)))
s = s.replace(old, new, 1)

old_stage = '// SHARPNESS_CLOSURETEST1A: fixed manual ISO160 / Standard probe.'
new_stage = '// SHARPNESS_CLOSURETEST1A/CLOSURETEST1B: fixed manual ISO160 / Standard mode4 probe.'
if s.count(old_stage) != 1:
    raise SystemExit('CLOSURETEST1B stage-comment anchor count=' + str(s.count(old_stage)))
s = s.replace(old_stage, new_stage, 1)

CPP.write_text(s)
print('SHARPNESS_CLOSURETEST1B applied: ISO160 slot0 Standard mode4 x2 signed LUT transform with [-2048,+2048] clamp')
