// DETAIL1H phone seam: exact D/G kernels on tiles, original native green intact.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
#include <chrono>
#include <new>
extern "C" void rb_domain_stages(const uint16_t*,int,int,int,int,double,double,uint16_t*,int32_t*,int32_t*,uint16_t*);
extern "C" void rb_domain_consume(const int32_t*,const uint16_t*,int,int,int,double,double,uint16_t*);
extern "C" int noise2_guard_native(const int32_t*,const double*,const uint8_t*,int,int,int,double,double,double,int32_t*,int32_t*,float*,float*);

using ReadBand = bool (*)(void*, int, int, uint16_t*);
#ifdef M9DETAIL1H_HOST
static thread_local int fail_guard_tile=-1;
extern "C" void detail1h_fail_guard_tile(int tile) {fail_guard_tile=tile;}
#endif
struct DetailInput {
    ReadBand read; void* owner; const uint16_t* sensor;
    int w,h,cfa,originY,white,mw,mh,tile;
    double nr,nb,scale; const float* black; const double* profile; const double* gains;
};
static double gain_at(const DetailInput& a,int y,int x) {
    const int rx=a.cfa&1,ry=a.cfa>>1;
    const bool red=(x&1)==rx && (y&1)==ry,blue=(x&1)!=rx && (y&1)!=ry;
    const int p=red?0:blue?3:((y+a.originY)&1)?2:1;
    const double gx=x*((a.mw-1.)/(a.w-1.)),gy=y*((a.mh-1.)/(a.h-1.));
    const int x0=int(std::floor(gx)),y0=int(std::floor(gy)),x1=std::min(a.mw-1,x0+1),y1=std::min(a.mh-1,y0+1);
    const auto g=[&](int yy,int xx){return a.gains[(yy*a.mw+xx)*4+p];};
    const double g0=g(y0,x0)+(gx-x0)*(g(y0,x1)-g(y0,x0));
    const double g1=g(y1,x0)+(gx-x0)*(g(y1,x1)-g(y1,x0));
    return g0+(gy-y0)*(g1-g0);
}
static double variance_at(const DetailInput& a,int y,int x) {
    const int p=(y&1)*2+(x&1),rx=a.cfa&1,ry=a.cfa>>1;
    const int colour=((x&1)==rx&&(y&1)==ry)?0:((x&1)!=rx&&(y&1)!=ry)?2:1;
    const float den=std::max(1.f,float(a.white)-a.black[p]);
    const float signal=std::clamp((float(a.sensor[y*a.w+x])-a.black[p])/den,0.f,1.f);
    const float v=static_cast<float>(a.profile[colour*2]*double(signal)+a.profile[colour*2+1]);
    const double scale=gain_at(a,y,x)/a.scale*16383.;
    return static_cast<float>(double(v)*(scale*scale));
}

