#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists():
    raise SystemExit('CLOSURETEST1A missing ' + str(CPP))
cpp = CPP.read_text()
if 'SPLITDEMOSAIC1A research seam' not in cpp or 'mhcNeutralGreenRggb(' not in cpp:
    raise SystemExit('CLOSURETEST1A requires assembled SPLITDEMOSAIC1A parent')
if 'SHARPNESS_CLOSURETEST1A' in cpp:
    raise SystemExit('CLOSURETEST1A already applied')

# This is deliberately a diagnostic, not production policy. Firmware-closed pieces:
#  - Leica Sharp runs in a 0..16383 numeric domain
#  - slot 0 is manual ISO160
#  - Standard is the unscaled base LUT
#  - Sharp modifies the green/base plane in place before R/B reconstruction
# Port-choice pieces intentionally isolated here:
#  - endpoint-nearest normalized16<->14 conversion
#  - preserving the frozen MHC R-G/B-G differences across the sharpened green
#    because exact Leica red-vs-blue difference-lane layout is still under study.
helpers = r'''

// SHARPNESS_CLOSURETEST1A -- RESEARCH ONLY, fixed ISO160 slot0 / Standard 1x.
inline uint16_t m9ClosureQ14(uint16_t v){
    return static_cast<uint16_t>((static_cast<uint32_t>(v)*16383u + 32767u)/65535u);
}
inline uint16_t m9ClosureQ16(uint16_t v){
    return static_cast<uint16_t>((static_cast<uint32_t>(v)*65535u + 8191u)/16383u);
}
inline int m9ClosureSlot0Coeff(int idx){
    // Canonical Leica M9 slot0 is identity (idx-1024) except these 54 entries.
    // Reconstructed int16[2050] SHA256 = 2317595946f76c3965b7479c1c68fd66e5a9ac8be81292a91f944a6cde85f6e9.
    switch(idx){
        case 997:return -26; case 998:return -25; case 999:return -24; case 1000:return -23;
        case 1001:return -21; case 1002:return -20; case 1003:return -19; case 1004:return -17;
        case 1005:return -16; case 1006:return -15; case 1007:return -13; case 1008:return -12;
        case 1009:return -11; case 1010:return -10; case 1011:return -9; case 1012:return -8;
        case 1013:return -7; case 1014:return -6; case 1015:return -5; case 1016:return -4;
        case 1017:return -3; case 1018:return -2; case 1019:return -2; case 1020:return -1;
        case 1021:return -1; case 1022:return 0; case 1023:return 0; case 1025:return 0;
        case 1026:return 0; case 1027:return 1; case 1028:return 1; case 1029:return 2;
        case 1030:return 2; case 1031:return 3; case 1032:return 4; case 1033:return 5;
        case 1034:return 6; case 1035:return 7; case 1036:return 8; case 1037:return 9;
        case 1038:return 10; case 1039:return 11; case 1040:return 12; case 1041:return 13;
        case 1042:return 15; case 1043:return 16; case 1044:return 17; case 1045:return 19;
        case 1046:return 20; case 1047:return 21; case 1048:return 23; case 1049:return 24;
        case 1050:return 25; case 1051:return 26;
        default:return idx-1024;
    }
}
inline uint16_t m9ClosureClamp14(int v){
    return static_cast<uint16_t>(v<0?0:(v>16383?16383:v));
}
inline void m9ClosureSharpIso160Standard(const std::vector<uint16_t>& src,
                                         std::vector<uint16_t>& dst,int w,int h){
    dst=src;
    // Firmware Sharp contributes a two-pixel untouched perimeter per side.
    for(int y=2;y<h-2;++y){
        for(int x=2;x<w-2;++x){
            const size_t p=static_cast<size_t>(y)*static_cast<size_t>(w)+static_cast<size_t>(x);
            const int a00=src[p-w-1],a01=src[p-w],a02=src[p-w+1];
            const int a10=src[p-1],  a11=src[p],  a12=src[p+1];
            const int a20=src[p+w-1],a21=src[p+w],a22=src[p+w+1];
            const int g=(a00+2*a01+a02+2*a10+4*a11+2*a12+a20+2*a21+a22)/16;
            int r=a11-g; if(r < -1024) r=-1024; else if(r > 1024) r=1024;
            const int corr=m9ClosureSlot0Coeff(1024+r); // Standard == 1x base LUT.
            dst[p]=m9ClosureClamp14(a11+corr);
        }
    }
}
'''

