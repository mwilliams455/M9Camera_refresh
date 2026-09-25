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


// PHASENOISEPERF1B: exact symmetric-pair reuse in bounded 64x512 target tiles.
//
// For any same-phase displacement d, the patch distance/weight is exactly
// symmetric:
//     W(i,d) == W(i+d,-d)
// because the nine compared sample pairs are the same pairs in reverse order,
// the squared raw difference is identical, and the variance sum is identical.
//
// To preserve the scalar oracle's floating accumulation order exactly, this
// implementation does NOT immediately apply the reverse contribution. It
// precomputes the 12 canonical (negative half-plane) weights for the tile plus
// a four-pixel target halo, then walks all 24 candidates in the original dy/dx
// order. Positive candidates fetch the already-computed canonical weight at the
// neighbour coordinate. sum/ws therefore receive additions in the same order as
// phase_noise and phase_noise_banded_exact.
//
// The term cache remains per-canonical-direction and uses the exact 1A term
// reuse arithmetic. Weight scratch is per worker and bounded; no full-frame
// distance or weight cache is allocated.
static inline int phase_noise_canonical_index(int dy,int dx){
 if(dy==-4 && dx>=-4 && dx<=4 && !(dx&1))return (dx+4)/2;
 if(dy==-2 && dx>=-4 && dx<=4 && !(dx&1))return 5+(dx+4)/2;
 if(dy==0 && dx==-4)return 10;
 if(dy==0 && dx==-2)return 11;
 return -1;
}

