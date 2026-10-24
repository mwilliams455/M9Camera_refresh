package com.particlesdevs.photoncamera.control.subject;

import java.util.Locale;

/**
 * Shared, offline, no-camera-dependency focusing policy for M9/Monochrom.
 *
 * Implements the inspired Spot / Expand Spot / Custom / Wide geometry. The
 * Android Camera2 owner is responsible for applying this computed region to
 * the active physical sensor with crop/mirror/rotation. NEVER touches AE/AWB.
 *
 * The policy can restrict candidate acquisition to the selected search area
 * and distinguish detection from HAL-reported focus. A UI box alone is never
 * proof of achieved focus.
 */
public final class FocusControlPolicy {
    public enum Mode { SPOT, EXPAND_SPOT, CUSTOM, WIDE }
    public enum FocusStatus { UNKNOWN, SCANNING, HAL_FOCUSED, HAL_UNFOCUSED, INACTIVE }
    public static final int AF_INACTIVE=0, AF_PASSIVE_SCAN=1, AF_PASSIVE_FOCUSED=2;
    public static final int AF_ACTIVE_SCAN=3, AF_FOCUSED_LOCKED=4;
    public static final int AF_NOT_FOCUSED_LOCKED=5, AF_PASSIVE_UNFOCUSED=6;
    public static final long AF_FRESH_MS=650;
    public static final long EXPAND_AFTER_MS=650;
    public static final float SPOT=.07f,EXPANDED=.19f;
    public static final float CUSTOM_MIN=.05f,CUSTOM_MAX=.50f;

    public static final class Region {
        public final float x,y,width,height;
        private Region(float x,float y,float width,float height) {
            this.x=x;this.y=y;this.width=width;this.height=height;
        }
        public float left(){return x-width*.5f;}
        public float right(){return x+width*.5f;}
        public float top(){return y-height*.5f;}
        public float bottom(){return y+height*.5f;}
        public boolean intersects(float l,float t,float r,float b) {
            return l<=right()&&r>=left()&&t<=bottom()&&b>=top();
        }
        public boolean contains(float px,float py) {
            return px>=left()&&px<=right()&&py>=top()&&py<=bottom();
        }
    }

    private long session=Long.MIN_VALUE;
    private Mode mode=Mode.WIDE;
    private float w=.20f,h=.20f;
    private float anchorX=.5f,anchorY=.5f;
    private boolean pinned;
    private long lastStateAtMs=Long.MIN_VALUE;
    private int afState=-1;
    private long unsuccessfulSinceMs=Long.MIN_VALUE;
    private boolean expanded;

