// JPEGPERF349: ThreadSanitizer driver for the band queue on a wide, short frame (8 workers, 9 bands).
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
extern "C" int m9_noisecancel1b_apply(uint16_t*,int,int,const double*,const double*,int,int,double,double*);
extern "C" int m9_noisecancel1b_apply_scalar_reference(uint16_t*,int,int,const double*,const double*,int,int,double,double*);
int main(){
 const int w=8000,h=300,mw=17,mh=13;const double scale=1.72;
 const double profile[6]={.00135,6.7e-6,.00134,6.1e-6,.00137,6.8e-6};
 std::vector<double> gains(mw*mh*4);
 for(int i=0;i<mw*mh;i++){const double g=std::fmin(scale,1.+.3*std::sin(i*.37)*std::sin(i*.37));for(int c=0;c<4;c++)gains[4*i+c]=g;}
 std::vector<uint16_t> a(size_t(w)*h*3);uint32_t s=349;
 for(auto& v:a){s=s*1664525u+1013904223u;v=uint16_t(9000+(s>>20));}
 std::vector<uint16_t> b=a;double sa[14]={},sb[14]={};
 if(m9_noisecancel1b_apply(a.data(),w,h,profile,gains.data(),mw,mh,scale,sa))return 2;
 if(m9_noisecancel1b_apply_scalar_reference(b.data(),w,h,profile,gains.data(),mw,mh,scale,sb))return 3;
 const bool same=std::memcmp(a.data(),b.data(),a.size()*2)==0&&sa[12]==8;
 std::printf("%s noise-cancel queue under ThreadSanitizer %dx%d, %d workers\n",same?"PASS":"FAIL",w,h,int(sa[12]));
 return same?0:1;
}