static int pass(const DetailInput& a,uint16_t* rgb,bool guard,double* stats) {
    constexpr int halo=12;
    std::fill(stats,stats+10,0.);stats[0]=guard?1.:0.;
    for(int top=0;top<a.h;top+=a.tile) {
        const int bottom=std::min(a.h,top+a.tile),sy=std::max(0,std::min(top-halo,a.h-24)),ey=std::min(a.h,bottom+halo),th=ey-sy;
        std::vector<uint16_t> band(size_t(th)*a.w);
        if(!a.read(a.owner,sy,th,band.data())) return -3;
        for(int left=0;left<a.w;left+=a.tile) {
            const int right=std::min(a.w,left+a.tile),sx=std::max(0,std::min(left-halo,a.w-24)),ex=std::min(a.w,right+halo),tw=ex-sx;
            // The last narrow tile includes more context, making every window >=24.
            if(tw<24 || th<24) return -4;
            const size_t n=size_t(tw)*th;
            std::vector<uint16_t> raw(n),g(n),u(n),base(n*3),result(n*3);
            std::vector<int32_t> d(n),c(n),filtered;
            for(int y=0;y<th;++y) {
                std::memcpy(raw.data()+size_t(y)*tw,band.data()+size_t(y)*a.w+sx,tw*2);
                std::memcpy(base.data()+size_t(y)*tw*3,rgb+(size_t(y+sy)*a.w+sx)*3,tw*6);
            }
            const int phase=(((a.cfa&1)^(sx&1)))+2*((a.cfa>>1)^(sy&1));
            rb_domain_stages(raw.data(),tw,th,phase,1,a.nr,a.nb,g.data(),d.data(),c.data(),u.data());
            std::vector<double> v;std::vector<uint8_t> mask;std::vector<int32_t> sm;std::vector<float> vr,conf;
            if(guard) {
#ifdef M9DETAIL1H_HOST
                if(int(stats[1])==fail_guard_tile){fail_guard_tile=-1;return 2;}
#endif
                v.resize(n);mask.resize(n);filtered.resize(n);sm.resize(n);vr.resize(n);conf.resize(n);
                for(int y=0;y<th;++y)for(int x=0;x<tw;++x) {
                    const int yy=y+sy,xx=x+sx,p=(yy&1)*2+(xx&1),i=y*tw+x;
                    const int rawValue=a.sensor[yy*a.w+xx];
                    v[i]=variance_at(a,yy,xx);
                    mask[i]=rawValue<=a.black[p] || rawValue>=a.white;
                }
                const int rc=noise2_guard_native(c.data(),v.data(),mask.data(),tw,th,phase,a.nr,a.nb,1.,filtered.data(),sm.data(),vr.data(),conf.data());
                if(rc) return 2; // Recompute the *entire* D fallback; never mix tiles.
            }
            rb_domain_consume(guard?filtered.data():c.data(),base.data(),tw,th,phase,a.nr,a.nb,result.data());
            for(int y=top;y<bottom;++y)for(int x=left;x<right;++x) {
                const int i=(y-sy)*tw+x-sx;
                if(guard)stats[5]+=mask[i]!=0;
                // Preserve the physical frame border, regardless of tile size.
                if(y<10||y>=a.h-10||x<10||x>=a.w-10)continue;
                std::memcpy(rgb+(size_t(y)*a.w+x)*3,result.data()+i*3,6);
                if(((x&1)==(a.cfa&1))!=((y&1)==(a.cfa>>1)))continue;
                ++stats[2];
                if(guard) {
                    const int correction=filtered[i]-c[i];stats[3]+=correction!=0;
                    stats[4]=std::max(stats[4],double(std::abs(correction)));
                    stats[6]+=conf[i];stats[7]+=vr[i];
                }
            }
            ++stats[1];stats[8]=std::max(stats[8],double(80*n+2*size_t(th)*a.w));
        }
    }
    if(stats[2]>0){stats[6]/=stats[2];stats[7]/=stats[2];}
    return 0;
}
static int process(const DetailInput& a,uint16_t* rgb,bool guard,double* stats) {
    if(!a.read||!rgb||!stats||a.w<24||a.h<24||a.w>8192||a.h>8192||a.cfa<0||a.cfa>3||
       a.tile<32||a.tile>512||a.tile%2||!std::isfinite(a.nr)||!std::isfinite(a.nb)||a.nr<.0625||a.nr>16||a.nb<.0625||a.nb>16)return -1;
    if(guard) {
        if(!a.sensor||!a.black||!a.profile||!a.gains||a.white<2||a.mw<1||a.mh<1||a.mw>256||a.mh>256||!std::isfinite(a.scale)||a.scale<=0)return -1;
        for(int p=0;p<4;++p)if(!std::isfinite(a.black[p])||a.black[p]>=a.white)return -1;
        for(int p=0;p<6;++p)if(!std::isfinite(a.profile[p])||a.profile[p]<0||a.profile[p]>1)return -1;
        for(int p=0;p<a.mw*a.mh*4;++p)if(!std::isfinite(a.gains[p])||a.gains[p]<=0||a.gains[p]>a.scale*(1.+1e-12))return -1;
    }
    const auto start=std::chrono::steady_clock::now();int rc;
    try {
        rc=pass(a,rgb,guard,stats);
        if(rc==2){rc=pass(a,rgb,false,stats);stats[0]=2.;}
    } catch(const std::bad_alloc&) {return -2;}
    stats[9]=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
    return rc;
}

