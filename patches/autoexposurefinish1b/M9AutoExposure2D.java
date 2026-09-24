package com.particlesdevs.photoncamera.m9.preview;

import java.nio.ByteBuffer;
import org.json.JSONArray;
import org.json.JSONObject;

/** Target-based scene placement from neutral-reference M9 GPU samples, never display feedback. */
public final class M9AutoExposure2D {
    public static final String REVISION="M9AUTOEXPOSUREFINISH1B_TARGETPLACEMENT";
    public static final int WIDTH=32, HEIGHT=24, STEPS=9;
    public static final long MAX_AGE_NS=1200000000L;
    private static final int SCENE_TARGET_MEDIAN=60;
    private static final int BACKLIGHT_TARGET_CENTER_MEDIAN=60;
    private static final int BACKLIGHT_TARGET_CENTER_Q25=30;
    private static final int BACKLIGHT_HARD_CENTER_MEDIAN=72;
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
        public final int median,centerMedian,centerQ25;
        public final double dark,bright,clipped,centerDark,outerBright,outerBright160;
        public Stats(int median,double dark,double bright,double clipped) {
            this(median,dark,bright,clipped,median,dark,bright,median,bright);
        }
        public Stats(int median,double dark,double bright,double clipped,
                int centerMedian,double centerDark,double outerBright) {
            this(median,dark,bright,clipped,centerMedian,centerDark,outerBright,
                    centerMedian,outerBright);
        }
        public Stats(int median,double dark,double bright,double clipped,
                int centerMedian,double centerDark,double outerBright,
                int centerQ25,double outerBright160) {
            this.median=median;this.dark=dark;this.bright=bright;this.clipped=clipped;
            this.centerMedian=centerMedian;this.centerDark=centerDark;this.outerBright=outerBright;
            this.centerQ25=centerQ25;this.outerBright160=outerBright160;
        }
        boolean valid() {
            return median>=0 && median<=255 && centerMedian>=0 && centerMedian<=255
                    && centerQ25>=0 && centerQ25<=255
                    && fraction(dark) && fraction(bright) && fraction(clipped)
                    && fraction(centerDark) && fraction(outerBright) && fraction(outerBright160);
        }
        JSONObject json() throws org.json.JSONException {
            return new JSONObject().put("weightedMedianCode",median).put("darkFraction",dark)
                    .put("brightFraction",bright).put("channelClipFraction",clipped)
                    .put("centerMedianCode",centerMedian).put("centerQ25Code",centerQ25)
                    .put("centerDarkFraction",centerDark).put("outerBrightFraction",outerBright)
                    .put("outerBright160Fraction",outerBright160);
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

    /** Read adjacent GPU viewports. Centre receives 3x weight; no local image lift. */
    public static Stats[] measure(ByteBuffer rgba) {
        if (rgba==null || rgba.limit()<WIDTH*HEIGHT*STEPS*4) throw new IllegalArgumentException("meter pixels");
        Stats[] out=new Stats[STEPS];
        for (int step=0;step<STEPS;step++) {
            int[] hist=new int[256],centerHist=new int[256];
            int total=0,dark=0,bright=0,clip=0,centerN=0,centerDark=0,outerN=0,outerBright=0,outerBright160=0;
            for (int y=0;y<HEIGHT;y++) for (int x=0;x<WIDTH;x++) {
                int at=4*(y*WIDTH*STEPS+step*WIDTH+x);
                int r=rgba.get(at)&255,g=rgba.get(at+1)&255,b=rgba.get(at+2)&255;
                int l=(77*r+150*g+29*b+128)>>8;
                boolean center=x>=WIDTH/4 && x<3*WIDTH/4 && y>=HEIGHT/4 && y<3*HEIGHT/4;
                int weight=center?3:1;
                hist[l]+=weight;total+=weight;
                if(l<32)dark++;if(l>=224)bright++;
                if(Math.max(r,Math.max(g,b))>=253)clip++;
                if(center) {
                    centerHist[l]++;centerN++;
                    if(l<32)centerDark++;
                } else {
                    outerN++;
                    if(l>=224)outerBright++;
                    if(l>=160)outerBright160++;
                }
            }
            int median=quantile(hist,total,.50),centerMedian=quantile(centerHist,centerN,.50);
            int centerQ25=quantile(centerHist,centerN,.25);
            double n=WIDTH*HEIGHT;
            out[step]=new Stats(median,dark/n,bright/n,clip/n,centerMedian,
                    centerN>0?centerDark/(double)centerN:0,
                    outerN>0?outerBright/(double)outerN:0,
                    centerQ25,outerN>0?outerBright160/(double)outerN:0);
        }
        return out;
    }

    /** Whole-scene low-key placement. Target 60 is intentionally below middle grey. */
    public static int select(Stats[] s) {
        if(!validStats(s))return 0;
        Stats base=s[0];
        if(base.median>=40 || base.dark<.55)return 0;
        double lossConfidence=Math.max(backlightConfidence(base),severeDarkConfidence(base));
        int chosen=0;
        for(int i=1;i<STEPS;i++) {
            Stats v=s[i];
            if(lossConfidence>=.10
                    ? unsafeAdaptivePositive(base,v,lossConfidence)
                    : unsafePositive(base,v))break;
            if(v.median>=base.median+3)chosen=i;
            if(v.median>=SCENE_TARGET_MEDIAN)break;
        }
        return chosen;
    }

    /**
     * Backlit-subject placement uses the centre lower quartile as well as the centre
     * median so bright background pixels inside the centre cannot hide a dark body.
     */
    public static int selectBacklight(Stats[] s) {
        if(!validStats(s))return 0;
        Stats base=s[0];
        double confidence=backlightConfidence(base);
        if(confidence<.10)return 0;
        double lossConfidence=Math.max(confidence,severeDarkConfidence(base));
        int chosen=0;
        for(int i=1;i<STEPS;i++) {
            Stats v=s[i];
            if(unsafeAdaptivePositive(base,v,lossConfidence))break;
            if(v.centerMedian>=base.centerMedian+3 || v.centerQ25>=base.centerQ25+2)chosen=i;
            if((v.centerMedian>=BACKLIGHT_TARGET_CENTER_MEDIAN
                    && v.centerQ25>=BACKLIGHT_TARGET_CENTER_Q25)
                    || v.centerMedian>=BACKLIGHT_HARD_CENTER_MEDIAN)break;
        }
        return chosen;
    }

    /** Strict ordinary-scene positive budget retained from 1A. */
    public static double positiveHeadroomLimit(Stats[] stats) {
        if (!validStats(stats)) return 0;
        Stats base = stats[0];int safe=0;
        for (int i=1;i<STEPS;i++) {
            if (unsafePositive(base,stats[i])) break;
            safe=i;
        }
        return ev(safe);
    }

    /** Backlight or severe darkness may sacrifice bounded background highlights. */
    public static double backlightHeadroomLimit(Stats[] stats) {
        if (!validStats(stats)) return 0;
        Stats base=stats[0];
        double confidence=Math.max(backlightConfidence(base),severeDarkConfidence(base));
        if(confidence<.10)return 0;
        int safe=0;
        for(int i=1;i<STEPS;i++) {
            if(unsafeAdaptivePositive(base,stats[i],confidence))break;
            safe=i;
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
            double referenceEnergy,double userEv,long manualExposure,int manualIso,double legacyEv,
            boolean autoEligible) {
        String key=camera+"|"+mode;
        if(!key.equals(owner)) {owner=key;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;}
        double rawBaseline=Double.isFinite(legacyEv)?Math.max(-.5,Math.min(.75,legacyEv)):0;
        double result=rawBaseline,target=rawBaseline;String reason="legacy_scene_baseline";
        Sample sample=latest;boolean valid=sample!=null && sample.matches(camera,mode,nowNs,referenceEnergy);

        double strictHeadroom=valid?positiveHeadroomLimit(sample.stats):0;
        double backlightConfidence=valid?backlightConfidence(sample.stats[0]):0;
        double severeDarkConfidence=valid?severeDarkConfidence(sample.stats[0]):0;
        double relaxedLossConfidence=Math.max(backlightConfidence,severeDarkConfidence);
        double backlightHeadroom=valid?backlightHeadroomLimit(sample.stats):0;
        double effectiveHeadroom=relaxedLossConfidence>=.10
                ? Math.max(strictHeadroom,backlightHeadroom) : strictHeadroom;
        double baseline=rawBaseline;
        if(manualExposure==0 && manualIso==0 && Math.abs(userEv)<=1e-6 && baseline>0)
            baseline=Math.min(baseline,effectiveHeadroom);

        int sceneChosen=0,backlightChosen=0;
        double scenePlacement=0,backlightPlacement=0;
        if(manualExposure!=0 || manualIso!=0) {
            result=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;reason="manual_ISO_or_shutter";
        } else if(Math.abs(userEv)>1e-6) {
            if(!haveAuto) {heldAutoEv=baseline;haveAuto=true;}
            result=heldAutoEv;target=result;reason="manual_EV_holds_auto_baseline";
        } else if(!autoEligible) {
            result=0;target=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            reason="auto_scene_placement_not_eligible";
        } else if(valid) {
            sceneChosen=select(sample.stats);
            backlightChosen=selectBacklight(sample.stats);
            scenePlacement=ev(sceneChosen);
            backlightPlacement=ev(backlightChosen);
            double placement=Math.max(scenePlacement,backlightPlacement);
            double selectedHeadroom=backlightPlacement>scenePlacement
                    ? backlightHeadroom : (backlightPlacement>0?Math.max(strictHeadroom,backlightHeadroom):strictHeadroom);
            target=placement>0?Math.max(baseline,Math.min(placement,selectedHeadroom)):baseline;
            double current=haveAuto?heldAutoEv:baseline;
            if(target<=current)result=target;
            else if(consumedSampleNs!=sample.submittedNs)result=Math.min(target,current+.25);
            else result=current;
            consumedSampleNs=sample.submittedNs;heldAutoEv=result;haveAuto=true;
            if(backlightPlacement>scenePlacement && backlightChosen>0)
                reason="target_rendered_backlight_subject_placement";
            else if(sceneChosen>0)
                reason="target_rendered_low_key_scene_placement";
            else
                reason="rendered_scene_no_extra_lift";
        } else {
            heldAutoEv=baseline;haveAuto=true;result=baseline;reason="rendered_meter_unavailable_or_stale";
        }

        JSONObject o=new JSONObject();
        try {
            o.put("revision",REVISION).put("reason",reason).put("sampleValid",valid).put("meterStatus",meterStatus)
                    .put("autoPlacementEligible",autoEligible)
                    .put("legacySceneEv",rawBaseline).put("headroomBoundedLegacyEv",baseline)
                    .put("strictPositiveHeadroomLimitEv",strictHeadroom)
                    .put("backlightPositiveHeadroomLimitEv",backlightHeadroom)
                    .put("effectivePositiveHeadroomLimitEv",effectiveHeadroom)
                    .put("positiveAutoRequiresFreshMeter",true)
                    .put("recommendedTotalAutoEv",target).put("appliedTotalAutoEv",result).put("userEv",userEv)
                    .put("meterDomain","neutral_reference_same_M9_GPU_shader")
                    .put("meterIncludesUserOrAutoEv",false).put("maximumPositiveSearchEv",ev(STEPS-1))
                    .put("sceneTargetMedianCode",SCENE_TARGET_MEDIAN)
                    .put("backlightTargetCenterMedianCode",BACKLIGHT_TARGET_CENTER_MEDIAN)
                    .put("backlightTargetCenterQ25Code",BACKLIGHT_TARGET_CENTER_Q25)
                    .put("backlightHardCenterMedianCode",BACKLIGHT_HARD_CENTER_MEDIAN)
                    .put("backlightConfidence",backlightConfidence)
                    .put("severeDarkConfidence",severeDarkConfidence)
                    .put("relaxedPositiveLossConfidence",relaxedLossConfidence)
                    .put("globalSceneSelectedStep",sceneChosen).put("backlightSelectedStep",backlightChosen)
                    .put("sceneTargetUnmetAtMaximum",valid && sceneChosen==STEPS-1
                            && sample.stats[STEPS-1].median<SCENE_TARGET_MEDIAN)
                    .put("backlightTargetUnmetAtMaximum",valid && backlightChosen==STEPS-1
                            && sample.stats[STEPS-1].centerMedian<BACKLIGHT_TARGET_CENTER_MEDIAN)
                    .put("leicaMeterNumericalParity",false);
            if(valid) {
                o.put("sampleAgeMs",(nowNs-sample.submittedNs)/1e6)
                        .put("textureTimestampNs",sample.textureNs).put("resultTimestampNs",sample.resultNs)
                        .put("referenceEnergy",sample.referenceEnergy)
                        .put("selectedStep",Math.max(sceneChosen,backlightChosen));
                JSONArray a=new JSONArray();for(Stats s:sample.stats)a.put(s.json());o.put("bracket",a);
            }
        } catch(org.json.JSONException e) {throw new IllegalStateException(e);}
        return new Decision(result,reason,o);
    }

    private static double backlightConfidence(Stats s) {
        double lowQuartileNeed=1.0-smoothstep(s.centerQ25,36,48);
        double centerNeed=1.0-smoothstep(s.centerMedian,52,68);
        double brightSurround=smoothstep(s.outerBright160,.015,.12);
        return Math.min(lowQuartileNeed,Math.min(centerNeed,brightSurround));
    }

    private static double severeDarkConfidence(Stats s) {
        double medianCollapse=1.0-smoothstep(s.median,18,32);
        double darkPopulation=smoothstep(s.dark,.68,.82);
        return Math.min(medianCollapse,darkPopulation);
    }

    private static boolean unsafePositive(Stats base,Stats v) {
        return v.clipped>base.clipped+.015 || v.bright>base.bright+.04;
    }

    private static boolean unsafeAdaptivePositive(Stats base,Stats v,double confidence) {
        double clipDelta=.02+.20*confidence;
        double brightDelta=.04+.24*confidence;
        double absoluteClip=.12+.23*confidence;
        double absoluteBright=.24+.26*confidence;
        if(v.clipped>base.clipped+clipDelta || v.bright>base.bright+brightDelta)return true;
        if(v.clipped>absoluteClip && v.clipped>base.clipped+.02)return true;
        if(v.bright>absoluteBright && v.bright>base.bright+.04)return true;
        return false;
    }

    private static boolean validStats(Stats[] s) {
        if(s==null || s.length!=STEPS)return false;
        for(Stats v:s)if(v==null || !v.valid())return false;
        return true;
    }

    private static int quantile(int[] hist,int total,double q) {
        if(total<=0)return 0;
        int target=(int)Math.ceil(Math.max(0,Math.min(1,q))*total);
        target=Math.max(1,target);
        int code=0,sum=0;
        while(code<255 && sum+hist[code]<target)sum+=hist[code++];
        return code;
    }

    private static double smoothstep(double value,double low,double high) {
        if(high<=low)return value>=high?1:0;
        double t=Math.max(0,Math.min(1,(value-low)/(high-low)));
        return t*t*(3-2*t);
    }
    private static boolean fraction(double x) {return Double.isFinite(x) && x>=0 && x<=1;}
    private static double log2(double x) {return Math.log(x)/Math.log(2);}
}
