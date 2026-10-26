package com.particlesdevs.photoncamera.control.tracking;

import java.util.List;

/**
 * Opt-in, camera-neutral tap-pinned recognition anchor for the existing
 * arbitrary-patch tracker. Class labels are merely detector observations;
 * they never establish optical focus. Only a fresh, spatially coherent
 * observation can move the autofocus region.
 *
 * The ordinary arbitrary-patch tracker remains available for objects
 * outside this deliberately restricted PERSON/CAT/DOG class set.
 */
public final class SubjectAnchorPolicy {
    public enum ClassId { PERSON, CAT, DOG }
    public enum State { WAITING, ACQUIRED, HOLD, UNAVAILABLE, RETIRED }
    public static final long MAX_ACTION_AGE_MS = 500L;
    public static final long MAX_HOLD_MS = 1150L;
    public static final long MAX_PENDING_MS = 1350L;
    private static final long MAX_DETECTION_GAP_MS = 850L;
    private static final float MIN_SCORE = .45f;

    public static final class Candidate {
        public final ClassId category;
        public final float score, left, top, right, bottom;
        public final SubjectAppearanceDescriptor appearance;
        public Candidate(String label, float score, float left, float top, float right, float bottom) {
            this(label,score,left,top,right,bottom,null);
        }
        public Candidate(String label, float score, float left, float top, float right, float bottom,
                         SubjectAppearanceDescriptor appearance) {
            category = classify(label); this.score=score;
            this.left=left; this.top=top; this.right=right; this.bottom=bottom;
            this.appearance=appearance;
        }
        public float width() { return right-left; }
        public float height() { return bottom-top; }
        public float cx() { return (left+right)*.5f; }
        public float cy() { return (top+bottom)*.5f; }
        public boolean contains(float x,float y,float pad) {
            return x>=left-pad && x<=right+pad && y>=top-pad && y<=bottom+pad;
        }
        public boolean valid() {
            return category!=null && finite(score) && score>=MIN_SCORE
                && finite(left)&&finite(top)&&finite(right)&&finite(bottom)
                && left>=0f && top>=0f && right<=1f && bottom<=1f
                && width()>=.07f && height()>=.09f && width()*height()>=.008f;
        }
    }
    public static final class Decision {
        public final State state;
        public final ClassId category;
        public final float x,y,halfWidth,halfHeight,score;
        private Decision(State state, ClassId category, float x,float y,float halfWidth,float halfHeight,float score) {
            this.state=state;this.category=category;this.x=x;this.y=y;
            this.halfWidth=halfWidth;this.halfHeight=halfHeight;this.score=score;
        }
        public boolean canMoveAf(){return state==State.ACQUIRED;}
    }

    private long epoch=Long.MIN_VALUE, tapAtMs=Long.MIN_VALUE, lastFrameMs=Long.MIN_VALUE;
    private long lastSeenMs=Long.MIN_VALUE, lastCandidateMs=Long.MIN_VALUE;
    private float tapX,tapY,relX=.5f,relY=.4f;
    private Candidate pending, current;
    private int confirmations;
    private boolean locked,retired;
    /** The optional 3.09 identity check does not alter 3.08 when disabled. */
    private boolean appearanceEnabled, recoveryNeeded;
    private SubjectAppearanceDescriptor pinnedAppearance;
    private Candidate recoveryCandidate;
    private int recoveryConfirmations;
    private long recoveryAtMs=Long.MIN_VALUE;

    public synchronized void useAppearance(boolean enable) {
        if(appearanceEnabled==enable)return;
        appearanceEnabled=enable;
        pinnedAppearance=null;
        recoveryNeeded=false;recoveryCandidate=null;recoveryConfirmations=0;
        recoveryAtMs=Long.MIN_VALUE;
    }

