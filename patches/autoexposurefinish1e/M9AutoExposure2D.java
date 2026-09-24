package com.particlesdevs.photoncamera.m9.preview;

import java.nio.ByteBuffer;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Target-based M9-like scene placement from neutral-reference rendered probes.
 * Exposure remains global capture exposure: no local HDR or post-capture relighting.
 */
public final class M9AutoExposure2D {
    public static final String REVISION="M9AUTOEXPOSUREFINISH1E_MULTIFIELD_BODY";
    public static final int WIDTH=32, HEIGHT=24, STEPS=11;
    public static final int FIELD_ROWS=4, FIELD_COLS=6, FIELD_COUNT=FIELD_ROWS*FIELD_COLS;
    public static final long MAX_AGE_NS=1200000000L;

    private static final double STEP_EV=.25;
    private static final double SEARCH_MAX_EV=(STEPS-1)*STEP_EV;

    // Deliberately low-key targets. These are visibility floors, not middle grey.
    private static final int SCENE_MEDIAN_TARGET=46;
    private static final int SCENE_CENTER_TARGET=54;
    private static final int SCENE_CENTER_Q25_TARGET=22;
    // Backlight target is intentionally adaptive rather than an EV boost.
    // Moderate contrast stays near the old low-key floor; severe subject starvation
    // can ask for a brighter but still dense M9-like body placement.
    private static final int BACKLIGHT_CENTER_TARGET_MIN=58;
    private static final int BACKLIGHT_CENTER_TARGET_MAX=72;
    private static final int BACKLIGHT_CENTER_Q25_TARGET_MIN=22;
    private static final int BACKLIGHT_CENTER_Q25_TARGET_MAX=32;

    private static Sample latest;
    private static String meterStatus="awaiting_gpu_probe";
    private static String owner="";
    private static double heldAutoEv;
    private static boolean haveAuto;
    private static long consumedSampleNs=-1;
    // Backlight classification hysteresis and lower-target confirmation prevent
    // neighbouring 0.25-EV decisions from visibly toggling the live preview.
    private static boolean backlightLatched;
    private static double pendingLowerTargetEv=Double.NaN;
    private static int lowerTargetConfirmations;
    private M9AutoExposure2D() {}

    public static double ev(int index) { return index*STEP_EV; }

    public static synchronized void reset() {
        latest=null;owner="";heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
        backlightLatched=false;pendingLowerTargetEv=Double.NaN;lowerTargetConfirmations=0;
        meterStatus="awaiting_gpu_probe";
    }
    public static synchronized void publish(Sample sample) {
        latest=sample;meterStatus="gpu_probe_available";
    }
    public static synchronized void invalidate(String reason) {
        latest=null;meterStatus="gpu_probe_disabled:"+reason;
    }

    public static final class Stats {
        public final int median,centerMedian,centerQ25,outerQ90;
        public final double dark,bright,clipped,centerDark,outerBright;
        public final double centerBright,centerClipped,outerClipped;
        public final boolean fieldMapValid;
        public final int[] fieldMedian,fieldQ25,fieldQ90;
        public final double[] fieldBright,fieldClipped;

        /** Compatibility constructor for inherited synthetic callers. */
        public Stats(int median,double dark,double bright,double clipped) {
            this(median,dark,bright,clipped,median,median,median,dark,bright,bright,clipped,clipped,
                    null,null,null,null,null);
        }
        public Stats(int median,double dark,double bright,double clipped,
                int centerMedian,int centerQ25,int outerQ90,
                double centerDark,double outerBright,double centerBright,
                double centerClipped,double outerClipped) {
            this(median,dark,bright,clipped,centerMedian,centerQ25,outerQ90,
                    centerDark,outerBright,centerBright,centerClipped,outerClipped,
                    null,null,null,null,null);
        }
        public Stats(int median,double dark,double bright,double clipped,
                int centerMedian,int centerQ25,int outerQ90,
                double centerDark,double outerBright,double centerBright,
                double centerClipped,double outerClipped,
                int[] fieldMedian,int[] fieldQ25,int[] fieldQ90,
                double[] fieldBright,double[] fieldClipped) {
            this.median=median;this.dark=dark;this.bright=bright;this.clipped=clipped;
            this.centerMedian=centerMedian;this.centerQ25=centerQ25;this.outerQ90=outerQ90;
            this.centerDark=centerDark;this.outerBright=outerBright;this.centerBright=centerBright;
            this.centerClipped=centerClipped;this.outerClipped=outerClipped;
            boolean ok=fieldMedian!=null&&fieldQ25!=null&&fieldQ90!=null
                    &&fieldBright!=null&&fieldClipped!=null
                    &&fieldMedian.length==FIELD_COUNT&&fieldQ25.length==FIELD_COUNT
                    &&fieldQ90.length==FIELD_COUNT&&fieldBright.length==FIELD_COUNT
                    &&fieldClipped.length==FIELD_COUNT;
            if(ok) {
                for(int i=0;i<FIELD_COUNT;i++) {
                    if(!code(fieldMedian[i])||!code(fieldQ25[i])||!code(fieldQ90[i])
                            ||!fraction(fieldBright[i])||!fraction(fieldClipped[i])) {
                        ok=false;break;
                    }
                }
            }
            fieldMapValid=ok;
            this.fieldMedian=ok?fieldMedian.clone():new int[0];
            this.fieldQ25=ok?fieldQ25.clone():new int[0];
            this.fieldQ90=ok?fieldQ90.clone():new int[0];
            this.fieldBright=ok?fieldBright.clone():new double[0];
            this.fieldClipped=ok?fieldClipped.clone():new double[0];
        }
        boolean valid() {
            return code(median)&&code(centerMedian)&&code(centerQ25)&&code(outerQ90)
                    && fraction(dark)&&fraction(bright)&&fraction(clipped)
                    && fraction(centerDark)&&fraction(outerBright)&&fraction(centerBright)
                    && fraction(centerClipped)&&fraction(outerClipped);
        }
        JSONObject json() throws org.json.JSONException {
            JSONObject o=new JSONObject()
                    .put("weightedMedianCode",median)
                    .put("darkFraction",dark)
                    .put("brightFraction",bright)
                    .put("channelClipFraction",clipped)
                    .put("centerMedianCode",centerMedian)
                    .put("centerQ25Code",centerQ25)
                    .put("outerQ90Code",outerQ90)
                    .put("centerDarkFraction",centerDark)
                    .put("outerBrightFraction",outerBright)
                    .put("centerBrightFraction",centerBright)
                    .put("centerClipFraction",centerClipped)
                    .put("outerClipFraction",outerClipped)
                    .put("fieldMapValid",fieldMapValid);
            if(fieldMapValid) {
                o.put("fieldGrid",FIELD_ROWS+"x"+FIELD_COLS)
                        .put("fieldMedianCode",M9AutoExposure2D.json(fieldMedian))
                        .put("fieldQ25Code",M9AutoExposure2D.json(fieldQ25))
                        .put("fieldQ90Code",M9AutoExposure2D.json(fieldQ90))
                        .put("fieldBrightFraction",M9AutoExposure2D.json(fieldBright))
                        .put("fieldClipFraction",M9AutoExposure2D.json(fieldClipped));
            }
            return o;
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
            if (!this.camera.equals(camera)||!this.mode.equals(mode)||nowNs<submittedNs
                    || nowNs-submittedNs>MAX_AGE_NS||referenceEnergy<=0||energy<=0
                    || !Double.isFinite(referenceEnergy)||!Double.isFinite(energy)
                    || Math.abs(log2(energy/referenceEnergy))>.25||textureNs<=0||resultNs<=0
                    || Math.abs(textureNs-resultNs)>150000000L||stats.length!=STEPS) return false;
            for(Stats s:stats)if(s==null||!s.valid())return false;
            return true;
        }
    }

