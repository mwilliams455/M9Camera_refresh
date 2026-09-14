#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
JAVA = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'
RENDER = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
for p in (CPP, JAVA, RENDER):
    if not p.exists():
        raise SystemExit('RBEXPERIMENT1A missing ' + str(p))

cpp = CPP.read_text()
if 'SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID' not in cpp:
    raise SystemExit('RBEXPERIMENT1A requires assembled SHARPSOURCE1C-RBANCHOR1A parent')
if 'RBEXPERIMENT1A_EXACT_GREEN_RB_ID' in cpp:
    raise SystemExit('RBEXPERIMENT1A already applied')

marker = 'extern "C" JNIEXPORT jlong JNICALL\nJava_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_demosaicMhcRggb('
if cpp.count(marker) != 1:
    raise SystemExit('RBEXPERIMENT1A JNI marker count=' + str(cpp.count(marker)))

helpers = r'''
// RBEXPERIMENT1A_EXACT_GREEN_RB_ID
// Android photographic experiment only. The arithmetic below is a direct C++
// translation of the machine-vs-scalar closed M9 GreenInterpolationWithCo
// composite (GREENORACLE6O) followed by the closed ASMRedBlueInterpolation1
// lattice/arithmetic (RBORACLE7B). The experiment fixes canonical RGGB phase=0
// and support-before=0 in Android image coordinates. The production Run-side
// frame-counter/pointer choreography remains a separate firmware concern.
//
// The candidate is promoted only inside the already validated 9-pixel support
// region. Any geometry/bounds failure leaves the parent neutral-MHC path active.

inline int16_t rbx1S16(uint16_t v) {
    return static_cast<int16_t>(v);
}
inline uint16_t rbx1U16(int v) {
    return static_cast<uint16_t>(v & 0xffff);
}
inline int rbx1Sat16(int v) {
    return v < -32768 ? -32768 : (v > 32767 ? 32767 : v);
}
inline int rbx1Wrap16(int v) {
    return static_cast<int16_t>(static_cast<uint16_t>(v));
}
inline int rbx1HAvg(uint16_t a, uint16_t b) {
    return rbx1Sat16(static_cast<int>(rbx1S16(a)) + static_cast<int>(rbx1S16(b))) >> 1;
}
inline int rbx1WrapAvg(uint16_t a, uint16_t b) {
    return rbx1Wrap16(static_cast<int>(rbx1S16(a)) + static_cast<int>(rbx1S16(b))) >> 1;
}
inline int rbx1DiagonalAvg(uint16_t a, uint16_t b, uint16_t c, uint16_t d) {
    return rbx1Wrap16(rbx1HAvg(a,b) + rbx1HAvg(c,d)) >> 1;
}
inline uint16_t rbx1FinalAdd(uint16_t green, int diffEstimate) {
    const int wrapped = rbx1Wrap16(static_cast<int>(rbx1S16(green)) + diffEstimate);
    return static_cast<uint16_t>(wrapped < 0 ? 0 : (wrapped > 16383 ? 16383 : wrapped));
}
inline uint16_t rbx1Abs16(uint16_t v) {
    const int x = static_cast<int>(rbx1S16(v));
    if (x == -32768) return 32767;
    return static_cast<uint16_t>(x < 0 ? -x : x);
}

inline bool rbx1Read(const std::vector<uint16_t>& p, int64_t byteOff, uint16_t& out) {
    if ((byteOff & 1LL) != 0 || byteOff < 0) return false;
    const int64_t i = byteOff >> 1;
    if (i < 0 || static_cast<uint64_t>(i) >= p.size()) return false;
    out = p[static_cast<size_t>(i)];
    return true;
}
inline bool rbx1Write(std::vector<uint16_t>& p, int64_t byteOff, uint16_t v) {
    if ((byteOff & 1LL) != 0 || byteOff < 0) return false;
    const int64_t i = byteOff >> 1;
    if (i < 0 || static_cast<uint64_t>(i) >= p.size()) return false;
    p[static_cast<size_t>(i)] = v;
    return true;
}

inline bool rbx1Filter010(std::vector<uint16_t>& src,
                          std::vector<uint16_t>& dst,
                          int64_t srcBase, int64_t dstBase,
                          int inner, int outer, int stride, int selector) {
    if (inner <= 0 || (inner & 1) || outer <= 0 || stride <= inner || (selector != 0 && selector != 2)) return false;
    for (int rr=0; rr<outer; ++rr) {
        const int64_t row = 4LL * stride * rr;
        for (int cc=0; cc<inner; ++cc) {
            const int64_t center = srcBase + row + 4LL*cc;
            uint16_t l,rh,u,dn;
            if (!rbx1Read(src,center-2,l) || !rbx1Read(src,center+2,rh)
                    || !rbx1Read(src,center-2LL*stride,u) || !rbx1Read(src,center+2LL*stride,dn)) return false;
            const uint32_t total = static_cast<uint32_t>(l)+rh+u+dn;
            const uint16_t v = selector==2 ? static_cast<uint16_t>(total >> 2) : static_cast<uint16_t>(total);
            if (!rbx1Write(dst,dstBase+row+4LL*cc,v)) return false;
        }
    }
    return true;
}

inline bool rbx1Filter101040(std::vector<uint16_t>& src,
                             std::vector<uint16_t>& out1,
                             std::vector<uint16_t>& out2,
                             int64_t srcBase, int64_t out1Base, int64_t out2Base,
                             int inner, int outer, int stride) {
    if (inner <= 0 || (inner & 1) || outer <= 0 || stride <= 0 || (stride & 1)) return false;
    const bool packedSwap = (srcBase & 0x2LL) != 0;
    for (int rr=0; rr<outer; ++rr) {
        const int64_t row = 4LL * stride * rr;
        if (packedSwap) {
            uint16_t v0,v1;
            if (!rbx1Read(out2,out2Base+row-8,v0) || !rbx1Read(out2,out2Base+row-4,v1)) return false;
            if (!rbx1Write(out2,out2Base+row-8,v1) || !rbx1Write(out2,out2Base+row-4,v0)) return false;
        }
        for (int cc=0; cc<inner; ++cc) {
            const int64_t center = srcBase + row + 4LL*cc;
            uint16_t cv,nw,ne,sw,se;
            if (!rbx1Read(src,center,cv)
                    || !rbx1Read(src,center-2LL*stride-2,nw)
                    || !rbx1Read(src,center-2LL*stride+2,ne)
                    || !rbx1Read(src,center+2LL*stride-2,sw)
                    || !rbx1Read(src,center+2LL*stride+2,se)) return false;
            const uint16_t filtered = static_cast<uint16_t>(
                    (4u*static_cast<uint32_t>(cv)+nw+ne+sw+se) >> 3);
            const uint16_t residual = rbx1Abs16(static_cast<uint16_t>(filtered-cv));
            if (!rbx1Write(out1,out1Base+row+4LL*cc,filtered)
                    || !rbx1Write(out2,out2Base+row+4LL*cc,residual)) return false;
        }
    }
    return true;
}

inline uint16_t rbx1DifferSample(uint16_t a,uint16_t b,uint16_t threshold,int shift) {
    int dd = static_cast<int>(a) - static_cast<int>(b);
    const int corr = static_cast<int>(threshold) >> shift;
    const int cand = dd >= 0 ? std::max(dd-corr,0) : std::min(dd+corr,0);
    if (std::abs(dd) < static_cast<int>(threshold)) dd = cand;
    return static_cast<uint16_t>(dd);
}
inline uint16_t rbx1DifferRaw(uint16_t a,uint16_t b) {
    return static_cast<uint16_t>(static_cast<uint16_t>(a)-static_cast<uint16_t>(b));
}

inline bool rbx1RedBlueDiffer(std::vector<uint16_t>& a,
                              std::vector<uint16_t>& b,
                              std::vector<uint16_t>& threshold,
                              std::vector<uint16_t>& out,
                              int64_t aBase,int64_t bBase,int64_t tBase,int64_t outBase,
                              int inner,int outer,int stride,int shift) {
    if (inner < 1 || outer < 1 || stride < inner) return false;
    auto av=[&](std::vector<uint16_t>& p,int64_t base,int rr,int cc,uint16_t& v)->bool{
        return rbx1Read(p,base+4LL*(static_cast<int64_t>(rr)*stride+cc),v);
    };
    uint16_t aa,bb,tt;
    if (!av(a,aBase,0,0,aa) || !av(b,bBase,0,0,bb) || !rbx1Write(out,outBase-4,rbx1DifferRaw(aa,bb))) return false;
    if (inner==1) {
        if (!av(threshold,tBase,0,0,tt) || !rbx1Write(out,outBase,rbx1DifferSample(aa,bb,tt,shift))) return false;
    } else {
        for (int cc=1;cc<inner;++cc) {
            if (!av(a,aBase,0,cc,aa)||!av(b,bBase,0,cc,bb)
                    || !rbx1Write(out,outBase+4LL*(cc-1),rbx1DifferRaw(aa,bb))) return false;
        }
        const int cc=inner-1;
        if (!av(a,aBase,0,cc,aa)||!av(b,bBase,0,cc,bb)||!av(threshold,tBase,0,cc,tt)
                || !rbx1Write(out,outBase+4LL*cc,rbx1DifferSample(aa,bb,tt,shift))) return false;
    }
    for (int rr=1;rr<outer;++rr) {
        for (int cc=0;cc<inner;++cc) {
            if (!av(a,aBase,rr,cc,aa)||!av(b,bBase,rr,cc,bb)
                    || !rbx1Write(out,outBase+4LL*(static_cast<int64_t>(rr)*stride-1+cc),rbx1DifferRaw(aa,bb))) return false;
        }
        const int cc=inner-1;
        if (!av(a,aBase,rr,cc,aa)||!av(b,bBase,rr,cc,bb)||!av(threshold,tBase,rr,cc,tt)
                || !rbx1Write(out,outBase+4LL*(static_cast<int64_t>(rr)*stride+cc),rbx1DifferSample(aa,bb,tt,shift))) return false;
    }
    return true;
}

inline bool rbx1Filter101000(std::vector<uint16_t>& src,
                             std::vector<uint16_t>& dst,
                             int64_t srcBase,int64_t dstBase,
                             int inner,int outer,int stride) {
    if (inner<=0 || (inner&1) || outer<=0 || stride<=inner) return false;
    for(int rr=0;rr<outer;++rr){
        const int64_t row=4LL*stride*rr;
        for(int cc=0;cc<inner;++cc){
            const int64_t center=srcBase+row+4LL*cc;
            uint16_t nw,ne,sw,se;
            if(!rbx1Read(src,center-2LL*stride-2,nw)||!rbx1Read(src,center-2LL*stride+2,ne)
                    ||!rbx1Read(src,center+2LL*stride-2,sw)||!rbx1Read(src,center+2LL*stride+2,se)) return false;
            const int total=static_cast<int>(rbx1S16(nw))+static_cast<int>(rbx1S16(ne))
                    +static_cast<int>(rbx1S16(sw))+static_cast<int>(rbx1S16(se));
            if(!rbx1Write(dst,dstBase+row+4LL*cc,static_cast<uint16_t>(total>>2))) return false;
        }
    }
    return true;
}

inline bool rbx1GreenComposite(std::vector<uint16_t>& a,
                               std::vector<uint16_t>& b,
                               std::vector<uint16_t>& c,
                               std::vector<uint16_t>& d,
                               int stride,int height,int shift,int phaseInitial,
                               int& phaseFinal) {
    if(stride<16 || height<12 || (stride&1)) return false;
    const int halfH=height>>1;
    const int p1=phaseInitial+1;
    const int outer0=halfH-p1;
    int inner0=(stride>>1)-p1; inner0 += inner0&1;
    const int64_t off1=2LL*p1*(stride+1);
    if(!rbx1Filter010(a,b,off1,off1,inner0,outer0,stride,2)) return false;
    if(!rbx1Filter010(a,b,off1+2LL*stride+2,off1+2LL*stride+2,inner0,outer0,stride,2)) return false;
    if(!rbx1Filter101040(a,b,c,off1+2,off1+2,off1+2,inner0,outer0,stride)) return false;
    if(!rbx1Filter101040(a,b,c,off1+2LL*stride,off1+2LL*stride,off1+2LL*stride,inner0,outer0,stride)) return false;

    const int p2=p1+1;
    const int outer1=halfH-p2;
    int inner1=(stride>>1)-p2; inner1 += inner1&1;
    const int64_t off2=2LL*p2*(stride+1);
    if(!rbx1Filter010(c,c,off2,off2,inner1,outer1,stride,0)) return false;
    if(!rbx1Filter010(c,c,off2+2LL*stride+2,off2+2LL*stride+2,inner1,outer1,stride,0)) return false;
    if(!rbx1RedBlueDiffer(a,b,c,d,off2,off2,off2,off2,inner1,outer1,stride,shift)) return false;
    const int64_t off2b=off2+2LL*stride+2;
    if(!rbx1RedBlueDiffer(a,b,c,d,off2b,off2b,off2b,off2b,inner1,outer1,stride,shift)) return false;

    const int p3=p2+1;
    const int outer2=halfH-p3;
    int inner2=(stride>>1)-p3; inner2 += inner2&1;
    const int64_t off3=2LL*p3*(stride+1);
    if(!rbx1Filter101000(d,a,off3,off3,inner2,outer2,stride)) return false;
    if(!rbx1Filter101000(d,a,off3+2LL*stride+2,off3+2LL*stride+2,inner2,outer2,stride)) return false;
    phaseFinal=p3;
    return true;
}

inline bool rbx1InterpExact(const std::vector<uint16_t>& diff,
                            const std::vector<uint16_t>& green,
                            int width,int height,int supportBefore,
                            std::vector<uint16_t>& red,
                            std::vector<uint16_t>& blue) {
    const int support=supportBefore+1;
    if(width<3||height<3||support<1||2*support>=std::min(width,height)) return false;
    const size_t n=static_cast<size_t>(width)*static_cast<size_t>(height);
    if(diff.size()<n||green.size()<n) return false;
    red.assign(n,0); blue.assign(n,0);
    const int blueParity=support&1;
    const int redParity=(support+1)&1;
    auto est=[&](int y,int x,int p)->int{
        const size_t k=static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x);
        if((y&1)==p && (x&1)==p) return static_cast<int>(rbx1S16(diff[k]));
        if((y&1)==p) return rbx1HAvg(diff[k-1],diff[k+1]);
        if((x&1)==p) return rbx1WrapAvg(diff[k-width],diff[k+width]);
        return rbx1DiagonalAvg(diff[k-width-1],diff[k-width+1],diff[k+width-1],diff[k+width+1]);
    };
    for(int y=support;y<height-support;++y){
        for(int x=support;x<width-support;++x){
            const size_t k=static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x);
            red[k]=rbx1FinalAdd(green[k],est(y,x,redParity));
            blue[k]=rbx1FinalAdd(green[k],est(y,x,blueParity));
        }
    }
    return true;
}
'''
cpp = cpp.replace(marker, helpers + '\n' + marker, 1)

