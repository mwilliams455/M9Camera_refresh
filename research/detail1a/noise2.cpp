// DETAIL1E offline mobile adaptation. Wide signed colour differences, fixed green.
// Modes 1..3, luma disabled. Not a complete Blackfin machine emulation.
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <vector>
static int64_t floor_div(int64_t v,int64_t n){return v>=0?v/n:-((-v+n-1)/n);}
static int32_t filter_round(int64_t v,int divisor,int rounding){
    int64_t q=floor_div(v,divisor),r=v-q*divisor;
    if(rounding && (r*2>divisor || (r*2==divisor && (rounding==2 || q%2!=0))))++q;
    return static_cast<int32_t>(q);
}
extern "C" void noise2_blend(const int32_t* c,const int32_t* m,const uint16_t* g,int n,
        const uint8_t* lut,int shift,int qshift,int32_t* out,uint64_t* counts){
    int64_t threshold=int64_t(1)<<shift,Q=int64_t(1)<<qshift;
    for(int i=0;i<n;i++){
        int64_t v=(std::llabs(int64_t(c[i])-m[i])*lut[g[i]>>6])/16,r;
        if(v<threshold){r=floor_div(v*c[i]+(threshold-v)*m[i],threshold);if(counts)counts[0]++;}
        else {int64_t z=v/threshold;if(z<Q){r=floor_div((Q-z)*c[i],Q);if(counts)counts[1]++;}
            else {r=0;if(counts)counts[2]++;}}
        out[i]=static_cast<int32_t>(r);
    }
}
extern "C" void noise2_filter(const int32_t* c,const uint16_t* green,int w,int h,int cfa,
        int mode,int rounding,const uint8_t* lut,int shift,int qshift,int32_t* smooth,int32_t* out,uint64_t* counts){
    static const int weights[3][7]={{1,2,1,0,0,0,0},{1,2,2,2,1,0,0},{1,2,3,4,3,2,1}};
    const int divisor=mode==1?4:mode==2?8:16,rad=mode*2,border=3+rad,taps=2*mode+1;
    const int round=mode==2?rounding:0,rx=(cfa==1||cfa==3),ry=(cfa==2||cfa==3);
    std::vector<int32_t> horizontal(w*h,0);
    std::memcpy(out,c,w*h*sizeof(int32_t));std::memcpy(smooth,c,w*h*sizeof(int32_t));
    for(int y=3;y<h-3;y++)for(int x=border;x<w-border;x++){
        if(((x&1)==rx)!=((y&1)==ry))continue;
        int64_t sum=0;for(int k=0;k<taps;k++)sum+=int64_t(weights[mode-1][k])*c[y*w+x+2*k-rad];
        horizontal[y*w+x]=filter_round(sum,divisor,round);
    }
    for(int y=border;y<h-border;y++)for(int x=border;x<w-border;x++){
        if(((x&1)==rx)!=((y&1)==ry))continue;
        int i=y*w+x;int64_t sum=0;
        for(int k=0;k<taps;k++)sum+=int64_t(weights[mode-1][k])*horizontal[(y+2*k-rad)*w+x];
        smooth[i]=filter_round(sum,divisor,round);
        noise2_blend(c+i,smooth+i,green+i,1,lut,shift,qshift,out+i,counts);
    }
}
