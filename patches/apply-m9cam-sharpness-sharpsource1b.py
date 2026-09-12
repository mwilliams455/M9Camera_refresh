#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists():
    raise SystemExit('SHARPSOURCE1B missing ' + str(CPP))
s = CPP.read_text()

# SHARPSOURCE1B is deliberately an isolated delta on the verified CLOSURETEST1B
# assembly. It keeps frozen neutral-MHC RGB, but derives the Leica Standard x2
# Sharp correction from the recovered Leica green source rather than MHC green.
if 'SHARPNESS_CLOSURETEST1B' not in s or 'm9ClosureSlot0Coeff' not in s:
    raise SystemExit('SHARPSOURCE1B requires assembled CLOSURETEST1B parent')
if 'SHARPNESS_SHARPSOURCE1B' in s:
    raise SystemExit('SHARPSOURCE1B already applied')

# Add the recovered Leica green-source constructor after q14/q16 helpers. All
# arithmetic is performed in the Leica 14-bit signal domain. The whole-frame
# implementation computes safe values everywhere, but only the proven 9-pixel
# valid interior is allowed to affect RGB later.
anchor = '''inline uint16_t m9ClosureQ16(uint16_t v){
    return static_cast<uint16_t>((static_cast<uint32_t>(v)*65535u + 8191u)/16383u);
}
'''
helpers = r'''inline uint16_t m9SharpSourceRaw14At(const jshort* raw,int w,int h,int y,int x){
    if(y<0) y=0; else if(y>=h) y=h-1;
    if(x<0) x=0; else if(x>=w) x=w-1;
    return m9ClosureQ14(u16(raw[static_cast<size_t>(y)*static_cast<size_t>(w)+static_cast<size_t>(x)]));
}

// SHARPNESS_SHARPSOURCE1B -- recovered GreenInterpolationWithCo interior source.
// R/B CFA sites: cardinal four-neighbour green average /4.
// Gr/Gb CFA sites: center/2 + four diagonal greens /8.
// This is the signal domain consumed by Leica Sharp; it does NOT replace frozen MHC RGB.
inline void m9SharpSourceLeicaGreen14(const jshort* raw,int w,int h,std::vector<uint16_t>& dst){
    const size_t n=static_cast<size_t>(w)*static_cast<size_t>(h);
    dst.resize(n);
    for(int y=0;y<h;++y){
        for(int x=0;x<w;++x){
            const size_t p=static_cast<size_t>(y)*static_cast<size_t>(w)+static_cast<size_t>(x);
            const bool ey=(y&1)==0, ex=(x&1)==0;
            int g;
            if(ey==ex){
                g=(static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y-1,x))+
                   static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y+1,x))+
                   static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y,x-1))+
                   static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y,x+1)))/4;
            }else{
                g=(4*static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y,x))+
                   static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y-1,x-1))+
                   static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y-1,x+1))+
                   static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y+1,x-1))+
                   static_cast<int>(m9SharpSourceRaw14At(raw,w,h,y+1,x+1)))/8;
            }
            dst[p]=static_cast<uint16_t>(g<0?0:(g>16383?16383:g));
        }
    }
}
'''
if s.count(anchor) != 1:
    raise SystemExit('SHARPSOURCE1B q16 anchor count=' + str(s.count(anchor)))
s = s.replace(anchor, anchor + '\n' + helpers + '\n', 1)

old_source = '''        // SHARPNESS_CLOSURETEST1A/CLOSURETEST1B: fixed manual ISO160 / Standard mode4 probe.
        // Convert the completed green plane to Leica's proven 14-bit domain,
        // run the recovered slot0 Sharp kernel, then let the second pass preserve
        // the frozen MHC colour differences around the sharpened green/base.
        std::vector<uint16_t> closureGreen14(static_cast<size_t>(pixels64));
        for (size_t p = 0; p < static_cast<size_t>(pixels64); ++p) {
            closureGreen14[p] = m9ClosureQ14(greenPlane[p]);
        }
        std::vector<uint16_t> closureSharp14;
        m9ClosureSharpIso160Standard(closureGreen14, closureSharp14, width, height);
'''
new_source = '''        // SHARPNESS_SHARPSOURCE1B: fixed ISO160 / Standard mode4 research candidate.
        // Keep frozen neutral-MHC RGB as the photographic foundation. Build the
        // recovered Leica green source independently in Leica's 14-bit domain,
        // sharpen that source with the unchanged mode4/x2 LUT, then apply only
        // the resulting correction to MHC RGB in the proven 9-pixel valid region.
        std::vector<uint16_t> sharpSourceGreen14;
        m9SharpSourceLeicaGreen14(raw, width, height, sharpSourceGreen14);
        std::vector<uint16_t> closureSharp14;
        m9ClosureSharpIso160Standard(sharpSourceGreen14, closureSharp14, width, height);
'''
if s.count(old_source) != 1:
    raise SystemExit('SHARPSOURCE1B source block anchor count=' + str(s.count(old_source)))
