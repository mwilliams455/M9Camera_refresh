#define M9DETAIL1H_HOST
#include "../../m9detail1o/m9detail1h.cpp"
#include <cassert>
#include <iostream>
int main(){
    size_t count=0;
    for(int w:{24,65,129,257})for(int h:{25,67,127,259})for(int cfa=0;cfa<4;++cfa){
        size_t n=size_t(w)*h;std::vector<uint16_t> sensor(n),norm(n),base(n*3),rgb(n*3),fallback(n*3);
        const int rx=cfa&1,ry=cfa>>1;
        for(int y=0;y<h;++y)for(int x=0;x<w;++x){
            size_t i=size_t(y)*w+x;bool red=(x&1)==rx&&(y&1)==ry,blue=(x&1)!=rx&&(y&1)!=ry;
            double nc=red?.41796875:blue?.6435546875:1.;
            double lum=((x+y*.43)-15*int((x+y*.43)/15)<4)?.05:1.4;
            int v=int(std::llround(64+std::min(1.,lum*nc)*(1023-64)));
            sensor[i]=uint16_t(std::clamp(v,64,1023));
            norm[i]=uint16_t(std::llround((sensor[i]-64.)/(1023-64)*65535.));
            base[i*3]=uint16_t(3000+i%12000);base[i*3+1]=uint16_t(5000+i%45000);base[i*3+2]=uint16_t(4000+i%13000);
        }
        const float black[4]={64,64,64,64};const double profile[6]={2.7e-5,4.4e-7,3.1e-5,3.7e-7,2.6e-5,4.5e-7};
        const double gains[4]={1,1,1,1};double stats[15];
        rgb=base;assert(detail1h_host(norm.data(),sensor.data(),w,h,cfa,0,black,1023,profile,gains,1,1,1.,.41796875,.6435546875,64,1,rgb.data(),stats)==0);
        for(size_t i=0;i<n;++i)assert(rgb[i*3+1]==base[i*3+1]);
        assert(stats[10]>=0&&stats[11]>=0&&stats[12]>=0&&stats[13]>=stats[10]&&stats[14]>=0);
        fallback=base;assert(detail1h_host(norm.data(),sensor.data(),w,h,cfa,0,black,1023,profile,gains,1,1,1.,.41796875,.6435546875,64,0,fallback.data(),stats)==0);
        detail1h_fail_guard_tile(0);rgb=base;
        assert(detail1h_host(norm.data(),sensor.data(),w,h,cfa,0,black,1023,profile,gains,1,1,1.,.41796875,.6435546875,64,1,rgb.data(),stats)==0);
        assert(rgb==fallback&&stats[0]==2.);count+=n*3;
    }
    std::cout<<"M9DETAIL1O ASan/UBSan PASS: "<<count<<" RGB samples\n";
}
