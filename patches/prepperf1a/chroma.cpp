// Offline trial. Partial directional chroma correction in pre-SAT Q14.
// Hue independent; no ISO/scene switch. Connected colour lines with one
// agreeing direction remain unchanged. Isolated real colour may still change.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <thread>
#include <vector>
static int med(int a,int b,int c){return a+b+c-std::min({a,b,c})-std::max({a,b,c});}
extern "C" int partial_chroma(const uint16_t* src,int w,int h,double amount,uint16_t* out){
 if(!src||!out||w<1||h<1||!std::isfinite(amount)||amount<0||amount>1)return -1;
 std::memcpy(out,src,size_t(w)*h*3*sizeof(uint16_t));
 if(amount==0)return 0;
 const int delta[4]={1,w,w+1,w-1};
 for(int y=1;y<h-1;y++)for(int x=1;x<w-1;x++){
  int i=y*w+x,r=int(src[3*i])-src[3*i+1],b=int(src[3*i+2])-src[3*i+1];
  int rr=r,bb=b;int64_t distance=INT64_MAX;
  for(int d:delta){
   int j=i-d,k=i+d;
   int mr=med(int(src[3*j])-src[3*j+1],r,int(src[3*k])-src[3*k+1]);
   int mb=med(int(src[3*j+2])-src[3*j+1],b,int(src[3*k+2])-src[3*k+1]);
   int64_t dr=mr-r,db=mb-b,dd=dr*dr+db*db;
   if(dd<distance){distance=dd;rr=mr;bb=mb;}
  }
  if(distance==0)continue;
  double nr=r+amount*(rr-r),nb=b+amount*(bb-b);
  double lum=.2126*src[3*i]+.7152*src[3*i+1]+.0722*src[3*i+2];
  double g=lum-.2126*nr-.0722*nb,v[3]={g+nr,g,g+nb};
  for(int c=0;c<3;c++)out[3*i+c]=uint16_t(std::clamp<long>(std::lround(v[c]),0,16383));
 }
 return 0;
}

// PREPPERF1A: exact row-parallel form of partial_chroma. The source is immutable,
// each worker owns disjoint destination rows, and the scalar arithmetic above is
// copied verbatim. The original scalar entry point is retained as the parity oracle.
extern "C" int partial_chroma_parallel(const uint16_t* src,int w,int h,double amount,uint16_t* out,int workers){
 if(!src||!out||w<1||h<1||workers<1||workers>8||!std::isfinite(amount)||amount<0||amount>1)return -1;
 std::memcpy(out,src,size_t(w)*h*3*sizeof(uint16_t));
 if(amount==0||h<3||w<3)return 0;
 const int rows=h-2,used=std::min(workers,rows);
 if(used<=1)return partial_chroma(src,w,h,amount,out);
 const int delta[4]={1,w,w+1,w-1};
 std::vector<std::thread> threads;threads.reserve(used);
 for(int t=0;t<used;t++){
  const int y0=1+(rows*t)/used,y1=1+(rows*(t+1))/used;
  threads.emplace_back([=]{
   for(int y=y0;y<y1;y++)for(int x=1;x<w-1;x++){
    int i=y*w+x,r=int(src[3*i])-src[3*i+1],b=int(src[3*i+2])-src[3*i+1];
    int rr=r,bb=b;int64_t distance=INT64_MAX;
    for(int d:delta){
     int j=i-d,k=i+d;
     int mr=med(int(src[3*j])-src[3*j+1],r,int(src[3*k])-src[3*k+1]);
     int mb=med(int(src[3*j+2])-src[3*j+1],b,int(src[3*k+2])-src[3*k+1]);
     int64_t dr=mr-r,db=mb-b,dd=dr*dr+db*db;
     if(dd<distance){distance=dd;rr=mr;bb=mb;}
    }
    if(distance==0)continue;
    double nr=r+amount*(rr-r),nb=b+amount*(bb-b);
    double lum=.2126*src[3*i]+.7152*src[3*i+1]+.0722*src[3*i+2];
    double g=lum-.2126*nr-.0722*nb,v[3]={g+nr,g,g+nb};
    for(int c=0;c<3;c++)out[3*i+c]=uint16_t(std::clamp<long>(std::lround(v[c]),0,16383));
   }
  });
 }
 for(auto& t:threads)t.join();
 return 0;
}
