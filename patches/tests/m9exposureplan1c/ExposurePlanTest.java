import android.hardware.camera2.*;
import android.util.*;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.api.CameraMode;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.circularbarlib.control.ManualParamModel;
import com.particlesdevs.photoncamera.m9.*;
import com.particlesdevs.photoncamera.processing.parameters.IsoExpoSelector;
import org.json.*;
import java.nio.file.*;

public class ExposurePlanTest {
    static int checks;
    static void check(boolean ok,String msg){checks++;if(!ok)throw new AssertionError(msg);}
    static void near(double a,double b,double tol,String msg){check(Double.isFinite(a)&&Math.abs(a-b)<=tol,msg+" actual="+a+" expected="+b);}
    static double energy(M9ExposurePlan1A p){return M9ExposurePlan1A.energy(p.iso,p.exposureNs);}
    public static void main(String[] args)throws Exception {
        CaptureController cc=PhotonCamera.getCaptureController();
        CameraCharacteristics c=CaptureController.mCameraCharacteristics;
        c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(50,6400));
        c.set(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE,new Range<Long>(1000L,1000000000L));
        c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,1600);
        c.set(CameraCharacteristics.CONTROL_AE_COMPENSATION_STEP,new Rational(1,3));
        CaptureResult obs=new CaptureResult();obs.set(CaptureResult.SENSOR_SENSITIVITY,50);
        obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,609503L);obs.set(CaptureResult.SENSOR_TIMESTAMP,123456L);
        obs.set(CaptureResult.CONTROL_AE_MODE,1);obs.set(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION,0);
        CaptureController.mPreviewCaptureResult=obs;cc.mPreviewIso=50;cc.mPreviewExposureTime=609503L;
        ManualParamModel model=new ManualParamModel();model.addObserver(cc.getParamController());model.reset();
        // Missing scene stats gives a neutral auto decision, isolating user-EV transport.
        M9SubjectMotionAnalyzer.scene=new JSONObject();
        PhotonCamera.getSettings().selectedMode=CameraMode.PHOTO;
        EvDialProbe dial=new EvDialProbe(model,1f/3f);
        dial.onSelectedKnobItemChanged(new EvDialProbe.KnobItemInfo(-1));
        M9ExposurePlan1A negative=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
        near(negative.userEv,-.9999999701976785,1e-12,"actual float dial conversion reproduced");
        near(negative.previewScale(),.5,2e-6,"device -1 EV must halve exposure at minimum ISO");
        JSONArray fixtures=new JSONObject(Files.readString(Path.of(System.getenv("M9_EXPOSURE_FIXTURE1C")))).getJSONArray("cases");
        for(int i=0;i<fixtures.length();i++) {
            JSONObject f=fixtures.getJSONObject(i);
            obs.set(CaptureResult.SENSOR_SENSITIVITY,f.getInt("observedIso"));
            obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,f.getLong("observedExposureNs"));
            dial.onSelectedKnobItemChanged(new EvDialProbe.KnobItemInfo(f.getDouble("shownEv")));
            M9ExposurePlan1A p=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
            near(p.userEv,f.getDouble("recordedUserEv"),1e-12,"fixture user EV");
            near(p.previewScale(),Math.pow(2,p.userEv),2e-6,"fixture exposure factor");
            near(p.renderIntentScale(p.iso,p.exposureNs),p.previewScale(),1e-12,"same intent reaches renderer");
            check(p.iso==50,"bright fixture retains base ISO");
            System.out.println("FIXTURE "+f.getString("capture")+" old="+f.getDouble("oldScale")+" new="+p.previewScale()+" ISO="+p.iso+" exposureNs="+p.exposureNs);
        }
        // Base-ISO boundary missed by older tests, which started above base ISO.
        for(CameraMode mode:new CameraMode[]{CameraMode.PHOTO,CameraMode.MOTION}) {
            PhotonCamera.getSettings().selectedMode=mode;
            for(int floor:new int[]{50,64,100,160}) {
                c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(floor,6400));
                c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,1600);
                for(int denominator:new int[]{3,6}) {
                    c.set(CameraCharacteristics.CONTROL_AE_COMPENSATION_STEP,new Rational(1,denominator));
                    dial=new EvDialProbe(model,1f/denominator);
                    for(int iso:new int[]{floor,floor*2,floor*8}) {
                        obs.set(CaptureResult.SENSOR_SENSITIVITY,iso);
                        obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,609503L);
                        double previous=0;
                        for(double shown:new double[]{-3,-2,-1.25,-1,-.75,-.5,-.25,0,.25,.5,1,2,3}) {
                            dial.onSelectedKnobItemChanged(new EvDialProbe.KnobItemInfo(shown));
                            M9ExposurePlan1A p=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
                            near(p.userEv,shown,1e-6,"dial maps visible EV");
                            // Above the shutter cap, physical integer ISO quantization
                            // retains the existing allocator's 0.025EV tolerance. The
                            // base-ISO device fixtures above remain strict to nanoseconds.
                            near(Math.log(p.previewScale())/Math.log(2),p.userEv,.025,
                                    "EV preserved across ISO floors and modes "+mode+" base="+floor+" ISO="+iso+" EV="+shown);
                            check(energy(p)>previous,"strictly increasing EV bracket");previous=energy(p);
                            check(p.iso>=floor&&p.iso<=6400&&p.exposureNs>=1000&&p.exposureNs<=1000000000,"hardware bounds");
                            if(shown==0)check(p.referenceIso==p.iso&&p.referenceExposureNs==p.exposureNs,"zero intent equals reference");
                        }
                    }
                }
            }
        }
        // At a true minimum shutter/ISO boundary, clamp to the closest feasible energy.
        c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(50,6400));
        c.set(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE,new Range<Long>(400000L,1000000000L));
        c.set(CameraCharacteristics.CONTROL_AE_COMPENSATION_STEP,new Rational(1,3));dial=new EvDialProbe(model,1f/3f);
        obs.set(CaptureResult.SENSOR_SENSITIVITY,50);obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,609503L);
        dial.onSelectedKnobItemChanged(new EvDialProbe.KnobItemInfo(-1));
        M9ExposurePlan1A limited=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
        check(limited.iso==50&&limited.exposureNs==400000,"minimum shutter gives nearest attainable exposure, not neutral rollback");
        // No unexpected overflow or cap violation when a positive offset cannot be delivered.
        obs.set(CaptureResult.SENSOR_SENSITIVITY,6400);obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,1000000000L);
        dial.onSelectedKnobItemChanged(new EvDialProbe.KnobItemInfo(4));
        M9ExposurePlan1A high=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
        check(high.iso>0&&high.iso<=6400&&high.exposureNs>=400000&&high.exposureNs<=1000000000,"high endpoint bounded");
        // Explicit manual sensor pair remains authoritative after allocation.
        model.setCurrentISOValue(200);model.setCurrentExposureValue(2000000L);
        M9ExposurePlan1A manual=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
        check(manual.iso==200&&manual.exposureNs==2000000,"manual ISO/shutter retained");
        System.out.println("M9EXPOSUREPLAN1C: "+checks+" assertions PASS; actual production allocator and dial");
    }
}
