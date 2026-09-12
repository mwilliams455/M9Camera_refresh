#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
R=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
C=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
CPP=ROOT/'app/src/main/cpp/m9color_jni.cpp'
T=ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
for p in (R,C,CPP,T):
    if not p.exists(): raise SystemExit('FULLISO1A missing '+str(p))
def rep(s,a,b,n):
    c=s.count(a)
    if c!=1: raise SystemExit(f'FULLISO1A {n} anchor count={c}')
    return s.replace(a,b,1)
r=R.read_text(); c=C.read_text(); cpp=CPP.read_text(); t=T.read_text()

# Carry the capture's physical ISO into the active native production renderer without
# widening every diagnostic helper signature. Primary rendering is already single-worker;
# same-RAW diagnostic calls on that worker deliberately inherit the same capture ISO.
iso_anchor='int iso = isoObj == null ? -1 : isoObj;'
if r.count(iso_anchor)!=1: raise SystemExit('FULLISO1A capture ISO anchor count='+str(r.count(iso_anchor)))
r=r.replace(iso_anchor,iso_anchor+'\n            if (iso > 0) M9_SHARP_NORMALIZED_ISO_TL.set(Math.max(1, iso * 2));',1)

class_anchor='''    private static final class RenderCore {\n        final Bitmap bitmap;'''
helper='''    private static final ThreadLocal<Integer> M9_SHARP_NORMALIZED_ISO_TL = ThreadLocal.withInitial(() -> 160);\n    private static final int[] M9_SHARP_ISOS = {160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500};\n    private static int m9SharpIsoSlot(int normalizedIso) {\n        int clamped=Math.max(160,Math.min(2500,normalizedIso));\n        int best=0; double bestD=Double.POSITIVE_INFINITY;\n        for(int i=0;i<M9_SHARP_ISOS.length;i++){\n            double d=Math.abs(Math.log(clamped/(double)M9_SHARP_ISOS[i])/Math.log(2.0));\n            if(d<bestD){bestD=d;best=i;}\n        }\n        return best;\n    }\n\n'''+class_anchor
r=rep(r,class_anchor,helper,'slot helper')

# Inject the per-frame selector directly into the active production function body.
fn='private static RenderCore renderNativeProspectiveCore('
if r.count(fn)!=1: raise SystemExit('FULLISO1A active function count='+str(r.count(fn)))
fs=r.index(fn); brace=r.index('{',fs)
selector='''\n        // STANDARD_FULLISO1A Xiaomi-main bridge: established system-ISO x2 normalization\n        // then nearest Leica physical ISO in log2(EV). Pull 80 is reserved for explicit UI.\n        final int sharpNormalizedCaptureIso = M9_SHARP_NORMALIZED_ISO_TL.get();\n        final int sharpIsoSlot = m9SharpIsoSlot(sharpNormalizedCaptureIso);\n        final int sharpLeicaIso = M9_SHARP_ISOS[sharpIsoSlot];\n'''
r=r[:brace+1]+selector+r[brace+1:]

# Native declaration and active MHC call gain one integer slot argument only.
c=rep(c,
'''                                       float neutralR, float neutralG, float neutralB,\n                                       boolean neutralAware,\n                                       long[] stats);''',
'''                                       float neutralR, float neutralG, float neutralB,\n                                       boolean neutralAware,\n                                       int sharpIsoSlot,\n                                       long[] stats);''','java native signature')
r=rep(r,
'''                        neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats);''',
'''                        neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,sharpIsoSlot,mhcStats);''','native call')

# Renderer telemetry carries the actual selected Leica ISO/slot/mode for field proof.
r=rep(r,'            d.put("demosaicElapsedMs", demosaicElapsedMs);',
'''            d.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");\n            d.put("sharpnessNormalizedCaptureIso", sharpNormalizedCaptureIso);\n            d.put("sharpnessLeicaIso", sharpLeicaIso);\n            d.put("sharpnessIsoSlot", sharpIsoSlot);\n            d.put("sharpnessInternalMode", sharpIsoSlot <= 5 ? 4 : (sharpIsoSlot <= 10 ? 3 : 2));\n            d.put("sharpnessMenu", "Standard");\n            d.put("sharpnessIsoBridge", "xiaomi_main_systemIso_x2_then_nearest_log2_Leica160_2500");\n            d.put("demosaicElapsedMs", demosaicElapsedMs);''','renderer telemetry')

