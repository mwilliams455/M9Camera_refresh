package com.particlesdevs.photoncamera.m9.preview;

import java.nio.ByteBuffer;
import org.json.JSONArray;
import org.json.JSONObject;

/** Bounded scene placement from neutral-reference M9 GPU samples, never display feedback. */
public final class M9AutoExposure2D {
    public static final String REVISION="M9COLOURTRIAL1A_TOTALAUTOHEADROOM";
    public static final int WIDTH=32, HEIGHT=24, STEPS=7;
    public static final long MAX_AGE_NS=1200000000L;
    public static double ev(int index) { return index*.25; }
    private static Sample latest;
    private static String meterStatus="awaiting_gpu_probe";
    private static String owner="";
    private static double heldAutoEv;
    private static boolean haveAuto;
    private static long consumedSampleNs=-1;
    private M9AutoExposure2D() {}

    public static synchronized void reset() {
        latest=null;owner="";heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;meterStatus="awaiting_gpu_probe";
    }
    public static synchronized void publish(Sample sample) { latest=sample;meterStatus="gpu_probe_available"; }
    public static synchronized void invalidate(String reason) { latest=null;meterStatus="gpu_probe_disabled:"+reason; }

    public static final class Stats {
        public final int median;
        public final double dark, bright, clipped;
        public Stats(int median,double dark,double bright,double clipped) {
            this.median=median;this.dark=dark;this.bright=bright;this.clipped=clipped;
        }
        boolean valid() {
            return median>=0 && median<=255 && fraction(dark) && fraction(bright) && fraction(clipped);
        }
        JSONObject json() throws org.json.JSONException {
            return new JSONObject().put("weightedMedianCode",median).put("darkFraction",dark)
                    .put("brightFraction",bright).put("channelClipFraction",clipped);
        }
    }
    public static final class Sample {
        public final String camera,mode;
        public final long submittedNs,textureNs,resultNs;
        public final double referenceEnergy;
        private final Stats[] stats;
        public Sample(String camera,String mode,long submittedNs,long textureNs,long resultNs,
                double referenceEnergy,Stats[] stats) {
            this.camera=camera;this.mode=mode;this.submittedNs=submittedNs;
            this.textureNs=textureNs;this.resultNs=resultNs;this.referenceEnergy=referenceEnergy;
            this.stats=stats.clone();
        }
        public Stats stats(int i) { return stats[i]; }
        boolean matches(String camera,String mode,long nowNs,double energy) {
            if (!this.camera.equals(camera) || !this.mode.equals(mode) || nowNs<submittedNs
                    || nowNs-submittedNs>MAX_AGE_NS || referenceEnergy<=0 || energy<=0
                    || !Double.isFinite(referenceEnergy) || !Double.isFinite(energy)
                    || Math.abs(log2(energy/referenceEnergy))>.25 || textureNs<=0 || resultNs<=0
                    || Math.abs(textureNs-resultNs)>150000000L || stats.length!=STEPS) return false;
            for (Stats s:stats) if (s==null || !s.valid()) return false;
            return true;
        }
    }
    /** Read seven adjacent GPU viewports. Centre receives 3x weight; no local image lift. */
    public static Stats[] measure(ByteBuffer rgba) {
        if (rgba==null || rgba.limit()<WIDTH*HEIGHT*STEPS*4) throw new IllegalArgumentException("meter pixels");
        Stats[] out=new Stats[STEPS];
        for (int step=0;step<STEPS;step++) {
            int[] hist=new int[256];int total=0,dark=0,bright=0,clip=0;
            for (int y=0;y<HEIGHT;y++) for (int x=0;x<WIDTH;x++) {
                int at=4*(y*WIDTH*STEPS+step*WIDTH+x);
                int r=rgba.get(at)&255,g=rgba.get(at+1)&255,b=rgba.get(at+2)&255;
                int l=(77*r+150*g+29*b+128)>>8;
                int weight=x>=WIDTH/4 && x<3*WIDTH/4 && y>=HEIGHT/4 && y<3*HEIGHT/4 ? 3:1;
                hist[l]+=weight;total+=weight;
                if(l<32)dark++;if(l>=224)bright++;
                if(Math.max(r,Math.max(g,b))>=253)clip++;
            }
            int median=0,sum=0;while(median<255 && sum+hist[median]<(total+1)/2)sum+=hist[median++];
            double n=WIDTH*HEIGHT;
            out[step]=new Stats(median,dark/n,bright/n,clip/n);
        }
        return out;
    }
    /** A shadow visibility floor, not middle-grey normalization or authentic Leica metering. */
    public static int select(Stats[] s) {
        if(s==null || s.length!=STEPS)return 0;
        for(Stats v:s)if(v==null || !v.valid())return 0;
        Stats base=s[0];
        if(base.median>=40 || base.dark<.55)return 0;
        int chosen=0;
        for(int i=1;i<STEPS;i++) {
            Stats v=s[i];
            // Permit already-clipped windows/speculars, but little NEW clipping.
            if(v.clipped>base.clipped+.015 || v.bright>base.bright+.04 || v.median>80)break;
            if(v.median>=base.median+4)chosen=i;
            if(v.median>=60)break;
        }
        return chosen;
    }
    /** Bound ALL positive Auto bias with the same fresh preview highlight evidence.
     * This is a processed-preview guard, not a RAW clipping guarantee. */
    public static double positiveHeadroomLimit(Stats[] stats) {
        if (stats == null || stats.length != STEPS) return 0;
        for (Stats s : stats) if (s == null || !s.valid()) return 0;
        Stats base = stats[0];
        int safe = 0;
        for (int i = 1; i < STEPS; i++) {
            if (stats[i].clipped > base.clipped + .015
                    || stats[i].bright > base.bright + .04) break;
            safe = i;
        }
        return ev(safe);
    }
    public static final class Decision {
        public final double appliedEv;
        public final String reason,diagnostics;
        Decision(double appliedEv,String reason,JSONObject diagnostics) {
            this.appliedEv=appliedEv;this.reason=reason;this.diagnostics=diagnostics.toString();
        }
    }
    public static synchronized Decision decide(String camera,String mode,long nowNs,
            double referenceEnergy,double userEv,long manualExposure,int manualIso,double legacyEv) {
        String key=camera+"|"+mode;
        if(!key.equals(owner)) {owner=key;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;}
        double baseline=Double.isFinite(legacyEv)?Math.max(-.5,Math.min(.75,legacyEv)):0;
        double result=baseline,target=baseline;String reason="legacy_scene_baseline";
        Sample sample=latest;boolean valid=sample!=null && sample.matches(camera,mode,nowNs,referenceEnergy);
        final double unboundedBaseline = baseline;
        final double headroomLimit = valid ? positiveHeadroomLimit(sample.stats) : 0;
        // Missing/stale samples cannot justify extra positive Auto bias. Negative
        // baseline and explicit user EV/manual controls retain their prior roles.
        if (manualExposure == 0 && manualIso == 0 && Math.abs(userEv) <= 1e-6) {
            baseline = Math.min(baseline, headroomLimit);
            result = baseline; target = baseline;
        }
        int chosen=0;
        if(manualExposure!=0 || manualIso!=0) {
            result=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;reason="manual_ISO_or_shutter";
        } else if(Math.abs(userEv)>1e-6) {
            // EV is compensation around the Auto baseline already shown. Freeze it
            // on handover so +0.25 EV cannot discard a larger automatic lift.
            if(!haveAuto) {heldAutoEv=baseline;haveAuto=true;}
            result=heldAutoEv;target=result;reason="manual_EV_holds_auto_baseline";
        } else if(valid) {
            chosen=select(sample.stats);
            double placement=ev(chosen)*confidence(sample.stats[0]);
            if(placement<.08)placement=0;
            target=Math.min(headroomLimit,placement>0?Math.max(baseline,placement):baseline);
            double current=haveAuto?heldAutoEv:baseline;
            if(target<=current)result=target; // Release immediately when the scene becomes bright.
            else if(consumedSampleNs!=sample.submittedNs)result=Math.min(target,current+.25);
            else result=current;
            consumedSampleNs=sample.submittedNs;heldAutoEv=result;haveAuto=true;
            reason=chosen>0?"bounded_rendered_shadow_placement":"rendered_scene_no_extra_lift";
        } else {
            heldAutoEv=baseline;haveAuto=true;result=baseline;reason="rendered_meter_unavailable_or_stale";
        }
        JSONObject o=new JSONObject();
        try {
            o.put("revision",REVISION).put("reason",reason).put("sampleValid",valid).put("meterStatus",meterStatus)
                    .put("legacySceneEv",unboundedBaseline).put("headroomBoundedLegacyEv",baseline)
                    .put("positiveAutoHeadroomLimitEv",headroomLimit)
                    .put("positiveAutoRequiresFreshMeter",true).put("recommendedTotalAutoEv",target)
                    .put("appliedTotalAutoEv",result).put("userEv",userEv)
                    .put("meterDomain","neutral_reference_same_M9_GPU_shader")
                    .put("meterIncludesUserOrAutoEv",false).put("maximumPositiveEv",1.5)
                    .put("shadowTargetCode",60).put("newClipBudget",.015)
                    .put("shadowConfidence",valid?confidence(sample.stats[0]):0)
                    .put("leicaMeterNumericalParity",false);
            if(valid) {
                o.put("sampleAgeMs",(nowNs-sample.submittedNs)/1e6)
                        .put("textureTimestampNs",sample.textureNs).put("resultTimestampNs",sample.resultNs)
                        .put("referenceEnergy",sample.referenceEnergy).put("selectedStep",chosen);
                JSONArray a=new JSONArray();for(Stats s:sample.stats)a.put(s.json());o.put("bracket",a);
            }
        } catch(org.json.JSONException e) {throw new IllegalStateException(e);}
        return new Decision(result,reason,o);
    }
    private static double confidence(Stats s) {
        double x=Math.max(0,Math.min(1,Math.min((40.-s.median)/16.,(s.dark-.55)/.25)));
        return x*x*(3-2*x);
    }
    private static boolean fraction(double x) {return Double.isFinite(x) && x>=0 && x<=1;}
    private static double log2(double x) {return Math.log(x)/Math.log(2);}
}
