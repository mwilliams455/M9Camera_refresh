#include <cstdio>
#include <cstdint>
#include <vector>
#include <array>
#include "../payload/app/src/main/cpp/m9color_jni.cpp"

static uint64_t fnv32(uint64_t h, uint32_t v){for(int i=0;i<4;i++){h^=(v>>(i*8))&255u;h*=0x100000001b3ULL;}return h;}
static uint64_t fnv64(uint64_t h, uint64_t v){for(int i=0;i<8;i++){h^=(v>>(i*8))&255u;h*=0x100000001b3ULL;}return h;}
int main(){
    constexpr int HD=90,SD=30,WIDTH=257,ROWS=97,PIXELS=WIDTH*ROWS;
    ColorContext ctx;ctx.hueDivisions=HD;ctx.satDivisions=SD;ctx.cw={.78,.92,.84};ctx.camToPp={1.15,-.08,-.02,-.04,1.07,-.03,.01,-.09,1.12};ctx.ppToM9={1.04,-.08,.03,-.05,1.08,-.02,.02,-.12,1.10};
    ctx.hsm.resize(HD*SD*3);for(int i=0;i<HD*SD;i++){ctx.hsm[i*3]=-25.0+((i*37)%3600)/100.0;ctx.hsm[i*3+1]=.75+((i*53)%600)/1000.0;ctx.hsm[i*3+2]=.8+((i*97)%400)/1000.0;}
    for(int i=0;i<2048;i++)ctx.curve[i]=static_cast<uint8_t>(std::min(255,(i*255+1023)/2047));
    std::vector<jshort> cam(PIXELS*3);uint32_t state=0x13579bdfu;for(auto &v:cam){state=state*1664525u+1013904223u;v=static_cast<jshort>((state>>8)&0xffffu);}std::vector<jint> out(PIXELS);
    const double scenarios[][3]={{.83,1,1},{1.2212466,.875,.92},{1.87,.75,.84},{2.35,.9375,.96}};uint64_t aggregate=0xcbf29ce484222325ULL;
    for(int k=0;k<4;k++){int64_t stats[3]{};renderStripScalar(ctx,cam.data(),PIXELS,WIDTH,out.data(),scenarios[k][0],scenarios[k][1],scenarios[k][2],stats);uint64_t h=0xcbf29ce484222325ULL;for(jint v:out)h=fnv32(h,static_cast<uint32_t>(v));h=fnv64(h,static_cast<uint64_t>(stats[0]));h=fnv64(h,static_cast<uint64_t>(stats[1]));h=fnv64(h,static_cast<uint64_t>(stats[2]));std::printf("case%d hash=%016llx even=%lld edge=%lld nearWhite=%lld\n",k,(unsigned long long)h,(long long)stats[0],(long long)stats[1],(long long)stats[2]);aggregate=fnv64(aggregate,h);}
    std::printf("aggregate=%016llx pixels=%d cases=4\n",(unsigned long long)aggregate,PIXELS);return 0;
}
