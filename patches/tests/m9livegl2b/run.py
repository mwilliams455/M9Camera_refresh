#!/usr/bin/env python3
"""Execute the production AF helper and controller transition bodies with a recording Camera2 session."""
from pathlib import Path
import re,sys,tempfile,subprocess,shutil
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
j=root/'app/src/main/java/com/particlesdevs/photoncamera'
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp)
 def write(rel,txt):
  p=d/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(txt)
 write('android/hardware/camera2/CaptureRequest.java','''package android.hardware.camera2;
 import java.util.*;
 public class CaptureRequest {
 public static final int CONTROL_AF_MODE_OFF=0,CONTROL_AF_MODE_AUTO=1,CONTROL_AF_MODE_MACRO=2,CONTROL_AF_MODE_CONTINUOUS_VIDEO=3,CONTROL_AF_MODE_CONTINUOUS_PICTURE=4,CONTROL_AF_MODE_EDOF=5;
 public static final int CONTROL_AF_TRIGGER_IDLE=0,CONTROL_AF_TRIGGER_START=1,CONTROL_AF_TRIGGER_CANCEL=2;
 public static final Key<Integer> CONTROL_AF_MODE=new Key<>(),CONTROL_AF_TRIGGER=new Key<>();
 public static final Key<Float> LENS_FOCUS_DISTANCE=new Key<>(); public static final Key<Object> CONTROL_AF_REGIONS=new Key<>();
 public static class Key<T>{}
 public final Map<Key<?>,Object> values=new HashMap<>();
 @SuppressWarnings("unchecked") public <T>T get(Key<T> k){return (T)values.get(k);}
 public static class Builder {
 public final Map<Key<?>,Object> values=new HashMap<>();
 public <T>void set(Key<T> k,T v){if(v==null)values.remove(k);else values.put(k,v);}
 @SuppressWarnings("unchecked") public <T>T get(Key<T> k){return (T)values.get(k);}
 public CaptureRequest build(){CaptureRequest r=new CaptureRequest();r.values.putAll(values);return r;}
 }}''')
 write('android/hardware/camera2/CaptureResult.java','''package android.hardware.camera2;public class CaptureResult extends CaptureRequest {
 public static final Key<Integer> CONTROL_AF_STATE=new Key<>();
 public static final int CONTROL_AF_STATE_INACTIVE=0,CONTROL_AF_STATE_ACTIVE_SCAN=3,CONTROL_AF_STATE_FOCUSED_LOCKED=4;
 }''')
 write('android/hardware/camera2/CameraMetadata.java','package android.hardware.camera2;public class CameraMetadata extends CaptureRequest {}')
 write('android/hardware/camera2/CameraAccessException.java','package android.hardware.camera2;public class CameraAccessException extends Exception {}')
 write('android/hardware/camera2/CameraCharacteristics.java','''package android.hardware.camera2;public class CameraCharacteristics {
 public static final CaptureRequest.Key<Float> LENS_INFO_MINIMUM_FOCUS_DISTANCE=new CaptureRequest.Key<>();
 public Float minimum=10f;public Float get(CaptureRequest.Key<Float> k){return minimum;}}
 ''')
 write('android/os/Handler.java','package android.os;public class Handler {}')
 write('android/hardware/camera2/CameraCaptureSession.java','''package android.hardware.camera2;
 import java.util.*;import android.os.Handler;
 public class CameraCaptureSession {
 public static class CaptureCallback{} public boolean failNext=false;
 public final List<CaptureRequest> captures=new ArrayList<>(),repeats=new ArrayList<>();
 public int capture(CaptureRequest r,CaptureCallback c,Handler h)throws CameraAccessException {if(failNext){failNext=false;throw new CameraAccessException();}captures.add(r);return captures.size();}
 public int setRepeatingRequest(CaptureRequest r,CaptureCallback c,Handler h)throws CameraAccessException {repeats.add(r);return repeats.size();}
 }''')
 shutil.copyfile(j/'m9/preview/M9FocusContinuity2B.java',d/'M9FocusContinuity2B.java')
 source=(j/'capture/CaptureController.java').read_text()
 def method(name):
  m=re.search(r'^    (?:private|public) (?:void|boolean) '+name+r'\(',source,re.M);assert m,name
  a=m.start();b=source.index('{',a)+1;depth=1
  while depth:
   if source[b]=='{':depth+=1
   elif source[b]=='}':depth-=1
   b+=1
  return source[a:b].replace('private ','public ',1)
 bodies='\n'.join(method(n) for n in ['useM9FocusContinuity2B','primeM9AutoFocus2B','lockFocus','unlockFocusM9Continuous1T'])
 write('Probe.java','''import android.hardware.camera2.*;import android.os.*;import com.particlesdevs.photoncamera.m9.preview.M9FocusContinuity2B;
 public class Probe {
 static final String TAG="test";boolean burst=false,mIsRecordingVideo=false,m9AutoAfPrimed2B=false;
 static final int STATE_PREVIEW=0,STATE_PICTURE_TAKEN=1,STATE_WAITING_LOCK=2;
 int mState=STATE_PREVIEW,stillCalls=0;float mFocus=.5703125f;
 CameraCharacteristics mCameraCharacteristics=new CameraCharacteristics();
 CaptureRequest.Builder mPreviewRequestBuilder=new CaptureRequest.Builder();
 CameraCaptureSession mCaptureSession=new CameraCaptureSession();
 CameraCaptureSession.CaptureCallback mCaptureCallback=new CameraCaptureSession.CaptureCallback();
 Handler mBackgroundHandler=new Handler();CaptureRequest mPreviewInputRequest;Touch mTouchFocus=new Touch();
 static class Touch {boolean isTouchFocus=false;}
 void startTimerLocked(){}void captureStillPicture(){stillCalls++;}
 '''+bodies+'''}
 class Log {static void d(Object...a){}static void w(Object...a){}static void e(Object...a){}}
 enum CameraMode {PHOTO,UNLIMITED,RAWVIDEO}
 class PhotonCamera {static class Settings {CameraMode selectedMode=CameraMode.PHOTO;}static Settings s=new Settings();static Settings getSettings(){return s;}}
 class M9Config {static boolean isCaptureTest(){return true;}}
 ''')
 # Integration wiring: tests above execute the helper, so verify the real still/callback call sites use it.
 assert 'M9FocusContinuity2B.prepareStill(mPreviewRequestBuilder, captureBuilder);' in source
 assert 'if (useM9FocusContinuity2B()) {\n                primeM9AutoFocus2B(result);\n            } else if' in source
 assert 'm9AutoAfPrimed2B = false;\n        mPreviewRequestBuilder = null;' in source
 shutil.copyfile(here/'FocusTest.java',d/'FocusTest.java')
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(d/'classes'),*[str(p) for p in d.rglob('*.java')]],check=True)
 subprocess.run(['java','-ea','-cp',str(d/'classes'),'FocusTest'],check=True)
