// Offline interpolation control. Not recovered Leica firmware or an app patch.
// Interpolate measured-phase Co2 differences directly using native pre-Sharp
// green as a range guide. The caller supplies sensor-based anchor validity.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>

static int q14(uint16_t v){return (uint32_t(v)*16383+32767)/65535;}
static uint16_t q16(int64_t v){v=std::clamp<int64_t>(v,0,16383);return (v*65535+8191)/16383;}

extern "C" void edge_guided_chroma(const uint16_t* green,const int32_t* diff,
        const uint8_t* valid,const uint8_t* support,const uint16_t* base,
        int w,int h,int cfa,double nr,double nb,double scale,uint16_t* out){
    std::memcpy(out,base,size_t(w)*h*3*sizeof(uint16_t));
    double range[16384],spatial[13][13];
    for(int d=0;d<16384;d++)range[d]=std::exp(-.5*std::pow(d*scale/16383/.08,2));
    for(int y=-6;y<=6;y++)for(int x=-6;x<=6;x++)spatial[y+6][x+6]=std::exp(-(x*x+y*y)/18.);
    int rx=cfa==1||cfa==3,ry=cfa==2||cfa==3;
    #pragma omp parallel for schedule(static) num_threads(4)
    for(int y=10;y<h-10;y++)for(int x=10;x<w-10;x++){
        int i=y*w+x;if(!support[i])continue;
        int sg=q14(base[3*i+1]);
        for(int channel: {0,2}){
            int ax=channel==0?rx:1-rx,ay=channel==0?ry:1-ry;
            double total=0,value=0;
            for(int yy=y-6;yy<=y+6;yy++){
                if((yy&1)!=ay)continue;
                for(int xx=x-6;xx<=x+6;xx++){
                    if((xx&1)!=ax)continue;
                    int j=yy*w+xx;if(!valid[j])continue;
                    double weight=spatial[yy-y+6][xx-x+6]*range[std::abs(int(green[i])-green[j])];
                    total+=weight;value+=weight*diff[j];
                }
            }
            if(total<=1e-12)continue;
            double nc=channel==0?nr:nb;
            out[3*i+channel]=q16(std::llround(nc*(sg+value/total)));
        }
    }
}
