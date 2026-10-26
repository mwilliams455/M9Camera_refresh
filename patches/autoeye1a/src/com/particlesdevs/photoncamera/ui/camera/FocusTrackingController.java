package com.particlesdevs.photoncamera.ui.camera;

import android.graphics.Bitmap;
import android.graphics.Rect;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.PixelCopy;
import android.view.SurfaceView;
import android.view.View;
import com.particlesdevs.photoncamera.R;
import com.particlesdevs.photoncamera.api.CameraMode;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.control.tracking.PatchTracker;
import com.particlesdevs.photoncamera.control.tracking.FocusMotionPredictor;
import com.particlesdevs.photoncamera.control.tracking.TrackingTogglePolicy;
import com.particlesdevs.photoncamera.settings.SettingsManager;
import com.particlesdevs.photoncamera.control.tracking.SubjectAnchorPolicy;
import com.particlesdevs.photoncamera.control.tracking.TrackingFrameDecision;
import com.particlesdevs.photoncamera.control.tracking.TrackingGeometry;
import com.particlesdevs.photoncamera.m9.M9Config;
import com.particlesdevs.photoncamera.ui.camera.views.TrackingFocusView;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.Collections;
import java.util.List;

/** Single-flight PixelCopy + worker. All ownership/UI state lives on the main thread. */
final class FocusTrackingController {
    static final String KEY = "pref_focus_tracking";
    private final CameraFragment fragment;
    private final SurfaceView source;
    private final TrackingFocusView overlay;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private boolean running, destroyed, busy, selected, acquiring, holding;
    private long holdSince;
    private long epoch, lastFrame, lastProgress, lastSuccess, freshSince;
    private String camera;
    private CameraMode mode;
    private boolean monochrom;
    private float tapX, tapY, x, y, hx, hy;
    private TrackingGeometry geometry;
    private CaptureController.TrackingFocus focus;
    private PatchTracker tracker;
    private Bitmap bitmap;
    private int[] pixels;
    private int[] detectionPixels;
    private final SubjectAnchorPolicy subjectAnchor = new SubjectAnchorPolicy();
    /** 3.08: opt-in bounded 2-D AF-area lead, never a lens depth estimate. */
    private final FocusMotionPredictor focusPredictor = new FocusMotionPredictor();
    // Optional COCO recognition is used solely as an identity anchor. The
    // baseline arbitrary textured-patch tracker remains the fallback.
    private TrackingSemanticDetector semanticDetector; // worker-thread owner
    private volatile boolean semanticUnavailable;
    private boolean warmRequested, semanticOwned, patchInitialized;
    private long lastSemanticRequestedMs = Long.MIN_VALUE;
    private long tapStartedMs;
    /** Identity checking applies only to a newly tapped opt-in target. */
    private boolean identityForTap;
    private boolean persistentIdentityEnabled(){
        SettingsManager manager=PhotonCamera.getSettingsManagerStatic();
        return manager!=null && recognitionEnabled() && manager.getBoolean(
                SettingsManager.SCOPE_GLOBAL,TrackingTogglePolicy.IDENTITY,false);
    }
    static final String HYBRID_KEY = "pref_focus_tracking_semantic";
    private static final long SEMANTIC_CADENCE_MS = 260;
    private boolean predictionEnabled() {
        SettingsManager manager=PhotonCamera.getSettingsManagerStatic();
        return manager!=null && enabled() && manager.getBoolean(
                SettingsManager.SCOPE_GLOBAL, TrackingTogglePolicy.PREDICTIVE, false);
    }
    /** Heal 3.07's previously accepted but inert child-only setting on return to camera. */
    private void reconcileTrackingSwitches() {
        SettingsManager manager=PhotonCamera.getSettingsManagerStatic();
        if(manager==null)return;
        boolean wantsIdentity=manager.getBoolean(SettingsManager.SCOPE_GLOBAL,
                TrackingTogglePolicy.IDENTITY,false);
        if(wantsIdentity && !manager.getBoolean(SettingsManager.SCOPE_GLOBAL,HYBRID_KEY,false))
            manager.set(SettingsManager.SCOPE_GLOBAL,HYBRID_KEY,true);
        boolean wantsTracking=wantsIdentity || manager.getBoolean(SettingsManager.SCOPE_GLOBAL,
                HYBRID_KEY, false)
                || manager.getBoolean(SettingsManager.SCOPE_GLOBAL,
                        TrackingTogglePolicy.PREDICTIVE, false);
        if(wantsTracking && !manager.getBoolean(SettingsManager.SCOPE_GLOBAL,KEY,false))
            manager.set(SettingsManager.SCOPE_GLOBAL,KEY,true);
    }
    private boolean recognitionEnabled() {
        return enabled() && PhotonCamera.getSettingsManagerStatic().getBoolean(
                com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL,
                HYBRID_KEY, false);
    }
    private static final long PATCH_TIMEOUT_MS = 850;

