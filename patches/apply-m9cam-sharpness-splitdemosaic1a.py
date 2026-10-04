#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
CPP = ROOT / 'app/src/main/cpp/m9color_jni.cpp'
if not CPP.exists():
    raise SystemExit('SPLITDEMOSAIC1A missing ' + str(CPP))
cpp = CPP.read_text()

if 'mhcPixelNeutralRggb(' not in cpp:
    raise SystemExit('SPLITDEMOSAIC1A requires validated DEMOSAICMHCNEUTRAL1A parent')
if 'mhcNeutralGreenRggb(' in cpp:
    raise SystemExit('SPLITDEMOSAIC1A already applied')

def function_end(src, marker):
    st = src.find(marker)
    if st < 0: raise SystemExit('SPLITDEMOSAIC1A marker missing: ' + marker)
    br = src.find('{', st)
    if br < 0: raise SystemExit('SPLITDEMOSAIC1A opening brace missing')
    d = 0
    for i in range(br, len(src)):
        if src[i] == '{': d += 1
        elif src[i] == '}':
            d -= 1
            if d == 0: return i + 1
    raise SystemExit('SPLITDEMOSAIC1A unterminated function')

# Keep the frozen monolithic helper in source as a forensic oracle. Add an exactly
# decomposed green-first + R/B-completion path beside it. Sharpness remains disabled.
mark = 'inline void mhcPixelNeutralRggb(const jshort* raw,int w,int h,int y,int x,uint16_t* rgb,double nr,double nb,double ir,double ib){'
e = function_end(cpp, mark)
helpers = r'''

// SPLITDEMOSAIC1A: exact structural decomposition of frozen MHCNEUTRAL1A.
// Pass 1 exposes the completed green plane. Pass 2 completes R/B from the same
// original CFA samples. With no inter-stage modification this must remain
// pixel-identical to mhcPixelNeutralRggb(). Leica Sharpness is NOT enabled here.
inline uint16_t mhcNeutralGreenRggb(const jshort* raw,int w,int h,int y,int x,
                                    double ir,double ib){
    const bool ey=(y&1)==0, ex=(x&1)==0;
    if(ey!=ex) return u16(raw[y*w+x]);
    const double ig=1.0;
    const double C=mhcNAt(raw,w,h,y,x,ir,ig,ib),N=mhcNAt(raw,w,h,y-1,x,ir,ig,ib),S=mhcNAt(raw,w,h,y+1,x,ir,ig,ib),W=mhcNAt(raw,w,h,y,x-1,ir,ig,ib),E=mhcNAt(raw,w,h,y,x+1,ir,ig,ib);
    const double NN=mhcNAt(raw,w,h,y-2,x,ir,ig,ib),SS=mhcNAt(raw,w,h,y+2,x,ir,ig,ib),WW=mhcNAt(raw,w,h,y,x-2,ir,ig,ib),EE=mhcNAt(raw,w,h,y,x+2,ir,ig,ib);
    const double g=(4*C+2*(N+S+W+E)-(NN+SS+WW+EE))/8.0;
    return mhcND(g);
}

inline void mhcPixelNeutralRbCompleteRggb(const jshort* raw,int w,int h,int y,int x,
                                          uint16_t green,uint16_t* rgb,
                                          double nr,double nb,double ir,double ib){
    const double ig=1.0;
    const double C=mhcNAt(raw,w,h,y,x,ir,ig,ib),N=mhcNAt(raw,w,h,y-1,x,ir,ig,ib),S=mhcNAt(raw,w,h,y+1,x,ir,ig,ib),W=mhcNAt(raw,w,h,y,x-1,ir,ig,ib),E=mhcNAt(raw,w,h,y,x+1,ir,ig,ib);
    const double NN=mhcNAt(raw,w,h,y-2,x,ir,ig,ib),SS=mhcNAt(raw,w,h,y+2,x,ir,ig,ib),WW=mhcNAt(raw,w,h,y,x-2,ir,ig,ib),EE=mhcNAt(raw,w,h,y,x+2,ir,ig,ib);
    const double NW=mhcNAt(raw,w,h,y-1,x-1,ir,ig,ib),NE=mhcNAt(raw,w,h,y-1,x+1,ir,ig,ib),SW=mhcNAt(raw,w,h,y+1,x-1,ir,ig,ib),SE=mhcNAt(raw,w,h,y+1,x+1,ir,ig,ib);
    const double o=(12*C+4*(NW+NE+SW+SE)-3*(NN+SS+WW+EE))/16.0;
    const double hh=(10*C+8*(W+E)+(NN+SS)-2*(NW+NE+SW+SE)-2*(WW+EE))/16.0;
    const double vv=(10*C+8*(N+S)+(WW+EE)-2*(NW+NE+SW+SE)-2*(NN+SS))/16.0;
    const bool ey=(y&1)==0,ex=(x&1)==0; const uint16_t sm=u16(raw[y*w+x]);
    if(ey&&ex){rgb[0]=sm;rgb[1]=green;rgb[2]=mhcND(o*nb);}
    else if(!ey&&!ex){rgb[0]=mhcND(o*nr);rgb[1]=green;rgb[2]=sm;}
    else if(ey){rgb[0]=mhcND(hh*nr);rgb[1]=green;rgb[2]=mhcND(vv*nb);}
    else{rgb[0]=mhcND(vv*nr);rgb[1]=green;rgb[2]=mhcND(hh*nb);}
}
'''
cpp = cpp[:e] + helpers + cpp[e:]

