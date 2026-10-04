// M9NOISEPERF1A_PARALLEL8
// Performance-only parallelization of NOISECANCEL1B_DECOUPLED_AMAZE_CHROMA.
// Pixel math, confidence gates, Camera2 noise authority and green-channel policy
// are frozen. Disjoint output row bands use preloaded boundary rows so no worker
// can observe a neighbour worker's already-filtered output.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <thread>
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

struct Nc1bAccum {
    uint64_t changed=0,changedR=0,changedB=0,considered=0,censored=0;
    double blendSum=0.0,maxCorrection=0.0,sigmaSum=0.0;
};
struct Nc1bRows {
    std::vector<uint16_t> prev,cur,next,out,boundaryAfter;
    explicit Nc1bRows(size_t n):prev(n),cur(n),next(n),out(n),boundaryAfter(n){}
};

static inline void nc1b_process_row(const uint16_t* prev,const uint16_t* cur,
        const uint16_t* next,uint16_t* out,int w,int h,int y,
        const double* profile,const double* gains,int mw,int mh,double scale,Nc1bAccum& a){
    auto chroma=[&](const uint16_t* row,int x,int ch){return int(row[3*x+ch])-int(row[3*x+1]);};
    for(int x=1;x<w-1;x++){
        const int r=cur[3*x],g=cur[3*x+1],b=cur[3*x+2];
        if(r<=8||g<=8||b<=8||r>=65527||g>=65527||b>=65527){a.censored++;continue;}
        const int gu=prev[3*x+1],gd=next[3*x+1],gl=cur[3*(x-1)+1],gr=cur[3*(x+1)+1];
        const int grad=std::max({std::abs(g-gu),std::abs(g-gd),std::abs(g-gl),std::abs(g-gr)});
        const double sg=nc1b_sigma(g/65535.0,profile[2],profile[3],
                .5*(nc1b_gain(gains,mw,mh,w,h,x,y,1)+nc1b_gain(gains,mw,mh,w,h,x,y,2)),scale);
        const double sr=nc1b_sigma(r/65535.0,profile[0],profile[1],nc1b_gain(gains,mw,mh,w,h,x,y,0),scale);
        const double sb=nc1b_sigma(b/65535.0,profile[4],profile[5],nc1b_gain(gains,mw,mh,w,h,x,y,3),scale);
        const double scr=std::sqrt(sr*sr+sg*sg),scb=std::sqrt(sb*sb+sg*sg);
        a.sigmaSum+=.5*(scr+scb);a.considered++;
        const double quiet=nc1b_unit(1.0-grad/std::max(3.0*sg+24.0,1.0));
        if(quiet<=.65)continue;

        const int cr0=r-g, cb0=b-g;
        const int crMed=nc1b_median5(cr0,chroma(prev,x,0),chroma(next,x,0),
                chroma(cur,x-1,0),chroma(cur,x+1,0));
        const int cbMed=nc1b_median5(cb0,chroma(prev,x,2),chroma(next,x,2),
                chroma(cur,x-1,2),chroma(cur,x+1,2));
        const int crSpread=std::max({std::abs(chroma(prev,x,0)-crMed),std::abs(chroma(next,x,0)-crMed),
                std::abs(chroma(cur,x-1,0)-crMed),std::abs(chroma(cur,x+1,0)-crMed)});
        const int cbSpread=std::max({std::abs(chroma(prev,x,2)-cbMed),std::abs(chroma(next,x,2)-cbMed),
                std::abs(chroma(cur,x-1,2)-cbMed),std::abs(chroma(cur,x+1,2)-cbMed)});

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
                out[3*x+ch]=uint16_t(nv);a.changed++;channelChanged++;
                a.maxCorrection=std::max(a.maxCorrection,double(std::abs(nv-old)));a.blendSum+=blend;
            }
        };
        filter(0,cr0,crMed,crSpread,scr,a.changedR);
        filter(2,cb0,cbMed,cbSpread,scb,a.changedB);
    }
}

