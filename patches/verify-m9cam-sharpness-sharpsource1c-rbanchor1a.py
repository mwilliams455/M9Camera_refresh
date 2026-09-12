#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
s = CPP.read_text(); j = JAVA.read_text()
required_cpp = [
    'SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID',
    'm9SharpSourceLeicaGreen14(raw, width, height, sharpSourceGreen14);',
    'm9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);',
    'if(x>=9 && x<width-9 && y>=9 && y<height-9)',
    'const int sg=static_cast<int>(closureSharp14[p]);',
    'const int mg=static_cast<int>(m9ClosureQ14(base[1]));',
    'const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;',
    'const int db=static_cast<int>(m9ClosureQ14(base[2]))-mg;',
    'dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));',
    'dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));',
    'dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));',
]
for needle in required_cpp:
    if needle not in s:
        raise SystemExit('missing C++ anchor: ' + needle)
for rejected in [
    'const int delta=static_cast<int>(closureSharp14[p])-static_cast<int>(sharpSourceGreen14[p]);',
    'm9ClosureQ14(base[0]))+delta',
    'm9ClosureQ14(base[1]))+delta',
    'm9ClosureQ14(base[2]))+delta',
]:
    if rejected in s:
        raise SystemExit('rejected SHARPSOURCE1B delta graft still present: ' + rejected)
required_java = [
    'root.put("sharpnessResearch", "SHARPSOURCE1C_RBANCHOR1A");',
    'root.put("sharpnessMenu", "Standard");',
    'root.put("sharpnessSlot", 0);',
    'root.put("sharpnessInternalMode", 4);',
    'root.put("sharpnessScale", "2x");',
    'root.put("sharpnessNoiseMode", 2);',
    'root.put("sharpnessSupportMargin", 9);',
    'root.put("sharpnessSource", "LeicaGreenInterpolationWithCo-interior14bit");',
    'root.put("sharpnessRgbFoundation", "MHCNeutralFrozen_color_difference_proxy");',
    'root.put("sharpnessCorrectionPolicy", "anchor_to_sharpLeicaGreen14_then_restore_frozenMHC_RminusG_BminusG_proxy");',
    'root.put("sharpnessRbPolicy", "RBANCHOR1A_sharpLeicaGreen_plus_frozenMHC_color_differences_proxy");',
]
for needle in required_java:
    if needle not in j:
        raise SystemExit('missing timing anchor: ' + needle)
print('SHARPSOURCE1C-RBANCHOR1A verify PASS')
print(' sharp_source=LeicaGreenInterpolationWithCo interior q14')
print(' menu=Standard slot=0 internal_mode=4 scale=2x noise_mode=2 support_margin=9')
print(' rb_policy=sharpLeicaGreen14 + frozenMHC(R-G,B-G) proxy differences')
print(' rejected_policy=LeicaSharpDelta grafted onto independent MHC green baseline')