    /** Read adjacent neutral-reference rendered probes. Centre receives 3x global-median weight. */
    /** Read adjacent neutral-reference rendered probes and a 4x6 body map. */
    public static Stats[] measure(ByteBuffer rgba) {
        if(rgba==null||rgba.limit()<WIDTH*HEIGHT*STEPS*4)
            throw new IllegalArgumentException("meter pixels");
        Stats[] out=new Stats[STEPS];
        int[] hist=new int[256],centerHist=new int[256],outerHist=new int[256];
        int[] fieldHist=new int[FIELD_COUNT*256],fieldN=new int[FIELD_COUNT];
        int[] fieldBrightN=new int[FIELD_COUNT],fieldClipN=new int[FIELD_COUNT];

        for(int step=0;step<STEPS;step++) {
            clear(hist);clear(centerHist);clear(outerHist);clear(fieldHist);
            clear(fieldN);clear(fieldBrightN);clear(fieldClipN);
            int total=0,dark=0,bright=0,clip=0;
            int centerN=0,centerDark=0,centerBright=0,centerClip=0;
            int outerN=0,outerBright=0,outerClip=0;
            for(int y=0;y<HEIGHT;y++)for(int x=0;x<WIDTH;x++) {
                int at=4*(y*WIDTH*STEPS+step*WIDTH+x);
                int r=rgba.get(at)&255,g=rgba.get(at+1)&255,b=rgba.get(at+2)&255;
                int l=(77*r+150*g+29*b+128)>>8;
                boolean center=x>=WIDTH/4&&x<3*WIDTH/4&&y>=HEIGHT/4&&y<3*HEIGHT/4;
                int weight=center?3:1;
                hist[l]+=weight;total+=weight;
                if(l<32)dark++;if(l>=224)bright++;
                boolean c=Math.max(r,Math.max(g,b))>=253;
                if(c)clip++;
                if(center) {
                    centerHist[l]++;centerN++;
                    if(l<32)centerDark++;if(l>=224)centerBright++;if(c)centerClip++;
                } else {
                    outerHist[l]++;outerN++;
                    if(l>=224)outerBright++;if(c)outerClip++;
                }

                int fy=Math.min(FIELD_ROWS-1,y*FIELD_ROWS/HEIGHT);
                int fx=Math.min(FIELD_COLS-1,x*FIELD_COLS/WIDTH);
                int field=fy*FIELD_COLS+fx;
                fieldHist[field*256+l]++;fieldN[field]++;
                if(l>=224)fieldBrightN[field]++;
                if(c)fieldClipN[field]++;
            }

            int[] fm=new int[FIELD_COUNT],fq25=new int[FIELD_COUNT],fq90=new int[FIELD_COUNT];
            double[] fb=new double[FIELD_COUNT],fc=new double[FIELD_COUNT];
            for(int f=0;f<FIELD_COUNT;f++) {
                fm[f]=quantile(fieldHist,f*256,fieldN[f],.50);
                fq25[f]=quantile(fieldHist,f*256,fieldN[f],.25);
                fq90[f]=quantile(fieldHist,f*256,fieldN[f],.90);
                fb[f]=fieldN[f]>0?fieldBrightN[f]/(double)fieldN[f]:0;
                fc[f]=fieldN[f]>0?fieldClipN[f]/(double)fieldN[f]:0;
            }

            double n=WIDTH*HEIGHT;
            out[step]=new Stats(
                    quantile(hist,total,.50),dark/n,bright/n,clip/n,
                    quantile(centerHist,centerN,.50),quantile(centerHist,centerN,.25),
                    quantile(outerHist,outerN,.90),
                    centerN>0?centerDark/(double)centerN:0,
                    outerN>0?outerBright/(double)outerN:0,
                    centerN>0?centerBright/(double)centerN:0,
                    centerN>0?centerClip/(double)centerN:0,
                    outerN>0?outerClip/(double)outerN:0,
                    fm,fq25,fq90,fb,fc);
        }
        return out;
    }

