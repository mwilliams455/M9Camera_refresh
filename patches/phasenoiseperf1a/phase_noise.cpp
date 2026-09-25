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


// PHASENOISEPERF1A: byte-exact banded candidate-term reuse.
//
// The selected filter compares a 3x3 same-Bayer-phase patch for each of 24
// same-phase neighbours. In the scalar oracle above, the normalized comparison
// term for a given candidate displacement is recomputed up to nine times for
// overlapping target patches. This implementation computes that exact term once
// per source sample and candidate displacement inside a bounded row band, then
// gathers the same nine terms in the same py/px order. Candidate order, floating
// arithmetic, exp(), accumulation order and llround() are unchanged.
//
// Scratch is bounded per worker; there is no full-frame distance/weight cache.
extern "C" int phase_noise_banded_exact(const uint16_t* raw,const float* variance,
 const uint8_t* clipped,int w,int h,uint16_t* out,int workers){
 if(!raw||!variance||!clipped||!out||w<16||h<16||workers<1||workers>8)return -1;
 std::memcpy(out,raw,size_t(w)*h*sizeof(uint16_t));
 constexpr int bandRows=64;
 const int firstY=6,lastY=h-6,rows=lastY-firstY;
 if(rows<=0||w<=12)return 0;
 const int bands=(rows+bandRows-1)/bandRows;

 #pragma omp parallel num_threads(workers)
 {
  std::vector<double> sum(size_t(bandRows)*w),ws(size_t(bandRows)*w);
  std::vector<uint8_t> active(size_t(bandRows)*w);
  std::vector<double> term(size_t(bandRows+4)*w);
  std::vector<uint8_t> valid(size_t(bandRows+4)*w);

  #pragma omp for schedule(static)
  for(int band=0;band<bands;band++){
   const int y0=firstY+band*bandRows,y1=std::min(lastY,y0+bandRows),bh=y1-y0;
   const size_t targetCount=size_t(bh)*w;
   std::fill(active.begin(),active.begin()+targetCount,uint8_t(0));

   for(int y=y0;y<y1;y++)for(int x=6;x<w-6;x++){
    const int i=y*w+x;const size_t q=size_t(y-y0)*w+x;
    if(clipped[i]||variance[i]<=0)continue;
    active[q]=1;sum[q]=raw[i];ws[q]=1.;
   }

   // Preserve the oracle candidate ordering exactly: dy outer, dx inner.
   for(int dy=-4;dy<=4;dy+=2)for(int dx=-4;dx<=4;dx+=2){
    if(!dx&&!dy)continue;
    const int termY0=y0-2,termY1=y1+2,th=termY1-termY0;
    const size_t termCount=size_t(th)*w;
    std::fill(valid.begin(),valid.begin()+termCount,uint8_t(0));

    // Precompute the exact normalized pair term once for this displacement.
    for(int y=termY0;y<termY1;y++)for(int x=4;x<w-4;x++){
     const int a=y*w+x,b=a+dy*w+dx;
     if(clipped[a]||clipped[b])continue;
     const double v=double(variance[a])+variance[b];if(v<=0)continue;
     const double d=double(raw[a])-raw[b];
     const size_t q=size_t(y-termY0)*w+x;
     term[q]=d*d/v;valid[q]=1;
    }

    for(int y=y0;y<y1;y++)for(int x=6;x<w-6;x++){
     const size_t tq=size_t(y-y0)*w+x;if(!active[tq])continue;
     const int i=y*w+x,j=i+dy*w+dx;if(clipped[j])continue;
     double distance=0.;int count=0;
     for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2){
      const size_t q=size_t(y+py-termY0)*w+(x+px);
      if(!valid[q])continue;
      distance+=term[q];count++;
     }
     if(count<7)continue;
     const double weight=std::exp(-2.*std::max(0.,distance/count-1.));
     sum[tq]+=weight*raw[j];ws[tq]+=weight;
    }
   }

   for(int y=y0;y<y1;y++)for(int x=6;x<w-6;x++){
    const size_t q=size_t(y-y0)*w+x;if(!active[q])continue;
    out[size_t(y)*w+x]=uint16_t(std::llround(sum[q]/ws[q]));
   }
  }
 }
 return 0;
}

extern "C" const char* m9_phasenoiseperf1a_revision(){
 return "M9PHASENOISEPERF1A_BANDED_TERM_REUSE_EXACT";
}
extern "C" int m9_phasenoiseperf1a_band_rows(){return 64;}
