// Scoped BF547 gain-normalization tail, ab714..ab7ba plus abb36..abb76.
// Not the upstream WB estimator or a Blackfin emulator. Preserve even the
// 65536-to-uint16 wrap observed at the packet boundary; mobile must reject it.
#include <algorithm>
#include <cstdint>
static int32_t signed32(uint32_t v) {
    return v <= 0x7fffffffU ? int32_t(v) : int32_t(int64_t(v)-0x100000000LL);
}
static int32_t mul32(int32_t a,int32_t b) {
    return signed32(uint32_t(a)*uint32_t(b));
}
static int32_t asr14(int32_t a) {
    return a>=0?a/16384:-int32_t((-int64_t(a)+16383)/16384);
}
extern "C" void wb_gain_contract(const int32_t* input,uint16_t* output,int n) {
    for(int i=0;i<n;i++) {
        const int r=std::min(input[2*i],65536), b=std::min(input[2*i+1],65536);
        const int scale=(r>=16384 && b>=16384)?16384:268435456/std::min(r,b);
        // ff: left shift 14 followed by arithmetic right shift 14 sign-extends
        // the low 18 bits of the green scale, exactly as the instruction tail.
        int g=asr14(signed32(uint32_t(scale)<<14));
        int v[3]={asr14(mul32(r,scale)),g,asr14(mul32(b,scale))};
        for(int c=0;c<3;c++) {
            int z=std::clamp(v[c],16384,65536);
            uint16_t packet=uint16_t(z);
            if(packet==16383 || packet==16385)packet=16384;
            output[3*i+c]=packet;
        }
    }
}
