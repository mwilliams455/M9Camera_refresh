#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists(): raise SystemExit('missing '+str(CPP))
s=CPP.read_text()
checks={
 'identity':'SHARPNESS_SHARPSOURCE1B_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen',
 'green_helper':'inline void m9SharpSourceLeicaGreen14(',
 'source_vector':'std::vector<uint16_t> sharpSourceGreen14;',
 'source_call':'m9SharpSourceLeicaGreen14(raw, width, height, sharpSourceGreen14);',
 'sharp_call':'m9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);',
 'margin':'if(x>=9 && x<width-9 && y>=9 && y<height-9){',
 'delta':'const int delta=static_cast<int>(closureSharp14[p])-static_cast<int>(sharpSourceGreen14[p]);',
 'r_apply':'m9ClosureQ14(base[0]))+delta',
 'g_apply':'m9ClosureQ14(base[1]))+delta',
 'b_apply':'m9ClosureQ14(base[2]))+delta',
 'border_preserve':'dst[0]=base[0]; dst[1]=base[1]; dst[2]=base[2];',
 'mode4':'const int doubledCorr=baseCorr*2;',
 'clamp':'doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr)',
}
for k,v in checks.items():
    n=s.count(v)
    if n != 1:
        raise SystemExit(f'SHARPSOURCE1B verify FAIL {k}: count={n}')
# The rejected CLOSURETEST1B full-resolution fixed-difference closure must no longer
# be the active second-pass arithmetic after SHARPSOURCE patching.
for bad in ('const int dr=m9ClosureQ14(base[0])-g14;',
            'const int db=m9ClosureQ14(base[2])-g14;',
            'dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));'):
    if bad in s:
        raise SystemExit('SHARPSOURCE1B verify FAIL rejected closure still active: '+bad)
print('SHARPSOURCE1B verify PASS')
print(' menu=Standard slot=0 internalMode=4 scale=2x')
print(' nNoise=2 supportMargin=9')
print(' sharpSource=LeicaGreenInterpolationWithCo interior 14-bit')
print(' rgbFoundation=MHCNeutralFrozen')
print(' correctionPolicy=delta(sharp(leicaGreen14)-leicaGreen14) applied equally to frozen MHC RGB')
print(' borderPolicy=outside 9px preserve frozen MHC exactly')