extern "C" int phase_noise_symtile_exact(const uint16_t* raw,const float* variance,
 const uint8_t* clipped,int w,int h,uint16_t* out,int workers){
 if(!raw||!variance||!clipped||!out||w<16||h<16||workers<1||workers>8)return -1;
 std::memcpy(out,raw,size_t(w)*h*sizeof(uint16_t));

 constexpr int tileRows=64;
 constexpr int tileCols=512;
 constexpr int canonicalCount=12;
 const int firstY=6,lastY=h-6,firstX=6,lastX=w-6;
 const int rows=lastY-firstY,cols=lastX-firstX;
 if(rows<=0||cols<=0)return 0;
 const int tilesY=(rows+tileRows-1)/tileRows;
 const int tilesX=(cols+tileCols-1)/tileCols;
 const int tileCount=tilesY*tilesX;

 const size_t maxPlane=size_t(tileRows+8)*(tileCols+8);
 const size_t maxTermPlane=size_t(tileRows+12)*(tileCols+12);

 #pragma omp parallel num_threads(workers)
 {
  std::vector<double> weights(size_t(canonicalCount)*maxPlane);
  std::vector<double> term(maxTermPlane);
  std::vector<uint8_t> valid(maxTermPlane);

  #pragma omp for schedule(static)
  for(int tile=0;tile<tileCount;tile++){
   const int ty=tile/tilesX,tx=tile%tilesX;
   const int y0=firstY+ty*tileRows,y1=std::min(lastY,y0+tileRows);
   const int x0=firstX+tx*tileCols,x1=std::min(lastX,x0+tileCols);

   // Positive candidates can reach four pixels beyond the target tile. Cache
   // canonical weights for that target halo as well. Patch terms need another
   // two pixels on each side.
   const int ey0=std::max(2,y0-4),ey1=std::min(h-2,y1+4);
   const int ex0=std::max(2,x0-4),ex1=std::min(w-2,x1+4);
   const int eh=ey1-ey0,ew=ex1-ex0;
   const size_t plane=size_t(eh)*ew;
   const int termY0=ey0-2,termY1=ey1+2;
   const int termX0=ex0-2,termX1=ex1+2;
   const int th=termY1-termY0,tw=termX1-termX0;
   const size_t termPlane=size_t(th)*tw;

   // PHASENOISEPERF1B clean-tile exact fast path.
   //
   // When every source/candidate/patch sample used by all 12 canonical
   // directions is uncensored and has positive variance, every 3x3 patch has
   // exactly nine valid terms. We can therefore remove only the censor/valid
   // branches and count bookkeeping. The normalized pair arithmetic, nine-term
   // accumulation order, exp(), 24-candidate output order and llround() remain
   // identical to the scalar oracle. Border/highlight/invalid tiles use the
   // original exact fallback below.
   const int scanY0=termY0-4,scanY1=termY1;
   const int scanX0=termX0-4,scanX1=termX1+4;
   bool clean=(scanY0>=0 && scanX0>=0 && scanY1<=h && scanX1<=w);
   if(clean){
    for(int sy=scanY0;sy<scanY1 && clean;sy++)for(int sx=scanX0;sx<scanX1;sx++){
     const int si=sy*w+sx;
     if(clipped[si]||variance[si]<=0){clean=false;break;}
    }
   }

   int ck=0;
   for(int cdy=-4;cdy<=0;cdy+=2){
    const int dxStart=-4,dxEnd=(cdy==0?-2:4);
    for(int cdx=dxStart;cdx<=dxEnd;cdx+=2){
     if(cdy==0 && cdx==0)continue;
     double* wk=weights.data()+size_t(ck)*maxPlane;

     if(clean){
      // Exact 1A normalized pair terms without branches that are already known
      // false for this tile.
      for(int y=termY0;y<termY1;y++)for(int x=termX0;x<termX1;x++){
       const int a=y*w+x,b=(y+cdy)*w+(x+cdx);
       const double v=double(variance[a])+variance[b];
       const double d=double(raw[a])-raw[b];
       term[size_t(y-termY0)*tw+(x-termX0)]=d*d/v;
      }

      // All nine terms are valid. Keep the scalar py/px traversal order exactly.
      for(int y=ey0;y<ey1;y++)for(int x=ex0;x<ex1;x++){
       double distance=0.;
       for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2){
        distance+=term[size_t(y+py-termY0)*tw+(x+px-termX0)];
       }
       wk[size_t(y-ey0)*ew+(x-ex0)]=
           std::exp(-2.*std::max(0.,distance/9.-1.));
      }
     }else{
      std::fill(wk,wk+plane,0.0);
      std::fill(valid.begin(),valid.begin()+termPlane,uint8_t(0));

      // Exact 1A normalized pair terms for this bounded tile+halo.
      for(int y=termY0;y<termY1;y++)for(int x=termX0;x<termX1;x++){
       const int yb=y+cdy,xb=x+cdx;
       if(yb<0||yb>=h||xb<0||xb>=w)continue;
       const int a=y*w+x,b=yb*w+xb;
       if(clipped[a]||clipped[b])continue;
       const double v=double(variance[a])+variance[b];if(v<=0)continue;
       const double d=double(raw[a])-raw[b];
       const size_t q=size_t(y-termY0)*tw+(x-termX0);
       term[q]=d*d/v;valid[q]=1;
      }

      // Convert the canonical direction's term field into the exact patch weight.
      for(int y=ey0;y<ey1;y++)for(int x=ex0;x<ex1;x++){
       const int yj=y+cdy,xj=x+cdx;
       if(yj<2||yj>=h-2||xj<2||xj>=w-2)continue;
       const int i=y*w+x,j=yj*w+xj;
       if(clipped[i]||clipped[j])continue;
       double distance=0.;int count=0;
       for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2){
        const size_t q=size_t(y+py-termY0)*tw+(x+px-termX0);
        if(!valid[q])continue;
        distance+=term[q];count++;
       }
       if(count<7)continue;
       wk[size_t(y-ey0)*ew+(x-ex0)]=
           std::exp(-2.*std::max(0.,distance/count-1.));
      }
     }
     ck++;
    }
   }

   // Apply cached weights in the original scalar candidate order. Clean tiles
   // omit only gates proven false by the bounding scan above.
   if(clean){
    for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){
     const int i=y*w+x;
     double sum=raw[i],ws=1.;
     for(int dy=-4;dy<=4;dy+=2)for(int dx=-4;dx<=4;dx+=2){
      if(!dx&&!dy)continue;
      const int j=(y+dy)*w+(x+dx);
      int k=phase_noise_canonical_index(dy,dx);
      int qx=x,qy=y;
      if(k<0){
       k=phase_noise_canonical_index(-dy,-dx);
       qx=x+dx;qy=y+dy;
      }
      const double weight=weights[size_t(k)*maxPlane+
          size_t(qy-ey0)*ew+(qx-ex0)];
      sum+=weight*raw[j];ws+=weight;
     }
     out[i]=uint16_t(std::llround(sum/ws));
    }
   }else{
    for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){
     const int i=y*w+x;if(clipped[i]||variance[i]<=0)continue;
     double sum=raw[i],ws=1.;
     for(int dy=-4;dy<=4;dy+=2)for(int dx=-4;dx<=4;dx+=2){
      if(!dx&&!dy)continue;
      const int j=(y+dy)*w+(x+dx);if(clipped[j])continue;
      int k=phase_noise_canonical_index(dy,dx);
      int qx=x,qy=y;
      if(k<0){
       k=phase_noise_canonical_index(-dy,-dx);
       qx=x+dx;qy=y+dy;
      }
      const double weight=weights[size_t(k)*maxPlane+
          size_t(qy-ey0)*ew+(qx-ex0)];
      if(weight==0.)continue;
      sum+=weight*raw[j];ws+=weight;
     }
     out[i]=uint16_t(std::llround(sum/ws));
    }
   }
  }
 }
 return 0;
}

