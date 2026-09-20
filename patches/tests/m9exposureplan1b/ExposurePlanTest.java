import android.hardware.camera2.*;
import android.util.*;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.api.CameraMode;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.circularbarlib.control.ManualParamModel;
import com.particlesdevs.photoncamera.m9.*;
import com.particlesdevs.photoncamera.processing.parameters.IsoExpoSelector;
import org.json.*;

/** Runs real plan, allocator, MFM, motion policy and manual control code with fake hardware. */
public class ExposurePlanTest {
    static int checks;
    static void check(boolean ok, String msg) { checks++; if (!ok) throw new AssertionError(msg); }
    static void near(double actual, double expected, double tolerance, String msg) {
        check(Double.isFinite(actual) && Math.abs(actual-expected)<=tolerance,
                msg+": actual="+actual+" expected="+expected);
    }
    static double ev(double ratio) {return Math.log(ratio)/Math.log(2);}
    static JSONObject scene(boolean backlit) {
        JSONArray rows=new JSONArray();
        for(int r=0;r<16;r++) { JSONArray row=new JSONArray();
            for(int c=0;c<22;c++) row.put(backlit && r<6 ? 220 : 40);
            rows.put(row);
        }
        return new JSONObject().put("previewLuma",new JSONObject().put("framesAnalyzed",10)
                .put("m10rAeGrid16x22",new JSONObject().put("valid",true).put("rows",rows)));
    }
    public static void main(String[] args) {
        CaptureController cc=PhotonCamera.getCaptureController();
        CameraCharacteristics c=CaptureController.mCameraCharacteristics;
        c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(50,6400));
        c.set(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE,new Range<Long>(100000L,1000000000L));
        c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,1600);
        c.set(CameraCharacteristics.CONTROL_AE_COMPENSATION_STEP,new Rational(1,3));
        CaptureResult obs=new CaptureResult();
        obs.set(CaptureResult.SENSOR_SENSITIVITY,100);
        obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,10000000L);
        obs.set(CaptureResult.SENSOR_TIMESTAMP,123456L);
        obs.set(CaptureResult.CONTROL_AE_MODE,1);
        obs.set(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION,0);
        cc.mPreviewIso=100;cc.mPreviewExposureTime=10000000L;
        CaptureController.mPreviewCaptureResult=obs;
        ManualParamModel model=new ManualParamModel();model.addObserver(cc.getParamController());model.reset();
        M9SubjectMotionAnalyzer.scene=scene(false);
        M9ExposurePlan1A base=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
        near(base.autoEv,0,1e-12,"uniform scene stays neutral");
        IsoExpoSelector.ExpoPair legacy=IsoExpoSelector.GenerateExpoPair(-1,cc);
        check(base.iso==legacy.iso && base.exposureNs==legacy.exposure,"neutral allocation matches GL1U");
        M9Probe.calls=0;
        double target=.107*8192/10000;
        double oldPlus=target*Math.pow(2,1.0/3)*M9ExposurePlan1A.boundedGain(target/(target*Math.pow(2,1.0/3)));
        near(oldPlus,target,1e-12,"reproduces old third-stop cancellation");
        for (CameraMode mode : new CameraMode[]{CameraMode.PHOTO, CameraMode.MOTION}) {
        PhotonCamera.getSettings().selectedMode=mode;
        check(cc.getParamController().useM9ExposurePlan1A(), "actual mode gate enables "+mode);
        check(!cc.isZslMode(), "actual capture route avoids ZSL for "+mode);
        for(boolean backlit:new boolean[]{false,true}) {
            M9SubjectMotionAnalyzer.scene=scene(backlit);
            model.setCurrentEvValue(0);
            M9ExposurePlan1A zero=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
            check(backlit ? zero.autoEv>0.08 : zero.autoEv==0,"auto backlight decision is active");
            double prevEnergy=0;
            for(int steps:new int[]{-3,-1,0,1,3}) {
                model.setCurrentEvValue(steps);
                M9ExposurePlan1A p=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
                near(p.userEv,steps/3.0,1e-12,"manual dial steps converted to EV");
                near(p.autoEv,zero.autoEv,1e-12,"moving EV preserves scene baseline");
                double energy=M9ExposurePlan1A.energy(p.iso,p.exposureNs);
                check(energy>prevEnergy,"exposure increases monotonically");prevEnergy=energy;
                near(ev(energy/M9ExposurePlan1A.energy(zero.iso,zero.exposureNs)),steps/3.0,.025,"allocator EV response");
                near(p.previewScale(),energy/1e9,1e-12,"display uses the planned capture energy");
                check(p.referenceIso==zero.referenceIso && p.referenceExposureNs==zero.referenceExposureNs,"tone reference independent of user EV");
                double intent=p.renderIntentScale(p.iso,p.exposureNs);
                for(double neutralMedian:new double[]{.025,target,.19}) {
                    double gain0=M9ExposurePlan1A.boundedGain(Math.min(
                            M9ExposurePlan1A.neutralBaseGain(neutralMedian,1,target),
                            M9ExposurePlan1A.neutralGuardGain(.65,1,.95)));
                    double gain=M9ExposurePlan1A.boundedGain(Math.min(
                            M9ExposurePlan1A.neutralBaseGain(neutralMedian*intent,intent,target),
                            M9ExposurePlan1A.neutralGuardGain(.65*intent,intent,.95)));
                    near(gain,gain0,1e-12,"render gain does not cancel intent");
                    near(neutralMedian*intent*gain/(neutralMedian*gain0),intent,1e-12,"precurve output retains exposure ratio");
                }
                check(cc.mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AE_MODE)==1,"hardware reference keeps AE on");
                check(cc.mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AE_EXPOSURE_COMPENSATION)==0,"hardware reference keeps zero EV");
                check(p.matches("0",mode.name(),1001,p.userEv,0,0),"fresh matching plan usable");
                check(!p.matches("1",mode.name(),1001,p.userEv,0,0),"lens change invalidates");
                check(!p.matches("0","NIGHT",1001,p.userEv,0,0),"mode change invalidates");
                check(!p.matches("0",mode.name(),2601,p.userEv,0,0),"stale plan invalidates");
                check(!p.matches("0",mode.name(),1001,p.userEv+1,0,0),"EV change invalidates");
                check(!p.matches("0",mode.name(),1001,p.userEv,1000000,0),"shutter change invalidates");
                check(!p.matches("0",mode.name(),1001,p.userEv,0,200),"ISO change invalidates");
                check(M9ExposurePlanDiagnostics1A.toJson(p).getLong("sourceSensorTimestampNs")==123456,"plan diagnostics preserve observation identity");
            }
        }
        }
        PhotonCamera.getSettings().selectedMode=CameraMode.MOTION;
        M9Config.pipeline=false;
        check(cc.isZslMode(), "non-M9 Motion keeps original ZSL route");
        M9Config.pipeline=true;
        PhotonCamera.getSettings().selectedMode=CameraMode.PHOTO;
        model.setCurrentEvValue(0);M9SubjectMotionAnalyzer.scene=scene(false);
        for(long shutter:new long[]{1000000L,10000000L,40000000L}) {
            model.setCurrentExposureValue(shutter);model.setCurrentISOValue(200);
            M9ExposurePlan1A p=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
            check(p.iso==200 && p.exposureNs==shutter,"explicit manual pair reaches plan");
            near(p.autoEv,0,1e-12,"auto assist bypassed in manual");
            near(p.renderIntentScale(100,shutter),.5*p.renderIntentScale(200,shutter),1e-12,"render honors actual RAW exposure, not requested ISO");
            check(cc.mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AE_MODE)==1,"manual controls preserve neutral metering feed");
        }
        model.setCurrentExposureValue(2000000000L);model.setCurrentISOValue(10000);
        M9ExposurePlan1A limited=IsoExpoSelector.planM9LiveExposure1A(cc,obs);
        check(limited.iso==6400 && limited.exposureNs==1000000000L,"physical bounds apply to manual pair");
        model.reset();
        check(base.iso==50 && base.exposureNs==20000000L,"old immutable plan survives later changes");
        check(IsoExpoSelector.pairs.isEmpty() && IsoExpoSelector.fullpairs.isEmpty(),"planning never populates capture burst history");
        check(M9Probe.calls==0,"planning never publishes capture diagnostics");
        obs.set(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION,1);
        check(IsoExpoSelector.planM9LiveExposure1A(cc,obs)==null,"reject transient compensated hardware frame");
        obs.set(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION,0);obs.set(CaptureResult.CONTROL_AE_MODE,0);
        check(IsoExpoSelector.planM9LiveExposure1A(cc,obs)==null,"reject old manual hardware frame");
        obs.set(CaptureResult.CONTROL_AE_MODE,1);obs.set(CaptureResult.SENSOR_SENSITIVITY,0);
        check(IsoExpoSelector.planM9LiveExposure1A(cc,obs)==null,"invalid metadata cannot produce plan");
        check(!M9ExposurePlan1A.autoEligible(true,true,0,0),"tripod bypass retained");
        System.out.println("M9EXPOSUREPLAN1B HOST PASS: "+checks+" assertions; real routing/allocator/MFM/manual controls, Photo + Motion synthetic scenes, no device claim");
    }
}
