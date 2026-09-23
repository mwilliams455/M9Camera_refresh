#include <cstring>
#include "m9color_jni.cpp"
extern "C" void* trial_context(const double* a,const uint8_t* curve) {
 auto* q=new ColorContext();int p=0;
 for(double& x:q->cw)x=a[p++];
 for(auto* v:{&q->camToPp,&q->ppToM9,&q->adapt50To65,&q->ppToXyz,&q->xyz2Srgb})for(double& x:*v)x=a[p++];
 q->hsm={0,1,1,0,1,1,0,1,1,0,1,1};q->hueDivisions=2;q->satDivisions=2;
 q->skyChromaMode1A=9;std::copy(curve,curve+2048,q->curve.begin());return q;
}
extern "C" void trial_destroy(void* ctx){delete static_cast<ColorContext*>(ctx);}
extern "C" int trial_prepare(void* ctx,const jshort* cam,int w,int h,double gain,uint16_t* out,int band){return trialPrepare(*static_cast<ColorContext*>(ctx),cam,w,h,gain,out,band);}
extern "C" void trial_border(const jshort* raw,int w,int h,int cfa,double nr,double nb,uint16_t* out){trialBorder(raw,w,h,cfa,nr,nb,out);}
extern "C" void trial_fields(void* ctx,const jshort* cam,int n,double gain,uint16_t* out){
 for(int i=0;i<n;i++){double hs[3],m[3];cameraToM9(cam,3*i,*static_cast<ColorContext*>(ctx),hs,m);
 for(int c=0;c<3;c++)out[3*i+c]=uint16_t(clipl(static_cast<int64_t>(std::rint(m[c]*gain*RAW_MAX)),0,RAW_MAX));}
}
extern "C" void trial_colour(void* ctx,const jshort* q14,int w,int h,int bank,double cb,double cr,int* out){
 ColorContext q=*static_cast<ColorContext*>(ctx);q.colourTrialPrepared=true;q.skyChromaMode1A=bank==2?9:bank==4?10:0;
 int64_t stats[3]={};renderStripScalar(q,q14,w*h,w,out,1.,cb,cr,stats);
}
extern "C" JNIEXPORT jlong JNICALL Java_com_particlesdevs_photoncamera_m9_render_TrialJniCheck_address(JNIEnv* env,jclass,jobject b){return reinterpret_cast<jlong>(env->GetDirectBufferAddress(b));}