    /**
     * Whole-scene low-key placement. It only engages when both the scene and its
     * central body are starved, so an intentionally dark scene can remain dark.
     */
    public static int selectSceneKey(Stats[] s) {
        if(!validStats(s)||!sceneKeyStarved(s[0]))return 0;
        Stats base=s[0];int chosen=0;
        for(int i=1;i<STEPS;i++) {
            Stats v=s[i];
            if(unsafeDarkScene(base,v))break;
            if(sceneImproved(base,v))chosen=i;
            if(sceneTargetReached(v))break;
        }
        return chosen;
    }

    /**
     * Backlight placement measures the dark body separately from the background.
     * It may sacrifice background headroom, but not central subject highlights.
     */
    public static int selectBacklight(Stats[] s) {
        if(!validStats(s))return 0;
        if(s[0].fieldMapValid) {
            BodyCandidate body=multifieldBodyCandidate(s[0]);
            return body.valid&&body.confidence>=.20?selectBodyBacklight(s,body):0;
        }
        if(backlightConfidence(s[0])<.20)return 0;
        return selectBacklightQualified(s,BodyCandidate.invalid("legacy_center_fallback"));
    }

    private static int selectBacklightQualified(Stats[] s,BodyCandidate body) {
        if(body!=null&&body.valid)return selectBodyBacklight(s,body);
        Stats base=s[0];int chosen=0;
        for(int i=1;i<STEPS;i++) {
            Stats v=s[i];
            if(m9CharacterHighlightUnsafe(base,v)||unsafeBacklight(base,v))break;
            if(backlightImproved(base,v))chosen=i;
            if(backlightTargetReached(base,v))break;
        }
        return chosen;
    }

    /** Existing strict positive budget for ordinary scenes and ordinary inherited bias. */
    public static double positiveHeadroomLimit(Stats[] s) {
        if(!validStats(s))return 0;
        Stats base=s[0];int safe=0;
        for(int i=1;i<STEPS;i++) {
            if(unsafeOrdinary(base,s[i]))break;
            safe=i;
        }
        return ev(safe);
    }

    /** Bounded isolated-highlight loss for a genuinely starved whole scene. */
    public static double sceneKeyHeadroomLimit(Stats[] s) {
        if(!validStats(s)||!sceneKeyStarved(s[0]))return 0;
        Stats base=s[0];int safe=0;
        for(int i=1;i<STEPS;i++) {
            if(unsafeDarkScene(base,s[i]))break;
            safe=i;
        }
        return ev(safe);
    }

    /** Separate background-loss allowance, only after strong backlight qualification. */
    public static double backlightHeadroomLimit(Stats[] s) {
        if(!validStats(s))return 0;
        if(s[0].fieldMapValid) {
            BodyCandidate body=multifieldBodyCandidate(s[0]);
            return body.valid&&body.confidence>=.20?bodyHeadroomLimit(s,body):0;
        }
        if(backlightConfidence(s[0])<.20)return 0;
        return backlightHeadroomLimitQualified(s,BodyCandidate.invalid("legacy_center_fallback"));
    }

    private static double backlightHeadroomLimitQualified(Stats[] s,BodyCandidate body) {
        if(body!=null&&body.valid)return bodyHeadroomLimit(s,body);
        Stats base=s[0];int safe=0;
        for(int i=1;i<STEPS;i++) {
            if(m9CharacterHighlightUnsafe(base,s[i])||unsafeBacklight(base,s[i]))break;
            safe=i;
        }
        return ev(safe);
    }

    public static final class BodyCandidate {
        public final boolean valid;
        public final String reason;
        public final int mask,fieldCount,targetMedian,targetQ25;
        public final double confidence,severity,bodyMedian,bodyQ25,bodyQ90;
        public final double bodyBright,bodyClipped,backgroundQ90,backgroundBrightFieldFraction;
        BodyCandidate(boolean valid,String reason,int mask,int fieldCount,
                double confidence,double severity,double bodyMedian,double bodyQ25,double bodyQ90,
                double bodyBright,double bodyClipped,double backgroundQ90,
                double backgroundBrightFieldFraction,int targetMedian,int targetQ25) {
            this.valid=valid;this.reason=reason;this.mask=mask;this.fieldCount=fieldCount;
            this.confidence=confidence;this.severity=severity;
            this.bodyMedian=bodyMedian;this.bodyQ25=bodyQ25;this.bodyQ90=bodyQ90;
            this.bodyBright=bodyBright;this.bodyClipped=bodyClipped;
            this.backgroundQ90=backgroundQ90;
            this.backgroundBrightFieldFraction=backgroundBrightFieldFraction;
            this.targetMedian=targetMedian;this.targetQ25=targetQ25;
        }
        static BodyCandidate invalid(String reason) {
            return new BodyCandidate(false,reason,0,0,0,0,0,0,0,0,0,0,0,0,0);
        }
        JSONObject json() throws org.json.JSONException {
            return new JSONObject().put("valid",valid).put("reason",reason)
                    .put("mask",mask).put("fieldCount",fieldCount)
                    .put("confidence",confidence).put("severity",severity)
                    .put("bodyMedianCode",bodyMedian).put("bodyQ25Code",bodyQ25)
                    .put("bodyQ90Code",bodyQ90).put("bodyBrightFraction",bodyBright)
                    .put("bodyClipFraction",bodyClipped)
                    .put("backgroundQ90Code",backgroundQ90)
                    .put("backgroundBrightFieldFraction",backgroundBrightFieldFraction)
                    .put("targetMedianCode",targetMedian).put("targetQ25Code",targetQ25);
        }
    }

