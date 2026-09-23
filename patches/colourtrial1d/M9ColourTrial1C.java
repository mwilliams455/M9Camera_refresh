package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Bitmap;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.LensShadingMap;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import org.json.JSONArray;
import org.json.JSONObject;

/** Selected colour balance. No Sharp, clipped-ratio repair or ISO scene switching. */
final class M9ColourTrial1C {
    static final String ID="M9COLOURTRIAL1C_AMAZE_QUARTER";
    private M9ColourTrial1C() {}
    private static native int reconstruct(short[] norm, ByteBuffer sensor, ByteBuffer rgb,
            int w,int h,int cfa,int originY,float[] black,int white,double[] profile,
            double[] gains,int mw,int mh,double scale,double nr,double nb,int workers,double[] stats);
    private static native int prepare(long context,long camera,int w,int h,double gain,ByteBuffer q14);
    private static native void renderDirect(long context,ByteBuffer q14,int w,int h,int y0,
            int pixels,int[] argb,double cb,double cr,int rotation,int workers,long[] stats);
    private static native boolean renderBitmap(long context,ByteBuffer q14,int w,int h,int y0,
            int pixels,Bitmap bitmap,double cb,double cr,int rotation,int workers,long[] stats);

    static JSONObject apply(short[] norm,ByteBuffer sensor,ByteBuffer rgb,int w,int h,
            int sourceCfa,int originX,int originY,float[] black,int white,float[] neutral,
            LensShadingMap map,double alpha,double scale,CaptureResult capture,int workers) throws Exception {
        double[] profile=M9Detail1H.packRgb(capture==null?null:capture.get(CaptureResult.SENSOR_NOISE_PROFILE),sourceCfa);
        int mw=map==null?0:map.getColumnCount(),mh=map==null?0:map.getRowCount();
        float[] grid=map==null?null:new float[map.getGainFactorCount()];if(grid!=null)map.copyGainFactors(grid,0);
        double[] gains=M9Detail1H.decompose(grid,alpha,scale);
        boolean noise=profile!=null&&gains!=null&&mw>0&&mh>0&&mw<=256&&mh<=256&&gains.length==mw*mh*4;
        int cfa=((sourceCfa&1)^(originX&1))+2*((sourceCfa>>1)^(originY&1));
        double nr=(double)neutral[0]/neutral[1],nb=(double)neutral[2]/neutral[1];
        double[] stats=new double[5];
        int rc=reconstruct(norm,sensor,rgb,w,h,cfa,originY,black,white,noise?profile:null,
                noise?gains:null,mw,mh,scale,nr,nb,workers,stats);
        if(rc!=0)throw new IllegalStateException(ID+" reconstruction failure "+rc);
        JSONObject d=new JSONObject();d.put("id",ID);d.put("demosaic","librtprocess_AMaZE_9a858270");
        d.put("sharpApplied",false);d.put("clippedRatioRepairApplied",false);
        d.put("rawNoiseRequestedStrength",.25);d.put("rawNoiseApplied",stats[0]==1.);
        d.put("rawNoiseEffectiveStrength",stats[0]==1.?.25:0.);
        d.put("rawNoiseReason",stats[0]==1.?"valid_unscaled_Camera2_profile":profile==null?
                "missing_or_invalid_Camera2_profile_noise_bypass":"invalid_variance_contract_noise_bypass");
        d.put("noiseAuthority","Camera2_SENSOR_NOISE_PROFILE_unscaled_CFA_order");
        d.put("rgbProfile",profile==null?JSONObject.NULL:new JSONArray(profile));
        d.put("representationScale",scale);d.put("sourceCfa",sourceCfa);d.put("localCfa",cfa);
        d.put("originX",originX);d.put("originY",originY);d.put("rawChangedSamples",(long)stats[1]);
        d.put("rawMaxCorrection",stats[2]);d.put("rawCensoredSamples",(long)stats[3]);
        d.put("reconstructionMs",stats[4]);d.put("border","16px_true_noSharp_MHC_original_RAW");
        d.put("chromaStrength",.25);d.put("chromaDomain","target_Q14_before_SAT");
        return d;
    }
    private static native ByteBuffer prepareInPlace(long context,long camera,int w,int h,double gain);
    // Borrowed native view: the caller owns and retains cam16 through the last JNI call.
    static ByteBuffer prepareFrameInPlace(long context,long camera,int w,int h,double gain) {
        ByteBuffer q=prepareInPlace(context,camera,w,h,gain);
        if(q==null)throw new IllegalStateException("M9COLOURTRIAL1D in-place preparation failed");
        return q.order(ByteOrder.nativeOrder());
    }
    static ByteBuffer prepareFrame(long context,long camera,int w,int h,double gain) {
        ByteBuffer q=ByteBuffer.allocateDirect(Math.multiplyExact(Math.multiplyExact(w,h),6)).order(ByteOrder.nativeOrder());
        int rc=prepare(context,camera,w,h,gain,q);
        if(rc!=0)throw new IllegalStateException(ID+" colour preparation failure "+rc);
        return q;
    }
    static boolean renderBlockParallelDirectBitmap(long context,long cam,int pixels,int w,
            Bitmap bitmap,int y0,int h,double gain,double cb,double cr,int rotation,int workers,long[] stats,ByteBuffer q) {
        if(q==null)return M9NativeColorCore.renderBlockParallelDirectBitmap(context,cam,pixels,w,bitmap,y0,h,gain,cb,cr,rotation,workers,stats);
        return renderBitmap(context,q,w,h,y0,pixels,bitmap,cb,cr,rotation,workers,stats);
    }
    static void renderBlockParallelDirect(long context,long cam,int pixels,int w,int[] argb,
            double gain,double cb,double cr,int rotation,int workers,long[] stats,ByteBuffer q,int y0,int h) {
        if(q==null)M9NativeColorCore.renderBlockParallelDirect(context,cam,pixels,w,argb,gain,cb,cr,rotation,workers,stats);
        else renderDirect(context,q,w,h,y0,pixels,argb,cb,cr,rotation,workers,stats);
    }
}