#ifdef M9DETAIL1H_HOST
struct HostBand {const uint16_t* norm;int w;};
static bool host_read(void* p,int y,int rows,uint16_t* out) {
    const auto& a=*static_cast<HostBand*>(p);std::memcpy(out,a.norm+size_t(y)*a.w,size_t(rows)*a.w*2);return true;
}
extern "C" int detail1h_host(const uint16_t* norm,const uint16_t* sensor,int w,int h,int cfa,int originY,
        const float* black,int white,const double* profile,const double* gains,int mw,int mh,double scale,
        double nr,double nb,int tile,int guard,uint16_t* rgb,double* stats) {
    HostBand b{norm,w};DetailInput a{host_read,&b,sensor,w,h,cfa,originY,white,mw,mh,tile,nr,nb,scale,black,profile,gains};
    return process(a,rgb,guard!=0,stats);
}
extern "C" double detail1h_variance(const uint16_t* sensor,int w,int h,int cfa,int originY,const float* black,int white,
        const double* profile,const double* gains,int mw,int mh,double scale,int y,int x) {
    DetailInput a{nullptr,nullptr,sensor,w,h,cfa,originY,white,mw,mh,256,1.,1.,scale,black,profile,gains};return variance_at(a,y,x);
}
#else
#include <jni.h>
struct JavaBand {JNIEnv* env;jshortArray norm;int w;};
static bool java_read(void* p,int y,int rows,uint16_t* out) {
    auto& a=*static_cast<JavaBand*>(p);
    a.env->GetShortArrayRegion(a.norm,y*a.w,rows*a.w,reinterpret_cast<jshort*>(out));
    return !a.env->ExceptionCheck();
}
extern "C" JNIEXPORT jint JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9Detail1H_applyNative(JNIEnv* env,jclass,
        jshortArray norm,jobject sensor,jobject output,jint w,jint h,jint cfa,jint originY,
        jfloatArray black,jint white,jdoubleArray profile,jdoubleArray gains,jint mw,jint mh,
        jdouble scale,jdouble nr,jdouble nb,jboolean guard,jdoubleArray stats) {
    if(!norm||!output||!stats||w<24||h<24||w>8192||h>8192||env->GetArrayLength(norm)<int64_t(w)*h||env->GetArrayLength(stats)<10)return -1;
    auto* rgb=static_cast<uint16_t*>(env->GetDirectBufferAddress(output));
    auto* raw=sensor?static_cast<const uint16_t*>(env->GetDirectBufferAddress(sensor)):nullptr;
    if(!rgb||env->GetDirectBufferCapacity(output)<int64_t(w)*h*6)return -1;
    float bl[4]={};double pairs[6]={},ss[10]={};std::vector<double> grid;
    try {
        if(guard) {
            if(!raw||env->GetDirectBufferCapacity(sensor)<int64_t(w)*h*2||!black||!profile||!gains||mw<1||mh<1||mw>256||mh>256||
                env->GetArrayLength(black)!=4||env->GetArrayLength(profile)!=6||env->GetArrayLength(gains)!=mw*mh*4)return -1;
            grid.resize(size_t(mw)*mh*4);env->GetFloatArrayRegion(black,0,4,bl);
            env->GetDoubleArrayRegion(profile,0,6,pairs);env->GetDoubleArrayRegion(gains,0,int(grid.size()),grid.data());
            if(env->ExceptionCheck())return -1;
        }
        JavaBand b{env,norm,w};DetailInput a{java_read,&b,raw,w,h,cfa,originY,white,mw,mh,256,nr,nb,scale,bl,pairs,grid.data()};
        const int rc=process(a,rgb,guard,ss);
        if(!env->ExceptionCheck())env->SetDoubleArrayRegion(stats,0,10,ss);
        return rc;
    }catch(const std::bad_alloc&){return -2;}
}
#endif
