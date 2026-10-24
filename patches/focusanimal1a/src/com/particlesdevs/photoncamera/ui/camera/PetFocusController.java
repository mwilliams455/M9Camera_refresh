package com.particlesdevs.photoncamera.ui.camera;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.drawable.Drawable;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.view.PixelCopy;
import android.view.SurfaceView;
import android.view.View;
import com.particlesdevs.photoncamera.R;
import com.particlesdevs.photoncamera.api.CameraMode;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.control.subject.PetTargetPolicy;
import com.particlesdevs.photoncamera.control.tracking.TrackingGeometry;
import com.particlesdevs.photoncamera.m9.M9Config;
import com.particlesdevs.photoncamera.renderprofile.RenderProfile;
import com.particlesdevs.photoncamera.settings.PreferenceKeys;
import com.particlesdevs.photoncamera.settings.SettingsManager;
import com.particlesdevs.photoncamera.ui.camera.views.TrackingFocusView;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Opt-in CAT/DOG whole-body continuous AF.
 *
 * EfficientDet runs on a single CPU worker over bounded, screen-aligned
 * PixelCopy snapshots. The existing CaptureController.TrackingFocus owns AF
 * region submissions and preserves AE, AWB and the image renderers.
 *
 * Never sends AF_START on object motion; never asserts an optical focus lock.
 * Tracking identity is spatially gated because COCO TFLite inference does not
 * provide ML Kit style object tracking IDs.
 */
final class PetFocusController {
    static final String KEY="pref_focus_subject_pet";
    private static final String TAG="FOCUSANIMAL1A";
    private static final long CADENCE_MS=250;
    private static final long LOST_MS=850;
    private final CameraFragment fragment;
    private final SurfaceView source;
    private final TrackingFocusView overlay;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final PetTargetPolicy policy=new PetTargetPolicy();
    private final PetBadge badge;
    private boolean started,closed,inFlight,unsupported,manualOverride,badgeAttached;
    private long epoch,lastFrameNs=Long.MIN_VALUE,firstPreviewNs,lastAttemptMs,lastGoodMs,lastCandidatesMs;
    private CameraMode mode;
    private String camera;
    private boolean mono;
    private TrackingGeometry geometry;
    private CaptureController.TrackingFocus af;
    private Bitmap bitmap;
    private PetObjectDetector detector; // worker-thread only
    private List<PetTargetPolicy.Candidate> lastCandidates=Collections.emptyList();

