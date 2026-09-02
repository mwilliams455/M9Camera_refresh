#include <cstdint>
#include <cstring>
#include <iostream>
#include <random>
#include <vector>
#include <cmath>
#include "../payload/app/src/main/cpp/m9color_jni.cpp"

static ColorContext makeContext() {
    ColorContext c;
    c.cw={1,1,1}; c.camToPp={1,0,0,0,1,0,0,0,1}; c.ppToM9={1,0,0,0,1,0,0,0,1};
    c.adapt50To65={1,0,0,0,1,0,0,0,1}; c.ppToXyz={1,0,0,0,1,0,0,0,1}; c.xyz2Srgb={1,0,0,0,1,0,0,0,1};
    c.hueDivisions=6; c.satDivisions=2; c.hsm.resize(36);
    for(int h=0;h<6;++h)for(int s=0;s<2;++s){size_t i=(h*2+s)*3;c.hsm[i]=0;c.hsm[i+1]=1;c.hsm[i+2]=1;}
    for(int i=0;i<2048;++i)c.curve[i]=static_cast<uint8_t>((i*255+1023)/2047);
    return c;
}
int main(){
    std::mt19937_64 rng(0x20D1EC7ULL); ColorContext ctx=makeContext(); int cases=0;
    for(int w:{3,8,17,31}) for(int h:{2,5,9}) {
        int pixels=w*h; std::vector<uint16_t> storage(static_cast<size_t>(pixels)*3u);
        for(auto&v:storage)v=static_cast<uint16_t>(rng());
        std::vector<jshort> copied(storage.size()); std::memcpy(copied.data(),storage.data(),storage.size()*2);
        const jshort* direct=reinterpret_cast<const jshort*>(storage.data());
        std::vector<double> rw(h),cw(w); for(int y=0;y<h;++y)rw[y]=1.0+0.01*y;for(int x=0;x<w;++x)cw[x]=1.0+0.02*x;
        double a[3]{},b[3]{}; int64_t ta[8]{},tb[8]{};
        meterTc20WeightedSelectScalar(ctx,copied.data(),pixels,w,h,rw.data(),cw.data(),a,ta);
        meterTc20WeightedSelectScalar(ctx,direct,pixels,w,h,rw.data(),cw.data(),b,tb);
        for(int i=0;i<3;++i) if (std::memcmp(&a[i],&b[i],sizeof(double))!=0) {std::cerr<<"FAIL stats "<<w<<"x"<<h<<" i="<<i<<"\n";return 1;}
        ++cases;
    }
    std::cout<<"PERF3H CVDIRECT1A TC20 direct-input parity PASS "<<cases<<" cases\n"; return 0;
}
