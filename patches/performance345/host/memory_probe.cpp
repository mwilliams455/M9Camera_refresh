#include <atomic>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <cstdint>
#include <cstddef>
#include <new>
#include <vector>
#include <sys/resource.h>
#include "raw16_adapter.h"
extern "C" int parent_m9_dng_noise_raw16(const uint16_t*,size_t,uint16_t*,size_t,int,int,int,int,const double*,const double*,const float*,int,int) noexcept;
namespace {
constexpr size_t scratch = 4096*68*sizeof(double);
struct alignas(std::max_align_t) Header {size_t bytes;};
std::atomic<int> active{0}, peak{0}, rejects{0};
int limit=1000;
}
void* operator new(size_t n) {
    if(n==scratch){
        int count=active.fetch_add(1)+1;
        if(count>limit){active--;rejects++;throw std::bad_alloc();}
        int seen=peak.load();while(count>seen&&!peak.compare_exchange_weak(seen,count)){}
    }
    auto* h=static_cast<Header*>(std::malloc(sizeof(Header)+n));if(!h)throw std::bad_alloc();
    h->bytes=n;return h+1;
}
void operator delete(void* ptr) noexcept {
    if(!ptr)return;
    auto* h=static_cast<Header*>(ptr)-1;
    if(h->bytes==scratch)active--;
    std::free(h);
}
void operator delete(void* ptr, size_t) noexcept{::operator delete(ptr);}
int main(int argc,char** argv){
    if(argc!=3)return 1;
    limit=std::atoi(argv[2]);
    int w=4096,h=3072;
    std::vector<uint16_t> src(w*h),dst(w*h);
    for(size_t i=0;i<src.size();i++)src[i]=400+(i*13+i/w*5)%11;
    double black[4]={64,64,64,64},profile[8]={.0002,.00002,.0002,.00002,.0002,.00002,.0002,.00002};
    float gains[4]={1,1,1,1};
    auto api=!std::strcmp(argv[1],"parent") ? parent_m9_dng_noise_raw16 : m9_dng_noise_raw16;
    int rc=api(src.data(),src.size()*2,dst.data(),dst.size()*2,w,h,1023,16,black,profile,gains,1,1);
    uint64_t digest=14695981039346656037ULL;
    if(rc==0)for(uint16_t value:dst){digest^=value;digest*=1099511628211ULL;}
    int changed=0; if(rc==0)for(size_t i=0;i<src.size();i++)changed+=dst[i]!=src[i]*16;
    struct rusage u{};getrusage(RUSAGE_SELF,&u);
    std::printf("%s allowance=%d status=%d scratch double arrays peak=%d rejections=%d maxRSS=%.1f MiB changed=%d digest=%016llx\n",argv[1],limit,rc,peak.load(),rejects.load(),u.ru_maxrss/1024.,changed,static_cast<unsigned long long>(digest));
}
