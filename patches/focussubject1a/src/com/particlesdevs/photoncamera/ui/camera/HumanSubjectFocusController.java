package com.particlesdevs.photoncamera.ui.camera;

import android.graphics.Bitmap;
import android.graphics.Rect;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.PixelCopy;
import android.view.SurfaceView;
import android.view.View;
import com.particlesdevs.photoncamera.api.CameraMode;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.control.subject.SubjectFocusPolicy;
import com.particlesdevs.photoncamera.control.tracking.TrackingGeometry;
import com.particlesdevs.photoncamera.m9.M9Config;
import com.particlesdevs.photoncamera.renderprofile.RenderProfile;
import com.particlesdevs.photoncamera.settings.PreferenceKeys;
import com.particlesdevs.photoncamera.settings.SettingsManager;
import com.particlesdevs.photoncamera.ui.camera.views.TrackingFocusView;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Opt-in still-camera Face/Eye AF. ML Kit runs asynchronously on the preview,
 * then the EXISTING Camera2 TrackingFocus submits only AF-region movements.
 * It never writes AE/AWB regions or issues AF_TRIGGER_START each frame.
 *
 * The camera/UI owner is the main looper. Epoch and TrackingGeometry checks
 * reject callback work after capture, pause, lens/zoom/profile/mode changes.
 */
final class HumanSubjectFocusController {
    static final String KEY = "pref_focus_subject_eye";
    private static final long CADENCE_MS = 200;
    private static final long FACE_LOST_MS = 750;
    private final CameraFragment fragment;
    private final SurfaceView source;
    private final TrackingFocusView overlay;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final SubjectFocusPolicy policy = new SubjectFocusPolicy();

    private boolean running, closed, inFlight, manualOverride, unsupported;
    private long epoch, freshSinceNs, lastFrameNs = Long.MIN_VALUE;
    private long lastAttemptMs, lastResultMs, lastFacesMs;
    private String camera;
    private CameraMode mode;
    private boolean monochrom;
    private TrackingGeometry geometry;
    private CaptureController.TrackingFocus focus;
    private HumanFaceLandmarkDetector detector;
    private Bitmap bitmap;
    private List<SubjectFocusPolicy.Face> latestFaces = Collections.emptyList();

    HumanSubjectFocusController(CameraFragment fragment, SurfaceView source,
                                TrackingFocusView overlay) {
        this.fragment=fragment;
        this.source=source;
        this.overlay=overlay;
        policy.beginSession(epoch);
    }

    private boolean enabled() {
        if (PhotonCamera.getSettings() == null || !M9Config.isM9Modern()) return false;
        CameraMode m=PhotonCamera.getSettings().selectedMode;
        return (m==CameraMode.PHOTO || m==CameraMode.NIGHT || m==CameraMode.MOTION)
                && PhotonCamera.getSettingsManagerStatic().getBoolean(
                        SettingsManager.SCOPE_GLOBAL, KEY, false);
    }

    // Invoked from the existing M9/Monochrom fragment lifecycle.
    void start() {
        if (closed || running) return;
        running=true;
        freshSinceNs=SystemClock.elapsedRealtimeNanos();
        main.post(tick);
    }
    void stop() {
        running=false;
        main.removeCallbacks(tick);
        clear();
    }
    void close() {
        if (closed) return;
        stop();
        closed=true;
        releaseIfIdle();
    }

    void clear() {
        epoch++;
        policy.beginSession(epoch);
        latestFaces=Collections.emptyList();
        lastFacesMs=0;
        lastResultMs=0;
        lastFrameNs=Long.MIN_VALUE;
        lastAttemptMs=0;
        manualOverride=false;
        unsupported=false;
        camera=null;
        mode=null;
        geometry=null;
        releaseFocus();
    }

