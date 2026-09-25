// NOISECANCEL1B_DECOUPLED: chroma-only quiet-region cancellation on the
// accepted AMaZE camera-RGB result. Independent of DETAIL/sharpness.
// Green samples are never written. Camera2 SENSOR_NOISE_PROFILE remains the
// noise authority; lens-shading transport scales the local variance estimate.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

static inline double nc1b_unit(double x){return std::clamp(x,0.0,1.0);}
static inline double nc1b_smoothstep(double x){x=nc1b_unit(x);return x*x*(3.0-2.0*x);}
static inline int nc1b_median5(int a,int b,int c,int d,int e){
    int v[5]={a,b,c,d,e};
    for(int i=1;i<5;i++){int x=v[i],j=i-1;while(j>=0&&v[j]>x){v[j+1]=v[j];j--;}v[j+1]=x;}
    return v[2];
}
static inline double nc1b_gain(const double* gains,int mw,int mh,int w,int h,int x,int y,int p){
    const double gx=(w>1)?x*((mw-1.0)/(w-1.0)):0.0;
    const double gy=(h>1)?y*((mh-1.0)/(h-1.0)):0.0;
    const int x0=int(std::floor(gx)),y0=int(std::floor(gy));
    const int x1=std::min(mw-1,x0+1),y1=std::min(mh-1,y0+1);
    const double fx=gx-x0,fy=gy-y0;
    auto at=[&](int yy,int xx){return gains[(yy*mw+xx)*4+p];};
    const double a=at(y0,x0)+fx*(at(y0,x1)-at(y0,x0));
    const double b=at(y1,x0)+fx*(at(y1,x1)-at(y1,x0));
    return a+fy*(b-a);
}
static inline double nc1b_sigma(double signal,double a,double b,double gain,double scale){
    const double v=std::max(0.0,a*nc1b_unit(signal)+b);
    return std::sqrt(v)*65535.0*(gain/std::max(scale,1e-12));
}

