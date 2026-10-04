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
extern "C" int trial_prepare_inplace(void* ctx,jshort* cam,int w,int h,double gain,int band){return trialPrepareInPlace(*static_cast<ColorContext*>(ctx),cam,w,h,gain,band);}


static int trialPrepareInPlace1AReference(const ColorContext& ctx,jshort* cam,int w,int h,double gain,int bandRows=128) {
 if(!cam||w<1||h<1||w>8192||h>8192||!std::isfinite(gain)||gain<=0||bandRows<2)return -1;
 constexpr int prepWorkers=8;
 auto* out=reinterpret_cast<uint16_t*>(cam);
 try {
  std::vector<uint16_t> previous(size_t(w)*2*3);
  for(int top=0;top<h;top+=bandRows) {
   const int bottom=std::min(h,top+bandRows),start=std::max(0,top-2),end=std::min(h,bottom+2),bh=end-start;
   std::vector<uint16_t> q(size_t(w)*bh*3),corrected(q.size());
   if(top>0)std::memcpy(q.data(),previous.data(),size_t(w)*2*3*sizeof(uint16_t));
   prepParallelRows(top,end,prepWorkers,[&](int y){
    for(int x=0;x<w;x++){
     double hsm[3],m[3];cameraToM9(cam,3*(y*w+x),ctx,hsm,m);
     for(int c=0;c<3;c++)q[3*(size_t(y-start)*w+x)+c]=uint16_t(clipl(static_cast<int64_t>(std::rint(m[c]*gain*RAW_MAX)),0,RAW_MAX));
    }
   });
   if(bottom<h)std::memcpy(previous.data(),q.data()+size_t(bottom-start-2)*w*3,size_t(w)*12);
   int rc=partial_chroma_parallel(q.data(),w,bh,.25,corrected.data(),prepWorkers);if(rc)return rc;
   std::memcpy(out+size_t(top)*w*3,corrected.data()+size_t(top-start)*w*3,size_t(bottom-top)*w*6);
  }
 }catch(...){return -30;}
 return 0;
}
extern "C" int trial_prepare_inplace_1a(void* ctx,jshort* cam,int w,int h,double gain,int band){
 return trialPrepareInPlace1AReference(*static_cast<ColorContext*>(ctx),cam,w,h,gain,band);
}