    /** Consumes a tap on a recognised face. Other taps retain normal tap AF. */
    boolean tap(float rawX,float rawY,boolean autofocus) {
        if (!running || closed || !enabled() || !autofocus || manualOverride) return false;
        TrackingGeometry g=TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
        if (g==null || geometry==null || !geometry.same(g) || !cameraGeometry(g)
                || SystemClock.elapsedRealtime()-lastFacesMs > FACE_LOST_MS) return false;
        int[] location=new int[2];
        source.getLocationOnScreen(location);
        float u=(rawX-location[0]-g.left)/g.w;
        float v=(rawY-location[1]-g.top)/g.h;
        if (u<0f || u>1f || v<0f || v>1f) return false;
        if (policy.tapSelect(latestFaces,u,v)) {
            // A new user choice supersedes any in-flight inference/AF command.
            // Retire its handle before it can write an older subject region.
            epoch++;
            policy.beginSession(epoch);
            policy.tapSelect(latestFaces,u,v);
            releaseFocus();
            lastFrameNs=Long.MIN_VALUE;
            return true;
        }
        // A deliberate non-face tap has priority over automatic subject AF
        // until the next capture/session or preference restart.
        clear();
        bind(g);
        manualOverride=true;
        return false;
    }

    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (!running || closed) return;
            try { step(); }
            finally { if (running && !closed) main.postDelayed(this,100); }
        }
    };
    private void step() {
        if (!enabled()) {
            if (geometry!=null || focus!=null || manualOverride) clear();
            return;
        }
        if (manualOverride) {
            // Do not keep suppressing subject AF on a replacement camera.
            TrackingGeometry g=TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
            if (g==null || geometry==null || !geometry.same(g) ||
                    !cameraGeometry(g) || !environment()) clear();
            return;
        }
        long nowNs=SystemClock.elapsedRealtimeNanos();
        TrackingGeometry g=TrackingGeometry.current(nowNs);
        if (g==null || g.published<freshSinceNs || !cameraGeometry(g)
                || !source.isAttachedToWindow() || g.w<=0 || g.h<=0
                || source.getWidth()!=g.width || source.getHeight()!=g.height) {
            if (geometry!=null) clear();
            return;
        }
        if (geometry==null || !geometry.same(g) || !environment()) {
            clear();
            bind(g);
        }
        if (focus!=null && !focus.valid()) { clear(); return; }
        long nowMs=SystemClock.elapsedRealtime();
        if (!inFlight && !unsupported && g.frameTime!=lastFrameNs
                && nowMs-lastAttemptMs>=CADENCE_MS
                && source.getHolder().getSurface().isValid()) {
            lastFrameNs=g.frameTime;
            lastAttemptMs=nowMs;
            sample(g);
        }
        if (focus!=null && lastResultMs>0 && nowMs-lastResultMs>FACE_LOST_MS) {
            releaseFocus();
        }
    }

    private void bind(TrackingGeometry g) {
        geometry=g;
        camera=PreferenceKeys.getCameraID();
        mode=PhotonCamera.getSettings().selectedMode;
        monochrom=RenderProfile.isMonochrom();
    }
    private boolean environment() {
        return Objects.equals(camera,PreferenceKeys.getCameraID())
                && mode==PhotonCamera.getSettings().selectedMode
                && monochrom==RenderProfile.isMonochrom();
    }
    private boolean cameraGeometry(TrackingGeometry g) {
        CaptureController c=fragment.getCaptureController();
        String key=RenderProfile.isMonochrom()
                ? (c==null ? null : c.monoCameraKey1A())
                : PhotonCamera.getSettings().mCameraID;
        return Objects.equals(g.camera,key) &&
                g.mode.equals(PhotonCamera.getSettings().selectedMode.name());
    }
    private boolean accepts(long ticket,TrackingGeometry g) {
        return running && !closed && enabled() && !manualOverride
                && ticket==epoch && geometry!=null && geometry.same(g)
                && environment() && cameraGeometry(g) && source.isAttachedToWindow()
                && g.same(TrackingGeometry.current(SystemClock.elapsedRealtimeNanos()));
    }

    private void sample(TrackingGeometry g) {
        final long ticket=epoch;
        final long startedNs=SystemClock.elapsedRealtimeNanos();
        int w,h;
        if (g.w>=g.h) {w=720; h=Math.max(1,Math.round(720f*g.h/g.w));}
        else {h=720;w=Math.max(1,Math.round(720f*g.w/g.h));}
        inFlight=true;
        try {
            if (bitmap==null || bitmap.getWidth()!=w || bitmap.getHeight()!=h) {
                // The previous ML task has finished because inFlight is single-owner.
                if (bitmap!=null) bitmap.recycle();
                bitmap=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
            }
            if (detector==null) detector=new HumanFaceLandmarkDetector();
            PixelCopy.request(source,new Rect(g.left,g.top,g.left+g.w,g.top+g.h),
                    bitmap,status -> {
                if (!accepts(ticket,g)) {finish();return;}
                if (status!=PixelCopy.SUCCESS) {finish();return;}
                detector.process(bitmap,
                        faces -> main.post(() -> received(ticket,g,startedNs,faces)),
                        failure -> main.post(() -> {
                            if (accepts(ticket,g)) releaseFocus();
                            finish();
                        }));
            },main);
        } catch (RuntimeException error) {
            releaseFocus();
            finish();
        }
    }
    private void received(long ticket,TrackingGeometry g,long startedNs,
                          List<SubjectFocusPolicy.Face> faces) {
        if (!accepts(ticket,g)) {finish();return;}
        long nowNs=SystemClock.elapsedRealtimeNanos();
        latestFaces=Collections.unmodifiableList(new ArrayList<>(faces));
        lastFacesMs=SystemClock.elapsedRealtime();
        SubjectFocusPolicy.Target target=policy.update(epoch,startedNs,nowNs,
                latestFaces,SubjectFocusPolicy.Kind.HUMAN_EYE);
        if (target==null) {
            if (lastResultMs>0 && SystemClock.elapsedRealtime()-lastResultMs>FACE_LOST_MS)
                releaseFocus();
            finish();
            return;
        }
        if (focus==null) {
            CaptureController c=fragment.getCaptureController();
            if (c==null) {finish();return;}
            focus=c.newTrackingFocus();
            if (focus==null || !focus.valid()) {
                unsupported=true;
                releaseFocus();
                finish();
                return;
            }
        }
        try {
            focus.update(g,target.x,target.y,applied -> main.post(() -> {
                if (accepts(ticket,g)) {
                    if (!applied) releaseFocus();
                    else {
                        lastResultMs=SystemClock.elapsedRealtime();
                        int[] a=new int[2],b=new int[2];
                        source.getLocationInWindow(a);
                        overlay.getLocationInWindow(b);
                        overlay.show(a[0]-b[0]+g.left+target.x*g.w,
                                a[1]-b[1]+g.top+target.y*g.h,
                                .5f*target.regionWidth*g.w,
                                .5f*target.regionHeight*g.h,false);
                    }
                }
                finish();
            }));
        } catch (RuntimeException error) {
            releaseFocus();
            finish();
        }
    }
    private void releaseFocus() {
        if (focus!=null) focus.close();
        focus=null;
        overlay.setVisibility(View.GONE);
    }
    private void finish() {
        inFlight=false;
        releaseIfIdle();
    }
    private void releaseIfIdle() {
        if (closed && !inFlight) {
            if (bitmap!=null) {bitmap.recycle();bitmap=null;}
            if (detector!=null) {detector.close();detector=null;}
        }
    }
}