extern "C" const char* m9_phasenoiseperf1b_revision(){
 return "M9PHASENOISEPERF1B_SYMTILE_EXACT";
}
extern "C" int m9_phasenoiseperf1b_tile_rows(){return 64;}
extern "C" int m9_phasenoiseperf1b_tile_cols(){return 512;}


// PHASENOISEPERF1C: adaptive exact clean-region recovery.
//
// Keep the proven 64x512 PHASENOISEPERF1B tile as the normal path. If that
// outer tile cannot use the clean fast path because its halo intersects a
// censored/invalid sample or the global frame boundary, subdivide only that
// outer tile into 64x128 target regions. Each subregion independently chooses
// the identical clean or exact fallback arithmetic. This recovers clean-path
// coverage around localized highlights/borders without imposing 128-wide tile
// overhead on already-clean 512-wide regions.
//
// Target regions are disjoint, and each target pixel still walks all 24
// candidates in the original scalar order. No photographic arithmetic changes.
static inline bool phase_noise_region_clean_exact(const float* variance,const uint8_t* clipped,
 int w,int h,int y0,int y1,int x0,int x1){
 const int ey0=std::max(2,y0-4),ey1=std::min(h-2,y1+4);
 const int ex0=std::max(2,x0-4),ex1=std::min(w-2,x1+4);
 const int termY0=ey0-2,termY1=ey1+2;
 const int termX0=ex0-2,termX1=ex1+2;
 const int scanY0=termY0-4,scanY1=termY1;
 const int scanX0=termX0-4,scanX1=termX1+4;
 if(scanY0<0||scanX0<0||scanY1>h||scanX1>w)return false;
 for(int y=scanY0;y<scanY1;y++)for(int x=scanX0;x<scanX1;x++){
  const int i=y*w+x;
  if(clipped[i]||variance[i]<=0)return false;
 }
 return true;
}

