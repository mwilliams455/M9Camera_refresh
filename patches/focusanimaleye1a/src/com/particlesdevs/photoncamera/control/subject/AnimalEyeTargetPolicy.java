package com.particlesdevs.photoncamera.control.subject;

/**
 * Conservatively selects an AP-10K cat/dog eye target relative to an already
 * confirmed COCO animal. No animal pose detector may create a new pet target.
 *
 * This is intentionally separate from PetTargetPolicy: its last-known body
 * centre remains the safe fallback whenever pose evidence is absent/late.
 * Coordinates and animal bounding boxes are normalized upright preview space.
 */
public final class AnimalEyeTargetPolicy {
    public static final int EYE_LEFT=0, EYE_RIGHT=1, NOSE=2;
    public static final int REQUIRED_HITS=2;
    public static final long MAX_FRAME_AGE_NS=700_000_000L;
    public static final long MAX_HIT_GAP_NS=1_400_000_000L;
    public static final float MIN_EYE_SCORE=.38f;
    public static final float MIN_NOSE_SCORE=.35f;

    public static final class Point {
        public final float x,y,score;
        public Point(float x,float y,float score){this.x=x;this.y=y;this.score=score;}
        public boolean valid(float min) {
            return Float.isFinite(x)&&Float.isFinite(y)&&Float.isFinite(score)
                    &&score>=min&&x>=0f&&x<=1f&&y>=0f&&y<=1f;
        }
    }
    public static final class Observation {
        public final PetTargetPolicy.Species species;
        public final float left,top,right,bottom;
        public final Point leftEye,rightEye,nose;
        public final long frameNs,sessionEpoch;
        public Observation(PetTargetPolicy.Species species,float left,float top,
                           float right,float bottom,Point leftEye,Point rightEye,
                           Point nose,long frameNs,long epoch) {
            this.species=species;this.left=left;this.top=top;
            this.right=right;this.bottom=bottom;
            this.leftEye=leftEye;this.rightEye=rightEye;this.nose=nose;
            this.frameNs=frameNs;this.sessionEpoch=epoch;
        }
        public boolean validBox(){
            return species!=null&&finite(left)&&finite(top)&&finite(right)&&finite(bottom)
                    &&left>=0f&&top>=0f&&right<=1f&&bottom<=1f
                    &&right-left>=.065f&&bottom-top>=.065f;
        }
        public float cx(){return (left+right)*.5f;}
        public float cy(){return (top+bottom)*.5f;}
    }
    public static final class Target {
        public final float x,y,confidence;
        public final PetTargetPolicy.Species species;
        public final long frameNs,sessionEpoch;
        public final int eyeIndex;
        private Target(float x,float y,float confidence,PetTargetPolicy.Species species,
                long frameNs,long epoch,int eyeIndex){
            this.x=x;this.y=y;this.confidence=confidence;this.species=species;
            this.frameNs=frameNs;this.sessionEpoch=epoch;this.eyeIndex=eyeIndex;
        }
    }

