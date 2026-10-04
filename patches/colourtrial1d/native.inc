#include <cstring>
// Included after the original kernel definitions to reuse the frozen transforms,
// no-Sharp MHC border, SAT, curve, TG1, 4:2:2 pairing and orientation code.
extern "C" int trial_variance(const uint16_t*,int,int,int,int,const float*,int,const double*,const double*,int,int,double,float*,uint8_t*);
extern "C" int trial_reconstruct(const uint16_t*,const float*,const uint8_t*,int,int,int,double,double,double,uint16_t*,int,double*);
extern "C" int partial_chroma(const uint16_t*,int,int,double,uint16_t*);

static int trialPrepare(const ColorContext& ctx,const jshort* cam,int w,int h,double gain,uint16_t* out,int bandRows=128) {
    if(!cam||!out||w<1||h<1||w>8192||h>8192||!std::isfinite(gain)||gain<=0||bandRows<1)return -1;
    try {
        for(int top=0;top<h;top+=bandRows) {
            const int bottom=std::min(h,top+bandRows),start=std::max(0,top-2),end=std::min(h,bottom+2),bh=end-start;
            std::vector<uint16_t> q(size_t(w)*bh*3),corrected(q.size());
            for(int y=start;y<end;y++)for(int x=0;x<w;x++) {
                double hsm[3],m[3];cameraToM9(cam,3*(y*w+x),ctx,hsm,m);
                for(int c=0;c<3;c++)q[3*(size_t(y-start)*w+x)+c]=uint16_t(clipl(static_cast<int64_t>(std::rint(m[c]*gain*RAW_MAX)),0,RAW_MAX));
            }
            int rc=partial_chroma(q.data(),w,bh,.25,corrected.data());if(rc)return rc;
            std::memcpy(out+size_t(top)*w*3,corrected.data()+size_t(top-start)*w*3,size_t(bottom-top)*w*6);
        }
    }catch(...){return -30;}
    return 0;
}
static int trialPrepareInPlace(const ColorContext& ctx,jshort* cam,int w,int h,double gain,int bandRows=128) {
    if(!cam||w<1||h<1||w>8192||h>8192||!std::isfinite(gain)||gain<=0||bandRows<2)return -1;
    auto* out=reinterpret_cast<uint16_t*>(cam);
    try {
        std::vector<uint16_t> previous(size_t(w)*2*3);
        for(int top=0;top<h;top+=bandRows) {
            const int bottom=std::min(h,top+bandRows),start=std::max(0,top-2),end=std::min(h,bottom+2),bh=end-start;
            std::vector<uint16_t> q(size_t(w)*bh*3),corrected(q.size());
            for(int y=start;y<end;y++)for(int x=0;x<w;x++) {
                if(y<top) {std::memcpy(q.data()+3*(size_t(y-start)*w+x),previous.data()+3*(size_t(y-start)*w+x),6);continue;}
                double hsm[3],m[3];cameraToM9(cam,3*(y*w+x),ctx,hsm,m);
                for(int c=0;c<3;c++)q[3*(size_t(y-start)*w+x)+c]=uint16_t(clipl(static_cast<int64_t>(std::rint(m[c]*gain*RAW_MAX)),0,RAW_MAX));
            }
            // Preserve uncorrected transformed halo before overwriting the camera buffer.
            if(bottom<h)std::memcpy(previous.data(),q.data()+size_t(bottom-start-2)*w*3,size_t(w)*12);
            int rc=partial_chroma(q.data(),w,bh,.25,corrected.data());if(rc)return rc;
            std::memcpy(out+size_t(top)*w*3,corrected.data()+size_t(top-start)*w*3,size_t(bottom-top)*w*6);
        }
    }catch(...){return -30;}
    return 0;
}
static void trialBorder(const jshort* raw,int w,int h,int cfa,double nr,double nb,uint16_t* out) {
    for(int y=0;y<h;y++)for(int x=0;x<w;x++) {
        if(x>=16&&x<w-16&&y>=16&&y<h-16)continue;
        uint16_t* pixel=out+3*(size_t(y)*w+x);
        if(cfa==0){
            uint16_t g=mhcNeutralGreenRggb(raw,w,h,y,x,1./nr,1./nb);
            mhcPixelNeutralRbCompleteRggb(raw,w,h,y,x,g,pixel,nr,nb,1./nr,1./nb);
        }else{
            uint16_t g=mhcNeutralGreenBayerPhase(raw,w,h,y,x,1./nr,1./nb,cfa&1,cfa>>1);
            mhcPixelNeutralRbCompleteBayerPhase(raw,w,h,y,x,g,pixel,nr,nb,1./nr,1./nb,cfa&1,cfa>>1);
        }
    }
}
extern "C" JNIEXPORT jint JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9ColourTrial1C_reconstruct(JNIEnv* env,jclass,
 jshortArray norm,jobject sensorBuffer,jobject rgbBuffer,jint w,jint h,jint cfa,jint originY,
 jfloatArray blackArray,jint white,jdoubleArray profileArray,jdoubleArray gainsArray,jint mw,jint mh,
 jdouble scale,jdouble nr,jdouble nb,jint workers,jdoubleArray statsArray) {
    if(!norm||!rgbBuffer||!statsArray||w<64||h<64||w>8192||h>8192||cfa<0||cfa>3||
       env->GetArrayLength(norm)!=w*h||env->GetArrayLength(statsArray)<5)return -1;
    auto* out=static_cast<uint16_t*>(env->GetDirectBufferAddress(rgbBuffer));
    if(!out||env->GetDirectBufferCapacity(rgbBuffer)<int64_t(w)*h*6)return -2;
    try {
        const auto start=std::chrono::steady_clock::now();const size_t count=size_t(w)*h;
        std::vector<uint16_t> raw(count);env->GetShortArrayRegion(norm,0,w*h,reinterpret_cast<jshort*>(raw.data()));
        if(env->ExceptionCheck())return -3;
        std::vector<float> variance;std::vector<uint8_t> censored;bool noise=false;
        if(profileArray&&gainsArray&&blackArray&&sensorBuffer&&mw>0&&mh>0&&mw<=256&&mh<=256&&
           env->GetArrayLength(profileArray)==6&&env->GetArrayLength(blackArray)==4&&env->GetArrayLength(gainsArray)==mw*mh*4) {
            const auto* sensor=static_cast<const uint16_t*>(env->GetDirectBufferAddress(sensorBuffer));
            if(sensor&&env->GetDirectBufferCapacity(sensorBuffer)>=int64_t(count)*2) {
                float black[4];double profile[6];std::vector<double> gains(mw*mh*4);
                env->GetFloatArrayRegion(blackArray,0,4,black);env->GetDoubleArrayRegion(profileArray,0,6,profile);
                env->GetDoubleArrayRegion(gainsArray,0,mw*mh*4,gains.data());if(env->ExceptionCheck())return -3;
                variance.resize(count);censored.resize(count);
                noise=trial_variance(sensor,w,h,cfa,originY,black,white,profile,gains.data(),mw,mh,scale,variance.data(),censored.data())==0;
            }
        }
        double stats[5]={};
        int rc=trial_reconstruct(raw.data(),noise?variance.data():nullptr,noise?censored.data():nullptr,
                w,h,cfa,nr,nb,scale,out,workers,stats);if(rc)return rc;
        trialBorder(reinterpret_cast<const jshort*>(raw.data()),w,h,cfa,nr,nb,out);
        stats[4]=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        env->SetDoubleArrayRegion(statsArray,0,5,stats);return env->ExceptionCheck()?-3:0;
    }catch(...){return -30;}
}
extern "C" JNIEXPORT jint JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9ColourTrial1C_prepare(JNIEnv* env,jclass,
 jlong context,jlong camera,jint w,jint h,jdouble gain,jobject buffer) {
    if(!context||!camera||!buffer||w<1||h<1||w>8192||h>8192)return -1;
    auto* out=static_cast<uint16_t*>(env->GetDirectBufferAddress(buffer));
    if(!out||env->GetDirectBufferCapacity(buffer)<int64_t(w)*h*6)return -2;
    return trialPrepare(*reinterpret_cast<ColorContext*>(context),reinterpret_cast<const jshort*>(camera),w,h,gain,out);
}
extern "C" JNIEXPORT jobject JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9ColourTrial1C_prepareInPlace(JNIEnv* env,jclass,
 jlong context,jlong camera,jint w,jint h,jdouble gain) {
    if(!context||!camera||w<1||h<1||w>8192||h>8192)return nullptr;
    int rc=trialPrepareInPlace(*reinterpret_cast<ColorContext*>(context),reinterpret_cast<jshort*>(camera),w,h,gain);
    if(rc)return nullptr;
    // Borrowed view. Java retains the owning OpenCV Mat until all renders finish.
    return env->NewDirectByteBuffer(reinterpret_cast<void*>(camera),int64_t(w)*h*6);
}
static const jshort* trialBlock(JNIEnv* env,jobject buffer,int w,int h,int y0,int pixels) {
    if(!buffer||w<1||h<1||w>8192||h>8192||y0<0||y0>=h||pixels<1||pixels%w||pixels/w>h-y0)return nullptr;
    auto* src=static_cast<const jshort*>(env->GetDirectBufferAddress(buffer));
    if(!src||env->GetDirectBufferCapacity(buffer)<int64_t(w)*h*6)return nullptr;
    return src+size_t(y0)*w*3;
}
extern "C" JNIEXPORT void JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9ColourTrial1C_renderDirect(JNIEnv* env,jclass cls,
 jlong context,jobject buffer,jint w,jint h,jint y0,jint pixels,jintArray argb,
 jdouble cb,jdouble cr,jint rotation,jint workers,jlongArray stats) {
    const auto* src=trialBlock(env,buffer,w,h,y0,pixels);
    if(!src||!context){env->ThrowNew(env->FindClass("java/lang/IllegalArgumentException"),"Invalid COLOURTRIAL1C colour buffer");return;}
    try {
        ColorContext copy=*reinterpret_cast<ColorContext*>(context);copy.colourTrialPrepared=true;
        Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallelDirect(env,cls,
            reinterpret_cast<jlong>(&copy),reinterpret_cast<jlong>(src),pixels,w,argb,1.,cb,cr,rotation,workers,stats);
    }catch(...){env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),"COLOURTRIAL1C colour rendering failed");}
}
extern "C" JNIEXPORT jboolean JNICALL
Java_com_particlesdevs_photoncamera_m9_render_M9ColourTrial1C_renderBitmap(JNIEnv* env,jclass cls,
 jlong context,jobject buffer,jint w,jint h,jint y0,jint pixels,jobject bitmap,
 jdouble cb,jdouble cr,jint rotation,jint workers,jlongArray stats) {
    const auto* src=trialBlock(env,buffer,w,h,y0,pixels);if(!src||!context)return JNI_FALSE;
    try {
        ColorContext copy=*reinterpret_cast<ColorContext*>(context);copy.colourTrialPrepared=true;
        return Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallelDirectBitmap(env,cls,
            reinterpret_cast<jlong>(&copy),reinterpret_cast<jlong>(src),pixels,w,bitmap,y0,h,1.,cb,cr,rotation,workers,stats);
    }catch(...){env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),"COLOURTRIAL1C bitmap rendering failed");return JNI_FALSE;}
}