    private static final class BodyMetrics {
        double median,q25,q90,bright,clipped,backgroundQ90,backgroundBright,backgroundClipped;
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
        if(!key.equals(owner)){
            owner=key;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();
        }

        double legacy=Double.isFinite(legacyEv)?clamp(legacyEv,-.5,.75):0;
        double result=legacy,target=legacy;String reason="legacy_scene_baseline";
        Sample sample=latest;
        boolean valid=sample!=null&&sample.matches(camera,mode,nowNs,referenceEnergy);

        int sceneChosen=0,backlightChosen=0;
        double sceneRequest=0,backlightRequest=0;
        double strictLimit=valid?positiveHeadroomLimit(sample.stats):0;
        double sceneLimit=valid?sceneKeyHeadroomLimit(sample.stats):0;
        BodyCandidate multifieldBody=valid&&sample.stats[0].fieldMapValid
                ?multifieldBodyCandidate(sample.stats[0]):BodyCandidate.invalid("field_map_unavailable");
        double backlightConf=valid?(sample.stats[0].fieldMapValid
                ?(multifieldBody.valid?multifieldBody.confidence:0)
                :backlightConfidence(sample.stats[0])):0;
        if(valid) {
            if(backlightConf>=.22)backlightLatched=true;
            else if(backlightConf<=.12)backlightLatched=false;
        } else backlightLatched=false;
        double backlightLimit=valid&&backlightLatched
                ?backlightHeadroomLimitQualified(sample.stats,multifieldBody):0;
        double backlightSeverity=multifieldBody.valid?multifieldBody.severity
                :(valid?backlightPlacementSeverity(sample.stats[0]):0);
        int backlightCenterTarget=valid?backlightCenterTarget(sample.stats[0]):BACKLIGHT_CENTER_TARGET_MIN;
        int backlightQ25Target=valid?backlightCenterQ25Target(sample.stats[0]):BACKLIGHT_CENTER_Q25_TARGET_MIN;
        boolean lowKeyAdequate=valid&&lowKeyAdequate(sample.stats[0]);

        if(manualExposure!=0||manualIso!=0) {
            result=0;target=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();
            reason="manual_ISO_or_shutter";
        } else if(Math.abs(userEv)>1e-6) {
            if(!haveAuto){heldAutoEv=legacy;haveAuto=true;}
            result=heldAutoEv;target=result;reason="manual_EV_holds_auto_baseline";
        } else if(!autoEligible) {
            result=0;target=0;heldAutoEv=0;haveAuto=false;consumedSampleNs=-1;
            backlightLatched=false;resetLowerTargetHysteresis();
            reason="auto_scene_placement_not_eligible";
        } else if(valid) {
            sceneChosen=selectSceneKey(sample.stats);
            backlightChosen=backlightLatched?selectBacklightQualified(sample.stats,multifieldBody):0;
            sceneRequest=ev(sceneChosen);
            backlightRequest=ev(backlightChosen);

            // A coherent multi-field backlit body owns placement once qualified.
            // This prevents the whole-scene branch from overriding an off-centre subject.
            boolean useBacklight=backlightChosen>0;
            boolean useScene=!useBacklight&&sceneChosen>0;
            double positiveLimit=useBacklight?backlightLimit:(useScene?sceneLimit:strictLimit);
            double boundedLegacy=legacy>0?Math.min(legacy,positiveLimit):legacy;
            double request=useBacklight?backlightRequest:(useScene?sceneRequest:0);

            target=request>0?Math.max(boundedLegacy,request):boundedLegacy;
            if(target>0)target=Math.min(target,positiveLimit);

            double current=haveAuto?heldAutoEv:boundedLegacy;
            boolean freshSample=consumedSampleNs!=sample.submittedNs;
            boolean hardSafetyRelease=positiveLimit<current-1e-9;

            if(target>current+1e-9) {
                resetLowerTargetHysteresis();
                result=freshSample?Math.min(target,current+.25):current;
            } else if(target<current-1e-9) {
                if(hardSafetyRelease) {
                    // A real highlight/headroom loss remains immediate.
                    result=Math.min(target,positiveLimit);
                    resetLowerTargetHysteresis();
                } else if(freshSample) {
                    // Ordinary target/classification noise needs two fresh samples
                    // before stepping down, preventing 0.25-EV preview ping-pong.
                    if(!Double.isFinite(pendingLowerTargetEv)
                            ||Math.abs(target-pendingLowerTargetEv)>.125) {
                        pendingLowerTargetEv=target;lowerTargetConfirmations=1;result=current;
                    } else {
                        lowerTargetConfirmations++;
                        if(lowerTargetConfirmations>=2) {
                            result=Math.max(target,current-.25);
                            if(result<=target+1e-9)resetLowerTargetHysteresis();
                            else {pendingLowerTargetEv=target;lowerTargetConfirmations=0;}
                        } else result=current;
                    }
                } else result=current;
            } else {
                result=current;resetLowerTargetHysteresis();
            }
            consumedSampleNs=sample.submittedNs;heldAutoEv=result;haveAuto=true;

            if(useBacklight) {
                if(multifieldBody.valid) {
                    BodyMetrics finalBody=bodyMetrics(sample.stats[backlightChosen],multifieldBody.mask);
                    reason=bodyTargetReached(multifieldBody,finalBody)
                            ?"rendered_multifield_body_readability_target"
                            :"rendered_multifield_m9_character_or_headroom";
                } else {
                    reason=backlightTargetReached(sample.stats[0],sample.stats[backlightChosen])
                            ?"rendered_adaptive_backlight_body_target"
                            :"rendered_adaptive_backlight_search_ceiling_or_headroom";
                }
            }
            else if(useScene)
                reason=sceneTargetReached(sample.stats[sceneChosen])
                        ?"rendered_low_key_scene_target"
                        :"rendered_dark_scene_search_ceiling_or_headroom";
            else if(lowKeyAdequate)
                reason="low_key_scene_body_adequate";
            else
                reason="rendered_scene_no_extra_lift";
        } else {
            double bounded=legacy>0?0:legacy;
            heldAutoEv=bounded;haveAuto=true;result=bounded;target=bounded;
            reason="rendered_meter_unavailable_or_stale";
        }

