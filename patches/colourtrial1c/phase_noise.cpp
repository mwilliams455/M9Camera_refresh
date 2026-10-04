// Selected same-phase kernel, unchanged from COLOURTRIAL1B. Quarter blend is applied by the caller.
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
