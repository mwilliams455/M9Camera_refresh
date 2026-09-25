// COLOURTRIAL1C Android integration of the selected COLOURTRIAL1B rendering.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <chrono>
#include <vector>
#include <omp.h>
#include "librtprocess.h"
extern "C" int phase_noise(const uint16_t*,const float*,const uint8_t*,int,int,uint16_t*,int);
extern "C" int phase_noise_banded_exact(const uint16_t*,const float*,const uint8_t*,int,int,uint16_t*,int);
extern "C" int phase_noise_symmetric_exact(const uint16_t*,const float*,const uint8_t*,int,int,uint16_t*,int);

extern "C" int trial_variance(const uint16_t* sensor,int w,int h,int cfa,int originY,
 const float* black,int white,const double* profile,const double* gains,int mw,int mh,
 double scale,float* variance,uint8_t* censored) {
 if(!sensor||!black||!profile||!gains||!variance||!censored||w<2||h<2||cfa<0||cfa>3||
    mw<1||mh<1||mw>256||mh>256||white<2||white>65535||!std::isfinite(scale)||scale<=0)return -1;
 for(int p=0;p<4;p++)if(!std::isfinite(black[p])||black[p]<0||black[p]>=white)return -1;
 for(int p=0;p<6;p++)if(!std::isfinite(profile[p])||profile[p]<0||profile[p]>1)return -1;
 for(int p=0;p<mw*mh*4;p++)if(!std::isfinite(gains[p])||gains[p]<=0||gains[p]>scale*(1.+1e-12))return -1;
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){
  const int i=y*w+x,p=(y&1)*2+(x&1);
  const bool red=(x&1)==(cfa&1)&&(y&1)==(cfa>>1),blue=(x&1)!=(cfa&1)&&(y&1)!=(cfa>>1);
  const int ch=red?0:blue?2:1,mp=red?0:blue?3:((y+originY)&1)?2:1;
  const double den=white-double(black[p]),signal=std::clamp((sensor[i]-double(black[p]))/den,0.,1.);
  const double gx=x*((mw-1.)/(w-1.)),gy=y*((mh-1.)/(h-1.));
  const int x0=int(gx),y0=int(gy),x1=std::min(mw-1,x0+1),y1=std::min(mh-1,y0+1);
  auto at=[&](int yy,int xx){return gains[(yy*mw+xx)*4+mp];};
  const double g0=at(y0,x0)+(gx-x0)*(at(y0,x1)-at(y0,x0));
  const double g1=at(y1,x0)+(gx-x0)*(at(y1,x1)-at(y1,x0));
  const double transport=(g0+(gy-y0)*(g1-g0))/scale*65535.;
  variance[i]=float((profile[2*ch]*signal+profile[2*ch+1]+1./(12.*den*den))*transport*transport);
  censored[i]=sensor[i]<=black[p]||sensor[i]>=white;
 }
 return 0;
}

extern "C" int trial_reconstruct(const uint16_t* raw,const float* variance,const uint8_t* censored,
 int w,int h,int cfa,double nr,double nb,double scale,uint16_t* out,int workers,double* stats) {
 if(!raw||!out||!stats||w<64||h<64||w>8192||h>8192||cfa<0||cfa>3||workers<1||workers>8||
    !std::isfinite(nr)||!std::isfinite(nb)||nr<.0625||nb<.0625||nr>16||nb>16||
    !std::isfinite(scale)||scale<=0||scale>64||(bool(variance)!=bool(censored)))return -1;
 std::fill(stats,stats+4,0.);
 try {
  const size_t count=size_t(w)*h;
  std::vector<uint16_t> corrected;
  const uint16_t* inputRaw=raw;
  if(variance){
   corrected.resize(count);
   int rc=phase_noise(raw,variance,censored,w,h,corrected.data(),workers);if(rc)return rc;
   for(size_t i=0;i<count;i++){
    corrected[i]=uint16_t((3u*raw[i]+corrected[i]+2u)/4u); // exact half-up quarter blend
    stats[1]+=corrected[i]!=raw[i];stats[2]=std::max(stats[2],double(std::abs(int(corrected[i])-int(raw[i]))));
    stats[3]+=censored[i]!=0;
   }
   inputRaw=corrected.data();stats[0]=1.;
  }
  const double n[3]={nr,1.,nb},headroom=std::max({1.,1./nr,1./nb});
  const unsigned patterns[4][2][2]={{{0,1},{1,2}},{{1,0},{2,1}},{{1,2},{0,1}},{{2,1},{1,0}}};
  const auto& pattern=patterns[cfa];
  // AMaZE's 160px tiles advance by 128. Keep that exact global tile grid,
  // including source halos; only the destination storage is banded.
  constexpr int bandRows=256;
  std::vector<float> input(count),red(size_t(w)*std::min(h,bandRows)),green(red.size()),blue(red.size());
  std::vector<float*> ir(h),r(h),g(h),b(h);
  for(int y=0;y<h;y++){
   ir[y]=input.data()+size_t(y)*w;
   for(int x=0;x<w;x++)ir[y][x]=float(double(inputRaw[y*w+x])/n[pattern[y&1][x&1]]/headroom);
  }
  std::vector<uint16_t>().swap(corrected);
  struct Threads {int old;Threads(int n):old(omp_get_max_threads()){omp_set_num_threads(n);}~Threads(){omp_set_num_threads(old);}} threads(workers);
  const auto progress=[](double){return false;};
  for(int top=0;top<h;top+=bandRows) {
  const int bottom=std::min(h,top+bandRows);
  for(int y=top;y<bottom;y++) {
   r[y]=red.data()+size_t(y-top)*w;g[y]=green.data()+size_t(y-top)*w;b[y]=blue.data()+size_t(y-top)*w;
  }
  // The final 16px MHC border is supplied by trialBorder from original RAW.
  // Suppress upstream's 3px full-frame border pass on each partial window.
  rpError rc=amaze_demosaic(w,h,0,top,w,bottom-top,ir.data(),r.data(),g.data(),b.data(),pattern,progress,scale*headroom,16,65535.f,65535.f,2,false);
  if(rc!=RP_NO_ERROR)return -10-int(rc);
  for(int y=top;y<bottom;y++)for(int x=0;x<w;x++){
   const double v[3]={r[y][x],g[y][x],b[y][x]};
   for(int ch=0;ch<3;ch++){
    double value=v[ch]*headroom*n[ch];if(!std::isfinite(value))return -20;
    out[3*(size_t(y)*w+x)+ch]=uint16_t(std::llround(std::clamp(value,0.,65535.)));
   }
  }
  }
 }catch(...){return -30;}
 return 0;
}


