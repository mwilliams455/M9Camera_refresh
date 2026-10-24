package com.particlesdevs.photoncamera.control.subject;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/**
 * Camera-independent cat/dog AF target gate.
 * Only class-labelled COCO detections enter the gate; a generic image patch,
 * person, houseplant or vehicle must never become a pet target.
 *
 * Normalized coordinates refer to the upright displayed preview, NOT
 * Camera2 active-array coordinates. The existing TrackingGeometry is the
 * sole owner of screen-to-sensor mapping.
 */
public final class PetTargetPolicy {
    public static final float MIN_CONFIDENCE = 0.64f;
    public static final int REQUIRED_CONFIRMATIONS = 3;
    public static final long MAX_FRAME_AGE_NS = 300_000_000L;
    public static final long MAX_GAP_NS = 850_000_000L;
    private static final long LOST_NS = 800_000_000L;

    public enum Species { CAT, DOG }

    public static final class Candidate {
        public final Species species;
        public final float score, left, top, right, bottom;
        public Candidate(String label, float score, float left, float top,
                         float right, float bottom) {
            this.species = speciesFor(label);
            this.score=score;
            this.left=left; this.top=top; this.right=right; this.bottom=bottom;
        }
        public float cx() { return (left+right)*.5f; }
        public float cy() { return (top+bottom)*.5f; }
        public float width() { return right-left; }
        public float height() { return bottom-top; }
        public boolean contains(float x,float y) {
            return x>=left && x<=right && y>=top && y<=bottom;
        }
        public boolean valid() {
            return species!=null && Float.isFinite(score) && score>=MIN_CONFIDENCE
                && finite(left) && finite(top) && finite(right) && finite(bottom)
                && left>=0 && top>=0 && right<=1 && bottom<=1
                && width()>=.065f && height()>=.065f
                && width()*height()>=.008f;
        }
    }
    public static final class Target {
        public final Species species;
        public final float x,y,halfWidth,halfHeight,score;
        public final long sessionEpoch, frameNs;
        private Target(Candidate candidate,long epoch,long frame) {
            species=candidate.species;
            x=candidate.cx(); y=candidate.cy();
            halfWidth=Math.min(.22f,Math.max(.045f,candidate.width()*.32f));
            halfHeight=Math.min(.22f,Math.max(.045f,candidate.height()*.32f));
            score=candidate.score;
            sessionEpoch=epoch;frameNs=frame;
        }
    }
    private long epoch=Long.MIN_VALUE,lastFrameNs=Long.MIN_VALUE,lastSeenNs=Long.MIN_VALUE;
    private Candidate current;
    private int confirmations;
    private boolean tapPinned;
    private Candidate pendingTap;

    public synchronized void beginSession(long token) {
        epoch=token; lastFrameNs=Long.MIN_VALUE; lastSeenNs=Long.MIN_VALUE;
        current=null;pendingTap=null;tapPinned=false;confirmations=0;
    }
    public synchronized void clear() {
        current=null;pendingTap=null;tapPinned=false;confirmations=0;
        lastSeenNs=Long.MIN_VALUE;
    }
    public static Species speciesFor(String label) {
        if (label==null) return null;
        switch(label.trim().toLowerCase(Locale.ROOT)) {
            case "cat": return Species.CAT;
            case "dog": return Species.DOG;
            default: return null;
        }
    }

    /** The tap itself is not proof: confidence and temporal gate still apply. */
    public synchronized boolean tapSelect(float x,float y,List<Candidate> candidates) {
        if(!finite(x)||!finite(y)||x<0||x>1||y<0||y>1||candidates==null) return false;
        Candidate chosen=null;
        for(Candidate c:candidates) {
            if(c==null||!c.valid()||!c.contains(x,y)) continue;
            if(chosen==null||area(c)<area(chosen)) chosen=c;
        }
        if(chosen==null) return false;
        pendingTap=chosen;
        current=chosen;
        confirmations=0; tapPinned=true; lastSeenNs=Long.MIN_VALUE;
        return true;
    }

    public synchronized Target update(long token,long frameNs,long nowNs,
                                      List<Candidate> candidates) {
        if(token!=epoch||frameNs<=lastFrameNs||frameNs<=0||nowNs<frameNs
                ||nowNs-frameNs>MAX_FRAME_AGE_NS) return null;
        lastFrameNs=frameNs;
        List<Candidate> good = new ArrayList<>();
        if(candidates!=null) for(Candidate c:candidates)
            if(c!=null&&c.valid()) good.add(c);
        Candidate next=null;
        if(current!=null) {
            double match=0;
            for(Candidate c:good) {
                if(c.species!=current.species) continue;
                double overlap=iou(current,c);
                // Match the same local moving target, not merely the next
                // largest object of the same species across the screen.
                if(overlap>.18 && overlap>match) {next=c;match=overlap;}
            }
            if(next==null) {
                if(lastSeenNs!=Long.MIN_VALUE&&frameNs-lastSeenNs<=LOST_NS)
                    return null;
                if(tapPinned) return null; // user owns identity until a new tap
                current=null;confirmations=0;
            }
        }
        if(next==null && current==null) {
            for(Candidate c:good)
                if(next==null||area(c)*c.score>area(next)*next.score)
                    next=c;
        }
        if(next==null) return null;
        final boolean continuing=current!=null && current.species==next.species
                && lastSeenNs!=Long.MIN_VALUE && frameNs-lastSeenNs<=MAX_GAP_NS
                && iou(current,next)>.18;
        confirmations=continuing?Math.min(REQUIRED_CONFIRMATIONS,confirmations+1):1;
        current=next;lastSeenNs=frameNs;
        if(confirmations<REQUIRED_CONFIRMATIONS)return null;
        return new Target(next,token,frameNs);
    }
    public synchronized List<Candidate> validCandidates(List<Candidate> candidates) {
        if(candidates==null)return Collections.emptyList();
        List<Candidate> safe=new ArrayList<>();
        for(Candidate c:candidates)if(c!=null&&c.valid())safe.add(c);
        return safe;
    }
    private static float area(Candidate c) {return c.width()*c.height();}
    private static boolean finite(float v){return Float.isFinite(v);}
    private static double iou(Candidate a,Candidate b) {
        float w=Math.max(0f,Math.min(a.right,b.right)-Math.max(a.left,b.left));
        float h=Math.max(0f,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
        double inter=w*h;
        double union=area(a)+area(b)-inter;
        return union>0?inter/union:0;
    }
}