old_prepare = '''        std::vector<uint16_t> sharpSourceGreen14;
        m9SharpSourceLeicaGreen14(raw, width, height, sharpSourceGreen14);
        std::vector<uint16_t> closureSharp14;
        m9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);'''
new_prepare = '''        // RBEXPERIMENT1A: exact closed Green composite -> exact closed R/B interpolation.
        // Canonical Android RGGB coordinates use Green phase 0 and R/B support-before 0.
        // Scratch planes start zero; the promoted 9-pixel interior is fully produced by
        // the closed helper sequence before it is consumed. MHC remains the preservation
        // fallback and border result.
        const size_t rbxPixels=static_cast<size_t>(pixels64);
        std::vector<uint16_t> sharpSourceGreen14(rbxPixels+1u,0);
        std::vector<uint16_t> rbxPlaneA(rbxPixels+1u,0);
        std::vector<uint16_t> rbxPlaneC(rbxPixels+1u,0);
        std::vector<uint16_t> rbxPlaneD(rbxPixels+1u,0);
        for(size_t p=0;p<rbxPixels;++p) rbxPlaneA[p]=m9ClosureQ14(u16(raw[p]));
        int rbxGreenPhaseFinal=-1;
        bool rbxExperimentOk=rbx1GreenComposite(
                rbxPlaneA,sharpSourceGreen14,rbxPlaneC,rbxPlaneD,
                width,height,2,0,rbxGreenPhaseFinal);
        std::vector<uint16_t> rbxRed14;
        std::vector<uint16_t> rbxBlue14;
        if(rbxExperimentOk) {
            // rbxPlaneA now carries the Green-stage colour-difference lattice at
            // the R/B sample sites consumed by ASMRedBlueInterpolation1.
            rbxExperimentOk=rbx1InterpExact(
                    rbxPlaneA,sharpSourceGreen14,width,height,0,rbxRed14,rbxBlue14);
        }
        if(!rbxExperimentOk) {
            // Preserve the validated parent behaviour if the experiment rejects
            // unexpected geometry or an address/side-effect bound.
            m9SharpSourceLeicaGreen14(raw,width,height,sharpSourceGreen14);
            rbxRed14.clear();
            rbxBlue14.clear();
        }
        std::vector<uint16_t> closureSharp14;
        m9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);'''
