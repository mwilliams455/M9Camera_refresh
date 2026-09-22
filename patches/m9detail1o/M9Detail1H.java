package com.particlesdevs.photoncamera.m9.render;

import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.LensShadingMap;
import android.util.Pair;
import java.nio.ByteBuffer;
import org.json.JSONArray;
import org.json.JSONObject;

/** Controlled DETAIL1O candidate. DETAIL1H + certificate-bounded common50 R/B correction. */
final class M9Detail1H {
    static final String ID = "M9DETAIL1O_COMMON50";
    private M9Detail1H() {}
    private static native int applyNative(short[] norm, ByteBuffer raw, ByteBuffer rgb,
            int width, int height, int cfa, int originY, float[] black, int white,
            double[] profile, double[] gains, int mapWidth, int mapHeight,
            double scale, double nr, double nb, boolean guard, double[] stats);

    // Fresh Camera2 CFA-position pairs only. Existing DNG tags are not rewritten.
    static double[] packRgb(Pair<Double,Double>[] pairs, int cfa) {
        if (pairs == null || pairs.length != 4 || cfa < 0 || cfa > 3) return null;
        for (Pair<Double,Double> p : pairs) {
            if (p == null || p.first == null || p.second == null ||
                    !Double.isFinite(p.first) || !Double.isFinite(p.second) ||
                    p.first < 0.0 || p.second < 0.0 || p.first > 1.0 || p.second > 1.0) return null;
        }
        int r=cfa, b=3-cfa, g1=r^1, g2=b^1;
        return new double[]{pairs[r].first,pairs[r].second,
                .5*pairs[g1].first+.5*pairs[g2].first,
                .5*pairs[g1].second+.5*pairs[g2].second,pairs[b].first,pairs[b].second};
    }
    static double[] decompose(float[] src, double alpha, double expectedScale) {
        if (src == null || src.length == 0 || src.length%4 != 0 || !Double.isFinite(alpha) ||
                alpha < 0.0 || alpha > 1.0 || !Double.isFinite(expectedScale) || expectedScale <= 0.0) return null;
        double[] gains=new double[src.length];double maxGain=0.0;
        for(int base=0;base<src.length;base+=4) {
            double ls=0.0;
            for(int p=0;p<4;p++){double g=src[base+p];if(!Double.isFinite(g)||g<=0.0)return null;ls+=Math.log(g);}
            double common=Math.exp(.25*ls),applied=Math.exp(alpha*Math.log(common));
            for(int p=0;p<4;p++){double g=src[base+p]/common*applied;gains[base+p]=g;maxGain=Math.max(maxGain,g);}
        }
        return Math.abs(maxGain-expectedScale)<=1e-12*Math.max(1.0,expectedScale)?gains:null;
    }
    static JSONObject apply(short[] norm, ByteBuffer raw, ByteBuffer rgb, int width, int height,
            int sourceCfa, int originX, int originY, float[] black, int white, float[] neutral,
            LensShadingMap map, double alpha, double scale, CaptureResult capture) throws Exception {
        JSONObject d=new JSONObject();d.put("id",ID);d.put("singleRaw",true);
        d.put("sourceCfa",sourceCfa);d.put("originX",originX);d.put("originY",originY);
        d.put("noiseAuthority","Camera2_SENSOR_NOISE_PROFILE_unscaled_CFA_order");
        d.put("writerNoiseAdjustmentApplied",false);d.put("varianceFactor",1.0);
        d.put("sensorCalibrationVerified",false);d.put("guardModel","DETAIL1F_mode1_bounded_confidence");
        d.put("commonModePolicy","certificate8_common_positive_excess_50pct");
        d.put("commonModeStrength",0.5);d.put("commonModeOpponentDifferencePreserved",true);
        d.put("commonModeHueClassifier",false);d.put("commonModeSubjectClassifier",false);
        d.put("greenAndIso160SharpUnchanged",true);d.put("fallback","DETAIL1D_corrected_RB");
        Pair<Double,Double>[] pairs=capture==null?null:capture.get(CaptureResult.SENSOR_NOISE_PROFILE);
        double[] profile=packRgb(pairs,sourceCfa);
        JSONArray original=new JSONArray();
        if(pairs!=null)for(Pair<Double,Double> p:pairs) {
            JSONArray pair=new JSONArray();
            pair.put(p!=null&&p.first!=null&&Double.isFinite(p.first)?p.first:JSONObject.NULL);
            pair.put(p!=null&&p.second!=null&&Double.isFinite(p.second)?p.second:JSONObject.NULL);original.put(pair);
        }
        d.put("camera2CfaPairs",original);d.put("rgbProfile",profile==null?JSONObject.NULL:new JSONArray(profile));
        d.put("blackLevel",new JSONArray(black));d.put("whiteLevel",white);
        d.put("neutral",new JSONArray(neutral));d.put("representationScale",scale);d.put("norm030Alpha",alpha);
        if(capture!=null) {
            d.put("sensorIso",capture.get(CaptureResult.SENSOR_SENSITIVITY));
            d.put("exposureNs",capture.get(CaptureResult.SENSOR_EXPOSURE_TIME));
            d.put("sensorTimestampNs",capture.get(CaptureResult.SENSOR_TIMESTAMP));
        }
        int mw=map==null?0:map.getColumnCount(),mh=map==null?0:map.getRowCount();
        float[] src=map==null?null:new float[map.getGainFactorCount()];if(src!=null)map.copyGainFactors(src,0);
        double[] gains=decompose(src,alpha,scale);
        boolean guard=profile!=null&&gains!=null&&mw>0&&mh>0&&mw<=256&&mh<=256&&gains.length==mw*mh*4;
        String reason=profile==null?"missing_or_invalid_four_pair_profile":!guard?"variance_shading_contract_invalid":"nominal_unscaled_profile";
        int phase=(sourceCfa&1)^(originX&1);phase+=2*((sourceCfa>>1)^(originY&1));
        double[] stats=new double[15];double nr=(double)neutral[0]/neutral[1],nb=(double)neutral[2]/neutral[1];
        int rc=applyNative(norm,raw,rgb,width,height,phase,originY,black,white,profile,gains,mw,mh,scale,nr,nb,guard,stats);
        if(rc!=0)throw new IllegalStateException(ID+" native failure "+rc);
        boolean applied=stats[0]==1.0;
        d.put("guardRequested",guard);d.put("guardApplied",applied);
        d.put("reason",stats[0]==2.0?"native_guard_failed_full_frame_D_fallback":reason);
        d.put("tiles",(long)stats[1]);d.put("supportedRbSamples",(long)stats[2]);
        d.put("changedCarrierSamples",(long)stats[3]);d.put("maxAbsCorrection",(long)stats[4]);
        d.put("rawCensoredSamples",applied?(long)stats[5]:JSONObject.NULL);
        d.put("meanConfidence",applied?stats[6]:JSONObject.NULL);
        d.put("meanResidualVariance14",applied?stats[7]:JSONObject.NULL);
        d.put("scratchBudgetBytes",(long)stats[8]);d.put("elapsedMs",stats[9]);
        long commonPixels=(long)stats[10];
        d.put("commonModeApplied",commonPixels>0);d.put("commonModeCorrectedPixels",commonPixels);
        d.put("commonModeMaxCorrectionQ14",(long)stats[11]);
        d.put("commonModeMeanCorrectionQ14",commonPixels>0?stats[12]/commonPixels:0.0);
        d.put("commonModeCertificateSupportPixels",(long)stats[13]);
        d.put("commonModeGenuineColorAbstainedPixels",(long)stats[14]);
        d.put("tileSize",256);d.put("halo",12);d.put("mapWidth",mw);d.put("mapHeight",mh);
        return d;
    }
}
