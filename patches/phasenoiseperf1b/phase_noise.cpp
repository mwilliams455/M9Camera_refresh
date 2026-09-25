// Selected same-phase kernel, unchanged from COLOURTRIAL1B. Quarter blend is applied by the caller.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>
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


// PHASENOISEPERF1B: exact symmetric patch-weight reuse.
//
// For any same-phase candidate displacement d:
//   weight(i,d) == weight(i+d,-d)
// because the nine patch comparisons are the same sample pairs in reverse,
// with identical squared differences, variance sums, patch order and exp math.
//
// We cache only the 12 canonical half-plane directions, then accumulate all 24
// candidates in the original oracle order. Positive-half candidates read the
// already-computed symmetric weight at the candidate centre. 2-D tiles keep the
// cache bounded; no full-frame weight/distance cache is introduced.
extern "C" int phase_noise_symmetric_exact(const uint16_t* raw,const float* variance,
 const uint8_t* clipped,int w,int h,uint16_t* out,int workers){
 if(!raw||!variance||!clipped||!out||w<16||h<16||workers<1||workers>8)return -1;
 std::memcpy(out,raw,size_t(w)*h*sizeof(uint16_t));
 constexpr int tileRows=32,tileCols=256;
 constexpr int canonicalCount=12,candidateCount=24;
 constexpr int cdy[canonicalCount]={-4,-4,-4,-4,-4,-2,-2,-2,-2,-2,0,0};
 constexpr int cdx[canonicalCount]={-4,-2,0,2,4,-4,-2,0,2,4,-4,-2};
 constexpr int ady[candidateCount]={
   -4,-4,-4,-4,-4,-2,-2,-2,-2,-2,0,0,0,0,2,2,2,2,2,4,4,4,4,4};
 constexpr int adx[candidateCount]={
   -4,-2,0,2,4,-4,-2,0,2,4,-4,-2,2,4,-4,-2,0,2,4,-4,-2,0,2,4};
 // Candidate indices 12..23 use the opposite canonical direction below.
 constexpr int oppositeCanonical[12]={11,10,9,8,7,6,5,4,3,2,1,0};

 const int firstY=6,lastY=h-6,firstX=6,lastX=w-6;
 if(firstY>=lastY||firstX>=lastX)return 0;
 const int tilesY=(lastY-firstY+tileRows-1)/tileRows;
 const int tilesX=(lastX-firstX+tileCols-1)/tileCols;
 const int totalTiles=tilesY*tilesX;

 #pragma omp parallel num_threads(workers)
 {
  // Max dimensions include the +/-4 symmetric-centre halo and +/-2 patch halo.
  const int maxCacheH=tileRows+8,maxCacheW=tileCols+8;
  const int maxTermH=maxCacheH+4,maxTermW=maxCacheW+4;
  std::vector<double> weights(size_t(canonicalCount)*maxCacheH*maxCacheW);
  std::vector<double> term(size_t(maxTermH)*maxTermW);
  std::vector<uint8_t> valid(size_t(maxTermH)*maxTermW);

  #pragma omp for schedule(static)
  for(int tile=0;tile<totalTiles;tile++){
   const int ty=tile/tilesX,tx=tile%tilesX;
   const int y0=firstY+ty*tileRows,y1=std::min(lastY,y0+tileRows);
   const int x0=firstX+tx*tileCols,x1=std::min(lastX,x0+tileCols);
   const int cacheY0=y0-4,cacheY1=y1+4,cacheH=cacheY1-cacheY0;
   const int cacheX0=x0-4,cacheX1=x1+4,cacheW=cacheX1-cacheX0;
   const size_t cachePlane=size_t(cacheH)*cacheW;

   for(int ci=0;ci<canonicalCount;ci++){
    const int dy=cdy[ci],dx=cdx[ci];
    const int termY0=cacheY0-2,termY1=cacheY1+2,termH=termY1-termY0;
    const int termX0=cacheX0-2,termX1=cacheX1+2,termW=termX1-termX0;
    const size_t termCount=size_t(termH)*termW;
    std::fill(valid.begin(),valid.begin()+termCount,uint8_t(0));

    // Exact normalized pair terms for this canonical displacement.
    for(int y=termY0;y<termY1;y++)for(int x=termX0;x<termX1;x++){
     const int by=y+dy,bx=x+dx;
     if(y<0||y>=h||x<0||x>=w||by<0||by>=h||bx<0||bx>=w)continue;
     const int a=y*w+x,b=by*w+bx;
     if(clipped[a]||clipped[b])continue;
     const double v=double(variance[a])+variance[b];if(v<=0)continue;
     const double d=double(raw[a])-raw[b];
     const size_t q=size_t(y-termY0)*termW+(x-termX0);
     term[q]=d*d/v;valid[q]=1;
    }

    double* weightPlane=weights.data()+size_t(ci)*cachePlane;
    std::fill(weightPlane,weightPlane+cachePlane,0.0);
    for(int y=cacheY0;y<cacheY1;y++)for(int x=cacheX0;x<cacheX1;x++){
     const int jy=y+dy,jx=x+dx;
     if(y<0||y>=h||x<0||x>=w||jy<0||jy>=h||jx<0||jx>=w)continue;
     // Same centre-candidate censor gate as the oracle candidate.
     if(clipped[jy*w+jx])continue;
     double distance=0.;int count=0;
     for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2){
      const size_t q=size_t(y+py-termY0)*termW+(x+px-termX0);
      if(!valid[q])continue;
      distance+=term[q];count++;
     }
     if(count<7)continue;
     weightPlane[size_t(y-cacheY0)*cacheW+(x-cacheX0)]=
       std::exp(-2.*std::max(0.,distance/count-1.));
    }
   }

   // Accumulate in the exact original 24-candidate order.
   for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){
    const int i=y*w+x;if(clipped[i]||variance[i]<=0)continue;
    double sum=raw[i],ws=1.;
    for(int ai=0;ai<candidateCount;ai++){
     const int dy=ady[ai],dx=adx[ai],jy=y+dy,jx=x+dx,j=jy*w+jx;
     if(clipped[j])continue;
     int ci,wy,wx;
     if(ai<canonicalCount){ci=ai;wy=y;wx=x;}
     else {ci=oppositeCanonical[ai-canonicalCount];wy=jy;wx=jx;}
     const double weight=weights[size_t(ci)*cachePlane+
       size_t(wy-cacheY0)*cacheW+(wx-cacheX0)];
     if(weight==0.)continue;
     sum+=weight*raw[j];ws+=weight;
    }
    out[i]=uint16_t(std::llround(sum/ws));
   }
  }
 }
 return 0;
}

extern "C" const char* m9_phasenoiseperf1b_revision(){
 return "M9PHASENOISEPERF1B_SYMMETRIC_WEIGHT_REUSE_EXACT";
}
extern "C" int m9_phasenoiseperf1b_tile_rows(){return 32;}
extern "C" int m9_phasenoiseperf1b_tile_cols(){return 256;}