        JSONObject o=new JSONObject();
        try {
            o.put("revision",REVISION).put("reason",reason)
                    .put("sampleValid",valid).put("meterStatus",meterStatus)
                    .put("autoPlacementEligible",autoEligible)
                    .put("legacySceneEv",legacy)
                    .put("strictPositiveHeadroomLimitEv",strictLimit)
                    .put("sceneKeyPositiveHeadroomLimitEv",sceneLimit)
                    .put("backlightPositiveHeadroomLimitEv",backlightLimit)
                    .put("sceneKeyRequestedEv",sceneRequest)
                    .put("backlightRequestedEv",backlightRequest)
                    .put("recommendedTotalAutoEv",target)
                    .put("appliedTotalAutoEv",result).put("userEv",userEv)
                    .put("meterDomain","neutral_reference_same_M9_GPU_shader")
                    .put("meterIncludesUserOrAutoEv",false)
                    .put("maximumPositiveSearchEv",SEARCH_MAX_EV)
                    .put("sceneMedianTargetCode",SCENE_MEDIAN_TARGET)
                    .put("sceneCenterTargetCode",SCENE_CENTER_TARGET)
                    .put("sceneCenterQ25TargetCode",SCENE_CENTER_Q25_TARGET)
                    .put("backlightCenterTargetCode",backlightCenterTarget)
                    .put("backlightCenterQ25TargetCode",backlightQ25Target)
                    .put("backlightCenterTargetRangeCode",
                            BACKLIGHT_CENTER_TARGET_MIN+".."+BACKLIGHT_CENTER_TARGET_MAX)
                    .put("backlightCenterQ25TargetRangeCode",
                            BACKLIGHT_CENTER_Q25_TARGET_MIN+".."+BACKLIGHT_CENTER_Q25_TARGET_MAX)
                    .put("backlightConfidence",backlightConf)
                    .put("backlightLatched",backlightLatched)
                    .put("backlightEngageConfidence",.22)
                    .put("backlightReleaseConfidence",.12)
                    .put("backlightPlacementSeverity",backlightSeverity)
                    .put("multifieldTopology","4x6_24_regions_rendered_neutral_reference")
                    .put("multifieldBorrowedArchitecture","M10R_4x6_topology_only_not_numerical_parity")
                    .put("multifieldBody",multifieldBody.json())
                    .put("m9CharacterHighlightGuard",true)
                    .put("lowerTargetConfirmations",lowerTargetConfirmations)
                    .put("pendingLowerTargetEv",
                            Double.isFinite(pendingLowerTargetEv)?pendingLowerTargetEv:JSONObject.NULL)
                    .put("lowKeyBodyAdequate",lowKeyAdequate)
                    .put("globalSceneSelectedStep",sceneChosen)
                    .put("backlightSelectedStep",backlightChosen)
                    .put("backgroundLossPolicy","multifield_body_protected_background_sacrifice_bounded")
                    .put("leicaMeterNumericalParity",false);
            if(valid) {
                o.put("sampleAgeMs",(nowNs-sample.submittedNs)/1e6)
                        .put("textureTimestampNs",sample.textureNs)
                        .put("resultTimestampNs",sample.resultNs)
                        .put("referenceEnergy",sample.referenceEnergy);
                JSONArray a=new JSONArray();
                for(Stats s:sample.stats)a.put(s.json());
                o.put("bracket",a);
            }
        } catch(org.json.JSONException e){throw new IllegalStateException(e);}
        return new Decision(result,reason,o);
    }

