import com.particlesdevs.photoncamera.m9.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
import com.particlesdevs.photoncamera.processing.parameters.IsoExpoSelector;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.circularbarlib.control.ManualParamModel;
import android.hardware.camera2.*;
import android.util.*;
import org.json.*;
import java.nio.*;

public class ExposurePlanTest {
    static int n;
    static void check(boolean x,String why){n++;if(!x)throw new AssertionError(why);}
    static void near(double x,double y,double eps,String why){check(Math.abs(x-y)<=eps,why+": "+x+" != "+y);}
    static Stats[] ramp(int... medians) {
        Stats[] s=new Stats[7];for(int i=0;i<7;i++)s[i]=new Stats(medians[i],medians[i]<32?.8:.4,.1,.05);return s;
    }
    static void publish(String camera,String mode,long time,double energy,Stats[] stats) {
        M9AutoExposure2D.publish(new Sample(camera,mode,time,time,time,energy,stats));
    }
    static Decision decide(String camera,long now,double energy,double ev,long shutter,int iso,double mfm) {
        return M9AutoExposure2D.decide(camera,"PHOTO",now,energy,ev,shutter,iso,mfm);
    }
    public static void main(String[] args) throws Exception {
        Stats[] dark=ramp(12,19,28,39,51,61,72);
        check(M9AutoExposure2D.select(dark)==5,"choose smallest bracket reaching modest shadow target");
        check(M9AutoExposure2D.select(ramp(0,0,0,0,0,0,0))==0,"black with no recovered detail gets no blind boost");
        check(M9AutoExposure2D.select(ramp(70,80,90,100,110,120,130))==0,"healthy scene unchanged");
        check(M9AutoExposure2D.select(ramp(20,21,22,23,24,25,26))==6,"extreme darkness can reach hard +1.5 EV cap");
        Stats[] clipping=dark.clone();clipping[3]=new Stats(39,.4,.11,.07);
        check(M9AutoExposure2D.select(clipping)==2,"new channel clipping limits lift before +0.75 EV");
        clipping=dark.clone();clipping[1]=new Stats(19,.8,.15,.05);
        check(M9AutoExposure2D.select(clipping)==0,"broad brightening budget stops lift");
        clipping=dark.clone();clipping[1]=new Stats(90,.2,.1,.05);
        check(M9AutoExposure2D.select(clipping)==0,"reject overshoot");
        clipping=dark.clone();clipping[0]=new Stats(12,.2,.1,.05);
        check(M9AutoExposure2D.select(clipping)==0,"one dark object is insufficient");
        clipping=dark.clone();clipping[4]=new Stats(51,Double.NaN,.1,.05);
        check(M9AutoExposure2D.select(clipping)==0,"invalid metrics rejected");
        // Actual packed atlas measurement: each viewport carries a distinct colour.
        ByteBuffer atlas=ByteBuffer.allocate(32*24*7*4);
        for(int y=0;y<24;y++)for(int i=0;i<7;i++)for(int x=0;x<32;x++) {
            int v=10+i*10;atlas.put((byte)v).put((byte)v).put((byte)v).put((byte)255);
        }
        Stats[] measured=M9AutoExposure2D.measure(atlas);
        for(int i=0;i<7;i++){check(measured[i].median==10+i*10,"atlas viewport layout");near(measured[i].clipped,0,0,"unclipped atlas");}
        M9AutoExposure2D.reset();long t=1000000000L;
        for(int i=0;i<6;i++) {
            publish("0","PHOTO",t,1e9,dark);Decision d=decide("0",t,1e9,0,0,0,0);
            near(d.appliedEv,Math.min((i+1)*.25,1.25),1e-12,"rise once per new meter sample");
            for(int callback=0;callback<20;callback++)near(decide("0",t+callback,1e9,0,0,0,0).appliedEv,d.appliedEv,0,"callback rate does not amplify auto");
            t+=250000000;
        }
        double held=decide("0",t,1e9,.25,0,0,.5).appliedEv;
        near(held,1.25,0,"manual EV holds shown baseline even when MFM changes");
        publish("0","PHOTO",t,1e9,ramp(90,100,110,120,130,140,150));
        near(decide("0",t,1e9,-1,0,0,-.5).appliedEv,held,0,"negative EV not fought by new auto metering");
        near(decide("0",t,1e9,0,0,0,0).appliedEv,0,0,"return Auto releases lift for bright scene");
        publish("0","PHOTO",t,1e9,dark);
        near(decide("0",t,1e9,0,1000000,0,.5).appliedEv,0,0,"manual shutter disables auto placement");
        near(decide("0",t,1e9,0,0,200,.5).appliedEv,0,0,"manual ISO disables auto placement");
        near(decide("1",t,1e9,0,0,0,0).appliedEv,0,0,"no cross-camera samples");
        near(decide("0",t+1300000000L,1e9,0,0,0,.3).appliedEv,.3,1e-12,"stale sample falls back to existing meter");
        near(decide("0",t,2e9,0,0,0,0).appliedEv,0,0,"changed reference energy rejects old sample");
        M9AutoExposure2D.publish(new Sample("0","PHOTO",t,t,t-200000000,1e9,dark));
        near(decide("0",t,1e9,0,0,0,0).appliedEv,0,0,"mismatched texture/result rejected");
        M9AutoExposure2D.reset();Stats[] boundary=ramp(39,43,49,55,61,67,73);
        boundary[0]=new Stats(39,.8,.1,.05);publish("0","PHOTO",t,1e9,boundary);
        near(decide("0",t,1e9,0,0,0,0).appliedEv,0,0,"soft activation avoids threshold flicker");
        // Real allocator integration: new lift is one plan for preview and RAW.
        M9AutoExposure2D.reset();CaptureController cc=PhotonCamera.getCaptureController();
        CameraCharacteristics c=CaptureController.mCameraCharacteristics;
        c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(50,6400));
        c.set(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE,new Range<Long>(100000L,1000000000L));
        c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,1600);
        c.set(CameraCharacteristics.CONTROL_AE_COMPENSATION_STEP,new Rational(1,3));
        CaptureResult obs=new CaptureResult();obs.set(CaptureResult.SENSOR_SENSITIVITY,100);
        obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,10000000L);obs.set(CaptureResult.SENSOR_TIMESTAMP,123456L);
        obs.set(CaptureResult.CONTROL_AE_MODE,1);obs.set(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION,0);
        cc.mPreviewIso=100;cc.mPreviewExposureTime=10000000L;CaptureController.mPreviewCaptureResult=obs;
        ManualParamModel model=new ManualParamModel();model.addObserver(cc.getParamController());model.reset();
        M9ExposurePlan1A base=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
        for(int i=0;i<6;i++) {
            // Fake clock stays at 1s; distinct earlier probe timestamps are all fresh.
            publish("0","PHOTO",500000000L+i*50000000L,1e9,dark);
            M9ExposurePlan1A p=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
            double intent=p.previewScale();
            near(Math.log(intent)/Math.log(2),p.autoEv,.025,"allocator retains requested Auto EV within integer ISO rounding");
            near(p.renderIntentScale(p.iso,p.exposureNs),intent,1e-6,"still renderer receives same Auto lift");
            double neutralMedian=.035,target=.107*8192/10000;
            double g0=M9ExposurePlan1A.boundedGain(M9ExposurePlan1A.neutralBaseGain(neutralMedian,1,target));
            double g1=M9ExposurePlan1A.boundedGain(M9ExposurePlan1A.neutralBaseGain(neutralMedian*intent,intent,target));
            near(g0,g1,1e-12,"TC20 cannot normalize away the automatic lift");
            check(M9ExposurePlanDiagnostics1A.toJson(p).getJSONObject("renderedAutoPlacement2D").getBoolean("sampleValid"),"captured decision telemetry");
            check(p.withShutterPreviewSnapshot1W("{}").getAutoPlacementSnapshot2D().equals(p.getAutoPlacementSnapshot2D()),"shutter snapshot preserves placement evidence");
        }
        double auto=IsoExpoSelector.planM9LiveExposure1A(cc,obs).autoEv;
        for(int steps:new int[]{-3,-1,1,3}) {
            model.setCurrentEvValue(steps);M9ExposurePlan1A p=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
            near(p.autoEv,auto,1e-12,"EV handover keeps baseline");
            near(Math.log(p.previewScale())/Math.log(2),auto+steps/3.,.025,"manual EV changes preview and capture energy together");
        }
        check(base.autoEv==0,"unmodified earlier plan remains immutable");
        System.out.println("M9LIVEGL2D Auto PASS: "+n+" assertions; actual allocator, bounded placement, manual ownership and neutral TC20 reference");
    }
}