if cpp.count(old_prepare) != 1:
    raise SystemExit('RBEXPERIMENT1A prepare anchor count=' + str(cpp.count(old_prepare)))
cpp = cpp.replace(old_prepare,new_prepare,1)

old_capture = '            threads.emplace_back([=, &greenPlane, &sharpSourceGreen14, &closureSharp14]() {'
new_capture = '            threads.emplace_back([=, &greenPlane, &sharpSourceGreen14, &closureSharp14, &rbxRed14, &rbxBlue14]() {'
if cpp.count(old_capture) != 1:
    raise SystemExit('RBEXPERIMENT1A lambda anchor count=' + str(cpp.count(old_capture)))
cpp = cpp.replace(old_capture,new_capture,1)

old_rgb = '''                            // SHARPSOURCE1C-RBANCHOR1A: do not graft a Leica-source Sharp
                            // delta onto a different MHC-green baseline. Anchor reconstructed
                            // RGB to the sharpened Leica green/base exactly, then carry the
                            // frozen neutral-MHC R-G and B-G differences only as temporary
                            // colour-difference proxies until exact BF561 lane semantics close.
                            const int sg=static_cast<int>(closureSharp14[p]);
                            const int mg=static_cast<int>(m9ClosureQ14(base[1]));
                            const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;
                            const int db=static_cast<int>(m9ClosureQ14(base[2]))-mg;
                            dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));
                            dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));
                            dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));'''