    PetFocusController(CameraFragment fragment, SurfaceView source,TrackingFocusView overlay) {
        this.fragment=fragment;this.source=source;this.overlay=overlay;
        badge=new PetBadge(overlay);
        policy.beginSession(epoch);
    }
    private boolean enabled() {
        if(PhotonCamera.getSettings()==null||!M9Config.isM9Modern())return false;
        CameraMode m=PhotonCamera.getSettings().selectedMode;
        return (m==CameraMode.PHOTO||m==CameraMode.MOTION||m==CameraMode.NIGHT)
            && PhotonCamera.getSettingsManagerStatic().getBoolean(
                    SettingsManager.SCOPE_GLOBAL,KEY,false);
    }
    void start() {
        if(closed||started)return;
        started=true;firstPreviewNs=SystemClock.elapsedRealtimeNanos();main.post(tick);
    }
    void stop() {
        started=false;main.removeCallbacks(tick);clear();
    }
    void close() {
        if(closed)return;
        stop();closed=true;
        // Resource teardown is serialized *after* any executing inference.
        try {worker.execute(()->{
            if(detector!=null) {detector.close();detector=null;}
        });}catch(RuntimeException ignored){}
        worker.shutdown();
        if(!inFlight&&bitmap!=null) {bitmap.recycle();bitmap=null;}
    }
    void clear() {
        epoch++;policy.beginSession(epoch);
        unsupported=false;manualOverride=false;geometry=null;camera=null;mode=null;
        lastFrameNs=Long.MIN_VALUE;lastGoodMs=lastCandidatesMs=lastAttemptMs=0;
        lastCandidates=Collections.emptyList();
        releaseFocus();
    }
    /** Return true only when a detected cat/dog tap was handled. */
    boolean tap(float rawX,float rawY,boolean autofocus) {
        if(!started||closed||!enabled()||!autofocus||manualOverride)return false;
        TrackingGeometry g=TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
        if(g==null||g.w<=0||g.h<=0||!cameraGeometry(g)||!source.isAttachedToWindow())return false;
        if(geometry==null||!geometry.same(g)
                ||SystemClock.elapsedRealtime()-lastCandidatesMs>LOST_MS) {
            clear();bind(g);manualOverride=true;return false;
        }
        int[] origin=new int[2];source.getLocationOnScreen(origin);
        float u=(rawX-origin[0]-g.left)/g.w;
        float v=(rawY-origin[1]-g.top)/g.h;
        if(u<0||u>1||v<0||v>1)return false;
        if(policy.tapSelect(u,v,lastCandidates)) {
            // The existing focus handle belongs to the former target.
            releaseFocus();
            // Inference generated before the tap must not overwrite the pin.
            epoch++;policy.beginSession(epoch);
            policy.tapSelect(u,v,lastCandidates);
            lastFrameNs=Long.MIN_VALUE;
            return true;
        }
        clear();bind(g);manualOverride=true;
        return false; // ordinary tap-to-focus owns the new selection
    }
    private final Runnable tick=new Runnable(){
        @Override public void run() {
            if(!started||closed)return;
            try{step();}finally{
                if(started&&!closed)main.postDelayed(this,100);
            }
        }
    };
    private void step() {
        if(!enabled()) {if(geometry!=null||af!=null||manualOverride)clear();return;}
        long nowNs=SystemClock.elapsedRealtimeNanos();
        TrackingGeometry g=TrackingGeometry.current(nowNs);
        if(manualOverride) {
            if(g==null||geometry==null||!geometry.same(g)||!environment())clear();
            return;
        }
        if(g==null||g.published<firstPreviewNs||!cameraGeometry(g)
                ||g.w<=0||g.h<=0||!source.isAttachedToWindow()
                ||g.width!=source.getWidth()||g.height!=source.getHeight()) {
            if(geometry!=null)clear();
            return;
        }
        if(geometry==null||!geometry.same(g)||!environment()) {
            clear();bind(g);
        }
        if(af!=null&&!af.valid()) {clear();return;}
        long nowMs=SystemClock.elapsedRealtime();
        if(!inFlight&&!unsupported&&g.frameTime!=lastFrameNs
                &&nowMs-lastAttemptMs>=CADENCE_MS
                &&source.getHolder().getSurface().isValid()) {
            lastFrameNs=g.frameTime;lastAttemptMs=nowMs;sample(g);
        }
        if(af!=null&&lastGoodMs>0&&nowMs-lastGoodMs>LOST_MS)releaseFocus();
    }
    private void bind(TrackingGeometry g) {
        geometry=g;
        camera=PreferenceKeys.getCameraID();
        mode=PhotonCamera.getSettings().selectedMode;
        mono=RenderProfile.isMonochrom();
    }
    private boolean environment() {
        return Objects.equals(camera,PreferenceKeys.getCameraID())
                &&mode==PhotonCamera.getSettings().selectedMode
                &&mono==RenderProfile.isMonochrom();
    }
    private boolean cameraGeometry(TrackingGeometry g) {
        CaptureController c=fragment.getCaptureController();
        String key=RenderProfile.isMonochrom()?(c==null?null:c.monoCameraKey1A()):
                PhotonCamera.getSettings().mCameraID;
        return Objects.equals(g.camera,key)&&Objects.equals(g.mode,
                PhotonCamera.getSettings().selectedMode.name());
    }
    private boolean accepts(long token,TrackingGeometry g) {
        return started&&!closed&&enabled()&&!manualOverride&&token==epoch
                &&geometry!=null&&geometry.same(g)&&environment()
                &&cameraGeometry(g)&&source.isAttachedToWindow()
                &&g.same(TrackingGeometry.current(SystemClock.elapsedRealtimeNanos()));
    }
    private void sample(TrackingGeometry g) {
        final long token=epoch;
        final long requested=SystemClock.elapsedRealtimeNanos();
        int w=g.w>=g.h?640:Math.max(64,Math.round(640f*g.w/g.h));
        int h=g.h>=g.w?640:Math.max(64,Math.round(640f*g.h/g.w));
        inFlight=true;
        try {
            if(bitmap==null||bitmap.getWidth()!=w||bitmap.getHeight()!=h) {
                if(bitmap!=null)bitmap.recycle();
                bitmap=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
            }
            PixelCopy.request(source,new Rect(g.left,g.top,g.left+g.w,g.top+g.h),
                bitmap,status->{
                    if(!accepts(token,g)||status!=PixelCopy.SUCCESS){finish();return;}
                    try {
                        worker.execute(()->{
                            List<PetTargetPolicy.Candidate> results=Collections.emptyList();
                            boolean error=false;
                            try {
                                if(detector==null)detector=new PetObjectDetector(
                                        fragment.requireContext().getApplicationContext());
                                results=detector.detect(bitmap);
                            }catch(Exception|LinkageError exception) {
                                Log.w(TAG,"Offline pet detector unavailable",exception);
                                error=true;
                            }
                            final List<PetTargetPolicy.Candidate> output=results;
                            final boolean failed=error;
                            main.post(()->{
                                if(failed&&accepts(token,g)) {
                                    unsupported=true;releaseFocus();
                                } else if(!failed)received(token,g,requested,output);
                                finish();
                            });
                        });
                    }catch(RuntimeException schedulingFailure){finish();}
                },main);
        }catch(RuntimeException|OutOfMemoryError failure) {
            // Allocation failure disables only optional pet detection.
            unsupported=true;releaseFocus();finish();
        }
    }
    private void received(long token,TrackingGeometry g,long frameNs,
                          List<PetTargetPolicy.Candidate> candidates) {
        if(!accepts(token,g))return;
        long nowNs=SystemClock.elapsedRealtimeNanos();
        // Policy rejects late frames, wrong sessions, implausible boxes,
        // non-cat/dog classes and unconfirmed one-frame results.
        PetTargetPolicy.Target target=policy.update(token,frameNs,nowNs,candidates);
        lastCandidates=policy.validCandidates(candidates);
        lastCandidatesMs=SystemClock.elapsedRealtime();
        if(target==null) {
            if(af!=null&&lastGoodMs>0&&SystemClock.elapsedRealtime()-lastGoodMs>LOST_MS)
                releaseFocus();
            return;
        }
        if(af==null) {
            CaptureController controller=fragment.getCaptureController();
            if(controller==null)return;
            af=controller.newTrackingFocus();
            if(af==null||!af.valid()){
                unsupported=true;releaseFocus();return;
            }
        }
        try {
            af.update(g,target.x,target.y,accepted->main.post(()->{
                if(accepts(token,g)&&af!=null&&af.valid()) {
                    if(!accepted)releaseFocus();
                    else {
                        lastGoodMs=SystemClock.elapsedRealtime();
                        int[] src=new int[2],dst=new int[2];
                        source.getLocationInWindow(src);overlay.getLocationInWindow(dst);
                        float x=src[0]-dst[0]+g.left+target.x*g.w;
                        float y=src[1]-dst[1]+g.top+target.y*g.h;
                        float hw=target.halfWidth*g.w,hh=target.halfHeight*g.h;
                        overlay.show(x,y,hw,hh,false);
                        String type=target.species==PetTargetPolicy.Species.CAT?"Cat AF":"Dog AF";
                        overlay.setContentDescription(type);
                        if(!badgeAttached) {
                            overlay.getOverlay().add(badge);
                            badgeAttached=true;
                        }
                        badge.place(x,y,hw,hh,type);
                    }
                }
            }));
        }catch(RuntimeException failure){releaseFocus();}
    }
    private void releaseFocus() {
        if(af!=null)af.close();
        af=null;
        if(badgeAttached) {overlay.getOverlay().remove(badge);badgeAttached=false;}
        overlay.setVisibility(View.GONE);
    }
    private void finish() {
        inFlight=false;
        if(closed&&bitmap!=null){bitmap.recycle();bitmap=null;}
    }
    private static final class PetBadge extends Drawable {
        private final TrackingFocusView parent;
        private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        private float x,y,hw,hh;
        private String label="Pet AF";
        PetBadge(TrackingFocusView view){parent=view;}
        void place(float x,float y,float hw,float hh,String label) {
            this.x=x;this.y=y;this.hw=hw;this.hh=hh;this.label=label;
            setBounds(0,0,parent.getWidth(),parent.getHeight());invalidateSelf();
        }
        @Override public void draw(Canvas canvas) {
            float d=parent.getResources().getDisplayMetrics().density;
            String old=parent.getContext().getString(R.string.focus_tracking_active);
            paint.setTextSize(13*d);paint.setStyle(Paint.Style.FILL);
            float width=Math.max(paint.measureText(label),paint.measureText(old));
            float tx=Math.max(4*d,Math.min(parent.getWidth()-width-4*d,x-hw));
            float ty=Math.max(18*d,y-hh-6*d);
            paint.setColor(0xf8000000);
            canvas.drawRect(tx-3*d,ty-16*d,tx+width+3*d,ty+4*d,paint);
            paint.setColor(0xffffffff);
            canvas.drawText(label,tx,ty,paint);
        }
        @Override public void setAlpha(int alpha){}
        @Override public void setColorFilter(ColorFilter colorFilter){}
        @Override public int getOpacity(){return PixelFormat.TRANSLUCENT;}
    }
}