    public synchronized void beginSession(long token){
        session=token;pinned=false;
        anchorX=anchorY=.5f;
        lastStateAtMs=Long.MIN_VALUE;
        unsuccessfulSinceMs=Long.MIN_VALUE;
        afState=-1;expanded=false;
    }
    public synchronized void configure(Mode next,float width,float height){
        if(next==null)next=Mode.WIDE;
        width=safeSize(width,.20f);
        height=safeSize(height,.20f);
        if(next!=mode||width!=w||height!=h){
            mode=next;w=width;h=height;
            pinned=false;anchorX=anchorY=.5f;
            unsuccessfulSinceMs=Long.MIN_VALUE;
            expanded=false;
        }
    }
    private static float safeSize(float value,float fallback){
        return Float.isFinite(value)?clamp(value,CUSTOM_MIN,CUSTOM_MAX):fallback;
    }
    public synchronized Mode mode(){return mode;}
    public synchronized boolean pinned(){return pinned;}
    public synchronized boolean tap(long token,float x,float y){
        if(session!=token||!valid(x)||!valid(y))return false;
        anchorX=clamp(x,0f,1f);anchorY=clamp(y,0f,1f);
        pinned=true;expanded=false;unsuccessfulSinceMs=Long.MIN_VALUE;
        return true;
    }
    public synchronized void releasePin(long token) {
        if(token!=session)return;
        pinned=false;anchorX=anchorY=.5f;
        expanded=false;unsuccessfulSinceMs=Long.MIN_VALUE;
    }
    public synchronized void observeAf(long token,Integer newState,long nowMs) {
        if(token!=session||newState==null||nowMs<0)return;
        if(lastStateAtMs>nowMs)return;
        lastStateAtMs=nowMs;afState=newState;
        if(newState==AF_PASSIVE_FOCUSED||newState==AF_FOCUSED_LOCKED){
            unsuccessfulSinceMs=Long.MIN_VALUE;expanded=false;return;
        }
        if(newState==AF_PASSIVE_UNFOCUSED||newState==AF_NOT_FOCUSED_LOCKED){
            if(unsuccessfulSinceMs==Long.MIN_VALUE)unsuccessfulSinceMs=nowMs;
            if(mode==Mode.EXPAND_SPOT&&nowMs-unsuccessfulSinceMs>=EXPAND_AFTER_MS)expanded=true;
        }else if(newState==AF_INACTIVE){
            unsuccessfulSinceMs=Long.MIN_VALUE;
        }
    }
    public synchronized FocusStatus afStatus(long nowMs){
        if(lastStateAtMs==Long.MIN_VALUE||nowMs<lastStateAtMs
                ||nowMs-lastStateAtMs>AF_FRESH_MS)return FocusStatus.UNKNOWN;
        if(afState==AF_PASSIVE_FOCUSED||afState==AF_FOCUSED_LOCKED)
            return FocusStatus.HAL_FOCUSED;
        if(afState==AF_PASSIVE_UNFOCUSED||afState==AF_NOT_FOCUSED_LOCKED)
            return FocusStatus.HAL_UNFOCUSED;
        if(afState==AF_PASSIVE_SCAN||afState==AF_ACTIVE_SCAN)
            return FocusStatus.SCANNING;
        return FocusStatus.INACTIVE;
    }
    public synchronized boolean expanded(){return mode==Mode.EXPAND_SPOT&&expanded;}
    /**
     * Spatial search restriction. WIDE searches the whole view.
     * A deliberately tapped subject is carried by its existing tracker; this
     * predicate is for acquiring *new* subjects without stealing identity.
     */
    public synchronized boolean mayAcquire(float l,float t,float r,float b) {
        if(!(valid(l)&&valid(t)&&valid(r)&&valid(b))||r<=l||b<=t)return false;
        if(mode==Mode.WIDE)return true;
        Region region=area(anchorX,anchorY,0f,0f);
        // The detector's box overlaps the selected region. A pet's body may
        // be big while its eye lies outside a tiny Spot; tapping selects it.
        return region!=null&&region.intersects(l,t,r,b);
    }

    /** Returns the ACTUAL desired AF width/height in normalized sensor crop. */
    public synchronized Region area(float followX,float followY,
                                    float suggestedW,float suggestedH){
        float cx,cy,width,height;
        if(mode==Mode.WIDE){
            cx=valid(followX)?followX:anchorX;
            cy=valid(followY)?followY:anchorY;
            width=suggestedW>0?clamp(suggestedW,.055f,.24f):.10f;
            height=suggestedH>0?clamp(suggestedH,.055f,.24f):.10f;
        }else{
            cx=valid(followX)?followX:anchorX;
            cy=valid(followY)?followY:anchorY;
            if(mode==Mode.CUSTOM){width=w;height=h;}
            else if(mode==Mode.EXPAND_SPOT&&expanded){width=height=EXPANDED;}
            else{width=height=SPOT;}
        }
        if(!valid(cx)||!valid(cy))return null;
        // Restrict centre so the region fits entirely inside the image.
        cx=clamp(cx,width*.5f,1f-width*.5f);
        cy=clamp(cy,height*.5f,1f-height*.5f);
        return new Region(cx,cy,width,height);
    }
    public static Mode parseMode(String value){
        if(value==null)return Mode.WIDE;
        String key=value.trim().toUpperCase(Locale.ROOT);
        if(key.equals("EXPAND SPOT")||key.equals("EXPAND_SPOT")||key.equals("EXPANDED_SPOT"))
            return Mode.EXPAND_SPOT;
        try{return Mode.valueOf(key);}catch(IllegalArgumentException ignored){return Mode.WIDE;}
    }
    private static boolean valid(float value){
        return Float.isFinite(value)&&value>=0f&&value<=1f;
    }
    private static float clamp(float v,float low,float high){
        return Math.max(low,Math.min(high,v));
    }
}
