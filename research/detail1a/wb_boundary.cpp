// Scalar arithmetic model of Process_WB ff6030d0, NOT a complete Blackfin emulator.
// Input spatial phases: 00 uses gain[0], 01/10 gain[1], 11 gain[2].
// Region/pointer traversal, packet gain normalization and pedestal provenance
// are deliberately outside this model. Never call this a phone implementation.
#include <algorithm>
#include <cstdint>
extern "C" void wb_boundary(const uint16_t* input,uint16_t* output,int n,
                            const uint16_t* gain,int pedestal) {
    // The firmware tests unity in this order and clears the region if none is
    // exactly Q14 unity. The selected phase group is left untouched.
    const int identity=gain[0]==16384?0:gain[1]==16384?1:gain[2]==16384?2:-1;
    for(int i=0;i<n;i++)for(int phase=0;phase<4;phase++) {
        const int channel=phase==0?0:phase==3?2:1;
        const int x=input[4*i+phase];
        if(identity<0){output[4*i+phase]=0;continue;}
        if(channel==identity){output[4*i+phase]=x;continue;}
        // Within the verified 14-bit input / uint16 gain / pedestal test range
        // this product fits signed 32-bit, so no multiply-overflow assumption.
        const int64_t product=int64_t(x-pedestal)*gain[channel];
        const int64_t shifted=product>=0?product/16384:-((-product+16383)/16384);
        output[4*i+phase]=std::clamp<int64_t>(pedestal+shifted,0,16383);
    }
}