new_rgb = '''                            const int sg=static_cast<int>(closureSharp14[p]);
                            if(rbxExperimentOk){
                                // RBEXPERIMENT1A: replace the temporary MHC R-G/B-G proxy
                                // with the machine-closed Leica R/B interpolator result.
                                // Sharp remains a green-domain stage: retain the Leica
                                // candidate colour differences while anchoring to sharp G.
                                const int mg=static_cast<int>(sharpSourceGreen14[p]);
                                const int dr=static_cast<int>(rbxRed14[p])-mg;
                                const int db=static_cast<int>(rbxBlue14[p])-mg;
                                dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));
                                dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));
                                dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));
                            }else{
                                // Preservation fallback is byte-for-byte the parent
                                // SHARPSOURCE1C-RBANCHOR1A colour-difference policy.
                                const int mg=static_cast<int>(m9ClosureQ14(base[1]));
                                const int dr=static_cast<int>(m9ClosureQ14(base[0]))-mg;
                                const int db=static_cast<int>(m9ClosureQ14(base[2]))-mg;
                                dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));
                                dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));
                                dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));
                            }'''
if cpp.count(old_rgb) != 1:
    raise SystemExit('RBEXPERIMENT1A RGB anchor count=' + str(cpp.count(old_rgb)))
cpp = cpp.replace(old_rgb,new_rgb,1)