# Helpers must be at C++ file scope. The previous version inserted them at the
# split-seam comment, which lives inside demosaicMhcRggb() and caused Clang's
# "function definition is not allowed here" error. Insert immediately before
# the JNI demosaic entry point instead, where all helpers are visible to it.
file_scope_anchor = '''extern "C" JNIEXPORT jlong JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb('''
idx = cpp.find(file_scope_anchor)
if idx < 0:
    raise SystemExit('CLOSURETEST1A file-scope JNI anchor missing')
cpp = cpp[:idx] + helpers + '\n' + cpp[idx:]

old = '''        for (auto& thread : threads) thread.join();
        threads.clear();
        for (int worker = 0; worker < workerCount; ++worker) {'''
new = '''        for (auto& thread : threads) thread.join();

        // SHARPNESS_CLOSURETEST1A: fixed manual ISO160 / Standard probe.
        // Convert the completed green plane to Leica's proven 14-bit domain,
        // run the recovered slot0 Sharp kernel, then let the second pass preserve
        // the frozen MHC colour differences around the sharpened green/base.
        std::vector<uint16_t> closureGreen14(static_cast<size_t>(pixels64));
        for (size_t p = 0; p < static_cast<size_t>(pixels64); ++p) {
            closureGreen14[p] = m9ClosureQ14(greenPlane[p]);
        }
        std::vector<uint16_t> closureSharp14;
        m9ClosureSharpIso160Standard(closureGreen14, closureSharp14, width, height);

        threads.clear();
        for (int worker = 0; worker < workerCount; ++worker) {'''
if cpp.count(old) != 1:
    raise SystemExit('CLOSURETEST1A pass-boundary anchor count=' + str(cpp.count(old)))
cpp = cpp.replace(old,new,1)

# The second pass reads the full sharpened plane. Capture it by reference so we
# do not copy a 12 MP uint16_t frame into every worker closure.
old_capture = '''            threads.emplace_back([=, &greenPlane]() {
                for (int y = y0; y < y1; ++y) {
                    for (int x = 0; x < width; ++x) {
                        const size_t p=static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x);'''
new_capture = '''            threads.emplace_back([=, &greenPlane, &closureSharp14]() {
                for (int y = y0; y < y1; ++y) {
                    for (int x = 0; x < width; ++x) {
                        const size_t p=static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x);'''
if cpp.count(old_capture) != 1:
    raise SystemExit('CLOSURETEST1A second-pass capture anchor count=' + str(cpp.count(old_capture)))
cpp = cpp.replace(old_capture,new_capture,1)

old2 = '''                        uint16_t* dst=out+p*3u;
                        mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,greenPlane[p],dst,nr,nb,invR,invB);'''
new2 = '''                        uint16_t* dst=out+p*3u;
                        uint16_t base[3];
                        mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,greenPlane[p],base,nr,nb,invR,invB);
                        const int g14=m9ClosureQ14(base[1]);
                        const int dr=m9ClosureQ14(base[0])-g14;
                        const int db=m9ClosureQ14(base[2])-g14;
                        const int sg=closureSharp14[p];
                        dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));
                        dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));
                        dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));'''
if cpp.count(old2) != 1:
    raise SystemExit('CLOSURETEST1A R/B completion anchor count=' + str(cpp.count(old2)))
cpp=cpp.replace(old2,new2,1)
CPP.write_text(cpp)
print('SHARPNESS_CLOSURETEST1A applied: fixed ISO160/Standard Leica Sharp + difference-preserving R/B closure probe')
