#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>
static uint64_t mix(uint64_t h, uint64_t v){h^=v; return h*1099511628211ULL;}
int main(){
    const int width=257,height=193,pixels=width*height,wl=1023;
    const std::array<float,4> black={64.0f,65.0f,63.0f,64.0f};
    std::vector<uint64_t> hist((size_t)4*wl,0); std::vector<uint16_t> out(pixels); uint64_t clipped=0;
    for(int y=0;y<height;y++){
        int row=y*width,py=y&1;
        for(int x=0;x<width;x++){
            int i=row+x,plane=py*2+(x&1);
            uint16_t rv=(uint16_t)((i*73 + y*19 + x*7 + ((unsigned)i>>3)) % 1300);
            if(rv>=wl) ++clipped; else ++hist[(size_t)plane*wl+rv];
            float bl=black[(size_t)plane];
            float denomRaw=(float)wl-bl; float denom=1.0f>denomRaw?1.0f:denomRaw;
            float v=((float)rv-bl)/denom; if(v<0.0f)v=0.0f; if(v>1.0f)v=1.0f;
            float scaled=v*65535.0f+0.5f; int nv=(int)std::floor((double)scaled); out[(size_t)i]=(uint16_t)nv;
        }
    }
    uint64_t h=1469598103934665603ULL;
    for(auto q:out)h=mix(h,q); h=mix(h,clipped); for(auto q:hist)h=mix(h,q);
    std::printf("normnative1a cpp checksum=%016llx clipped=%llu pixels=%d\n",(unsigned long long)h,(unsigned long long)clipped,pixels);
}