    public static BodyCandidate multifieldBodyCandidate(Stats s) {
        if(s==null||!s.valid()||!s.fieldMapValid)
            return BodyCandidate.invalid("field_map_unavailable");
        if(lowKeyAdequate(s))
            return BodyCandidate.invalid("accepted_low_key_body_adequate");
        if(s.median>=110&&s.bright>=.20)
            return BodyCandidate.invalid("scene_already_high_key");

        int sceneHigh=fieldQuantile(s.fieldQ90,-1,.75);
        int allBrightFields=0;
        for(int f=0;f<FIELD_COUNT;f++)
            if(s.fieldQ90[f]>=180||s.fieldBright[f]>=.02)allBrightFields++;
        double brightFieldFraction=allBrightFields/(double)FIELD_COUNT;

        boolean[] q=new boolean[FIELD_COUNT];
        double[] score=new double[FIELD_COUNT];
        for(int f=0;f<FIELD_COUNT;f++) {
            int med=s.fieldMedian[f],low=s.fieldQ25[f],hi=s.fieldQ90[f];
            boolean deepFloor=med<7&&hi<24;
            double need=Math.max(smoothstep(68.-med,4,36),smoothstep(34.-low,2,24));
            double contrast=smoothstep(sceneHigh-med,30,95);
            double brightSupport=smoothstep(brightFieldFraction,.10,.32);
            double support=Math.max(contrast,brightSupport);
            double structure=smoothstep(hi,16,50);
            q[f]=!deepFloor&&med<76&&low<50&&hi>=16&&need>.10&&support>.15;
            int row=f/FIELD_COLS,col=f%FIELD_COLS;
            double relevance=(row>=1&&row<=2&&col>=1&&col<=4)?1.12
                    :(col>=1&&col<=4?1.03:.96);
            score[f]=need*support*(.65+.35*structure)*relevance;
        }

        boolean[] seen=new boolean[FIELD_COUNT];
        int[] stack=new int[FIELD_COUNT];
        int bestMask=0,bestCount=0;
        double bestScore=0;
        for(int start=0;start<FIELD_COUNT;start++) {
            if(!q[start]||seen[start])continue;
            int top=0;stack[top++]=start;seen[start]=true;
            int mask=0,count=0;double sum=0;boolean hasInner=false;
            while(top>0) {
                int f=stack[--top];
                mask|=1<<f;count++;sum+=score[f];
                int row=f/FIELD_COLS,col=f%FIELD_COLS;
                if(row>=1&&row<=2&&col>=1&&col<=4)hasInner=true;
                int up=f-FIELD_COLS,down=f+FIELD_COLS,left=f-1,right=f+1;
                if(row>0&&q[up]&&!seen[up]){seen[up]=true;stack[top++]=up;}
                if(row<FIELD_ROWS-1&&q[down]&&!seen[down]){seen[down]=true;stack[top++]=down;}
                if(col>0&&q[left]&&!seen[left]){seen[left]=true;stack[top++]=left;}
                if(col<FIELD_COLS-1&&q[right]&&!seen[right]){seen[right]=true;stack[top++]=right;}
            }
            if(count>14)continue; // broad low-key field belongs to scene-key, not "subject".
            if(count==1) {
                int f=Integer.numberOfTrailingZeros(mask);
                if(!hasInner||score[f]<.72||s.fieldQ90[f]<45)continue;
            }
            if(count==2&&!hasInner)continue; // reject a narrow edge-shadow strip.
            double componentScore=sum*(1+.12*Math.min(count-1,4));
            if(componentScore>bestScore) {
                bestScore=componentScore;bestMask=mask;bestCount=count;
            }
        }
        if(bestMask==0)return BodyCandidate.invalid("no_coherent_dark_body");

        BodyMetrics body=bodyMetrics(s,bestMask);
        double contrast=body.backgroundQ90-body.median;
        double need=Math.max(smoothstep(60.-body.median,4,34),
                smoothstep(28.-body.q25,2,20));
        double support=Math.max(smoothstep(contrast,32,95),
                smoothstep(body.backgroundBright,.08,.30));
        double highKey=smoothstep(s.median,100,135)*smoothstep(s.bright,.16,.28);
        double confidence=clamp(Math.min(need,support)*(1-.90*highKey),0,1);
        if(confidence<.12)return BodyCandidate.invalid("body_confidence_too_low");

        double severity=clamp(Math.max(smoothstep(52.-body.median,4,30),
                .75*smoothstep(20.-body.q25,2,16)),0,1);
        int targetMedian=(int)Math.round(clamp(
                body.median+16+6*(1-severity),44,60));
        int targetQ25=(int)Math.round(clamp(
                body.q25+8+4*(1-severity),14,26));
        return new BodyCandidate(true,"coherent_dark_body",bestMask,bestCount,
                confidence,severity,body.median,body.q25,body.q90,
                body.bright,body.clipped,body.backgroundQ90,body.backgroundBright,
                targetMedian,targetQ25);
    }

    private static int selectBodyBacklight(Stats[] s,BodyCandidate body) {
        int chosen=0;
        BodyMetrics base=bodyMetrics(s[0],body.mask);
        for(int i=1;i<STEPS;i++) {
            BodyMetrics v=bodyMetrics(s[i],body.mask);
            if(m9BodyUnsafe(s[0],base,body,s[i],v))break;
            if(bodyImproved(base,v))chosen=i;
            if(bodyTargetReached(body,v))break;
        }
        return chosen;
    }

    private static double bodyHeadroomLimit(Stats[] s,BodyCandidate body) {
        int safe=0;
        BodyMetrics base=bodyMetrics(s[0],body.mask);
        for(int i=1;i<STEPS;i++) {
            BodyMetrics v=bodyMetrics(s[i],body.mask);
            if(m9BodyUnsafe(s[0],base,body,s[i],v))break;
            safe=i;
        }
        return ev(safe);
    }

    private static boolean bodyTargetReached(BodyCandidate body,BodyMetrics v) {
        return v.median>=body.targetMedian
                &&(v.q25>=body.targetQ25||v.q90>=body.targetMedian+18);
    }

    private static boolean bodyImproved(BodyMetrics base,BodyMetrics v) {
        return v.median>=base.median+3||v.q25>=base.q25+2||v.q90>=base.q90+5;
    }

