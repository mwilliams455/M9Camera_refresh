#include "m9color_jni.cpp"
extern "C" void saturation_probe(int mode,const double* samples,int count,const uint8_t* curve,uint8_t* out) {
 ColorContext ctx;ctx.skyChromaMode1A=mode;
 std::copy(curve,curve+2048,ctx.curve.begin());
 for(int i=0;i<count;i++){int rgb[3];m9CurvePixel(samples+3*i,1.0,ctx,rgb);for(int c=0;c<3;c++)out[3*i+c]=rgb[c];}
}
