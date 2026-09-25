#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <thread>
#include <vector>
#include "m9color_jni.cpp"

extern "C" void* trial_colorperf_context(const double* a,const uint8_t* curve) {
    auto* q=new ColorContext();int p=0;
    for(double& x:q->cw)x=a[p++];
    for(auto* v:{&q->camToPp,&q->ppToM9,&q->adapt50To65,&q->ppToXyz,&q->xyz2Srgb})
        for(double& x:*v)x=a[p++];
    q->hsm={0,1,1,0,1,1,0,1,1,0,1,1};
    q->hueDivisions=2;q->satDivisions=2;
    q->skyChromaMode1A=9;
    std::copy(curve,curve+2048,q->curve.begin());
    return q;
}
extern "C" void trial_colorperf_destroy(void* ctx){delete static_cast<ColorContext*>(ctx);}

extern "C" int trial_colorperf_old(
        void* handle,const uint16_t* cam,int w,int h,int blockRows,double gain,double cb,double cr,
        int rotation,int workers,uint8_t* bitmap,uint32_t stride,int64_t* stats) {
    auto* ctx=static_cast<ColorContext*>(handle);
    if(!ctx||!cam||!bitmap||!stats||w<=0||h<=0||blockRows<=0||workers<=0)return -1;
    std::fill(stats,stats+12,0);
    std::vector<jint> argb(size_t(w)*std::min(h,blockRows));
    for(int blockY0=0;blockY0<h;blockY0+=blockRows){
        const int rows=std::min(blockRows,h-blockY0);
        const int workerCount=std::max(1,std::min(workers,rows));
        std::vector<std::array<int64_t,3>> ws(size_t(workerCount));
        std::vector<int64_t> renderNs(size_t(workerCount),0),orientNs(size_t(workerCount),0),combined(size_t(workerCount),0);
        std::vector<std::thread> ts;ts.reserve(size_t(workerCount));
        for(int worker=0;worker<workerCount;worker++){
            const int y0=(rows*worker)/workerCount,y1=(rows*(worker+1))/workerCount;
            ts.emplace_back([&,worker,y0,y1](){
                const auto a=std::chrono::steady_clock::now();
                const int localRows=y1-y0,localPixels=localRows*w;
                const size_t localOff=size_t(y0)*w;
                const size_t camOff=size_t(blockY0+y0)*w*3u;
                renderStripScalar(*ctx,reinterpret_cast<const jshort*>(cam)+camOff,localPixels,w,
                                  argb.data()+localOff,gain,cb,cr,ws[size_t(worker)].data());
                const auto b=std::chrono::steady_clock::now();
                writeCompletedSubrangeToBitmap(argb.data(),bitmap,stride,rows,w,blockY0,h,y0,y1,rotation);
                const auto e=std::chrono::steady_clock::now();
                renderNs[size_t(worker)]=std::chrono::duration_cast<std::chrono::nanoseconds>(b-a).count();
                orientNs[size_t(worker)]=std::chrono::duration_cast<std::chrono::nanoseconds>(e-b).count();
                combined[size_t(worker)]=std::chrono::duration_cast<std::chrono::nanoseconds>(e-a).count();
            });
        }
        for(auto& t:ts)t.join();
        int64_t blockMax=0;
        for(int worker=0;worker<workerCount;worker++){
            stats[0]+=ws[size_t(worker)][0];
            stats[1]+=ws[size_t(worker)][1];
            stats[2]+=ws[size_t(worker)][2];
            stats[3]+=renderNs[size_t(worker)];
            stats[9]+=orientNs[size_t(worker)];
            blockMax=std::max(blockMax,combined[size_t(worker)]);
        }
        stats[8]+=blockMax;
        stats[4]=std::max<int64_t>(stats[4],workerCount);
    }
    return 0;
}

extern "C" int trial_colorperf_persistent(
        void* handle,const uint16_t* cam,int w,int h,int blockRows,double gain,double cb,double cr,
        int rotation,int workers,uint8_t* bitmap,uint32_t stride,int64_t* stats) {
    auto* ctx=static_cast<ColorContext*>(handle);
    if(!ctx||!cam||!bitmap||!stats)return -1;
    std::array<int64_t,12> s{};
    int rc=renderFramePersistentCoreExact(*ctx,reinterpret_cast<const jshort*>(cam),w,h,bitmap,stride,
                                          blockRows,gain,cb,cr,rotation,workers,s);
    for(int i=0;i<12;i++)stats[i]=s[size_t(i)];
    return rc;
}