old_id = '// SHARPNESS_SHARPSOURCE1C_RBANCHOR1A_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen rbPolicy=sharpLeicaGreen_plus_frozenMhcRgBg_differences'
new_id = '// RBEXPERIMENT1A_EXACT_GREEN_RB_ACTIVE_ID: menu=Standard slot=0 internalMode=4 scale=2x nNoise=2 supportMargin=9 demosaic=GREENORACLE6O_phase0_plus_RBORACLE7B_support0 rgbFoundation=MHCNeutralFrozen_border_and_failure_fallback'
if cpp.count(old_id) != 1:
    raise SystemExit('RBEXPERIMENT1A ID anchor count=' + str(cpp.count(old_id)))
cpp = cpp.replace(old_id,new_id,1)
CPP.write_text(cpp)

j = JAVA.read_text()
repls = {
    'root.put("sharpnessResearch", "SHARPSOURCE1C_RBANCHOR1A");':
        'root.put("sharpnessResearch", "RBEXPERIMENT1A_EXACT_GREEN_RB");',
    'root.put("sharpnessRgbFoundation", "MHCNeutralFrozen_color_difference_proxy");':
        'root.put("sharpnessRgbFoundation", "LeicaGreenRbExactCandidate_MHCNeutralFrozen_border_fallback");',
    'root.put("sharpnessCorrectionPolicy", "anchor_to_sharpLeicaGreen14_then_restore_frozenMHC_RminusG_BminusG_proxy");':
        'root.put("sharpnessCorrectionPolicy", "anchor_to_sharpLeicaGreen14_then_restore_exact_RBORACLE7B_RminusG_BminusG");',
    'root.put("sharpnessRbPolicy", "RBANCHOR1A_sharpLeicaGreen_plus_frozenMHC_color_differences_proxy");':
        'root.put("sharpnessRbPolicy", "RBEXPERIMENT1A_GREENORACLE6O_phase0_RBORACLE7B_support0_interior9_MHC_fallback");',
}
for a,b in repls.items():
    if j.count(a) != 1:
        raise SystemExit('RBEXPERIMENT1A timing anchor count for ' + a + '=' + str(j.count(a)))
    j=j.replace(a,b,1)
insert='        root.put("sharpnessRbPolicy", "RBEXPERIMENT1A_GREENORACLE6O_phase0_RBORACLE7B_support0_interior9_MHC_fallback");\n'
extra=insert + '        root.put("rbExperiment1A", true);\n        root.put("rbExperimentGreenParity", 0);\n        root.put("rbExperimentSupportBefore", 0);\n        root.put("rbExperimentProductionRunGlueClaimed", false);\n'
if j.count(insert) != 1:
    raise SystemExit('RBEXPERIMENT1A timing insert anchor count=' + str(j.count(insert)))
j=j.replace(insert,extra,1)
JAVA.write_text(j)

r=RENDER.read_text()
old_label='"DEMOSAICMHCNEUTRAL1A_MalvarHeCutler5x5_RGGB_liveNeutral_balanced_restore"'
if old_label in r:
    r=r.replace(old_label,'"RBEXPERIMENT1A_GREENORACLE6O_RBORACLE7B_interior9_MHC_border"',1)
RENDER.write_text(r)

print('RBEXPERIMENT1A applied: exact closed Green composite + exact closed R/B interpolation in canonical RGGB interior; parent MHC preserved as border/failure fallback')
