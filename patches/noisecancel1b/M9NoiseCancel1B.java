package com.particlesdevs.photoncamera.m9.render;

import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.LensShadingMap;
import java.nio.ByteBuffer;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * NOISECANCEL1B: independent quiet-chroma cancellation for the accepted AMaZE
 * production path. No DETAIL/sharpness dependency and no green-channel writes.
 */
final class M9NoiseCancel1B {
    static final String ID="M9NOISECANCEL1B_DECOUPLED_AMAZE_CHROMA";
    private M9NoiseCancel1B() {}
    private static native int applyNative(ByteBuffer rgb,int w,int h,double[] profile,double[] gains,
            int mw,int mh,double scale,double[] stats);

    static JSONObject apply(ByteBuffer rgb,int w,int h,int sourceCfa,
            LensShadingMap map,double alpha,double scale,CaptureResult capture) throws Exception {
        JSONObject d=new JSONObject();
        d.put("id",ID);
        d.put("stage","post_AMaZE_camera_RGB_pre_SOURCECAL2A");
        d.put("detailSharpnessDependency",false);
        d.put("greenChannelMutation",false);
        d.put("lumaPolicy","green_exact_chroma_only_RminusG_BminusG");
        d.put("noiseAuthority","Camera2_SENSOR_NOISE_PROFILE_unscaled_CFA_order");
        d.put("confidenceGateStart",0.65);
        d.put("confidenceGateFull",0.90);
        d.put("maxBlendToCrossMedian",0.50);
        d.put("neighbourhood","cross5_camera_chroma");
        d.put("edgeProtection","green_gradient_plus_chroma_spread_noise_scaled");
        double[] profile=M9Detail1H.packRgb(capture==null?null:capture.get(CaptureResult.SENSOR_NOISE_PROFILE),sourceCfa);
        int mw=map==null?0:map.getColumnCount(),mh=map==null?0:map.getRowCount();
        float[] grid=map==null?null:new float[map.getGainFactorCount()];
        if(grid!=null)map.copyGainFactors(grid,0);
        double[] gains=M9Detail1H.decompose(grid,alpha,scale);
        d.put("rgbProfile",profile==null?JSONObject.NULL:new JSONArray(profile));
        d.put("representationScale",scale);
        d.put("mapWidth",mw);d.put("mapHeight",mh);
        boolean eligible=rgb!=null&&rgb.isDirect()&&profile!=null&&gains!=null&&mw>0&&mh>0&&
                mw<=256&&mh<=256&&gains.length==mw*mh*4;
        d.put("eligible",eligible);
        if(!eligible){
            d.put("applied",false);
            d.put("reason",profile==null?"missing_or_invalid_Camera2_profile":
                    gains==null?"invalid_shading_variance_transport":"invalid_direct_rgb_or_map_contract");
            return d;
        }
        double[] stats=new double[12];
        int rc=applyNative(rgb,w,h,profile,gains,mw,mh,scale,stats);
        if(rc!=0)throw new IllegalStateException(ID+" native failure "+rc);
        d.put("applied",stats[0]==1.0);
        d.put("changedChannelSamples",(long)stats[1]);
        d.put("changedRedSamples",(long)stats[2]);
        d.put("changedBlueSamples",(long)stats[3]);
        d.put("maxAbsCorrection16",(long)stats[4]);
        d.put("meanAppliedBlend",stats[5]);
        d.put("censoredPixels",(long)stats[6]);
        d.put("consideredPixels",(long)stats[7]);
        d.put("meanEstimatedChromaSigma16",stats[8]);
        d.put("elapsedMs",stats[9]);
        d.put("greenMutatedSamples",0);
        d.put("reason","valid_profile_decoupled_quiet_chroma");
        if(capture!=null){
            d.put("sensorIso",capture.get(CaptureResult.SENSOR_SENSITIVITY));
            d.put("exposureNs",capture.get(CaptureResult.SENSOR_EXPOSURE_TIME));
        }
        return d;
    }
}
