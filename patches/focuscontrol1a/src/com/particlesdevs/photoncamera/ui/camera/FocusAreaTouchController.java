package com.particlesdevs.photoncamera.ui.camera;

import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.SurfaceView;
import android.view.View;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.control.subject.FocusControlPolicy;
import com.particlesdevs.photoncamera.control.tracking.TrackingGeometry;
import com.particlesdevs.photoncamera.renderprofile.RenderProfile;
import com.particlesdevs.photoncamera.settings.PreferenceKeys;
import com.particlesdevs.photoncamera.settings.SettingsManager;
import com.particlesdevs.photoncamera.ui.camera.views.TrackingFocusView;
import java.util.Objects;

/**
 * Nonsemantic spot/expand/custom tap AF and separate HAL AF feedback.
 * All UI state is on main; Camera2 mutations stay in TrackingFocus's handler.
 * Wide is the accepted 3.03 default, so it does not intercept plain tap AF.
 */
final class FocusAreaTouchController {
    private final CameraFragment fragment;
    private final SurfaceView source;
    private final TrackingFocusView overlay;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final FocusControlPolicy policy=new FocusControlPolicy();
    private CaptureController.TrackingFocus focus;
    private TrackingGeometry geometry;
    private View statusHost;
    private FocusAfStatusBadge badge;
    private boolean badgeAttached;
    private boolean running,closed;
    private long epoch;
    private float u=.5f,v=.5f;
    private boolean touchActive;
    private boolean lastExpanded;
    private FocusControlPolicy.Mode lastMode=FocusControlPolicy.Mode.WIDE;

