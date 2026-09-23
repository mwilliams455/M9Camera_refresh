// Offline experiment. No application integration or photo-specific constants.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <omp.h>

// Variance is in the same squared code units as raw, propagated from the
// independent sensor samples through black normalization and shading gains.
// Compare 3x3 patches on the SAME Bayer phase; average a 5x5 phase neighbourhood.
// Saturated measurements are censored and never used as ordinary observations.
extern "C" int phase_noise(const uint16_t* raw,const float* variance,
 const uint8_t* clipped,int w,int h,uint16_t* out,int workers){
 if(!raw||!variance||!clipped||!out||w<16||h<16||workers<1)return -1;
 std::memcpy(out,raw,size_t(w)*h*sizeof(uint16_t));
 #pragma omp parallel for num_threads(workers) schedule(static)
 for(int y=6;y<h-6;y++)for(int x=6;x<w-6;x++){
  const int i=y*w+x;if(clipped[i]||variance[i]<=0)continue;
  double sum=raw[i],ws=1.;
  for(int dy=-4;dy<=4;dy+=2)for(int dx=-4;dx<=4;dx+=2){
   if(!dx&&!dy)continue;
   const int j=i+dy*w+dx;if(clipped[j])continue;
   double distance=0.;int count=0;
   for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2){
    const int a=i+py*w+px,b=j+py*w+px;
    if(clipped[a]||clipped[b])continue;
    const double v=double(variance[a])+variance[b];if(v<=0)continue;
    const double d=double(raw[a])-raw[b];distance+=d*d/v;count++;
   }
   if(count<7)continue;
   const double weight=std::exp(-2.*std::max(0.,distance/count-1.));
   sum+=weight*raw[j];ws+=weight;
  }
  out[i]=uint16_t(std::llround(sum/ws));
 }
 return 0;
}

// At a physically clipped site only, predict a lower-bound lift from nearby
// uncensored samples on the same Bayer phase. Ratios are conditioned on the
// other two channels agreeing in chromaticity. Inconsistent donors abstain.
// This is a local colour-continuity hypothesis, not recovery of ground truth.
extern "C" int clipped_ratio(const uint16_t* raw,const uint16_t* rgb,
 const uint8_t* clipped,const float* variance,int w,int h,int cfa,
 double nr,double nb,uint16_t* out,int workers){
 if(!raw||!rgb||!clipped||!variance||!out||w<32||h<32||cfa<0||cfa>3||nr<=0||nb<=0||workers<1)return -1;
 const int patterns[4][4]={{0,1,1,2},{1,0,2,1},{1,2,0,1},{2,1,1,0}};
 const double neutral[3]={nr,1.,nb};
 std::memcpy(out,raw,size_t(w)*h*sizeof(uint16_t));
 #pragma omp parallel for num_threads(workers) schedule(static)
 for(int y=16;y<h-16;y++)for(int x=16;x<w-16;x++){
  const int i=y*w+x;if(!clipped[i])continue;
  const int c=patterns[cfa][2*(y&1)+(x&1)],a=(c+1)%3,b=(c+2)%3;
  const double ta=rgb[3*i+a]/neutral[a],tb=rgb[3*i+b]/neutral[b],ts=ta+tb;
  if(ts<=0)continue;
  const double tc=ta/ts;
  double sw=0.,sr=0.,sr2=0.;int count=0;
  for(int dy=-12;dy<=12;dy+=2)for(int dx=-12;dx<=12;dx+=2){
   const int j=i+dy*w+dx;bool reliable=true;
   for(int py=-1;py<=1&&reliable;py++)for(int px=-1;px<=1;px++)
    if(clipped[j+py*w+px]){reliable=false;break;}
   if(!reliable||raw[j]<=4.*std::sqrt(std::max(0.f,variance[j])))continue;
   const double da=rgb[3*j+a]/neutral[a],db=rgb[3*j+b]/neutral[b],ds=da+db;
   if(ds<=0||ts>8.*ds||ds>8.*ts)continue;
   const double cd=da/ds-tc;if(std::abs(cd)>.1)continue;
   const double weight=std::exp(-.5*(dx*dx+dy*dy)/64.-.5*cd*cd/.0025);
   const double ratio=(raw[j]/neutral[c])/ds;
   sw+=weight;sr+=weight*ratio;sr2+=weight*ratio*ratio;count++;
  }
  if(count<4||sw<=0)continue;
  const double mean=sr/sw,sd=std::sqrt(std::max(0.,sr2/sw-mean*mean));
  if(mean<=0||sd>.15*mean)continue;
  const double predicted=mean*ts*neutral[c];
  const double value=std::max(double(raw[i]),std::min({predicted,2.*raw[i],65535.}));
  out[i]=uint16_t(std::llround(value));
 }
 return 0;
}