    private static boolean m9BodyUnsafe(Stats baseScene,BodyMetrics base,BodyCandidate body,
            Stats scene,BodyMetrics v) {
        if(scene.clipped>.30+1e-9)return true;

        // Once the coherent dark body has clearly opened, do not chase remaining
        // black material into a phone-like exposure.
        if(v.median>=72&&v.q25>=36)return true;

        boolean readable=v.median>=Math.max(42,body.targetMedian-4);
        if(readable) {
            double bodyClipCap=Math.min(.10,
                    Math.max(.05,base.clipped+.045+.015*body.severity));
            double bodyBrightCap=Math.min(.18,
                    Math.max(.10,base.bright+.08+.03*body.severity));
            if(v.clipped>bodyClipCap+1e-9||v.bright>bodyBrightCap+1e-9)return true;

            // High-key scene protection: do not brighten an already-open frame
            // merely because one dark patch remains.
            if(scene.median>=100&&scene.bright>.24+1e-9)return true;
        }

        // Background may already be very bright at neutral reference. Do not
        // reject it for being bright; bound only additional loss from that baseline.
        double bgClipCap=Math.min(1.0,
                base.backgroundClipped+.18+.10*body.severity);
        double bgBrightCap=Math.min(1.0,
                base.backgroundBright+.16+.08*body.severity);
        return (v.backgroundClipped>.38&&v.backgroundClipped>bgClipCap+1e-9)
                ||(v.backgroundBright>.84&&v.backgroundBright>bgBrightCap+1e-9);
    }

    private static BodyMetrics bodyMetrics(Stats s,int mask) {
        BodyMetrics o=new BodyMetrics();
        if(s==null||!s.fieldMapValid||mask==0)return o;
        int n=0,bn=0;double sm=0,sq=0,sh=0,sb=0,sc=0,bgBright=0,bgClip=0;
        int[] bgHist=new int[256];
        for(int f=0;f<FIELD_COUNT;f++) {
            if((mask&(1<<f))!=0) {
                sm+=s.fieldMedian[f];sq+=s.fieldQ25[f];sh+=s.fieldQ90[f];
                sb+=s.fieldBright[f];sc+=s.fieldClipped[f];n++;
            } else {
                bgHist[s.fieldQ90[f]]++;
                bgBright+=(s.fieldQ90[f]>=180||s.fieldBright[f]>=.02)?1:0;
                bgClip+=s.fieldClipped[f];bn++;
            }
        }
        if(n>0) {
            o.median=sm/n;o.q25=sq/n;o.q90=sh/n;o.bright=sb/n;o.clipped=sc/n;
        }
        o.backgroundQ90=bn>0?quantile(bgHist,bn,.75):0;
        o.backgroundBright=bn>0?bgBright/bn:0;
        o.backgroundClipped=bn>0?bgClip/bn:0;
        return o;
    }

    private static int fieldQuantile(int[] values,int excludedMask,double q) {
        int[] h=new int[256];int n=0;
        for(int f=0;f<FIELD_COUNT;f++) {
            if(excludedMask>=0&&(excludedMask&(1<<f))!=0)continue;
            int v=values[f];if(v<0||v>255)continue;h[v]++;n++;
        }
        return quantile(h,n,q);
    }

    private static boolean sceneKeyStarved(Stats s) {
        return s.median<42&&s.centerMedian<56&&s.centerQ25<34&&backlightConfidence(s)<.20;
    }
    private static boolean lowKeyAdequate(Stats s) {
        return s.median<45&&s.centerMedian>=58&&s.centerQ25>=34;
    }
    private static boolean sceneTargetReached(Stats s) {
        return s.median>=SCENE_MEDIAN_TARGET
                && (s.centerMedian>=SCENE_CENTER_TARGET||s.centerQ25>=SCENE_CENTER_Q25_TARGET);
    }
    private static boolean backlightTargetReached(Stats base,Stats s) {
        return s.centerMedian>=backlightCenterTarget(base)
                && s.centerQ25>=backlightCenterQ25Target(base);
    }

    /**
     * Placement severity is deliberately different from backlight confidence.
     * Confidence answers "is this backlight?"; severity answers "how starved is
     * the body?". This prevents every qualified backlight scene from being driven
     * to the same brightness.
     */
    public static double backlightPlacementSeverity(Stats s) {
        if(s==null||!s.valid())return 0;
        double medianDeficit=smoothstep(58.-s.centerMedian,2,36);
        double lowBodyDeficit=smoothstep(28.-s.centerQ25,2,22);
        return clamp(Math.max(.65*medianDeficit,lowBodyDeficit),0,1);
    }

    public static int backlightCenterTarget(Stats s) {
        double severity=backlightPlacementSeverity(s);
        return (int)Math.round(BACKLIGHT_CENTER_TARGET_MIN
                +(BACKLIGHT_CENTER_TARGET_MAX-BACKLIGHT_CENTER_TARGET_MIN)*severity);
    }

    public static int backlightCenterQ25Target(Stats s) {
        double severity=backlightPlacementSeverity(s);
        return (int)Math.round(BACKLIGHT_CENTER_Q25_TARGET_MIN
                +(BACKLIGHT_CENTER_Q25_TARGET_MAX-BACKLIGHT_CENTER_Q25_TARGET_MIN)*severity);
    }
    private static boolean sceneImproved(Stats base,Stats v) {
        return v.median>=base.median+3||v.centerMedian>=base.centerMedian+3
                ||v.centerQ25>=base.centerQ25+2;
    }
    private static boolean backlightImproved(Stats base,Stats v) {
        return v.centerMedian>=base.centerMedian+3||v.centerQ25>=base.centerQ25+2;
    }

