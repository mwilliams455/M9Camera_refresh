package com.particlesdevs.photoncamera.control.tracking;

/**
 * Bounded 2-D preview motion estimate used ONLY to lead the Camera2 AF region.
 * This is not depth prediction and never commands a lens-focus distance.
 * Results are session-scoped and valid only for accepted, fresh target positions.
 */
public final class FocusMotionPredictor {
    public enum Source { PATCH, SUBJECT }
    public static final long MAX_SAMPLE_AGE_MS = 480L;
    public static final long MIN_SAMPLE_GAP_MS = 45L;
    public static final long MAX_SAMPLE_GAP_MS = 650L;
    public static final long MAX_LEAD_MS = 140L;
    public static final float MAX_LEAD_FRACTION = .045f;
    public static final float MAX_ACCEPTED_STEP = .20f;
    public static final float MOVEMENT_DEADBAND = .006f;
    public static final float MAX_SPEED_PER_SECOND = 1.50f;

    public static final class Aim {
        public final float x,y;
        public final boolean predicted;
        public final long leadMs;
        private Aim(float x,float y,boolean predicted,long leadMs){
            this.x=x;this.y=y;this.predicted=predicted;this.leadMs=leadMs;
        }
    }

    private long epoch = Long.MIN_VALUE;
    private long lastFrameMs = Long.MIN_VALUE;
    private float lastX,lastY,velocityX,velocityY;
    private Source lastSource;

    /** Retire all previous samples and their velocity after a tap or session change. */
    public synchronized void begin(long token) {
        epoch=token;
        forgetMotion();
    }

    /** Suspend prediction across an uncertain match or occlusion; never extrapolate blindly. */
    public synchronized void hold(long token) {
        if(token==epoch)forgetMotion();
    }

    private void forgetMotion(){
        lastFrameMs=Long.MIN_VALUE;
        velocityX=velocityY=0f;
        lastSource=null;
    }

    /**
     * @param token camera/tracker selection epoch
     * @param frameMs monotonic preview sample time (before PixelCopy/inference)
     * @param nowMs monotonic submission time
     * @param x observed visual target centre in the upright 0..1 preview
     * @param y observed visual target centre in the upright 0..1 preview
     * @param source PATCH or SUBJECT; changes reset velocity for safety
     */
    public synchronized Aim observe(long token,long frameMs,long nowMs,
                                    float x,float y,Source source) {
        if(!finite(x)||!finite(y)||x<0f||x>1f||y<0f||y>1f)
            return new Aim(.5f,.5f,false,0);
        Aim observed=new Aim(x,y,false,0);
        if(token!=epoch||source==null||frameMs<0||nowMs<frameMs||
                nowMs-frameMs>MAX_SAMPLE_AGE_MS) {
            // An invalid / stale measurement never contributes momentum.
            if(token==epoch)forgetMotion();
            return observed;
        }
        if(lastFrameMs!=Long.MIN_VALUE && frameMs<=lastFrameMs)
            return observed; // duplicate / out-of-order frame must not update state
        if(lastFrameMs==Long.MIN_VALUE || lastSource!=source) {
            setAnchor(frameMs,x,y,source);
            return observed;
        }
        long dtMs=frameMs-lastFrameMs;
        float dx=x-lastX,dy=y-lastY;
        float displacement=(float)Math.hypot(dx,dy);
        if(dtMs<MIN_SAMPLE_GAP_MS || dtMs>MAX_SAMPLE_GAP_MS ||
                displacement>MAX_ACCEPTED_STEP) {
            setAnchor(frameMs,x,y,source);
            return observed;
        }
        // Low-amplitude preview jitter is not subject motion. Drain any old
        // velocity rather than keeping a predicted lead after the target stops.
        if(displacement<MOVEMENT_DEADBAND) {
            velocityX*=.28f;
            velocityY*=.28f;
            lastX=x;lastY=y;lastFrameMs=frameMs;
            if(Math.hypot(velocityX,velocityY)<.055f)velocityX=velocityY=0f;
            return observed;
        }
        float seconds=dtMs/1000f;
        float vx=dx/seconds,vy=dy/seconds;
        float speed=(float)Math.hypot(vx,vy);
        if(speed>MAX_SPEED_PER_SECOND){
            // An unreasonably rapid box movement may be a new visual target.
            // Accept its *position* but never predict its continuation.
            setAnchor(frameMs,x,y,source);
            return observed;
        }
        // Modest smoothing suppresses oscillation while retaining meaningful
        // motion response. Each coordinate remains bounded independently.
        velocityX=.65f*velocityX+.35f*vx;
        velocityY=.65f*velocityY+.35f*vy;
        lastX=x;lastY=y;lastFrameMs=frameMs;lastSource=source;
        if(Math.hypot(velocityX,velocityY)<.055f)return observed;
        long age=nowMs-frameMs;
        long horizon=Math.min(MAX_LEAD_MS,70L+age/3L);
        float leadX=clamp(velocityX*horizon/1000f,-MAX_LEAD_FRACTION,MAX_LEAD_FRACTION);
        float leadY=clamp(velocityY*horizon/1000f,-MAX_LEAD_FRACTION,MAX_LEAD_FRACTION);
        if(Math.hypot(leadX,leadY)<.002f)return observed;
        return new Aim(clamp(x+leadX,0f,1f),clamp(y+leadY,0f,1f),true,horizon);
    }

    private void setAnchor(long frameMs,float x,float y,Source source){
        lastFrameMs=frameMs;lastX=x;lastY=y;
        velocityX=velocityY=0f;lastSource=source;
    }
    private static boolean finite(float x){return Float.isFinite(x);}
    private static float clamp(float value,float min,float max){return Math.max(min,Math.min(max,value));}
}