    private void warmSemantic() {
        if (warmRequested || destroyed || !recognitionEnabled()) return;
        Context context = PhotonCamera.getAppContext();
        if (context == null) context = source.getContext();
        if (context == null) { semanticUnavailable = true; return; }
        final Context appContext = context.getApplicationContext();
        warmRequested = true;
        try {
            worker.execute(() -> {
                if (semanticUnavailable || destroyed) return;
                try { semanticDetector = new TrackingSemanticDetector(appContext); }
                catch (RuntimeException | LinkageError | OutOfMemoryError unsupported) {
                    semanticUnavailable = true; // Normal patch fallback remains usable.
                }
            });
        } catch (java.util.concurrent.RejectedExecutionException done) {
            semanticUnavailable = true;
        }
    }

    FocusTrackingController(CameraFragment fragment, SurfaceView source, TrackingFocusView overlay) {
        this.fragment = fragment; this.source = source; this.overlay = overlay;
    }
    private boolean enabled() {
        CameraMode mode = PhotonCamera.getSettings().selectedMode;
        return M9Config.isM9Modern() && (mode == CameraMode.PHOTO || mode == CameraMode.NIGHT || mode == CameraMode.MOTION)
                && PhotonCamera.getSettingsManagerStatic().getBoolean(com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, KEY, false)
                && !PhotonCamera.getSettingsManagerStatic().getBoolean(
                        com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, PetFocusController.KEY, false);
    }
    /** True only for an explicit user-selected object, not a visible detector box. */
    boolean hasExplicitTrackingTarget() { return running && !destroyed && selected; }
    void start() { if (destroyed || running) return; running = true;
        reconcileTrackingSwitches();
        freshSince = SystemClock.elapsedRealtimeNanos(); warmSemantic(); main.post(tick); }
    void stop() { running = false; main.removeCallbacks(tick); clear(); }
    void close() {
        stop(); destroyed = true;
        try { worker.execute(() -> {
            if (semanticDetector != null) { semanticDetector.close(); semanticDetector = null; }
        }); } catch (java.util.concurrent.RejectedExecutionException ignored) { }
        worker.shutdown(); releaseBitmap();
    }
    void clear() {
        epoch++; focusPredictor.begin(epoch); selected = false; acquiring = false; holding = false; holdSince = 0;
        semanticOwned = false; patchInitialized = false;
        identityForTap = false;
        lastSemanticRequestedMs = Long.MIN_VALUE;
        subjectAnchor.begin(epoch, Float.NaN, Float.NaN, 0);
        if (focus != null) focus.close(); focus = null;
        overlay.setVisibility(View.GONE); geometry = null;
    }
    boolean tap(float rawX, float rawY, boolean autofocus) {
        if (!running || !enabled()) return false;
        TrackingGeometry g = TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
        if (g == null || g.published < freshSince || !cameraGeometry(g) || !source.isAttachedToWindow()) {
            fragment.showToast(fragment.getString(R.string.focus_tracking_preview_required)); return true;
        }
        int[] location = new int[2]; source.getLocationOnScreen(location);
        float u = (rawX - location[0] - g.left) / g.w, v = (rawY - location[1] - g.top) / g.h;
        if (u < 0 || v < 0 || u >= 1 || v >= 1) return true;
        if (selected && Math.abs(u - x) <= hx && Math.abs(v - y) <= hy) { clear(); return true; }
        clear();
        if (!autofocus) { fragment.showToast(fragment.getString(R.string.focus_tracking_auto_required)); return true; }
        focus = fragment.getCaptureController().newTrackingFocus();
        if (focus != null) focus.enableArbitraryCadence();
        if (focus == null || !focus.valid()) { clear(); fragment.showToast(fragment.getString(R.string.focus_tracking_unavailable)); return true; }
        camera = com.particlesdevs.photoncamera.settings.PreferenceKeys.getCameraID();
        mode = PhotonCamera.getSettings().selectedMode;
        monochrom = com.particlesdevs.photoncamera.renderprofile.RenderProfile.isMonochrom();
        geometry = g; tapX = u; tapY = v; tracker = new PatchTracker();
        selected = true; acquiring = true; holding = false; holdSince = 0;
        patchInitialized = false; semanticOwned = false;
        lastSemanticRequestedMs = Long.MIN_VALUE;
        tapStartedMs = SystemClock.elapsedRealtime();
        subjectAnchor.begin(epoch, u, v, tapStartedMs);
        identityForTap = persistentIdentityEnabled();
        subjectAnchor.useAppearance(identityForTap);
        focusPredictor.begin(epoch);
        warmSemantic();
        x = u; y = v; hx = hy = .06f;
        lastFrame = -1; lastSuccess = lastProgress = SystemClock.elapsedRealtime();
        return true;
    }
    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (!running || destroyed) return;
            if (recognitionEnabled()) warmSemantic();
            if (selected && identityForTap != persistentIdentityEnabled()) clear();
            if (geometry != null && (!enabled() || !environment())) clear();
            TrackingGeometry current = TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
            if (!selected && geometry != null && current != null && !geometry.same(current)) clear();
            if (selected) {
                TrackingGeometry g = TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
                if (g == null) lost();
                else if (!enabled() || focus == null || !focus.valid() || !geometry.same(g)
                        || !source.isAttachedToWindow() || source.getWidth() != geometry.width
                        || source.getHeight() != geometry.height) clear();
                else {
                    long now = SystemClock.elapsedRealtime();
                    if (g.frameTime != lastFrame) {
                        lastFrame = g.frameTime; lastProgress = now;
                        if (!busy) sample();
                    }
                    // Preview freshness remains the original strict 600 ms.
                    // An occluded subject freezes the last AF region; its
                    // extra window is time-bounded, never a valid focus claim.
                    if (selected && (now - lastProgress > 600
                            || (holding ? now - holdSince >
                                    (semanticOwned ? SubjectAnchorPolicy.MAX_HOLD_MS :
                                      recognitionEnabled() && acquiring ?
                                        SubjectAnchorPolicy.MAX_PENDING_MS : PATCH_TIMEOUT_MS)
                                    : now - lastSuccess > (semanticOwned ? 1500 : 600)))) lost();
                }
            }
            main.postDelayed(this, 100);
        }
    };
    private boolean cameraGeometry(TrackingGeometry g) {
        if (g == null) return false;
        CaptureController capture = fragment.getCaptureController();
        String key = com.particlesdevs.photoncamera.renderprofile.RenderProfile.isMonochrom()
                ? (capture == null ? null : capture.monoCameraKey1A()) : PhotonCamera.getSettings().mCameraID;
        return java.util.Objects.equals(g.camera, key) && g.mode.equals(PhotonCamera.getSettings().selectedMode.name());
    }
    private boolean environment() {
        return java.util.Objects.equals(camera, com.particlesdevs.photoncamera.settings.PreferenceKeys.getCameraID())
                && mode == PhotonCamera.getSettings().selectedMode
                && monochrom == com.particlesdevs.photoncamera.renderprofile.RenderProfile.isMonochrom();
    }
    private boolean accepts(long ticket, TrackingGeometry g) {
        return running && !destroyed && selected && ticket == epoch && focus != null && focus.valid()
                && enabled() && environment() && cameraGeometry(g) && g.same(TrackingGeometry.current(SystemClock.elapsedRealtimeNanos()));
    }
    private void sample() {
        if (!source.getHolder().getSurface().isValid()) { lost(); return; }
        final long ticket = epoch, requested = SystemClock.elapsedRealtime();
        final TrackingGeometry g = geometry;
        final PatchTracker target = tracker;
        final boolean hybrid = recognitionEnabled();
        final boolean identity = hybrid && identityForTap;
        final boolean first = hybrid ? !patchInitialized : acquiring;
        final float u = tapX, v = tapY;
        // 448-pixel detector input improves person/cat/dog acquisition. The
        // existing patch matcher still sees its original 256-pixel coordinate
        // domain, so its scale/search window and tested thresholds do not change.
        final int w = g.w >= g.h ? 256 : Math.max(48, Math.round(256f * g.w / g.h));
        final int h = g.h >= g.w ? 256 : Math.max(48, Math.round(256f * g.h / g.w));
        final int dw = hybrid ? (g.w >= g.h ? 448 : Math.max(48, Math.round(448f * g.w / g.h))) : w;
        final int dh = hybrid ? (g.h >= g.w ? 448 : Math.max(48, Math.round(448f * g.h / g.w))) : h;
        final boolean infer = hybrid && !semanticUnavailable && warmRequested
                && (lastSemanticRequestedMs == Long.MIN_VALUE
                    || requested - lastSemanticRequestedMs >= SEMANTIC_CADENCE_MS);
        if (infer) lastSemanticRequestedMs = requested;
        busy = true;
        try {
            if (bitmap == null || bitmap.getWidth() != dw || bitmap.getHeight() != dh) {
                if (bitmap != null) bitmap.recycle();
                bitmap = Bitmap.createBitmap(dw, dh, Bitmap.Config.ARGB_8888);
                detectionPixels = hybrid ? new int[dw * dh] : null;
                pixels = new int[w * h];
            }
            PixelCopy.request(source, new Rect(g.left, g.top, g.left + g.w, g.top + g.h), bitmap, status -> {
                if (!accepts(ticket, g)) { finish(); return; }
                if (status != PixelCopy.SUCCESS) { lost(); finish(); return; }
                // With hybrid OFF, preserve 3.06's original 256px PixelCopy
                // buffer and grayscale/patch matching unchanged.
                if (hybrid) bitmap.getPixels(detectionPixels, 0, dw, 0, 0, dw, dh);
                else bitmap.getPixels(pixels, 0, w, 0, 0, w, h);
                final int[] framePixels = detectionPixels;
                final int[] sample = pixels;
                if (hybrid) patchInitialized = true;
                worker.execute(() -> {
                    PatchTracker.Result patchResult = null;
                    SubjectAnchorPolicy.Decision anchor = null;
                    boolean detectorRan = false;
                    try {
                        if (infer && semanticDetector != null && !semanticUnavailable) {
                            try {
                                List<SubjectAnchorPolicy.Candidate> found =
                                        semanticDetector.detect(bitmap, framePixels,dw,dh,identity);
                                detectorRan = true;
                                anchor = subjectAnchor.observe(ticket, requested,
                                        SystemClock.elapsedRealtime(), found);
                            } catch (RuntimeException | LinkageError | OutOfMemoryError inferenceFailure) {
                                // The camera remains functional. Do not repeatedly run
                                // an inoperable optional model in the same session.
                                semanticUnavailable = true;
                            }
                        }
                        if (!subjectAnchor.owns(ticket)) {
                            if (hybrid) {
                                // 2x2 filtered downscale: protect texture matching
                                // against nearest-neighbour aliasing while reusing
                                // the pinned detector's PixelCopy bitmap.
                                for (int py=0;py<h;py++) {
                                    int sy=Math.min(dh-2,(py*dh)/h);
                                    for (int px=0;px<w;px++) {
                                        int sx=Math.min(dw-2,(px*dw)/w);
                                        int k=sy*dw+sx;
                                        int a=framePixels[k],b=framePixels[k+1];
                                        int c=framePixels[k+dw],d=framePixels[k+dw+1];
                                        int r=(((a>>16)&255)+((b>>16)&255)+((c>>16)&255)+((d>>16)&255)+2)>>2;
                                        int gr=(((a>>8)&255)+((b>>8)&255)+((c>>8)&255)+((d>>8)&255)+2)>>2;
                                        int bl=((a&255)+(b&255)+(c&255)+(d&255)+2)>>2;
                                        sample[py*w+px]=0xff000000|(r<<16)|(gr<<8)|bl;
                                    }
                                }
                            }
                            patchResult = first ? target.select(sample, w, h, u, v, requested)
                                    : target.update(sample, w, h, requested);
                        }
                    } catch (RuntimeException ignored) {
                        // Any malformed preview is treated as unsafe for focus.
                    }
                    final PatchTracker.Result patch = patchResult;
                    final SubjectAnchorPolicy.Decision recognized = anchor;
                    final boolean recognitionFrame = detectorRan;
                    main.post(() -> {
                        if (!accepts(ticket, g)) { finish(); return; }
                        if (recognized != null && recognized.state == SubjectAnchorPolicy.State.ACQUIRED) {
                            if (SystemClock.elapsedRealtime() - requested > 500) {
                                onHold(requested,recognized.x,recognized.y,
                                        recognized.halfWidth,recognized.halfHeight);
                                finish(); return;
                            }
                            semanticOwned = true;
                            submitAf(g, ticket, requested, recognized.x, recognized.y,
                                    recognized.halfWidth, recognized.halfHeight,
                                    "Tracking " + recognized.category.name().toLowerCase(java.util.Locale.ROOT));
                            return;
                        }
                        if (semanticOwned && hybrid) {
                            if (recognitionFrame && recognized != null
                                    && recognized.state == SubjectAnchorPolicy.State.RETIRED) {
                                lost(); finish(); return;
                            }
                            if (recognitionFrame && recognized != null
                                    && recognized.state == SubjectAnchorPolicy.State.HOLD) {
                                onHold(requested, recognized.x, recognized.y,
                                        recognized.halfWidth, recognized.halfHeight);
                                finish(); return;
                            }
                            // No new detector frame: neither move AF nor show
                            // misleading amber flicker while last position is fresh.
                            finish(); return;
                        }
                        TrackingFrameDecision.Action decision =
                                TrackingFrameDecision.classify(patch,
                                        SystemClock.elapsedRealtime() - requested);
                        if (decision == TrackingFrameDecision.Action.RETIRE) {
                            if (hybrid && !semanticUnavailable &&
                                    SystemClock.elapsedRealtime()-tapStartedMs<=SubjectAnchorPolicy.MAX_PENDING_MS &&
                                    (recognized==null || recognized.state==SubjectAnchorPolicy.State.WAITING)) {
                                onPending(); finish(); return;
                            }
                            lost(); finish(); return;
                        }
                        if (decision == TrackingFrameDecision.Action.HOLD) {
                            onHold(requested, patch.x, patch.y, patch.halfWidth, patch.halfHeight);
                            finish(); return;
                        }
                        submitAf(g,ticket,requested,patch.x,patch.y,
                                patch.halfWidth,patch.halfHeight,"Tracking patch");
                    });
                });
            }, main);
        } catch (RuntimeException unavailable) { lost(); finish(); }
    }
    private void onPending() {
        focusPredictor.hold(epoch); // uncertain ownership never carries velocity forward
        if (!holding) { holding = true; holdSince = SystemClock.elapsedRealtime(); }
        // This means recognition is in progress, NOT a proven occlusion.
        int[] a = new int[2], b = new int[2];
        source.getLocationInWindow(a); overlay.getLocationInWindow(b);
        overlay.showPending(a[0]-b[0]+geometry.left+x*geometry.w,
                a[1]-b[1]+geometry.top+y*geometry.h,hx*geometry.w,hy*geometry.h);
    }
    private void onHold(long requested, float cx,float cy,float halfW,float halfH) {
        focusPredictor.hold(epoch); // no new lens-region aim while occluded
        if (!holding) { holding = true; holdSince = SystemClock.elapsedRealtime(); }
        x = cx; y = cy; hx = halfW; hy = halfH;
        showHolding();
    }
    private void submitAf(TrackingGeometry g,long ticket,long requested,
                          float targetX,float targetY,float halfW,float halfH,String label) {
        // Always submit through the unchanged M9 3.05 Camera2 handle. AF-only;
        // no exposure, colour, AWB, AE, AF trigger or renderer modifications.
        // The display overlay stays on the measured subject. Only the small
        // Camera2 AF region may be aimed slightly ahead of its 2-D movement.
        // Never extrapolate stale, held or otherwise unconfirmed targets.
        float afX=targetX,afY=targetY;
        if(predictionEnabled()) {
            FocusMotionPredictor.Aim aim=focusPredictor.observe(epoch,requested,
                    SystemClock.elapsedRealtime(),targetX,targetY,
                    semanticOwned?FocusMotionPredictor.Source.SUBJECT:
                            FocusMotionPredictor.Source.PATCH);
            afX=aim.x;afY=aim.y;
        } else focusPredictor.hold(epoch);
        FocusControlPolicyRegion304Holder holder =
                new FocusControlPolicyRegion304Holder(afX,afY);
        focus.update(g,holder.x,holder.y,holder.width,holder.height,
                applied -> main.post(() -> {
            if (accepts(ticket,g)) {
                if (!applied) lost();
                else {
                    acquiring = false; holding = false; holdSince = 0;
                    lastSuccess = requested;
                    x = targetX; y = targetY; hx = halfW; hy = halfH;
                    show(false);
                    overlay.setContentDescription(label);
                }
            }
            finish();
        }));
    }
    private void finish() { busy = false; if (destroyed) releaseBitmap(); }
    private void releaseBitmap() {
        if (!busy && bitmap != null) { bitmap.recycle(); bitmap = null; pixels = null; detectionPixels = null; }
    }
    private void lost() {
        epoch++; focusPredictor.begin(epoch); selected = false; acquiring = false; holding = false; holdSince = 0;
        semanticOwned = false; patchInitialized = false;
        subjectAnchor.begin(epoch,Float.NaN,Float.NaN,0);
        if (focus != null) focus.close(); focus = null;
        show(true);
    }
    private void showHolding() {
        int[] a = new int[2], b = new int[2];
        source.getLocationInWindow(a); overlay.getLocationInWindow(b);
        overlay.showHolding(a[0] - b[0] + geometry.left + x * geometry.w,
                a[1] - b[1] + geometry.top + y * geometry.h,
                hx * geometry.w, hy * geometry.h);
    }
    private void show(boolean lost) {
        int[] a = new int[2], b = new int[2];
        source.getLocationInWindow(a); overlay.getLocationInWindow(b);
        overlay.show(a[0] - b[0] + geometry.left + x * geometry.w,
                a[1] - b[1] + geometry.top + y * geometry.h, hx * geometry.w, hy * geometry.h, lost);
    }
}