cpp=rep(cpp,'#include <jni.h>','#include <jni.h>\n#include "m9_sharp_fulliso_bank.h"','header include')
cpp=rep(cpp,
'''        jfloat neutralR, jfloat neutralG, jfloat neutralB,\n        jboolean neutralAware,\n        jlongArray statsArray) {''',
'''        jfloat neutralR, jfloat neutralG, jfloat neutralB,\n        jboolean neutralAware,\n        jint sharpIsoSlot,\n        jlongArray statsArray) {''','jni signature')
cpp=rep(cpp,'    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;',
'''    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;\n    if (sharpIsoSlot < 0 || sharpIsoSlot >= M9_SHARP_ISO_ROWS) return -8;''','slot validation')

marker='inline uint16_t m9ClosureClamp14(int v){'
helper_cpp=r'''inline int m9SharpArShift1(int v){
    return v>=0 ? (v>>1) : -(((-v)+1)>>1);
}
inline int m9SharpStandardCoeff(int slot,int idx){
    int v=static_cast<int>(M9_SHARP_BASE[slot][idx]);
    const int mode=M9_SHARP_STANDARD_MODE[slot];
    if(mode==4) v*=2;
    else if(mode==3) {}
    else if(mode==2) v=m9SharpArShift1(v);
    else return 0;
    if(v < -2048) v=-2048; else if(v > 2048) v=2048;
    return v;
}
'''+marker
cpp=rep(cpp,marker,helper_cpp,'working coeff helper')
cpp=rep(cpp,
'''inline void m9ClosureSharpIso160Standard(const std::vector<uint16_t>& src,\n                                         std::vector<uint16_t>& dst,int w,int h){''',
'''inline void m9ClosureSharpStandardFullIso(const std::vector<uint16_t>& src,\n                                         std::vector<uint16_t>& dst,int w,int h,int isoSlot){''','sharp function signature')
cpp=rep(cpp,
'''            // SHARPNESS_CLOSURETEST1B: Leica Standard slot0 selects internal mode 4.\n            // Firmware mode4 is signed coefficient x2 followed by [-2048,+2048] clamp.\n            // Use multiplication rather than left-shifting a negative signed value in C++.\n            const int baseCorr=m9ClosureSlot0Coeff(1024+r);\n            const int doubledCorr=baseCorr*2;\n            const int corr=doubledCorr < -2048 ? -2048 : (doubledCorr > 2048 ? 2048 : doubledCorr);''',
'''            // STANDARD_FULLISO1A: canonical ISO-specific base row plus proven Standard mode.\n            const int corr=m9SharpStandardCoeff(isoSlot,1024+r);''','coeff use')
cpp=rep(cpp,'m9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);','m9ClosureSharpStandardFullIso(sharpSourceGreen14, closureSharp14, width, height, sharpIsoSlot);','sharp call')
cpp=cpp.replace('SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=sharpLeicaGreen_plus_frozenMhcRgBg_differences','SHARPNESS_STANDARD_FULLISO1A_ID: menu=Standard slot=dynamic modes=4/3/2 nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=RBANCHOR1A',1)

t=t.replace('root.put("sharpnessResearch", "SHARPSOURCE1C_RBANCHOR1A");','root.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");',1)
t=t.replace('root.put("sharpnessSlot", 0);','root.put("sharpnessSlot", -1); // dynamic; actual slot in nested renderer diagnostics',1)
t=t.replace('root.put("sharpnessInternalMode", 4);','root.put("sharpnessInternalMode", -1); // dynamic Standard 4/3/2 by slot',1)
t=t.replace('root.put("sharpnessScale", "2x");','root.put("sharpnessScale", "slot-dependent Standard mode4/mode3/mode2");',1)

R.write_text(r); C.write_text(c); CPP.write_text(cpp); T.write_text(t)
print('STANDARD_FULLISO1A applied: active native renderer uses dynamic Leica ISO slot; canonical bank + Standard 4/3/2; RBANCHOR1A unchanged')