// AMAZEPERF1A: performance-only parallel wrappers. The exact COLOURTRIAL1D
// scalar/peripheral entry points above remain untouched as parity oracles.

extern "C" int trial_variance_parallel(const uint16_t* sensor,int w,int h,int cfa,int originY,
 const float* black,int white,const double* profile,const double* gains,int mw,int mh,
 double scale,float* variance,uint8_t* censored,int workers) {
 if(!sensor||!black||!profile||!gains||!variance||!censored||w<2||h<2||cfa<0||cfa>3||
    mw<1||mh<1||mw>256||mh>256||white<2||white>65535||workers<1||workers>8||
    !std::isfinite(scale)||scale<=0)return -1;
 for(int p=0;p<4;p++)if(!std::isfinite(black[p])||black[p]<0||black[p]>=white)return -1;
 for(int p=0;p<6;p++)if(!std::isfinite(profile[p])||profile[p]<0||profile[p]>1)return -1;
 for(int p=0;p<mw*mh*4;p++)if(!std::isfinite(gains[p])||gains[p]<=0||gains[p]>scale*(1.+1e-12))return -1;
 #pragma omp parallel for num_threads(workers) schedule(static)
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){
  const int i=y*w+x,p=(y&1)*2+(x&1);
  const bool red=(x&1)==(cfa&1)&&(y&1)==(cfa>>1),blue=(x&1)!=(cfa&1)&&(y&1)!=(cfa>>1);
  const int ch=red?0:blue?2:1,mp=red?0:blue?3:((y+originY)&1)?2:1;
  const double den=white-double(black[p]),signal=std::clamp((sensor[i]-double(black[p]))/den,0.,1.);
  const double gx=x*((mw-1.)/(w-1.)),gy=y*((mh-1.)/(h-1.));
  const int x0=int(gx),y0=int(gy),x1=std::min(mw-1,x0+1),y1=std::min(mh-1,y0+1);
  auto at=[&](int yy,int xx){return gains[(yy*mw+xx)*4+mp];};
  const double g0=at(y0,x0)+(gx-x0)*(at(y0,x1)-at(y0,x0));
  const double g1=at(y1,x0)+(gx-x0)*(at(y1,x1)-at(y1,x0));
  const double transport=(g0+(gy-y0)*(g1-g0))/scale*65535.;
  variance[i]=float((profile[2*ch]*signal+profile[2*ch+1]+1./(12.*den*den))*transport*transport);
  censored[i]=sensor[i]<=black[p]||sensor[i]>=white;
 }
 return 0;
}

