// DETAIL1C: pre-Noise colour difference carrier and final R/B consumer probe.
// Noise2 is intentionally absent. Green/Sharp and outer ten pixels stay baseline.
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <vector>
static int divfloor(int v,int n){return v>=0?v/n:-((-v+n-1)/n);}
static int q14(int v){return (v*16383+32767)/65535;}
static uint16_t q16(int v){v=std::clamp(v,0,16383);return (v*65535+8191)/16383;}
static int interp(const int16_t* d,int w,int y,int x,int ax,int ay){
    bool hx=(x&1)!=ax,hy=(y&1)!=ay;
    auto row=[&](int yy){return hx?divfloor(int(d[yy*w+x-1])+d[yy*w+x+1],2):int(d[yy*w+x]);};
    return hy?divfloor(row(y-1)+row(y+1),2):row(y);
}
extern "C" void rb_stages(const uint16_t* raw,int w,int h,int cfa,int shrink,
        uint16_t* green,int16_t* diff,int16_t* carrier,uint16_t* uncertainty){
    int n=w*h,rx=(cfa==1||cfa==3),ry=(cfa==2||cfa==3);
    std::vector<int> z(n),res(n,0);
    for(int i=0;i<n;i++)z[i]=q14(raw[i]);
    std::fill(green,green+n,0);std::fill(diff,diff+n,0);
    std::fill(carrier,carrier+n,0);std::fill(uncertainty,uncertainty+n,0);
    for(int y=1;y<h-1;y++)for(int x=1;x<w-1;x++){
        int i=y*w+x;bool g=((x&1)==rx)!=((y&1)==ry);
        int v=g?(4*z[i]+z[i-w-1]+z[i-w+1]+z[i+w-1]+z[i+w+1])/8:
            (z[i-w]+z[i+w]+z[i-1]+z[i+1])/4;
        green[i]=v;if(g)res[i]=std::abs(v-z[i]);
    }
    for(int y=2;y<h-2;y++)for(int x=2;x<w-2;x++){
        if(((x&1)==rx)!=((y&1)==ry))continue;
        int i=y*w+x,a=res[i-w]+res[i+w]+res[i-1]+res[i+1],d=z[i]-green[i];
        uncertainty[i]=a;
        if(shrink&&std::abs(d)<a){int v=std::max(std::abs(d)-(a>>2),0);d=d<0?-v:v;}
        diff[i]=d;
    }
    for(int y=3;y<h-3;y++)for(int x=3;x<w-3;x++){
        if(((x&1)==rx)!=((y&1)==ry))continue;
        int i=y*w+x;carrier[i]=divfloor(int(diff[i-w-1])+diff[i-w+1]+diff[i+w-1]+diff[i+w+1],4);
    }
}
extern "C" void rb_consume(const int16_t* carrier,const uint16_t* base,int w,int h,int cfa,uint16_t* out){
    std::memcpy(out,base,w*h*3*sizeof(uint16_t));
    int rx=(cfa==1||cfa==3),ry=(cfa==2||cfa==3);
    for(int y=10;y<h-10;y++)for(int x=10;x<w-10;x++){
        int i=(y*w+x)*3,sg=q14(base[i+1]);
        out[i]=q16(sg+interp(carrier,w,y,x,1-rx,1-ry));
        out[i+2]=q16(sg+interp(carrier,w,y,x,rx,ry));
    }
}