    FocusAreaTouchController(CameraFragment fragment,SurfaceView source,TrackingFocusView overlay) {
        this.fragment=fragment;this.source=source;this.overlay=overlay;
        policy.beginSession(epoch);
    }
    void start(){
        if(running||closed)return;
        running=true;main.post(poll);
    }
    void stop() {
        running=false;main.removeCallbacks(poll);clear();detach();
    }
    void close(){if(closed)return;stop();closed=true;}
    void clear(){
        epoch++;policy.beginSession(epoch);
        touchActive=false;lastExpanded=false;geometry=null;
        releaseFocus();
    }
    /**
     * Called AFTER semantic subject taps and legacy patch tracking. A tap
     * outside detected subjects selects a fixed Spot/Expand/Custom AF region.
     */
    boolean tap(float rawX,float rawY,boolean auto){
        if(!running||closed||!auto||FocusControlSettings.mode()==FocusControlPolicy.Mode.WIDE)
            return false;
        TrackingGeometry g=TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
        CaptureController capture=fragment.getCaptureController();
        if(g==null||capture==null||g.w<=0||g.h<=0||!source.isAttachedToWindow())
            return false;
        if(!cameraGeometry(g))return false;
        CaptureController.TrackingFocus handle=capture.newTrackingFocus();
        if(handle==null||!handle.valid())return false; // AF-S/MF retain normal tap AF
        int[] loc=new int[2];source.getLocationOnScreen(loc);
        float x=(rawX-loc[0]-g.left)/g.w;
        float y=(rawY-loc[1]-g.top)/g.h;
        if(x<0f||x>1f||y<0f||y>1f) {handle.close();return false;}
        releaseFocus();
        focus=handle;geometry=g;epoch++;
        policy.beginSession(epoch);
        FocusControlSettings.configure(policy);
        if(!policy.tap(epoch,x,y)){releaseFocus();return false;}
        u=x;v=y;touchActive=true;
        submit(g);
        return true;
    }
    private void submit(TrackingGeometry g){
        if(!running||!touchActive||focus==null||!focus.valid()
                ||geometry==null||!geometry.same(g))return;
        final long ticket=epoch;
        FocusControlPolicy.Region desired=policy.area(u,v,0f,0f);
        if(desired==null)return;
        focus.update(g,desired.x,desired.y,desired.width,desired.height,
                ok->main.post(()->{
                    if(ticket!=epoch||!running||geometry==null||!geometry.same(g))return;
                    if(!ok){releaseFocus();return;}
                    int[] a=new int[2],b=new int[2];
                    source.getLocationInWindow(a);
                    overlay.getLocationInWindow(b);
                    float px=a[0]-b[0]+g.left+desired.x*g.w;
                    float py=a[1]-b[1]+g.top+desired.y*g.h;
                    overlay.show(px,py,.5f*desired.width*g.w,.5f*desired.height*g.h,false);
                    overlay.setContentDescription("Focus "+policy.mode().name());
                }));
    }
    private final Runnable poll=new Runnable(){
        @Override public void run(){
            if(!running||closed)return;
            try {step();}finally{if(running&&!closed)main.postDelayed(this,140);}
        }
    };
    private void step(){
        FocusControlPolicy.Mode mode=FocusControlSettings.mode();
        if(mode!=lastMode&&touchActive)clear();
        lastMode=mode;
        FocusControlSettings.configure(policy);
        long now=SystemClock.elapsedRealtime();
        CaptureController capture=fragment.getCaptureController();
        boolean subjectOwner=semanticEnabled();
        // Spot/Expand/Custom are active focus-area controls even BEFORE a
        // user tap: use the centre until another area is explicitly tapped.
        // Never compete for AF ownership with face/pet/legacy tracking.
        if(subjectOwner && touchActive){clear();}
        if(!subjectOwner && !touchActive && mode!=FocusControlPolicy.Mode.WIDE) {
            TrackingGeometry available=TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
            if(available!=null && cameraGeometry(available) && capture!=null) {
                CaptureController.TrackingFocus owner=capture.newTrackingFocus();
                if(owner!=null && owner.valid()) {
                    epoch++;policy.beginSession(epoch);
                    FocusControlSettings.configure(policy);
                    policy.tap(epoch,.5f,.5f);
                    touchActive=true;geometry=available;focus=owner;
                    u=v=.5f;submit(available);
                }else if(owner!=null)owner.close();
            }
        }
        CaptureController.FocusStateSnapshot state=capture==null?null:capture.focusStateSnapshot();
        if(state!=null && (!touchActive || focus!=null && focus.matchesFocusSample(state)))
            policy.observeAf(epoch,state.state,now);
        if(touchActive){
            TrackingGeometry g=TrackingGeometry.current(SystemClock.elapsedRealtimeNanos());
            if(mode==FocusControlPolicy.Mode.WIDE||g==null||geometry==null
                    ||!geometry.same(g)||!cameraGeometry(g)||focus==null||!focus.valid()){
                clear();
            }else if(policy.expanded()!=lastExpanded){
                lastExpanded=policy.expanded();
                submit(g);
            }
        }
        boolean tracking=semanticEnabled();
        boolean show=FocusControlSettings.showAfFeedback()
                &&(touchActive||tracking||mode!=FocusControlPolicy.Mode.WIDE);
        if(!show){detach();return;}
        attach();
        String name=mode==FocusControlPolicy.Mode.EXPAND_SPOT && policy.expanded()
                ?"Expand Spot (expanded)":mode.name().replace('_',' ');
        FocusControlPolicy.FocusStatus focusState=policy.afStatus(now);
        String af=focusState==FocusControlPolicy.FocusStatus.HAL_FOCUSED
                ?"AF reported focused":focusState==FocusControlPolicy.FocusStatus.SCANNING
                ?"AF scanning":focusState==FocusControlPolicy.FocusStatus.HAL_UNFOCUSED
                ?"AF not focused":focusState==FocusControlPolicy.FocusStatus.INACTIVE
                ?"AF idle":"AF unknown";
        String who=overlay.getVisibility()==View.VISIBLE
                &&overlay.getContentDescription()!=null?
                    overlay.getContentDescription().toString():"No subject";
        if(badge!=null)badge.update(name+" | "+who+" | "+af);
    }
    private boolean semanticEnabled(){
        if(PhotonCamera.getSettingsManagerStatic()==null)return false;
        return PhotonCamera.getSettingsManagerStatic().getBoolean(
                    SettingsManager.SCOPE_GLOBAL,PetFocusController.KEY,false)
                ||PhotonCamera.getSettingsManagerStatic().getBoolean(
                    SettingsManager.SCOPE_GLOBAL,HumanSubjectFocusController.KEY,false)
                ||PhotonCamera.getSettingsManagerStatic().getBoolean(
                    SettingsManager.SCOPE_GLOBAL,FocusTrackingController.KEY,false);
    }
    private boolean cameraGeometry(TrackingGeometry g){
        CaptureController capture=fragment.getCaptureController();
        String key=RenderProfile.isMonochrom()?
                (capture==null?null:capture.monoCameraKey1A()):
                PhotonCamera.getSettings().mCameraID;
        return Objects.equals(g.camera,key)
                &&Objects.equals(g.mode,PhotonCamera.getSettings().selectedMode.name());
    }
    private void attach(){
        if(badgeAttached||closed)return;
        View root=fragment.getView();
        if(root==null||!root.isAttachedToWindow())return;
        badge=new FocusAfStatusBadge(root);
        root.getOverlay().add(badge);
        statusHost=root;badgeAttached=true;
    }
    private void detach(){
        if(badgeAttached&&statusHost!=null&&badge!=null)
            statusHost.getOverlay().remove(badge);
        badgeAttached=false;badge=null;statusHost=null;
    }
    private void releaseFocus(){
        if(focus!=null){
            focus.close();focus=null;
            overlay.setVisibility(View.GONE);
        }
    }
}
