#!/usr/bin/env python3
"""Compile assembled production Java against minimal fake hardware, then test behaviour.
Only org.json is downloaded; fixed version and SHA256 verified. No Android SDK required.
"""
from pathlib import Path
import hashlib, re, shutil, subprocess, sys, tempfile, urllib.request
ROOT=Path(sys.argv[1]).resolve()
J=ROOT/'app/src/main/java/com/particlesdevs/photoncamera'
P='com.particlesdevs.photoncamera.'
with tempfile.TemporaryDirectory(prefix='m9-exposure-test-') as d:
 d=Path(d); src=d/'src';src.mkdir();out=d/'classes';out.mkdir()
 def write(name, body):
  p=src/(name.replace('.','/')+'.java');p.parent.mkdir(parents=True,exist_ok=True)
  package,cls=name.rsplit('.',1);p.write_text('package '+package+';\n'+body)
 def copy(path,name):
  dest=src/(name.replace('.','/')+'.java');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
 for name in ['m9.M9ExposurePlan1A','m9.M9ExposurePlanDiagnostics1A','m9.M9M10rMfmTest1A','m9.M9ModernExposurePolicy','manual.ParamController','processing.parameters.IsoExpoSelector','processing.parameters.ExposureIndex']:
  copy(J/(name.replace('.','/')+'.java'),P+name)
 copy(ROOT/'circularbarlib/src/main/java/com/particlesdevs/photoncamera/circularbarlib/control/ManualParamModel.java',P+'circularbarlib.control.ManualParamModel')
 write('androidx.annotation.NonNull','public @interface NonNull {}')
 write('android.graphics.Rect','public class Rect {public int width(){return 4000;}}')
 write('android.util.SizeF','public class SizeF {public float getWidth(){return 9;}}')
 write('android.util.Rational','public class Rational {double v; public Rational(int n,int d){v=(double)n/d;} public double doubleValue(){return v;}}')
 write('android.util.Range','public class Range<T> {T a,b;public Range(T x,T y){a=x;b=y;}public T getLower(){return a;} public T getUpper(){return b;}}')
 write('android.os.SystemClock','public class SystemClock {public static long elapsedRealtime(){return 1000;}public static long elapsedRealtimeNanos(){return 1000000000L;}}')
 write('android.os.Build','public class Build {public static class VERSION {public static int SDK_INT=35;}public static class VERSION_CODES {public static int R=30;}}')
 write(P+'util.Log','public class Log {public static void d(String t,String s){} public static void v(String t,String s){} public static void w(String t,String s){}}')
 write('android.hardware.camera2.CameraMetadata','public class CameraMetadata {public static final int CONTROL_AE_MODE_OFF=0,CONTROL_AE_MODE_ON=1,CONTROL_AF_MODE_OFF=0,LENS_OPTICAL_STABILIZATION_MODE_ON=1;}')
 keys={
 'CameraCharacteristics':{'SENSOR_INFO_SENSITIVITY_RANGE':'android.util.Range<Integer>','SENSOR_INFO_EXPOSURE_TIME_RANGE':'android.util.Range<Long>','SENSOR_MAX_ANALOG_SENSITIVITY':'Integer','CONTROL_AE_COMPENSATION_STEP':'android.util.Rational','LENS_INFO_AVAILABLE_FOCAL_LENGTHS':'float[]','SENSOR_INFO_PHYSICAL_SIZE':'android.util.SizeF','SENSOR_INFO_ACTIVE_ARRAY_SIZE':'android.graphics.Rect','LENS_INFO_AVAILABLE_OPTICAL_STABILIZATION':'int[]'},
 'CaptureResult':{'SENSOR_EXPOSURE_TIME':'Long','SENSOR_SENSITIVITY':'Integer','SENSOR_TIMESTAMP':'Long','CONTROL_POST_RAW_SENSITIVITY_BOOST':'Integer','CONTROL_AE_MODE':'Integer','CONTROL_AE_EXPOSURE_COMPENSATION':'Integer','CONTROL_ZOOM_RATIO':'Float','SCALER_CROP_REGION':'android.graphics.Rect'},
 'CaptureRequest':{'SENSOR_EXPOSURE_TIME':'Long','SENSOR_SENSITIVITY':'Integer','CONTROL_AE_MODE':'Integer','CONTROL_AF_MODE':'Integer','CONTROL_AE_EXPOSURE_COMPENSATION':'Integer','LENS_FOCUS_DISTANCE':'Float'}}
 for cls, fields in keys.items():
  body='public class '+cls+' extends CameraMetadata { public static class Key<T>{} java.util.Map<Key<?>,Object> m=new java.util.HashMap<>();public <T> T get(Key<T> k){return (T)m.get(k);} public <T> void set(Key<T> k,T v){m.put(k,v);}'
  body+=''.join('public static final Key<'+t+'> '+k+'=new Key<>();' for k,t in fields.items())
  if cls=='CaptureRequest':body+='public static class Builder extends CaptureRequest {}'
  write('android.hardware.camera2.'+cls,body+'}')
 write(P+'api.CameraMode','public enum CameraMode {PHOTO,NIGHT,MOTION,RAWVIDEO,UNLIMITED,VIDEO}')
 write(P+'settings.PreferenceKeys','public class PreferenceKeys {public static int getBracketingMode(){return 2;}public static int getAfMode(){return 1;}}')
 write(P+'m9.M9Config','public class M9Config {public static boolean usesM9Pipeline(){return true;}public static boolean isM9Modern(){return true;}public static boolean isCaptureTest(){return true;}}')
 write(P+'m9.preview.M9LivePreview1A','public class M9LivePreview1A {public static final boolean ENABLED=false;}')
 write(P+'app.PhotonCamera','''public class PhotonCamera {
 public static class Settings {public double exposureCompensation;public com.particlesdevs.photoncamera.api.CameraMode selectedMode=com.particlesdevs.photoncamera.api.CameraMode.PHOTO;public String mCameraID="0";public boolean eisPhoto;}
 public static class Gyro {public boolean getTripod(){return false;}public int getFilteredShakiness(){return 100;}}
 public static class Gravity {public int getCameraRotation(int r){return r;}}
 static Settings s=new Settings();static Gyro g=new Gyro();static Gravity v=new Gravity();
 static com.particlesdevs.photoncamera.capture.CaptureController c=new com.particlesdevs.photoncamera.capture.CaptureController();
 public static Settings getSettings(){return s;}public static Gyro getGyro(){return g;}public static Gravity getGravity(){return v;}public static com.particlesdevs.photoncamera.capture.CaptureController getCaptureController(){return c;}}
 ''')
 write(P+'capture.CaptureController','''public class CaptureController {
 public static android.hardware.camera2.CameraCharacteristics mCameraCharacteristics=new android.hardware.camera2.CameraCharacteristics();
 public static android.hardware.camera2.CaptureResult mPreviewCaptureResult;
 public android.hardware.camera2.CaptureRequest.Builder mPreviewRequestBuilder=new android.hardware.camera2.CaptureRequest.Builder();
 public long mPreviewExposureTime; public int mPreviewIso,mSensorOrientation,cameraRotation,oisMode;
 public float exposureBalanceMultiplier=1,exposureBalanceShutterLimit=-1;public int exposureBalanceIsoLimit=-1;
 final com.particlesdevs.photoncamera.manual.ParamController p=new com.particlesdevs.photoncamera.manual.ParamController(this);
 public com.particlesdevs.photoncamera.manual.ParamController getParamController(){return p;}
 public com.particlesdevs.photoncamera.m9.M9ExposurePlan1A getM9ExposurePlan1A(){return null;}
 public boolean isZslMode(){return false;}public void resetPreviewAEMode(){}public void rebuildPreviewBuilder(){}public void unlockFocus(){}}
 ''')
 write(P+'m9.M9SubjectMotionAnalyzer','''public class M9SubjectMotionAnalyzer {
 public static org.json.JSONObject scene=new org.json.JSONObject();
 public static org.json.JSONObject snapshotJson(int r){return scene;}
 public static double getCaptureMotionScore(){return 0;} public static double getRecentPeakScore(){return 0;}public static long getFramesUsed(){return 10;}}
 ''')
 write(P+'m9.M9Probe','public class M9Probe {public static int calls;}')
 allocator=(J/'processing/parameters/IsoExpoSelector.java').read_text()
 for cls in ['M9ExposureAudit','M9ExposureDiagnostics','M9SceneExposureDiagnostic']:
  methods=set(re.findall(cls+r'\.([\w]+)\(',allocator))
  write(P+'m9.'+cls,'public class '+cls+' {'+''.join('public static void '+m+'(Object... args){M9Probe.calls++;}' for m in methods)+'}')
 write(P+'m9.M9BacklightDiagnostic','''public class M9BacklightDiagnostic {
 public static class LiveFeedbackDecision {public final boolean valid,wouldApply;public final double recommendedEv,appliedEv;public final String reason; public LiveFeedbackDecision(boolean v,boolean w,double r,double a,String s,org.json.JSONObject j){valid=v;wouldApply=w;recommendedEv=r;appliedEv=a;reason=s;}}
 public static LiveFeedbackDecision evaluateLiveFeedback(Object... args){M9Probe.calls++;return new LiveFeedbackDecision(false,false,0,0,"stub",new org.json.JSONObject());}
 public static void recordLiveFeedbackApplication(Object... args){M9Probe.calls++;}}
 ''')
 shutil.copyfile(Path(__file__).with_name('ExposurePlanTest.java'),src/'ExposurePlanTest.java')
 jar=d/'json.jar'
 if len(sys.argv)>2:shutil.copyfile(sys.argv[2],jar)
 else:urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar',jar)
 assert hashlib.sha256(jar.read_bytes()).hexdigest()=='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed','JSON dependency hash mismatch'
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(jar),'-d',str(out)]+[str(p) for p in src.rglob('*.java')],check=True)
 subprocess.run(['java','-ea','-cp',str(out)+':'+str(jar),'ExposurePlanTest'],check=True)
