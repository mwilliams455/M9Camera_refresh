#include <algorithm>
#include <chrono>
#include <cstdint>
#include <vector>
#include "m9_sharpness_bank.h"
#ifndef M9_SHARP_HOST
#include <jni.h>
#endif

// Firmware kernel on the accepted AMaZE green signal. RGB transport below is
// an app adaptation, not a claim to reproduce Leica's complete reconstruction.
static int arshift(int v,int n) {return v>=0 ? v>>n : -(((-v)+(1<<n)-1)>>n);}
extern "C" int m9_sharp_coeff(int slot,int level,int residual) {
    if(slot<0||slot>=13||level<0||level>4||residual< -1024||residual>1024)return 0;
    if(level==0)return 0; // App Off: exact bypass, not LUT row0's quarter-strength transform.
    int v=M9_SHARP_BASE[slot][1024+residual];
    switch(M9_SHARP_MODES[level][slot]) {
        case 1:v=arshift(v,2);break; case 2:v=arshift(v,1);break;
        case 3:break; case 4:v*=2;break; case 5:v*=4;break;
        case 6:v=arshift(v,1)*3;break; case 7:v*=3;break;
        default:return 0;
    }
    return std::clamp(v,-2048,2048);
}
static uint16_t q14(uint16_t v) {return uint16_t((uint32_t(v)*16383u+32767u)/65535u);}
static int corrected(int a,int b,int c,int d,int e,int f,int g,int h,int i,int slot,int level) {
    int gaussian=(a+2*b+c+2*d+4*e+2*f+g+2*h+i)/16;
    return std::clamp(e+m9_sharp_coeff(slot,level,std::clamp(e-gaussian,-1024,1024)),0,16383);
}
extern "C" int m9_sharp_plane(const uint16_t* src,uint16_t* dst,int w,int h,int slot,int level,int border) {
    if(!src||!dst||src==dst||w<1||h<1||w>8192||h>8192||slot<0||slot>=13||level<0||level>4||border<2)return -1;
    std::copy(src,src+size_t(w)*h,dst);
    if(level==0)return 0;
    for(int y=border;y<h-border;y++)for(int x=border;x<w-border;x++) {
        size_t p=size_t(y)*w+x;
        dst[p]=uint16_t(corrected(src[p-w-1],src[p-w],src[p-w+1],src[p-1],src[p],src[p+1],src[p+w-1],src[p+w],src[p+w+1],slot,level));
    }
    return 0;
}
// O(width) scratch; all source green neighbours are captured before row writes.
// A common rational gain preserves camera-RGB ratios up to half a 16-bit code.
// The brightest channel bounds the common gain, so no new channel clips arise.
extern "C" int m9_sharp_rgb(uint16_t* rgb,int w,int h,int slot,int level,double* stats) {
    if(!rgb||!stats||w<1||h<1||w>8192||h>8192||slot<0||slot>=13||level<0||level>4)return -1;
    std::fill(stats,stats+7,0.);
    auto start=std::chrono::steady_clock::now();
    if(level==0)return 0;
    constexpr int border=18; // accepted AMaZE/MHC boundary 16 + recovered Sharp support 2
    if(w<=2*border||h<=2*border)return 0;
    try {
        std::vector<uint16_t> prev(w),cur(w),next(w);
        auto row=[&](int y,std::vector<uint16_t>& dst){for(int x=0;x<w;x++)dst[x]=q14(rgb[3*(size_t(y)*w+x)+1]);};
        row(border-1,prev);row(border,cur);
        for(int y=border;y<h-border;y++) {
            row(y+1,next);
            for(int x=border;x<w-border;x++) {
                stats[0]++;
                int e=cur[x];
                int s=corrected(prev[x-1],prev[x],prev[x+1],cur[x-1],e,cur[x+1],next[x-1],next[x],next[x+1],slot,level);
                if(s==e||e==0)continue;
                auto* p=rgb+3*(size_t(y)*w+x);
                uint64_t num=uint64_t(s),den=uint64_t(e);
                int peak=std::max({int(p[0]),int(p[1]),int(p[2])});
                if(num*uint64_t(peak)>uint64_t(65535)*den) {num=65535;den=uint64_t(peak);stats[2]++;}
                bool changed=false;
                for(int c=0;c<3;c++) {
                    uint16_t v=uint16_t((uint64_t(p[c])*num+den/2)/den);
                    stats[3]=std::max(stats[3],double(std::abs(int(v)-int(p[c]))));
                    changed|=v!=p[c];p[c]=v;
                }
                stats[1]+=changed;
            }
            prev.swap(cur);cur.swap(next);
        }
        stats[4]=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        stats[5]=double(size_t(w)*3*sizeof(uint16_t));stats[6]=border;
    }catch(...){return -30;}
    return 0;
}
#ifndef M9_SHARP_HOST
extern "C" JNIEXPORT jint JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9SharpnessStage_applyNative(JNIEnv* env,jclass,
 jlong address,jint w,jint h,jint slot,jint level,jdoubleArray output) {
    if(!address||!output||env->GetArrayLength(output)<7)return -1;
    double stats[7]={};
    int rc=m9_sharp_rgb(reinterpret_cast<uint16_t*>(address),w,h,slot,level,stats);
    if(rc==0)env->SetDoubleArrayRegion(output,0,7,stats);
    return env->ExceptionCheck()?-3:rc;
}
#endif