s = s.replace(old_source, new_source, 1)

old_capture = 'threads.emplace_back([=, &greenPlane, &closureSharp14]() {'
new_capture = 'threads.emplace_back([=, &greenPlane, &sharpSourceGreen14, &closureSharp14]() {'
if s.count(old_capture) != 1:
    raise SystemExit('SHARPSOURCE1B second-pass capture anchor count=' + str(s.count(old_capture)))
s = s.replace(old_capture, new_capture, 1)

old_closure = '''                        uint16_t base[3];
                        mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,greenPlane[p],base,nr,nb,invR,invB);
                        const int g14=m9ClosureQ14(base[1]);
                        const int dr=m9ClosureQ14(base[0])-g14;
                        const int db=m9ClosureQ14(base[2])-g14;
                        const int sg=closureSharp14[p];
                        dst[0]=m9ClosureQ16(m9ClosureClamp14(sg+dr));
                        dst[1]=m9ClosureQ16(static_cast<uint16_t>(sg));
                        dst[2]=m9ClosureQ16(m9ClosureClamp14(sg+db));'''
new_closure = '''                        uint16_t base[3];
                        mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,greenPlane[p],base,nr,nb,invR,invB);
                        // GreenInterpolationWithCo(+3) + Noise mode2(+4) + Sharp(+2)
                        // gives the firmware-proven cumulative support margin of 9 px.
                        if(x>=9 && x<width-9 && y>=9 && y<height-9){
                            const int delta=static_cast<int>(closureSharp14[p])-static_cast<int>(sharpSourceGreen14[p]);
                            dst[0]=m9ClosureQ16(m9ClosureClamp14(static_cast<int>(m9ClosureQ14(base[0]))+delta));
                            dst[1]=m9ClosureQ16(m9ClosureClamp14(static_cast<int>(m9ClosureQ14(base[1]))+delta));
                            dst[2]=m9ClosureQ16(m9ClosureClamp14(static_cast<int>(m9ClosureQ14(base[2]))+delta));
                        }else{
                            // Outside Leica's valid accumulated support region, leave the
                            // validated frozen neutral-MHC output byte-for-byte untouched.
                            dst[0]=base[0]; dst[1]=base[1]; dst[2]=base[2];
                        }'''
if s.count(old_closure) != 1:
    raise SystemExit('SHARPSOURCE1B closure anchor count=' + str(s.count(old_closure)))
s = s.replace(old_closure, new_closure, 1)

# Make the research identity greppable in native source/build artifacts even before
# Java sidecar wiring is added. Do not alter production labels here.
identity_anchor = '// SHARPNESS_SHARPSOURCE1B: fixed ISO160 / Standard mode4 research candidate.'
identity = ('// SHARPNESS_SHARPSOURCE1B_ID: menu=Standard slot=0 internalMode=4 scale=2x '
            'nNoise=2 supportMargin=9 sharpSource=LeicaGreen14 rgbFoundation=MHCNeutralFrozen')
if s.count(identity_anchor) != 1:
    raise SystemExit('SHARPSOURCE1B identity anchor count=' + str(s.count(identity_anchor)))
s = s.replace(identity_anchor, identity + '\n        ' + identity_anchor, 1)

CPP.write_text(s)
print('SHARPSOURCE1B applied: Leica-green-derived Standard mode4/x2 correction onto frozen neutral-MHC RGB, supportMargin=9, nNoise=2')