    public synchronized void begin(long token,float u,float v,long nowMs) {
        epoch=token;tapAtMs=nowMs;lastFrameMs=Long.MIN_VALUE;
        lastCandidateMs=lastSeenMs=Long.MIN_VALUE;
        tapX=u;tapY=v;relX=.5f;relY=.4f;
        pending=current=null; confirmations=0;locked=false;retired=false;
        pinnedAppearance=null;recoveryNeeded=false;recoveryCandidate=null;
        recoveryConfirmations=0;recoveryAtMs=Long.MIN_VALUE;
        if(!inUnit(u)||!inUnit(v)||nowMs<0)retired=true;
    }
    public synchronized boolean owns(long token){return token==epoch&&locked&&!retired;}
    public synchronized Decision observe(long token,long frameAtMs,long nowMs,List<Candidate> observations) {
        if(token!=epoch||retired||nowMs<0)return decision(State.RETIRED,null);
        if(frameAtMs<=lastFrameMs)return decision(locked?State.HOLD:State.WAITING,null);
        lastFrameMs=frameAtMs;
        if(frameAtMs>nowMs || nowMs-frameAtMs>MAX_ACTION_AGE_MS)
            return missing(nowMs);
        if(observations==null) return missing(nowMs);
        Candidate choice=choose(observations,nowMs);
        if(choice==null)return missing(nowMs);
        if(!locked) {
            if(pending!=null && samePending(pending,choice,nowMs))confirmations++;
            else confirmations=1;
            pending=choice;
            lastCandidateMs=nowMs;
            if(confirmations<2)return decision(State.WAITING,choice);
            locked=true;
            // Preserve the user's original tap INSIDE the subject across
            // viewpoint/size changes, rather than forcing centre-body focus.
            relX=clamp((tapX-choice.left)/choice.width(),.15f,.85f);
            relY=clamp((tapY-choice.top)/choice.height(),.12f,.88f);
            if(appearanceEnabled && choice.appearance!=null && choice.appearance.informative())
                pinnedAppearance=choice.appearance;
        }
        // One fresh rectangle after a hold is insufficient evidence of identity.
        // Two spatially coherent, distinct detector frames are required before
        // allowing Camera2 to move again. This applies only to the 3.09 opt-in.
        if(appearanceEnabled && recoveryNeeded) {
            if(recoveryCandidate!=null && nowMs-recoveryAtMs<=MAX_DETECTION_GAP_MS
                    && recoveryCandidate.category==choice.category
                    && spatialMatch(recoveryCandidate,choice,.22f))recoveryConfirmations++;
            else recoveryConfirmations=1;
            recoveryCandidate=choice;recoveryAtMs=nowMs;
            if(recoveryConfirmations<2)return decision(State.HOLD,current);
            recoveryNeeded=false;recoveryCandidate=null;recoveryConfirmations=0;
            recoveryAtMs=Long.MIN_VALUE;
        }
        // Change signature only on unambiguous, strongly consistent looks;
        // a passing stranger must never gradually replace the pinned reference.
        if(appearanceEnabled && pinnedAppearance!=null && choice.appearance!=null) {
            float similarity=pinnedAppearance.similarity(choice.appearance);
            if(Float.isFinite(similarity) && similarity>.88f && current!=null
                    && Math.hypot(current.cx()-choice.cx(),current.cy()-choice.cy())<.15)
                pinnedAppearance=pinnedAppearance.blend(choice.appearance,.05f);
        }
        current=choice;lastSeenMs=nowMs;
        return decision(State.ACQUIRED,choice);
    }
    private boolean samePending(Candidate old,Candidate next,long nowMs) {
        return old.category==next.category && nowMs-lastCandidateMs<=MAX_DETECTION_GAP_MS
                && spatialMatch(old,next,.26f);
    }
    private Candidate choose(List<Candidate> observations,long nowMs) {
        Candidate best=null;float bestQuality=Float.NEGATIVE_INFINITY,runner=Float.NEGATIVE_INFINITY;
        for(Candidate candidate:observations){
            if(candidate==null||!candidate.valid())continue;
            if(locked) {
                if(current==null||candidate.category!=current.category)continue;
                // Even distinctive appearance cannot justify a distant jump.
                float look=pinnedAppearance==null?Float.NaN:
                        pinnedAppearance.similarity(candidate.appearance);
                float radius=appearanceEnabled && Float.isFinite(look) && look>.86f
                        ? .37f : .32f;
                if(!spatialMatch(current,candidate,radius))continue;
                if(appearanceEnabled && pinnedAppearance!=null &&
                        pinnedAppearance.informative()) {
                    // Reject different clothing/fur. If the new observation is
                    // colourless/uncertain, only allow spatial continuity while
                    // unobstructed; never use it to reacquire after a hold.
                    if(Float.isFinite(look) && look<.63f)continue;
                    if(!Float.isFinite(look) && recoveryNeeded)continue;
                }
            }else{
                if(!candidate.contains(tapX,tapY,.025f))continue;
                if(pending!=null&&candidate.category!=pending.category)continue;
            }
            float quality=candidate.score;
            if(locked && current!=null){
                float motion=(float)Math.hypot(candidate.cx()-current.cx(),candidate.cy()-current.cy());
                quality-=motion*.45f;
            } else if(pending!=null){
                float motion=(float)Math.hypot(candidate.cx()-pending.cx(),candidate.cy()-pending.cy());
                quality-=motion*.18f;
            }
            if(appearanceEnabled && locked && pinnedAppearance!=null) {
                float app=pinnedAppearance.similarity(candidate.appearance);
                if(Float.isFinite(app))quality+=.70f*app;
                else quality-=.20f;
            }
            if(quality>bestQuality){runner=bestQuality;bestQuality=quality;best=candidate;}
            else runner=Math.max(runner,quality);
        }
        // Two plausible matches are not safe identity evidence. Prefer HOLD
        // over stealing a neighbouring person's or animal's AF target.
        if(locked && runner>Float.NEGATIVE_INFINITY && bestQuality-runner<
                (appearanceEnabled?.16f:.09f))return null;
        return best;
    }
    private static boolean spatialMatch(Candidate old,Candidate next,float maxDistance){
        float dist=(float)Math.hypot(old.cx()-next.cx(),old.cy()-next.cy());
        float sizeChange=Math.max(next.width()/old.width(),old.width()/next.width());
        float heightChange=Math.max(next.height()/old.height(),old.height()/next.height());
        return sizeChange<=2.3f&&heightChange<=2.3f
                && (iou(old,next)>=.10f || dist<=maxDistance);
    }
    private static float iou(Candidate a,Candidate b){
        float ix=Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left));
        float iy=Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
        float intersection=ix*iy;
        return intersection/Math.max(.0001f,a.width()*a.height()+b.width()*b.height()-intersection);
    }
    private Decision missing(long nowMs){
        if(locked){
            if(lastSeenMs!=Long.MIN_VALUE && nowMs-lastSeenMs<=MAX_HOLD_MS) {
                if(appearanceEnabled)recoveryNeeded=true;
                return decision(State.HOLD,current);
            }
            locked=false;retired=true;return decision(State.RETIRED,null);
        }
        if(tapAtMs!=Long.MIN_VALUE && nowMs-tapAtMs<=MAX_PENDING_MS)
            return decision(State.WAITING,null);
        return decision(State.UNAVAILABLE,null);
    }
    public synchronized Decision current(long token,long nowMs){
        if(token!=epoch||retired)return decision(State.RETIRED,null);
        return missing(nowMs);
    }
    private Decision decision(State state,Candidate chosen){
        Candidate c=chosen!=null?chosen:current;
        if(c==null)return new Decision(state,null,tapX,tapY,.07f,.07f,0f);
        float x=clamp(c.left+c.width()*relX,0f,1f);
        float y=clamp(c.top+c.height()*relY,0f,1f);
        // AF and indicator anchor are SMALL relative to the target body;
        // never treat a full-body detection rectangle as an optical focus area.
        float halfW=clamp(c.width()*.16f,.035f,.14f);
        float halfH=clamp(c.height()*.13f,.035f,.14f);
        return new Decision(state,c.category,x,y,halfW,halfH,c.score);
    }
    public static ClassId classify(String s){
        if(s==null)return null;
        if("person".equalsIgnoreCase(s))return ClassId.PERSON;
        if("cat".equalsIgnoreCase(s))return ClassId.CAT;
        if("dog".equalsIgnoreCase(s))return ClassId.DOG;
        return null;
    }
    private static boolean finite(float x){return Float.isFinite(x);}
    private static boolean inUnit(float x){return finite(x)&&x>=0f&&x<=1f;}
    private static float clamp(float x,float lo,float hi){return Math.max(lo,Math.min(hi,x));}
}