static bool nc1b_validate(uint16_t* rgb,int w,int h,const double* profile,
        const double* gains,int mw,int mh,double scale,double* stats){
    if(!rgb||!profile||!gains||!stats||w<8||h<8||w>8192||h>8192||
       mw<1||mh<1||mw>256||mh>256||!std::isfinite(scale)||scale<=0)return false;
    for(int i=0;i<6;i++)if(!std::isfinite(profile[i])||profile[i]<0||profile[i]>1)return false;
    for(int i=0;i<mw*mh*4;i++)if(!std::isfinite(gains[i])||gains[i]<=0||gains[i]>scale*(1.000000000001))return false;
    return true;
}
static void nc1b_finish_stats(double* stats,const Nc1bAccum& a,double elapsedMs,int workers){
    std::fill(stats,stats+14,0.0);
    stats[0]=1.0;stats[1]=double(a.changed);stats[2]=double(a.changedR);stats[3]=double(a.changedB);
    stats[4]=a.maxCorrection;stats[5]=a.changed?a.blendSum/a.changed:0.0;stats[6]=double(a.censored);
    stats[7]=double(a.considered);stats[8]=a.considered?a.sigmaSum/a.considered:0.0;stats[9]=elapsedMs;
    stats[10]=0.65;stats[11]=0.50;stats[12]=double(workers);stats[13]=1.0;
}

static void nc1b_process_band(uint16_t* rgb,int w,int h,int startY,int endY,
        const double* profile,const double* gains,int mw,int mh,double scale,
        Nc1bRows& rows,Nc1bAccum& acc){
    const size_t rowSamples=size_t(w)*3;
    const size_t rowBytes=rowSamples*sizeof(uint16_t);
    for(int y=startY;y<endY;y++){
        if(y+1==endY)std::memcpy(rows.next.data(),rows.boundaryAfter.data(),rowBytes);
        else std::memcpy(rows.next.data(),rgb+size_t(y+1)*rowSamples,rowBytes);
        std::memcpy(rows.out.data(),rows.cur.data(),rowBytes);
        nc1b_process_row(rows.prev.data(),rows.cur.data(),rows.next.data(),rows.out.data(),
                w,h,y,profile,gains,mw,mh,scale,acc);
        std::memcpy(rgb+size_t(y)*rowSamples,rows.out.data(),rowBytes);
        rows.prev.swap(rows.cur);
        rows.cur.swap(rows.next);
    }
}

extern "C" int m9_noisecancel1b_apply(uint16_t* rgb,int w,int h,
        const double* profile,const double* gains,int mw,int mh,double scale,double* stats){
    if(!nc1b_validate(rgb,w,h,profile,gains,mw,mh,scale,stats))return -1;
    const auto started=std::chrono::steady_clock::now();
    const int innerRows=h-2;
    const int workers=(innerRows>=256)?std::min(8,innerRows):1;
    if(workers==1){
        const size_t rowSamples=size_t(w)*3,rowBytes=rowSamples*sizeof(uint16_t);
        Nc1bRows rows(rowSamples);Nc1bAccum a;
        std::memcpy(rows.prev.data(),rgb,rowBytes);
        std::memcpy(rows.cur.data(),rgb+rowSamples,rowBytes);
        std::memcpy(rows.boundaryAfter.data(),rgb+size_t(h-1)*rowSamples,rowBytes);
        nc1b_process_band(rgb,w,h,1,h-1,profile,gains,mw,mh,scale,rows,a);
        nc1b_finish_stats(stats,a,std::chrono::duration<double,std::milli>(
                std::chrono::steady_clock::now()-started).count(),1);
        return 0;
    }

    const size_t rowSamples=size_t(w)*3,rowBytes=rowSamples*sizeof(uint16_t);
    std::vector<Nc1bRows> rows;rows.reserve(workers);
    std::vector<Nc1bAccum> acc(workers);
    std::vector<int> starts(workers),ends(workers);
    for(int i=0;i<workers;i++){
        const int s=1+(innerRows*i)/workers;
        const int e=1+(innerRows*(i+1))/workers;
        starts[i]=s;ends[i]=e;rows.emplace_back(rowSamples);
        // All neighbour rows that cross a worker boundary are snapshotted before
        // any worker starts writing. This is the exact-parity race barrier.
        std::memcpy(rows[i].prev.data(),rgb+size_t(s-1)*rowSamples,rowBytes);
        std::memcpy(rows[i].cur.data(),rgb+size_t(s)*rowSamples,rowBytes);
        std::memcpy(rows[i].boundaryAfter.data(),rgb+size_t(e)*rowSamples,rowBytes);
    }

    std::vector<std::thread> threads;threads.reserve(workers);
    for(int i=0;i<workers;i++)threads.emplace_back([&,i]{
        nc1b_process_band(rgb,w,h,starts[i],ends[i],profile,gains,mw,mh,scale,rows[i],acc[i]);
    });
    for(auto& t:threads)t.join();

    Nc1bAccum total;
    for(int i=0;i<workers;i++){
        total.changed+=acc[i].changed;total.changedR+=acc[i].changedR;total.changedB+=acc[i].changedB;
        total.considered+=acc[i].considered;total.censored+=acc[i].censored;
        total.blendSum+=acc[i].blendSum;total.sigmaSum+=acc[i].sigmaSum;
        total.maxCorrection=std::max(total.maxCorrection,acc[i].maxCorrection);
    }
    nc1b_finish_stats(stats,total,std::chrono::duration<double,std::milli>(
            std::chrono::steady_clock::now()-started).count(),workers);
    return 0;
}

