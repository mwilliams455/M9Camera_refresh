#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <random>
#include <vector>

static inline void storeArgbAsRgba8888(uint8_t* d, int32_t argb) {
    uint32_t u = static_cast<uint32_t>(argb);
    d[0] = static_cast<uint8_t>((u >> 16) & 0xffu);
    d[1] = static_cast<uint8_t>((u >> 8) & 0xffu);
    d[2] = static_cast<uint8_t>(u & 0xffu);
    d[3] = static_cast<uint8_t>((u >> 24) & 0xffu);
}
static uint32_t loadArgbFromRgba(const uint8_t* p) {
    return (uint32_t(p[3])<<24)|(uint32_t(p[0])<<16)|(uint32_t(p[1])<<8)|uint32_t(p[2]);
}

static std::vector<uint32_t> oldCompose(const std::vector<uint32_t>& src,int w,int h,int br,int rot){
    int ow=(rot==90||rot==270)?h:w, oh=(rot==90||rot==270)?w:h;
    std::vector<uint32_t> out(size_t(ow)*oh,0), local;
    for(int y0=0;y0<h;y0+=br){
        int rows=std::min(br,h-y0); local.assign(size_t(rows)*w,0);
        for(int y=0;y<rows;y++) for(int x=0;x<w;x++){
            auto v=src[size_t(y0+y)*w+x]; size_t idx;
            if(rot==90) idx=size_t(x)*rows+(rows-1-y);
            else if(rot==180) idx=size_t(rows-1-y)*w+(w-1-x);
            else if(rot==270) idx=size_t(w-1-x)*rows+y;
            else idx=size_t(y)*w+x;
            local[idx]=v;
        }
        if(rot==90){int dx0=h-(y0+rows); for(int y=0;y<w;y++)for(int x=0;x<rows;x++)out[size_t(y)*ow+dx0+x]=local[size_t(y)*rows+x];}
        else if(rot==270){int dx0=y0; for(int y=0;y<w;y++)for(int x=0;x<rows;x++)out[size_t(y)*ow+dx0+x]=local[size_t(y)*rows+x];}
        else if(rot==180){int dy0=h-(y0+rows); for(int y=0;y<rows;y++)for(int x=0;x<w;x++)out[size_t(dy0+y)*ow+x]=local[size_t(y)*w+x];}
        else {for(int y=0;y<rows;y++)for(int x=0;x<w;x++)out[size_t(y0+y)*ow+x]=local[size_t(y)*w+x];}
    }
    return out;
}

static std::vector<uint32_t> directCompose(const std::vector<uint32_t>& src,int w,int h,int br,int rot){
    int ow=(rot==90||rot==270)?h:w, oh=(rot==90||rot==270)?w:h;
    uint32_t stride=uint32_t(ow*4+((ow%3)==0?16:0));
    std::vector<uint8_t> bytes(size_t(stride)*oh,0x5a);
    for(int y0=0;y0<h;y0+=br){int rows=std::min(br,h-y0);
        for(int y=0;y<rows;y++){int gy=y0+y; for(int x=0;x<w;x++){
            int dx,dy; if(rot==90){dx=h-1-gy;dy=x;} else if(rot==180){dx=w-1-x;dy=h-1-gy;} else if(rot==270){dx=gy;dy=w-1-x;} else {dx=x;dy=gy;}
            storeArgbAsRgba8888(bytes.data()+size_t(dy)*stride+size_t(dx)*4, static_cast<int32_t>(src[size_t(gy)*w+x]));
        }}
    }
    std::vector<uint32_t> out(size_t(ow)*oh);
    for(int y=0;y<oh;y++)for(int x=0;x<ow;x++)out[size_t(y)*ow+x]=loadArgbFromRgba(bytes.data()+size_t(y)*stride+size_t(x)*4);
    return out;
}
int main(){
    std::mt19937_64 rng(0x9b17d1aULL); long long cases=0;
    for(int w=1;w<=19;w++)for(int h=1;h<=17;h++)for(int br=1;br<=9;br++)for(int rot: {0,90,180,270}){
        std::vector<uint32_t> src(size_t(w)*h); for(auto& v:src)v=uint32_t(rng());
        if(oldCompose(src,w,h,br,rot)!=directCompose(src,w,h,br,rot)){std::cerr<<"mismatch\n"; return 1;} cases++;
    }
    std::cout << "PERF3I BITMAPDIRECT1A exact mapping/packing parity PASS cases=" << cases << "\n";
}
