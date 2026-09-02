#include <cstdint>
#include <cstring>
#include <iostream>
#include <random>
#include <vector>
#include "../payload/app/src/main/cpp/m9color_jni.cpp"

static ColorContext makeContext() {
    ColorContext c;
    c.cw = {1.0,1.0,1.0};
    c.camToPp = {1,0,0, 0,1,0, 0,0,1};
    c.ppToM9 = {1,0,0, 0,1,0, 0,0,1};
    c.hueDivisions = 6;
    c.satDivisions = 2;
    c.hsm.resize(static_cast<size_t>(c.hueDivisions*c.satDivisions*3));
    for (int h=0; h<c.hueDivisions; ++h) for (int s=0; s<c.satDivisions; ++s) {
        size_t i=static_cast<size_t>((h*c.satDivisions+s)*3);
        c.hsm[i]=0.0; c.hsm[i+1]=1.0; c.hsm[i+2]=1.0;
    }
    for (int i=0;i<2048;++i) c.curve[static_cast<size_t>(i)] = static_cast<uint8_t>((i*255 + 1023)/2047);
    return c;
}

int main() {
    std::mt19937_64 rng(0xC0BA17D1ULL);
    ColorContext ctx=makeContext();
    int cases=0;
    for (int width : {1,2,3,7,16,31,64}) {
        for (int fullRows : {1,2,5,17,63}) {
            const size_t scalars=static_cast<size_t>(width)*fullRows*3u;
            std::vector<uint16_t> storage(scalars);
            for (auto& v:storage) v=static_cast<uint16_t>(rng());
            const jshort* directBase=reinterpret_cast<const jshort*>(storage.data());
            for (int y0=0;y0<fullRows;++y0) {
                for (int rows=1;rows<=fullRows-y0;++rows) {
                    const int pixels=width*rows;
                    const size_t off=static_cast<size_t>(y0)*width*3u;
                    std::vector<jshort> copied(static_cast<size_t>(pixels)*3u);
                    std::memcpy(copied.data(), storage.data()+off, copied.size()*sizeof(jshort));
                    std::vector<jint> a(static_cast<size_t>(pixels)), b(static_cast<size_t>(pixels));
                    int64_t sa[3]{}, sb[3]{};
                    renderStripScalar(ctx, copied.data(), pixels, width, a.data(), 1.0, 1.0, 1.0, sa);
                    renderStripScalar(ctx, directBase+off, pixels, width, b.data(), 1.0, 1.0, 1.0, sb);
                    if (a!=b || sa[0]!=sb[0] || sa[1]!=sb[1] || sa[2]!=sb[2]) {
                        std::cerr << "FAIL width="<<width<<" fullRows="<<fullRows<<" y0="<<y0<<" rows="<<rows<<"\n";
                        return 1;
                    }
                    ++cases;
                }
            }
        }
    }
    // Explicit unsigned edge bit patterns used by CV_16U -> Java jshort representation.
    for (uint16_t v : {uint16_t(0),uint16_t(1),uint16_t(32767),uint16_t(32768),uint16_t(65534),uint16_t(65535)}) {
        jshort s; std::memcpy(&s,&v,sizeof(v));
        if (u16(s)!=v) { std::cerr<<"u16 reinterpret FAIL\n"; return 2; }
    }
    std::cout << "PERF3H CVDIRECT1A actual scalar-kernel input parity PASS " << cases << " block cases\n";
    return 0;
}
