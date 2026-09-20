import android.hardware.camera2.*;
import com.particlesdevs.photoncamera.m9.preview.M9FocusContinuity2B;
public class FocusTest {
    static int checks;
    static void check(boolean condition,String label){checks++;if(!condition)throw new AssertionError(label);}
    static Probe probe(int mode){Probe p=new Probe();p.mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE,mode);return p;}
    static int trigger(CaptureRequest r){return r.get(CaptureRequest.CONTROL_AF_TRIGGER);}
    static CaptureResult result(int state){CaptureResult r=new CaptureResult();r.values.put(CaptureResult.CONTROL_AF_STATE,state);return r;}
    public static void main(String[] args)throws Exception {
        for(int mode=0;mode<=5;mode++) {
            Probe p=probe(mode);Object regions=new Object();p.mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AF_REGIONS,regions);
            p.mPreviewRequestBuilder.set(CaptureRequest.LENS_FOCUS_DISTANCE,0f);
            p.mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER,1);
            CaptureRequest.Builder still=new CaptureRequest.Builder();
            M9FocusContinuity2B.prepareStill(p.mPreviewRequestBuilder,still);
            check(still.get(CaptureRequest.CONTROL_AF_MODE)==mode,"still retains mode "+mode);
            check(still.get(CaptureRequest.CONTROL_AF_TRIGGER)==0,"still never cancels or restarts lock");
            check(still.get(CaptureRequest.CONTROL_AF_REGIONS)==regions,"metering region retained");
            check(mode==0?still.get(CaptureRequest.LENS_FOCUS_DISTANCE)==0f:still.get(CaptureRequest.LENS_FOCUS_DISTANCE)==null,"manual infinity only");
            p.lockFocus();
            boolean active=mode>=1&&mode<=4;
            check(p.stillCalls==(active?0:1),"manual/fixed bypass AF wait");
            if(active) {
                check(p.mCaptureSession.captures.size()==1,"one START request");
                check(trigger(p.mCaptureSession.captures.get(0))==1,"START on one-shot");
                check(trigger(p.mCaptureSession.repeats.get(0))==0,"repeat is IDLE");
                check(p.mState==Probe.STATE_WAITING_LOCK,"wait for AF result");
            }
            p.unlockFocusM9Continuous1T();
            int count=p.mCaptureSession.captures.size();
            boolean continuous=mode==3||mode==4;
            check(count==(active?1:0)+(continuous?1:0),"only continuous AF receives release CANCEL");
            if(continuous)check(trigger(p.mCaptureSession.captures.get(count-1))==2,"continuous CANCEL once");
            check(trigger(p.mCaptureSession.repeats.get(p.mCaptureSession.repeats.size()-1))==0,"resume IDLE");
            check(p.mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AF_MODE)==mode,"resume mode retained");
            check(p.mPreviewRequestBuilder.get(CaptureRequest.LENS_FOCUS_DISTANCE)==0f,"manual setting retained");
        }
        Probe fixed=probe(4);fixed.mCameraCharacteristics.minimum=0f;fixed.lockFocus();
        check(fixed.stillCalls==1&&fixed.mCaptureSession.captures.isEmpty(),"fixed lens with advertised AF mode");
        Probe auto=probe(1);
        for(int i=0;i<50;i++)auto.primeM9AutoFocus2B(result(0));
        check(auto.mCaptureSession.captures.size()==1,"stale INACTIVE results cannot retrigger AUTO");
        auto.primeM9AutoFocus2B(result(3));auto.primeM9AutoFocus2B(result(4));auto.unlockFocusM9Continuous1T();
        for(int i=0;i<50;i++)auto.primeM9AutoFocus2B(result(4));
        check(auto.mCaptureSession.captures.size()==1,"AUTO focus retained after capture");
        auto.lockFocus();check(auto.mCaptureSession.captures.size()==2,"next shutter can focus again");
        Probe tap=probe(1);tap.mTouchFocus.isTouchFocus=true;tap.primeM9AutoFocus2B(result(0));
        check(tap.mCaptureSession.captures.isEmpty(),"touch sequence owns AF trigger");
        Probe manual=probe(0);manual.primeM9AutoFocus2B(result(0));
        check(manual.mCaptureSession.captures.isEmpty(),"manual is never AUTO primed");
        Probe offThenAuto=probe(0);offThenAuto.m9AutoAfPrimed2B=true;offThenAuto.primeM9AutoFocus2B(result(0));
        offThenAuto.mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE,1);offThenAuto.primeM9AutoFocus2B(result(0));
        check(offThenAuto.mCaptureSession.captures.size()==1,"entering AUTO primes once");
        Probe failed=probe(4);failed.mCaptureSession.failNext=true;failed.lockFocus();
        check(failed.mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AF_TRIGGER)==0,"failed START still clears builder");
        check(failed.mState==Probe.STATE_PREVIEW,"failed lock exits waiting state");
        failed.mCaptureSession.failNext=true;failed.unlockFocusM9Continuous1T();
        check(failed.mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AF_TRIGGER)==0,"failed CANCEL clears builder");
        check(!M9FocusContinuity2B.canTrigger(null,null),"unknown AF mode not triggered");
        System.out.println("M9LIVEGL2B AF PASS: "+checks+" assertions; production still/lock/resume/prime methods, recording Camera2 stub; hardware focus not verified");
    }
}