    private static double backlightConfidence(Stats s) {
        double medianNeed=smoothstep(60.-s.centerMedian,4,20);
        double lowNeed=smoothstep(36.-s.centerQ25,2,18);
        double subjectNeed=Math.max(medianNeed,lowNeed);
        double contrast=smoothstep(s.outerQ90-s.centerQ25,32,80);
        double brightSupport=smoothstep(s.outerBright,.02,.12);
        return Math.min(subjectNeed,Math.max(contrast,brightSupport));
    }

    private static boolean unsafeOrdinary(Stats base,Stats v) {
        return v.clipped>base.clipped+.015||v.bright>base.bright+.04;
    }

    private static boolean unsafeDarkScene(Stats base,Stats v) {
        // A genuinely starved scene may contain a lamp/specular. Permit bounded
        // isolated highlight loss rather than letting one point prevent useful exposure.
        double clipCap=Math.min(.25,Math.max(.14,base.clipped+.10));
        double brightCap=Math.min(.35,Math.max(.22,base.bright+.14));
        double centerClipCap=Math.min(.20,Math.max(.12,base.centerClipped+.08));
        return v.clipped>clipCap+1e-9||v.bright>brightCap+1e-9
                ||v.centerClipped>centerClipCap+1e-9;
    }

    /**
     * Soft M9-character ceiling. This is deliberately much tighter than the
     * catastrophic backlight guard and mostly protects the subject/centre.
     * Background sky/window clipping may still be sacrificed.
     */
    public static boolean m9CharacterHighlightUnsafe(Stats base,Stats v) {
        if(base==null||v==null||!base.valid()||!v.valid())return true;
        double severity=backlightPlacementSeverity(base);

        // A central window can already be clipped while the body is almost black.
        // Do not mistake that background for a bright subject. Central-highlight
        // pressure only gains authority once the lower body has actually opened.
        boolean bodyReadable=v.centerMedian>=58&&v.centerQ25>=28;
        if(bodyReadable) {
            double centerClipCap=Math.min(.22,
                    base.centerClipped+.06+.02*severity);
            double centerBrightCap=Math.min(.32,
                    base.centerBright+.10+.04*severity);
            if(v.centerClipped>centerClipCap+1e-9)return true;
            if(v.centerBright>centerBrightCap+1e-9)return true;
        }

        // Independent M9-character ceiling: once the body itself is this open,
        // substantial highlight pressure means the scene is being normalized
        // rather than merely giving the subject useful exposure.
        boolean bodyTooOpen=v.centerMedian>=100&&v.centerQ25>=42;
        if(bodyTooOpen&&(v.centerBright>=.18||v.centerClipped>=.10||v.clipped>=.12))
            return true;

        // Background sacrifice is still bounded globally.
        return v.clipped>.30+1e-9;
    }

    private static void resetLowerTargetHysteresis() {
        pendingLowerTargetEv=Double.NaN;lowerTargetConfirmations=0;
    }

    private static boolean unsafeBacklight(Stats base,Stats v) {
        // Background sacrifice scales with subject starvation. A mildly backlit
        // scene stays conservative; a severely black foreground may accept more
        // window/sky loss. This is still one global exposure, never local HDR.
        double severity=backlightPlacementSeverity(base);
        double centerClipCap=Math.min(.35,
                Math.max(.15,base.centerClipped+.10+.08*severity));
        double centerBrightCap=Math.min(.50,
                Math.max(.30,base.centerBright+.18+.10*severity));
        if(v.centerClipped>centerClipCap+1e-9)return true;
        if(v.centerBright>centerBrightCap+1e-9)return true;
        double outerClipCap=Math.min(.68,
                Math.max(.35,base.outerClipped+.20+.15*severity));
        double outerBrightCap=Math.min(.82,
                Math.max(.55,base.outerBright+.25+.15*severity));
        if(v.outerClipped>outerClipCap+1e-9||v.outerBright>outerBrightCap+1e-9)return true;
        return v.clipped>.40+.10*severity+1e-9;
    }

    private static boolean validStats(Stats[] s) {
        if(s==null||s.length!=STEPS)return false;
        for(Stats v:s)if(v==null||!v.valid())return false;
        return true;
    }
    private static int quantile(int[] hist,int total,double q) {
        if(total<=0)return 0;
        int target=(int)Math.ceil(clamp(q,0,1)*total);
        if(target<1)target=1;
        int sum=0;
        for(int i=0;i<256;i++){sum+=hist[i];if(sum>=target)return i;}
        return 255;
    }
    private static int quantile(int[] hist,int offset,int total,double q) {
        if(total<=0)return 0;
        int target=(int)Math.ceil(clamp(q,0,1)*total);
        if(target<1)target=1;
        int sum=0;
        for(int i=0;i<256;i++){sum+=hist[offset+i];if(sum>=target)return i;}
        return 255;
    }
    private static void clear(int[] a){for(int i=0;i<a.length;i++)a[i]=0;}
    private static JSONArray json(int[] a) {
        JSONArray out=new JSONArray();for(int v:a)out.put(v);return out;
    }
    private static JSONArray json(double[] a) {
        JSONArray out=new JSONArray();for(double v:a)out.put(v);return out;
    }
    private static boolean code(int x){return x>=0&&x<=255;}
    private static boolean fraction(double x){return Double.isFinite(x)&&x>=0&&x<=1;}
    private static double smoothstep(double value,double low,double high) {
        if(high<=low)return value>=high?1:0;
        double t=clamp((value-low)/(high-low),0,1);
        return t*t*(3-2*t);
    }
    private static double clamp(double x,double lo,double hi){return Math.max(lo,Math.min(hi,x));}
    private static double log2(double x){return Math.log(x)/Math.log(2);}
}