static inline void phase_noise_process_region_exact(const uint16_t* raw,const float* variance,
 const uint8_t* clipped,int w,int h,uint16_t* out,
 int y0,int y1,int x0,int x1,bool clean,
 std::vector<double>& weights,std::vector<double>& term,std::vector<uint8_t>& valid,
 size_t maxPlane){
 constexpr int canonicalCount=12;
 (void)canonicalCount;
 const int ey0=std::max(2,y0-4),ey1=std::min(h-2,y1+4);
 const int ex0=std::max(2,x0-4),ex1=std::min(w-2,x1+4);
 const int eh=ey1-ey0,ew=ex1-ex0;
 const size_t plane=size_t(eh)*ew;
 const int termY0=ey0-2,termY1=ey1+2;
 const int termX0=ex0-2,termX1=ex1+2;
 const int th=termY1-termY0,tw=termX1-termX0;
 const size_t termPlane=size_t(th)*tw;

 int ck=0;
 for(int cdy=-4;cdy<=0;cdy+=2){
  const int dxStart=-4,dxEnd=(cdy==0?-2:4);
  for(int cdx=dxStart;cdx<=dxEnd;cdx+=2){
   if(cdy==0 && cdx==0)continue;
   double* wk=weights.data()+size_t(ck)*maxPlane;

   if(clean){
    for(int y=termY0;y<termY1;y++)for(int x=termX0;x<termX1;x++){
     const int a=y*w+x,b=(y+cdy)*w+(x+cdx);
     const double v=double(variance[a])+variance[b];
     const double d=double(raw[a])-raw[b];
     term[size_t(y-termY0)*tw+(x-termX0)]=d*d/v;
    }
    for(int y=ey0;y<ey1;y++)for(int x=ex0;x<ex1;x++){
     double distance=0.;
     for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2)
      distance+=term[size_t(y+py-termY0)*tw+(x+px-termX0)];
     wk[size_t(y-ey0)*ew+(x-ex0)]=
         std::exp(-2.*std::max(0.,distance/9.-1.));
    }
   }else{
    std::fill(wk,wk+plane,0.0);
    std::fill(valid.begin(),valid.begin()+termPlane,uint8_t(0));
    for(int y=termY0;y<termY1;y++)for(int x=termX0;x<termX1;x++){
     const int yb=y+cdy,xb=x+cdx;
     if(yb<0||yb>=h||xb<0||xb>=w)continue;
     const int a=y*w+x,b=yb*w+xb;
     if(clipped[a]||clipped[b])continue;
     const double v=double(variance[a])+variance[b];if(v<=0)continue;
     const double d=double(raw[a])-raw[b];
     const size_t q=size_t(y-termY0)*tw+(x-termX0);
     term[q]=d*d/v;valid[q]=1;
    }
    for(int y=ey0;y<ey1;y++)for(int x=ex0;x<ex1;x++){
     const int yj=y+cdy,xj=x+cdx;
     if(yj<2||yj>=h-2||xj<2||xj>=w-2)continue;
     const int i=y*w+x,j=yj*w+xj;
     if(clipped[i]||clipped[j])continue;
     double distance=0.;int count=0;
     for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2){
      const size_t q=size_t(y+py-termY0)*tw+(x+px-termX0);
      if(!valid[q])continue;
      distance+=term[q];count++;
     }
     if(count<7)continue;
     wk[size_t(y-ey0)*ew+(x-ex0)]=
         std::exp(-2.*std::max(0.,distance/count-1.));
    }
   }
   ck++;
  }
 }

 if(clean){
  for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){
   const int i=y*w+x;
   double sum=raw[i],ws=1.;
   for(int dy=-4;dy<=4;dy+=2)for(int dx=-4;dx<=4;dx+=2){
    if(!dx&&!dy)continue;
    const int j=(y+dy)*w+(x+dx);
    int k=phase_noise_canonical_index(dy,dx);
    int qx=x,qy=y;
    if(k<0){k=phase_noise_canonical_index(-dy,-dx);qx=x+dx;qy=y+dy;}
    const double weight=weights[size_t(k)*maxPlane+
        size_t(qy-ey0)*ew+(qx-ex0)];
    sum+=weight*raw[j];ws+=weight;
   }
   out[i]=uint16_t(std::llround(sum/ws));
  }
 }else{
  for(int y=y0;y<y1;y++)for(int x=x0;x<x1;x++){
   const int i=y*w+x;if(clipped[i]||variance[i]<=0)continue;
   double sum=raw[i],ws=1.;
   for(int dy=-4;dy<=4;dy+=2)for(int dx=-4;dx<=4;dx+=2){
    if(!dx&&!dy)continue;
    const int j=(y+dy)*w+(x+dx);if(clipped[j])continue;
    int k=phase_noise_canonical_index(dy,dx);
    int qx=x,qy=y;
    if(k<0){k=phase_noise_canonical_index(-dy,-dx);qx=x+dx;qy=y+dy;}
    const double weight=weights[size_t(k)*maxPlane+
        size_t(qy-ey0)*ew+(qx-ex0)];
    if(weight==0.)continue;
    sum+=weight*raw[j];ws+=weight;
   }
   out[i]=uint16_t(std::llround(sum/ws));
  }
 }
}

