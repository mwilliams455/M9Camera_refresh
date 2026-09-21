import android.hardware.camera2.*;
import android.util.*;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.api.CameraMode;
import com.particlesdevs.photoncamera.capture.CaptureController;
import com.particlesdevs.photoncamera.circularbarlib.control.ManualParamModel;
import com.particlesdevs.photoncamera.processing.parameters.IsoExpoSelector;
import com.particlesdevs.photoncamera.m9.*;
import org.json.*;
import java.nio.file.*;

public class ExposurePlanTest {
 static int checks;
 static void check(boolean v,String why){checks++;if(!v)throw new AssertionError(why);}
 static void near(double a,double b,double tol,String why){check(Double.isFinite(a)&&Math.abs(a-b)<=tol,why+" actual="+a+" expected="+b);}
 static double ev(double x){return Math.log(x)/Math.log(2);}
 static CaptureController cc=PhotonCamera.getCaptureController();
 static CameraCharacteristics c=CaptureController.mCameraCharacteristics;
 static CaptureResult obs=new CaptureResult();
 static ManualParamModel model=new ManualParamModel();
 static void observe(int iso,long time){obs.set(CaptureResult.SENSOR_SENSITIVITY,iso);obs.set(CaptureResult.SENSOR_EXPOSURE_TIME,time);cc.mPreviewIso=iso;cc.mPreviewExposureTime=time;}
 static M9ExposurePlan1A plan(){return IsoExpoSelector.planM9LiveExposure1A(cc,obs);}
 static JSONObject allocation(M9ExposurePlan1A p){return new JSONObject(p.getAllocationSnapshot2G()).getJSONObject("intended");}
 public static void main(String[] args)throws Exception {
  JSONObject f=new JSONObject(Files.readString(Path.of(System.getenv("M9_ENERGY_FIXTURE2G"))));
  JSONObject camera=f.getJSONObject("camera");
  c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(50,12800));
  c.set(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE,new Range<Long>(11041L,33430445787L));
  c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,3200);
  c.set(CameraCharacteristics.CONTROL_AE_COMPENSATION_STEP,new Rational(1,3));
  obs.set(CaptureResult.SENSOR_TIMESTAMP,123L);obs.set(CaptureResult.CONTROL_AE_MODE,1);obs.set(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION,0);
  CaptureController.mPreviewCaptureResult=obs;model.addObserver(cc.getParamController());model.reset();
  M9SubjectMotionAnalyzer.scene=new JSONObject();
  JSONObject sweep=f.getJSONObject("controlledGyroSweep");
  observe(sweep.getInt("observedIso"),sweep.getLong("observedExposureNs"));
  PhotonCamera.getSettings().selectedMode=CameraMode.MOTION;
  JSONArray shakes=sweep.getJSONArray("shake"),oldScales=sweep.getJSONArray("gl2fPreviewScale");
  for(int i=0;i<shakes.length();i++) {
   PhotonCamera.getGyro().shake=shakes.getInt(i);M9ExposurePlan1A p=plan();
   near(p.previewScale(),1,1e-6,"steady scene cannot pulse with gyro");
   check(p.iso<=3200,"automatic RAW uses analog budget");
   near(ev(p.renderIntentScale(p.iso,p.exposureNs)),0,1e-6,"neutral RAW intent");
   System.out.println("SWEEP shake="+shakes.getInt(i)+" oldScale="+oldScales.getDouble(i)+" newScale="+p.previewScale()+" ISO="+p.iso+" ns="+p.exposureNs);
  }
  JSONArray captures=f.getJSONArray("captures");
  for(int i=0;i<captures.length();i++) {
   JSONObject sample=captures.getJSONObject(i);PhotonCamera.getSettings().selectedMode=CameraMode.valueOf(sample.getString("mode"));
   observe(sample.getInt("observedIso"),sample.getLong("observedExposureNs"));
   for(int shake:new int[]{25,50,100,200,400,1829}) {
    PhotonCamera.getGyro().shake=shake;M9ExposurePlan1A p=plan();
    near(p.previewScale(),1,1e-6,"recorded observation retains neutral energy");check(p.iso<=3200,"recorded automatic capture avoids rejected ISO");
    CaptureRequest.Builder request=new CaptureRequest.Builder();
    IsoExpoSelector.setExactExposureM9Wysiwyg1B(request,0,p.exposureNs,p.iso);
    check(request.get(CaptureRequest.SENSOR_SENSITIVITY)==p.iso&&request.get(CaptureRequest.SENSOR_EXPOSURE_TIME)==p.exposureNs,"production RAW setter submits displayed pair");
    near(ev(p.renderIntentScale(p.iso,p.exposureNs)),0,1e-6,"shared render intent");
   }
  }
  // Exposure remains monotonic through both ISO floors and saturation, with a
  // wide range of native base ISO values (no normalized-100 unit assumptions).
  for(CameraMode mode:new CameraMode[]{CameraMode.PHOTO,CameraMode.MOTION}) {
   PhotonCamera.getSettings().selectedMode=mode;
   for(int floor:new int[]{50,64,100,160}) {
    c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(floor,12800));
    for(int shake:new int[]{25,100,400,1829}) {
     PhotonCamera.getGyro().shake=shake;
     for(int observedIso:new int[]{floor,1743,3200,10000}) {
      observe(observedIso,20000000L);double previous=0;
      for(double offset:new double[]{-3,-1,-.25,0,.25,1,3}) {
       model.setCurrentEvValue(offset*3);M9ExposurePlan1A p=plan();
       near(ev(p.previewScale()),offset,0.001,"EV retained through saturation");
       near(ev(p.renderIntentScale(p.iso,p.exposureNs)),offset,0.001,"RAW intent retains EV");
       check(p.iso>=floor&&p.iso<=3200,"native automatic ISO bounds");
       check(p.previewScale()>previous,"monotonic EV");previous=p.previewScale();
      }
     }
    }
   }
  }
  model.reset();c.set(CameraCharacteristics.SENSOR_INFO_SENSITIVITY_RANGE,new Range<Integer>(50,12800));
  PhotonCamera.getSettings().selectedMode=CameraMode.PHOTO;observe(1824,20000000L);
  // Missing/invalid optional analog metadata must not invent an ISO 100 ceiling.
  for(Integer analog:new Integer[]{null,0,49,15000}) {
   c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,analog);
   M9ExposurePlan1A p=plan();near(p.previewScale(),1,1e-6,"fallback sensor range energy");
   check(allocation(p).getInt("automaticIsoMax")==12800,"invalid analog uses advertised sensor range");
  }
  c.set(CameraCharacteristics.SENSOR_MAX_ANALOG_SENSITIVITY,3200);
  // Explicit balance caps remain hard; do not silently turn an ISO cap into extra gain.
  for(int limit:new int[]{-4,-3,-2,800}) {
   cc.exposureBalanceIsoLimit=limit;M9ExposurePlan1A p=plan();int expected=limit==-4?800:limit==-3?1600:limit==-2?3200:800;
   check(p.iso<=expected,"physical units for explicit ISO ceiling");near(p.previewScale(),1,1e-6,"shutter compensates explicit ISO ceiling");
  }
  cc.exposureBalanceIsoLimit=-1;cc.exposureBalanceShutterLimit=.005f;
  M9ExposurePlan1A capped=plan();check(capped.iso==3200&&capped.exposureNs<=5000000,"explicit shutter cap retained");
  check(allocation(capped).getDouble("allocationErrorEv")<-.9,"unattainable target reported honestly");
  PhotonCamera.getGyro().tripod=true;near(plan().previewScale(),1,1e-6,"existing tripod override");PhotonCamera.getGyro().tripod=false;
  cc.exposureBalanceShutterLimit=-1;
  // Manual shutter/ISO override their automatic axis; the remaining axis uses the target.
  model.setCurrentExposureValue(1000000L);M9ExposurePlan1A shutter=plan();
  check(shutter.exposureNs==1000000&&shutter.iso==3200,"manual fast shutter respected at ISO ceiling");
  model.reset();model.setCurrentISOValue(6400);M9ExposurePlan1A iso=plan();
  check(iso.iso==6400,"explicit ISO may exceed conservative automatic ceiling");near(iso.previewScale(),1,1e-6,"manual ISO compensates via shutter");
  model.setCurrentExposureValue(2000000L);M9ExposurePlan1A both=plan();check(both.iso==6400&&both.exposureNs==2000000,"both explicit controls retained");
  model.reset();c.set(CameraCharacteristics.SENSOR_INFO_EXPOSURE_TIME_RANGE,new Range<Long>(1000000L,100000000L));
  observe(12800,100000000L);M9ExposurePlan1A high=plan();check(high.iso==3200&&high.exposureNs==100000000L,"true maximum reachable energy");
  observe(50,1000000L);model.setCurrentEvValue(-3);M9ExposurePlan1A low=plan();check(low.iso==50&&low.exposureNs==1000000,"true minimum reachable energy");
  check(allocation(low).getString("reason").equals("minimum_exposure_boundary"),"minimum boundary evidence");
  // Evidence copies must survive both subsequent attachment paths without mutation.
  String evidence=both.getAllocationSnapshot2G();M9ExposurePlan1A copy=both.withAutoPlacement2D("{}").withShutterPreviewSnapshot1W("{}");
  check(evidence.equals(copy.getAllocationSnapshot2G()),"immutable allocation evidence survives shutter copy");
  check(M9ExposurePlanDiagnostics1A.toJson(copy).getJSONObject("allocation2G").getJSONObject("intended").getString("reason").equals("explicit_sensor_pair"),"PRIMARY exports actual allocation evidence");
  System.out.println("M9LIVEGL2G HOST PASS: "+checks+" assertions; real allocator/RAW setter; phone validation pending");
 }
}
