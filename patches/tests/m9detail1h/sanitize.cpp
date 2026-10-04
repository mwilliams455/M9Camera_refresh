#define M9DETAIL1H_HOST
#include "../../m9detail1h/m9detail1h.cpp"
#include <cassert>
#include <iostream>
int main(){
    size_t count=0;
    for(int w:{24,65,257})for(int h:{25,67,259})for(int cfa=0;cfa<4;++cfa){
        size_t n=size_t(w)*h;std::vector<uint16_t> raw(n),norm(n),base(n*3),rgb(n*3),fallback(n*3);
        for(size_t i=0;i<n;++i){raw[i]=uint16_t(1000+i%9000);norm[i]=raw[i];for(int c=0;c<3;++c)base[i*3+c]=uint16_t(3000+i%11000);}
        const float black[4]={64,64,64,64};const double profile[6]={.0002,.000001,.00015,.000001,.00025,.000001};
        const double gains[4]={1,1,1,1};double stats[10];
        rgb=base;assert(detail1h_host(norm.data(),raw.data(),w,h,cfa,0,black,65535,profile,gains,1,1,1.,.37,.61,64,1,rgb.data(),stats)==0);
        for(size_t i=0;i<n;++i)assert(rgb[i*3+1]==base[i*3+1]);
        fallback=base;assert(detail1h_host(norm.data(),raw.data(),w,h,cfa,0,black,65535,profile,gains,1,1,1.,.37,.61,64,0,fallback.data(),stats)==0);
        detail1h_fail_guard_tile(0);rgb=base;
        assert(detail1h_host(norm.data(),raw.data(),w,h,cfa,0,black,65535,profile,gains,1,1,1.,.37,.61,64,1,rgb.data(),stats)==0);
        assert(rgb==fallback&&stats[0]==2.);count+=n*3;
    }
    std::cout<<"DETAIL1H ASan/UBSan PASS: "<<count<<" RGB samples\n";
}