extern "C" int phase_noise_symtile_adaptive_exact(const uint16_t* raw,const float* variance,
 const uint8_t* clipped,int w,int h,uint16_t* out,int workers){
 if(!raw||!variance||!clipped||!out||w<16||h<16||workers<1||workers>8)return -1;
 std::memcpy(out,raw,size_t(w)*h*sizeof(uint16_t));

 constexpr int tileRows=64;
 constexpr int outerCols=512;
 constexpr int dirtySubCols=128;
 constexpr int canonicalCount=12;
 const int firstY=6,lastY=h-6,firstX=6,lastX=w-6;
 const int rows=lastY-firstY,cols=lastX-firstX;
 if(rows<=0||cols<=0)return 0;
 const int tilesY=(rows+tileRows-1)/tileRows;
 const int tilesX=(cols+outerCols-1)/outerCols;
 const int tileCount=tilesY*tilesX;
 const size_t maxPlane=size_t(tileRows+8)*(outerCols+8);
 const size_t maxTermPlane=size_t(tileRows+12)*(outerCols+12);

 #pragma omp parallel num_threads(workers)
 {
  std::vector<double> weights(size_t(canonicalCount)*maxPlane);
  std::vector<double> term(maxTermPlane);
  std::vector<uint8_t> valid(maxTermPlane);

  #pragma omp for schedule(static)
  for(int tile=0;tile<tileCount;tile++){
   const int ty=tile/tilesX,tx=tile%tilesX;
   const int y0=firstY+ty*tileRows,y1=std::min(lastY,y0+tileRows);
   const int x0=firstX+tx*outerCols,x1=std::min(lastX,x0+outerCols);
   const bool outerClean=phase_noise_region_clean_exact(variance,clipped,w,h,y0,y1,x0,x1);
   if(outerClean){
    phase_noise_process_region_exact(raw,variance,clipped,w,h,out,
        y0,y1,x0,x1,true,weights,term,valid,maxPlane);
   }else{
    for(int sx0=x0;sx0<x1;sx0+=dirtySubCols){
     const int sx1=std::min(x1,sx0+dirtySubCols);
     const bool subClean=phase_noise_region_clean_exact(variance,clipped,w,h,y0,y1,sx0,sx1);
     phase_noise_process_region_exact(raw,variance,clipped,w,h,out,
         y0,y1,sx0,sx1,subClean,weights,term,valid,maxPlane);
    }
   }
  }
 }
 return 0;
}

extern "C" const char* m9_phasenoiseperf1c_revision(){
 return "M9PHASENOISEPERF1C_ADAPTIVE128_EXACT";
}
extern "C" int m9_phasenoiseperf1c_outer_tile_rows(){return 64;}
extern "C" int m9_phasenoiseperf1c_outer_tile_cols(){return 512;}
extern "C" int m9_phasenoiseperf1c_dirty_subtile_cols(){return 128;}
