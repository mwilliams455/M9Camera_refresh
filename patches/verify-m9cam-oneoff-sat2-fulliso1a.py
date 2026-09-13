#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
T = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
for p in (CPP, R, T):
    if not p.exists(): raise SystemExit('ONEOFF-SAT2 verify missing ' + str(p))
cpp=CPP.read_text(); r=R.read_text(); t=T.read_text()

checks = {
    'fulliso_parent': 'SHARPNESS_STANDARD_FULLISO1A_ID' in cpp,
    'dynamic_fulliso_call': 'm9ClosureSharpStandardFullIso(sharpSourceGreen14, closureSharp14, width, height, sharpIsoSlot)' in cpp,
    'rbanchor': 'const int sg=static_cast<int>(closureSharp14[p]);' in cpp and 'const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;' in cpp,
    'support9': 'if(x>=9 && x<width-9 && y>=9 && y<height-9)' in cpp,
    'sat2_even_exact': '13659, -4457, -1004' in cpp and '-2244, 13469, -3033' in cpp and '-199, -6014, 14398' in cpp,
    'sat2_odd_exact': '14811, -5604, -1004' in cpp and '-2455, 13688, -3033' in cpp and '393, -6588, 14398' in cpp,
    'sat2_default_selector': 'const std::array<int64_t, 9>* qPtr = &(evenBranch ? Q2E : Q2O);' in cpp,
    'sat3_not_default_selector': 'const std::array<int64_t, 9>* qPtr = &(evenBranch ? QE : QO);' not in cpp,
    'sat3_constants_retained': 'constexpr std::array<int64_t, 9> QE' in cpp and 'constexpr std::array<int64_t, 9> QO' in cpp,
    'sat4_retained': 'constexpr std::array<int64_t, 9> Q4E' in cpp and 'constexpr std::array<int64_t, 9> Q4O' in cpp,
    'oneoff_native_identity': 'ONEOFF_SAT2_FULLISO1A_ID' in cpp,
    'renderer_marker': 'SAT2_STANDARD_M04_M05_ONEOFF' in r,
    'normal_default_marker': 'SAT3_M06_M07_on_normal_branches' in r,
    'timing_marker': 'SAT2_STANDARD_M04_M05' in t and 'saturationOneOffProductionEligible' in t,
}
bad=[k for k,v in checks.items() if not v]
if bad:
    raise SystemExit('ONEOFF-SAT2 verify FAIL ' + ','.join(bad))
print('ONEOFF SAT2 FULLISO1A verify PASS')
print(' saturation=exact recovered SAT2 Standard M04/M05')
print(' comparison baseline=normal SAT3 M06/M07')
print(' sharpness=STANDARD_FULLISO1A + RBANCHOR1A unchanged')
print(' disposition=disposable A/B; do not promote as default')
