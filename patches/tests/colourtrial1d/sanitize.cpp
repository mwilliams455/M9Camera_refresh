#include <vector>
#include <cstdint>
#include <cassert>
#include <iostream>
extern "C" int trial_reconstruct(const uint16_t*,const float*,const uint8_t*,int,int,int,double,double,double,uint16_t*,int,double*);
extern "C" void* trial_context(const double*,const uint8_t*);
extern "C" void trial_destroy(void*);
extern "C" int trial_prepare_inplace(void*,int16_t*,int,int,double,int);
int main(){
 {uint16_t a[32*32]={},b[32*32*3]={};double stats[4];assert(trial_reconstruct(a,nullptr,nullptr,32,32,0,.37,.61,1.7,b,8,stats)==-1);}
 for(int w:{64,65,128,129,256,257,512,513})for(int h:{64,129,256,257,513}){
  size_t n=size_t(w)*h;std::vector<uint16_t> raw(n),out(n*3);std::vector<float> variance(n,30000);std::vector<uint8_t> mask(n,0);
  for(size_t i=0;i<n;i++)raw[i]=uint16_t((i*2719+32768)%65536);
  for(int cfa=0;cfa<4;cfa++)for(int workers:{1,8}){
   double stats[4];assert(trial_reconstruct(raw.data(),variance.data(),mask.data(),w,h,cfa,.37,.61,1.7,out.data(),workers,stats)==0);
  }
  double a[48]={1,1,1};for(int i=3;i<48;i+=9)a[i]=a[i+4]=a[i+8]=1;uint8_t curve[2048]={};
  void* ctx=trial_context(a,curve);assert(ctx);assert(trial_prepare_inplace(ctx,reinterpret_cast<int16_t*>(out.data()),w,h,1.4,128)==0);trial_destroy(ctx);
 }
 std::cout<<"ASAN_UBSAN_PASS 320 reconstruction cases, 40 in-place preparations, workers 1/8\n";
}
