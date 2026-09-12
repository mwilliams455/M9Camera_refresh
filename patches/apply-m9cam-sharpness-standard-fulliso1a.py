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

# Java: carry actual capture ISO into renderCore, then select nearest discrete Leica
# ISO in log-EV space after the established main-module x2 normalization.
r=rep(r,
'''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation);''',
'''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, iso, cameraRotation);''','render call')
r=rep(r,
'''                                         int whiteLevel,\n                                         float[] neutralF,\n                                         int cameraRotation) throws Exception {\n        final int pixels = Math.multiplyExact(width, height);''',
'''                                         int whiteLevel,\n                                         float[] neutralF,\n                                         int sensorIso,\n                                         int cameraRotation) throws Exception {\n        final int pixels = Math.multiplyExact(width, height);\n        // STANDARD_FULLISO1A Xiaomi-main bridge: Photon/Xiaomi system ISO is normalized\n        // by the already-established x2 main-module factor, then quantized to the nearest\n        // physical Leica M9 ISO enum in log2(EV) space. Pull 80 is intentionally excluded.\n        final int sharpNormalizedCaptureIso = Math.max(1, sensorIso * 2);\n        final int sharpIsoSlot = m9SharpIsoSlot(sharpNormalizedCaptureIso);\n        final int sharpLeicaIso = M9_SHARP_ISOS[sharpIsoSlot];''','render signature')
anchor='''    private static final class RenderCore {\n        final Bitmap bitmap;'''
helper='''    private static final int[] M9_SHARP_ISOS = {160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500};\n    private static int m9SharpIsoSlot(int normalizedIso) {\n        int clamped=Math.max(160,Math.min(2500,normalizedIso));\n        int best=0; double bestD=Double.POSITIVE_INFINITY;\n        for(int i=0;i<M9_SHARP_ISOS.length;i++){\n            double d=Math.abs(Math.log(clamped/(double)M9_SHARP_ISOS[i])/Math.log(2.0));\n            if(d<bestD){bestD=d;best=i;}\n        }\n        return best;\n    }\n\n'''+anchor
r=rep(r,anchor,helper,'slot helper')

# Native declaration and call gain one integer slot argument only.
c=rep(c,
'''                                       float neutralR, float neutralG, float neutralB,\n                                       boolean neutralAware,\n                                       long[] stats);''',
'''                                       float neutralR, float neutralG, float neutralB,\n                                       boolean neutralAware,\n                                       int sharpIsoSlot,\n                                       long[] stats);''','java native signature')
r=rep(r,
'''                        neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,mhcStats);''',
'''                        neutralF[0],neutralF[1],neutralF[2],!demosaicPlainMhc1A,sharpIsoSlot,mhcStats);''','native call')

# Renderer telemetry carries the actual per-frame selection.
r=rep(r,'            d.put("demosaicElapsedMs", demosaicElapsedMs);',
'''            d.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");\n            d.put("sharpnessNormalizedCaptureIso", sharpNormalizedCaptureIso);\n            d.put("sharpnessLeicaIso", sharpLeicaIso);\n            d.put("sharpnessIsoSlot", sharpIsoSlot);\n            d.put("sharpnessInternalMode", sharpIsoSlot <= 5 ? 4 : (sharpIsoSlot <= 10 ? 3 : 2));\n            d.put("sharpnessMenu", "Standard");\n            d.put("sharpnessIsoBridge", "xiaomi_main_systemIso_x2_then_nearest_log2_Leica160_2500");\n            d.put("demosaicElapsedMs", demosaicElapsedMs);''','renderer telemetry')

# Generated canonical bank header is created by CI immediately before this patch is compiled.
cpp=rep(cpp,'#include <jni.h>','#include <jni.h>\n#include "m9_sharp_fulliso_bank.h"','header include')
cpp=rep(cpp,
'''        jfloat neutralR, jfloat neutralG, jfloat neutralB,\n        jboolean neutralAware,\n        jlongArray statsArray) {''',
'''        jfloat neutralR, jfloat neutralG, jfloat neutralB,\n        jboolean neutralAware,\n        jint sharpIsoSlot,\n        jlongArray statsArray) {''','jni signature')
cpp=rep(cpp,'    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;',
'''    if (!rawArray || !outBuffer || width <= 0 || height <= 0) return -1;\n    if (sharpIsoSlot < 0 || sharpIsoSlot >= M9_SHARP_ISO_ROWS) return -8;''','slot validation')

# Exact Standard working coefficient: mode4 x2, mode3 unchanged, mode2 arithmetic >>>1.
marker='inline uint16_t m9ClosureClamp14(int v){'
helper_cpp=r'''inline int m9SharpArShift1(int v){
    // Exact arithmetic signed >>>1, including negative odd values (floor toward -inf).
    return v>=0 ? (v>>1) : -(((-v)+1)>>1);
}
inline int m9SharpStandardCoeff(int slot,int idx){
    int v=static_cast<int>(M9_SHARP_BASE[slot][idx]);
    const int mode=M9_SHARP_STANDARD_MODE[slot];
    if(mode==4) v*=2;
    else if(mode==3) {}
    else if(mode==2) v=m9SharpArShift1(v);
    else return 0; // impossible after canonical build-time mode-table verification
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
'''            // STANDARD_FULLISO1A: canonical ISO-specific base row plus the proven\n            // Standard selector mode for that slot, then firmware [-2048,+2048] clamp.\n            const int corr=m9SharpStandardCoeff(isoSlot,1024+r);''','coeff use')
cpp=rep(cpp,
'm9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);',
'm9ClosureSharpStandardFullIso(sharpSourceGreen14, closureSharp14, width, height, sharpIsoSlot);','sharp call')
cpp=cpp.replace('SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=sharpLeicaGreen_plus_frozenMhcRgBg_differences',
'SHARPNESS_STANDARD_FULLISO1A_ID: menu=Standard slot=dynamic modes=4/3/2 nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=RBANCHOR1A',1)

# PRIMARY identity must no longer claim fixed slot0/mode4.
t=t.replace('root.put("sharpnessResearch", "SHARPSOURCE1C_RBANCHOR1A");','root.put("sharpnessResearch", "STANDARD_FULLISO1A_RBANCHOR1A");',1)
t=t.replace('root.put("sharpnessSlot", 0);','root.put("sharpnessSlot", -1); // dynamic; actual slot in nested renderer diagnostics',1)
t=t.replace('root.put("sharpnessInternalMode", 4);','root.put("sharpnessInternalMode", -1); // dynamic Standard 4/3/2 by slot',1)
t=t.replace('root.put("sharpnessScale", "2x");','root.put("sharpnessScale", "slot-dependent Standard mode4/mode3/mode2");',1)

R.write_text(r); C.write_text(c); CPP.write_text(cpp); T.write_text(t)
print('STANDARD_FULLISO1A applied: dynamic Leica ISO slot, canonical 13-row LUT bank, Standard mode 4/3/2, RBANCHOR1A unchanged')