extern "C" int trial_reconstruct_perf(const uint16_t* raw,const float* variance,const uint8_t* censored,
 int w,int h,int cfa,double nr,double nb,double scale,uint16_t* out,int workers,double* stats,double* perf) {
 if(!raw||!out||!stats||!perf||w<64||h<64||w>8192||h>8192||cfa<0||cfa>3||workers<1||workers>8||
    !std::isfinite(nr)||!std::isfinite(nb)||nr<.0625||nb<.0625||nr>16||nb>16||
    !std::isfinite(scale)||scale<=0||scale>64||(bool(variance)!=bool(censored)))return -1;
 std::fill(stats,stats+4,0.);std::fill(perf,perf+5,0.);
 using Clock=std::chrono::steady_clock;
 auto elapsed=[](Clock::time_point a,Clock::time_point b){return std::chrono::duration<double,std::milli>(b-a).count();};
 try {
  const size_t count=size_t(w)*h;
  std::vector<uint16_t> corrected;
  const uint16_t* inputRaw=raw;
  if(variance){
   corrected.resize(count);
   auto t0=Clock::now();
   int rc=phase_noise_symmetric_exact(raw,variance,censored,w,h,corrected.data(),workers);if(rc)return rc;
   perf[0]=elapsed(t0,Clock::now());
   uint64_t changed=0,censoredCount=0;int maxCorrection=0;
   t0=Clock::now();
   #pragma omp parallel for num_threads(workers) schedule(static) reduction(+:changed,censoredCount) reduction(max:maxCorrection)
   for(int64_t ii=0;ii<int64_t(count);ii++){
    const size_t i=size_t(ii);
    corrected[i]=uint16_t((3u*raw[i]+corrected[i]+2u)/4u);
    changed+=corrected[i]!=raw[i];
    maxCorrection=std::max(maxCorrection,std::abs(int(corrected[i])-int(raw[i])));
    censoredCount+=censored[i]!=0;
   }
   perf[1]=elapsed(t0,Clock::now());
   stats[1]=double(changed);stats[2]=double(maxCorrection);stats[3]=double(censoredCount);
   inputRaw=corrected.data();stats[0]=1.;
  }

  const double n[3]={nr,1.,nb},headroom=std::max({1.,1./nr,1./nb});
  const unsigned patterns[4][2][2]={{{0,1},{1,2}},{{1,0},{2,1}},{{1,2},{0,1}},{{2,1},{1,0}}};
  const auto& pattern=patterns[cfa];
  constexpr int bandRows=256;
  std::vector<float> input(count),red(size_t(w)*std::min(h,bandRows)),green(red.size()),blue(red.size());
  std::vector<float*> ir(h),r(h),g(h),b(h);

  auto t0=Clock::now();
  #pragma omp parallel for num_threads(workers) schedule(static)
  for(int y=0;y<h;y++){
   ir[y]=input.data()+size_t(y)*w;
   for(int x=0;x<w;x++)ir[y][x]=float(double(inputRaw[size_t(y)*w+x])/n[pattern[y&1][x&1]]/headroom);
  }
  perf[2]=elapsed(t0,Clock::now());
  std::vector<uint16_t>().swap(corrected);

  struct Threads {int old;Threads(int n):old(omp_get_max_threads()){omp_set_num_threads(n);}~Threads(){omp_set_num_threads(old);}} threads(workers);
  const auto progress=[](double){return false;};
  double amazeMs=0.,quantizeMs=0.;
  for(int top=0;top<h;top+=bandRows) {
   const int bottom=std::min(h,top+bandRows);
   for(int y=top;y<bottom;y++) {
    r[y]=red.data()+size_t(y-top)*w;g[y]=green.data()+size_t(y-top)*w;b[y]=blue.data()+size_t(y-top)*w;
   }
   t0=Clock::now();
   rpError rc=amaze_demosaic(w,h,0,top,w,bottom-top,ir.data(),r.data(),g.data(),b.data(),pattern,progress,
           scale*headroom,16,65535.f,65535.f,2,false);
   amazeMs+=elapsed(t0,Clock::now());
   if(rc!=RP_NO_ERROR)return -10-int(rc);

   int invalid=0;
   t0=Clock::now();
   #pragma omp parallel for num_threads(workers) schedule(static) reduction(|:invalid)
   for(int y=top;y<bottom;y++)for(int x=0;x<w;x++){
    const double v[3]={r[y][x],g[y][x],b[y][x]};
    for(int ch=0;ch<3;ch++){
     double value=v[ch]*headroom*n[ch];
     if(!std::isfinite(value)){invalid=1;value=0.;}
     out[3*(size_t(y)*w+x)+ch]=uint16_t(std::llround(std::clamp(value,0.,65535.)));
    }
   }
   quantizeMs+=elapsed(t0,Clock::now());
   if(invalid)return -20;
  }
  perf[3]=amazeMs;perf[4]=quantizeMs;
 }catch(...){return -30;}
 return 0;
}

extern "C" const char* m9_amazeperf1a_revision(){return "M9AMAZEPERF1A_PARALLEL_PERIPHERY_EXACT";}


extern "C" const char* m9_phasenoiseperf1a_reconstruct_revision(){
 return "M9PHASENOISEPERF1A_BANDED_TERM_REUSE_EXACT";
}


extern "C" const char* m9_phasenoiseperf1b_reconstruct_revision(){
 return "M9PHASENOISEPERF1B_SYMMETRIC_WEIGHT_REUSE_EXACT";
}