extern "C" int m9_noisecancel1b_apply(uint16_t* rgb,int w,int h,
        const double* profile,const double* gains,int mw,int mh,double scale,double* stats){
    if(!rgb||!profile||!gains||!stats||w<8||h<8||w>8192||h>8192||
       mw<1||mh<1||mw>256||mh>256||!std::isfinite(scale)||scale<=0)return -1;
    for(int i=0;i<6;i++)if(!std::isfinite(profile[i])||profile[i]<0||profile[i]>1)return -1;
    for(int i=0;i<mw*mh*4;i++)if(!std::isfinite(gains[i])||gains[i]<=0||gains[i]>scale*(1.000000000001))return -1;
    std::fill(stats,stats+12,0.0);
    const auto started=std::chrono::steady_clock::now();
    const size_t rowSamples=size_t(w)*3;
    std::vector<uint16_t> prev(rowSamples),cur(rowSamples),next(rowSamples),out(rowSamples);
    std::memcpy(prev.data(),rgb,rowSamples*sizeof(uint16_t));
    std::memcpy(cur.data(),rgb+rowSamples,rowSamples*sizeof(uint16_t));
    std::memcpy(next.data(),rgb+2*rowSamples,rowSamples*sizeof(uint16_t));
    uint64_t changed=0,changedR=0,changedB=0,considered=0,censored=0;
    double blendSum=0.0,maxCorrection=0.0,sigmaSum=0.0;
    auto chroma=[&](const uint16_t* row,int x,int ch){return int(row[3*x+ch])-int(row[3*x+1]);};
    for(int y=1;y<h-1;y++){
        if(y+1<h)std::memcpy(next.data(),rgb+size_t(y+1)*rowSamples,rowSamples*sizeof(uint16_t));
        std::memcpy(out.data(),cur.data(),rowSamples*sizeof(uint16_t));
        for(int x=1;x<w-1;x++){
            const int r=cur[3*x],g=cur[3*x+1],b=cur[3*x+2];
            if(r<=8||g<=8||b<=8||r>=65527||g>=65527||b>=65527){censored++;continue;}
            const int gu=prev[3*x+1],gd=next[3*x+1],gl=cur[3*(x-1)+1],gr=cur[3*(x+1)+1];
            const int grad=std::max({std::abs(g-gu),std::abs(g-gd),std::abs(g-gl),std::abs(g-gr)});
            const double sg=nc1b_sigma(g/65535.0,profile[2],profile[3],
                    .5*(nc1b_gain(gains,mw,mh,w,h,x,y,1)+nc1b_gain(gains,mw,mh,w,h,x,y,2)),scale);
            const double sr=nc1b_sigma(r/65535.0,profile[0],profile[1],nc1b_gain(gains,mw,mh,w,h,x,y,0),scale);
            const double sb=nc1b_sigma(b/65535.0,profile[4],profile[5],nc1b_gain(gains,mw,mh,w,h,x,y,3),scale);
            const double scr=std::sqrt(sr*sr+sg*sg),scb=std::sqrt(sb*sb+sg*sg);
            sigmaSum+=.5*(scr+scb);considered++;
            const double quiet=nc1b_unit(1.0-grad/std::max(3.0*sg+24.0,1.0));
            if(quiet<=.65)continue;

            const int cr0=r-g, cb0=b-g;
            const int crMed=nc1b_median5(cr0,chroma(prev.data(),x,0),chroma(next.data(),x,0),
                    chroma(cur.data(),x-1,0),chroma(cur.data(),x+1,0));
            const int cbMed=nc1b_median5(cb0,chroma(prev.data(),x,2),chroma(next.data(),x,2),
                    chroma(cur.data(),x-1,2),chroma(cur.data(),x+1,2));
            const int crSpread=std::max({std::abs(chroma(prev.data(),x,0)-crMed),std::abs(chroma(next.data(),x,0)-crMed),
                    std::abs(chroma(cur.data(),x-1,0)-crMed),std::abs(chroma(cur.data(),x+1,0)-crMed)});
            const int cbSpread=std::max({std::abs(chroma(prev.data(),x,2)-cbMed),std::abs(chroma(next.data(),x,2)-cbMed),
                    std::abs(chroma(cur.data(),x-1,2)-cbMed),std::abs(chroma(cur.data(),x+1,2)-cbMed)});

            auto filter=[&](int ch,int base,int med,int spread,double sigma,uint64_t& channelChanged){
                if(spread>6.0*sigma+64.0)return;
                const int delta=med-base;
                if(delta==0)return;
                const double residual=nc1b_unit(1.0-std::abs(delta)/std::max(3.0*sigma+24.0,1.0));
                const double confidence=quiet*residual;
                if(confidence<=.65)return;
                const double gate=nc1b_smoothstep((confidence-.65)/.25);
                const double blend=.50*gate;
                if(blend<=0)return;
                const int moved=int(std::llround(base+blend*delta));
                const int nv=std::clamp(g+moved,0,65535);
                const int old=cur[3*x+ch];
                if(nv!=old){
                    out[3*x+ch]=uint16_t(nv);changed++;channelChanged++;
                    maxCorrection=std::max(maxCorrection,double(std::abs(nv-old)));blendSum+=blend;
                }
            };
            filter(0,cr0,crMed,crSpread,scr,changedR);
            filter(2,cb0,cbMed,cbSpread,scb,changedB);
        }
        // Green is copied byte-for-byte from cur and never modified above.
        std::memcpy(rgb+size_t(y)*rowSamples,out.data(),rowSamples*sizeof(uint16_t));
        prev.swap(cur);cur.swap(next);
    }
    stats[0]=1.0;stats[1]=double(changed);stats[2]=double(changedR);stats[3]=double(changedB);
    stats[4]=maxCorrection;stats[5]=changed?blendSum/changed:0.0;stats[6]=double(censored);
    stats[7]=double(considered);stats[8]=considered?sigmaSum/considered:0.0;stats[9]=0.0;
    stats[10]=0.65;stats[11]=0.50;
    stats[9]=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();
    return 0;
}

extern "C" const char* m9_noisecancel1b_revision(){return "M9NOISECANCEL1B_DECOUPLED_AMAZE_CHROMA";}

#ifndef M9NOISECANCEL1B_HOST
#include <jni.h>
extern "C" JNIEXPORT jint JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NoiseCancel1B_applyNative(JNIEnv* env,jclass,
        jobject rgb,jint w,jint h,jdoubleArray profile,jdoubleArray gains,jint mw,jint mh,
        jdouble scale,jdoubleArray stats){
    if(!rgb||!profile||!gains||!stats||env->GetArrayLength(profile)<6||
       env->GetArrayLength(gains)<jlong(mw)*mh*4||env->GetArrayLength(stats)<12)return -1;
    auto* p=static_cast<uint16_t*>(env->GetDirectBufferAddress(rgb));
    const jlong cap=env->GetDirectBufferCapacity(rgb);
    if(!p||cap<jlong(w)*h*6)return -1;
    jdouble* pr=env->GetDoubleArrayElements(profile,nullptr);
    jdouble* ga=env->GetDoubleArrayElements(gains,nullptr);
    jdouble out[12]={};
    if(!pr||!ga){if(pr)env->ReleaseDoubleArrayElements(profile,pr,JNI_ABORT);if(ga)env->ReleaseDoubleArrayElements(gains,ga,JNI_ABORT);return -2;}
    int rc=m9_noisecancel1b_apply(p,w,h,pr,ga,mw,mh,scale,out);
    env->ReleaseDoubleArrayElements(profile,pr,JNI_ABORT);
    env->ReleaseDoubleArrayElements(gains,ga,JNI_ABORT);
    if(rc==0)env->SetDoubleArrayRegion(stats,0,12,out);
    return rc;
}
#endif