    private long epoch=Long.MIN_VALUE;
    private long previousFrameNs=Long.MIN_VALUE;
    private long lastHitNs=Long.MIN_VALUE;
    private PetTargetPolicy.Species species;
    private int selectedEye=-1;
    private int hits;
    private float previousEyeX,previousEyeY,previousBodyX,previousBodyY;
    private String reason="no_pose";
    public synchronized String lastReason(){return reason;}
    public synchronized void beginSession(long sessionEpoch) {
        epoch=sessionEpoch;previousFrameNs=Long.MIN_VALUE;lastHitNs=Long.MIN_VALUE;
        species=null;selectedEye=-1;hits=0;reason="session_reset";
    }
    public synchronized void clear() {
        lastHitNs=Long.MIN_VALUE;species=null;selectedEye=-1;hits=0;
        reason="fallback_body";
    }
    /**
     * Returns null until a credible same-animal eye has appeared twice.
     * Does NOT submit focus regions or replace normal AF-C on its own.
     */
    public synchronized Target update(long sessionEpoch,long nowNs,
                                      Observation observation,PetTargetPolicy.Target pet) {
        if(observation==null||pet==null||observation.sessionEpoch!=epoch
                ||sessionEpoch!=epoch||observation.sessionEpoch!=sessionEpoch
                ||observation.frameNs!=pet.frameNs) {
            reason="session_or_pet_mismatch";return null;
        }
        long stamp=observation.frameNs;
        if(stamp<=previousFrameNs||stamp<=0||nowNs<stamp
                ||nowNs-stamp>MAX_FRAME_AGE_NS) {
            reason="stale_pose";return null;
        }
        previousFrameNs=stamp;
        if(!observation.validBox()||pet.species!=observation.species
                ||!contains(observation,pet.x,pet.y)) {
            clear();reason="not_current_pet";return null;
        }
        Point nose=observation.nose;
        if(nose==null||!nose.valid(MIN_NOSE_SCORE)
                ||!contains(observation,nose.x,nose.y)){
            clear();reason="nose_unverified";return null;
        }
        Point left=credibleEye(observation,observation.leftEye,nose)
                ?observation.leftEye:null;
        Point right=credibleEye(observation,observation.rightEye,nose)
                ?observation.rightEye:null;
        if(left==null&&right==null) {
            clear();reason="eye_unverified";return null;
        }
        float bodyX=observation.cx(),bodyY=observation.cy();
        boolean continuing=lastHitNs!=Long.MIN_VALUE
                &&stamp-lastHitNs<=MAX_HIT_GAP_NS
                &&observation.species==species
                &&Math.abs(bodyX-previousBodyX)<.18f
                &&Math.abs(bodyY-previousBodyY)<.18f;
        int nextEye;
        if(continuing&&selectedEye==EYE_LEFT&&left!=null)nextEye=EYE_LEFT;
        else if(continuing&&selectedEye==EYE_RIGHT&&right!=null)nextEye=EYE_RIGHT;
        else if(left==null)nextEye=EYE_RIGHT;
        else if(right==null)nextEye=EYE_LEFT;
        else if(continuing) {
            float dl=sq(left.x-previousEyeX)+sq(left.y-previousEyeY);
            float dr=sq(right.x-previousEyeX)+sq(right.y-previousEyeY);
            nextEye=dl<=dr?EYE_LEFT:EYE_RIGHT;
        } else {
            nextEye=left.score>=right.score?EYE_LEFT:EYE_RIGHT;
        }
        Point chosen=nextEye==EYE_LEFT?left:right;
        boolean stable=continuing&&nextEye==selectedEye
                &&Math.abs(chosen.x-previousEyeX)<=.14f
                &&Math.abs(chosen.y-previousEyeY)<=.14f;
        hits=stable?Math.min(REQUIRED_HITS,hits+1):1;
        selectedEye=nextEye;
        species=observation.species;lastHitNs=stamp;
        previousEyeX=chosen.x;previousEyeY=chosen.y;
        previousBodyX=bodyX;previousBodyY=bodyY;
        if(hits<REQUIRED_HITS){reason="eye_confirming";return null;}
        reason="eye_ready";
        return new Target(chosen.x,chosen.y,chosen.score,observation.species,
                stamp,epoch,nextEye);
    }
    private static boolean credibleEye(Observation o,Point eye,Point nose){
        if(eye==null||!eye.valid(MIN_EYE_SCORE)||!contains(o,eye.x,eye.y))
            return false;
        float w=o.right-o.left,h=o.bottom-o.top;
        float nx=(eye.x-nose.x)/w,ny=(eye.y-nose.y)/h;
        float normalizedDistance=(float)Math.hypot(nx,ny);
        // AP-10K eye must be within the head region near the nose, not
        // a bright patch at the hips/paws or a floating point outside pet.
        return normalizedDistance>=.035f&&normalizedDistance<=.62f
                &&(eye.y-o.top)/h<=.74f;
    }
    private static boolean contains(Observation o,float x,float y){
        return x>=o.left&&x<=o.right&&y>=o.top&&y<=o.bottom;
    }
    private static boolean finite(float x){return Float.isFinite(x);}
    private static float sq(float x){return x*x;}
}