old = r'''    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));
    for (int worker = 0; worker < workerCount; ++worker) {
        const int y0 = (height * worker) / workerCount;
        const int y1 = (height * (worker + 1)) / workerCount;
        threads.emplace_back([=]() {
            for (int y = y0; y < y1; ++y) {
                for (int x = 0; x < width; ++x) {
                    uint16_t* dst=out+(static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x))*3u;
                    if(neutralAware) mhcPixelNeutralRggb(raw,width,height,y,x,dst,nr,nb,invR,invB);
                    else mhcPixelRggb(raw,width,height,y,x,dst);
                }
            }
        });
    }
    for (auto& thread : threads) thread.join();'''
new = r'''    std::vector<std::thread> threads;
    threads.reserve(static_cast<size_t>(workerCount));
    if (neutralAware) {
        // SPLITDEMOSAIC1A research seam: retain a 16-bit completed-green frame
        // between interpolation phases. No Sharpness modification is permitted yet.
        std::vector<uint16_t> greenPlane(static_cast<size_t>(pixels64));
        for (int worker = 0; worker < workerCount; ++worker) {
            const int y0 = (height * worker) / workerCount;
            const int y1 = (height * (worker + 1)) / workerCount;
            threads.emplace_back([=, &greenPlane]() {
                for (int y = y0; y < y1; ++y) {
                    for (int x = 0; x < width; ++x) {
                        greenPlane[static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x)] =
                                mhcNeutralGreenRggb(raw,width,height,y,x,invR,invB);
                    }
                }
            });
        }
        for (auto& thread : threads) thread.join();
        threads.clear();
        for (int worker = 0; worker < workerCount; ++worker) {
            const int y0 = (height * worker) / workerCount;
            const int y1 = (height * (worker + 1)) / workerCount;
            threads.emplace_back([=, &greenPlane]() {
                for (int y = y0; y < y1; ++y) {
                    for (int x = 0; x < width; ++x) {
                        const size_t p=static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x);
                        uint16_t* dst=out+p*3u;
                        mhcPixelNeutralRbCompleteRggb(raw,width,height,y,x,greenPlane[p],dst,nr,nb,invR,invB);
                    }
                }
            });
        }
        for (auto& thread : threads) thread.join();
    } else {
        for (int worker = 0; worker < workerCount; ++worker) {
            const int y0 = (height * worker) / workerCount;
            const int y1 = (height * (worker + 1)) / workerCount;
            threads.emplace_back([=]() {
                for (int y = y0; y < y1; ++y) {
                    for (int x = 0; x < width; ++x) {
                        uint16_t* dst=out+(static_cast<size_t>(y)*static_cast<size_t>(width)+static_cast<size_t>(x))*3u;
                        mhcPixelRggb(raw,width,height,y,x,dst);
                    }
                }
            });
        }
        for (auto& thread : threads) thread.join();
    }'''
if cpp.count(old) != 1:
    raise SystemExit('SPLITDEMOSAIC1A JNI loop anchor count=' + str(cpp.count(old)))
cpp = cpp.replace(old, new, 1)
CPP.write_text(cpp)
print('SPLITDEMOSAIC1A applied: frozen neutral MHC split into green + R/B passes; Sharp disabled')