#ifdef M9NOISEPERF1A_HOST
// Frozen 1.86 scalar implementation for exact output parity testing only.
extern "C" int m9_noisecancel1b_apply_scalar_reference(uint16_t* rgb,int w,int h,
        const double* profile,const double* gains,int mw,int mh,double scale,double* stats){
    if(!nc1b_validate(rgb,w,h,profile,gains,mw,mh,scale,stats))return -1;
    const auto started=std::chrono::steady_clock::now();
    const size_t rowSamples=size_t(w)*3,rowBytes=rowSamples*sizeof(uint16_t);
    std::vector<uint16_t> prev(rowSamples),cur(rowSamples),next(rowSamples),out(rowSamples);
    std::memcpy(prev.data(),rgb,rowBytes);
    std::memcpy(cur.data(),rgb+rowSamples,rowBytes);
    std::memcpy(next.data(),rgb+2*rowSamples,rowBytes);
    Nc1bAccum a;
    for(int y=1;y<h-1;y++){
        if(y+1<h)std::memcpy(next.data(),rgb+size_t(y+1)*rowSamples,rowBytes);
        std::memcpy(out.data(),cur.data(),rowBytes);
        nc1b_process_row(prev.data(),cur.data(),next.data(),out.data(),w,h,y,
                profile,gains,mw,mh,scale,a);
        std::memcpy(rgb+size_t(y)*rowSamples,out.data(),rowBytes);
        prev.swap(cur);cur.swap(next);
    }
    nc1b_finish_stats(stats,a,std::chrono::duration<double,std::milli>(
            std::chrono::steady_clock::now()-started).count(),1);
    stats[13]=0.0;
    return 0;
}
#endif

extern "C" const char* m9_noisecancel1b_revision(){return "M9NOISEPERF1A_PARALLEL8_EXACT";}

#ifndef M9NOISEPERF1A_HOST
#include <jni.h>
extern "C" JNIEXPORT jint JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9NoiseCancel1B_applyNative(JNIEnv* env,jclass,
        jobject rgb,jint w,jint h,jdoubleArray profile,jdoubleArray gains,jint mw,jint mh,
        jdouble scale,jdoubleArray stats){
    if(!rgb||!profile||!gains||!stats||env->GetArrayLength(profile)<6||
       env->GetArrayLength(gains)<jlong(mw)*mh*4||env->GetArrayLength(stats)<14)return -1;
    auto* p=static_cast<uint16_t*>(env->GetDirectBufferAddress(rgb));
    const jlong cap=env->GetDirectBufferCapacity(rgb);
    if(!p||cap<jlong(w)*h*6)return -1;
    jdouble* pr=env->GetDoubleArrayElements(profile,nullptr);
    jdouble* ga=env->GetDoubleArrayElements(gains,nullptr);
    jdouble out[14]={};
    if(!pr||!ga){if(pr)env->ReleaseDoubleArrayElements(profile,pr,JNI_ABORT);if(ga)env->ReleaseDoubleArrayElements(gains,ga,JNI_ABORT);return -2;}
    int rc=m9_noisecancel1b_apply(p,w,h,pr,ga,mw,mh,scale,out);
    env->ReleaseDoubleArrayElements(profile,pr,JNI_ABORT);
    env->ReleaseDoubleArrayElements(gains,ga,JNI_ABORT);
    if(rc==0)env->SetDoubleArrayRegion(stats,0,14,out);
    return rc;
}
#endif
