#!/usr/bin/env python3
"""Run bounded Java control-flow probes extracted from the exact 2.72 source.

These reproduce request values and a state transition, not Android/HAL behaviour.
Requires only Python and a JDK. Does not edit the assembled app.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
prefix = 'app/src/main/java/com/particlesdevs/photoncamera/'
pins = {
    'capture/CaptureController.java': '000ab6d4712a6120d544ee5355c7521a0182d8d264b47c7a992a5e4ec25dcb75',
    'control/TouchFocus.java': 'e36670e15ec00b0ab64828e8b74127341c9b5c1d679310f88203ed166d6ba3d2',
}
sources = {}
for name, expected in pins.items():
    data = (root / prefix / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected, name
    sources[name] = data.decode()
c = sources['capture/CaptureController.java']
t = sources['control/TouchFocus.java']

def between(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]

unlock = between(c, '    public void unlockFocus() {', '    public CaptureRequest.Builder getDebugCaptureRequestBuilder()')
reset = between(c, '    public void reset3Aparams() {', '    public void setPreviewAEModeRebuild(')
mono = c[c.index('private void captureStillPictureMono()'):]
mono_af = between(mono, '            Object mode = mPreviewRequestBuilder.get(CONTROL_AF_MODE);', '            //captureBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_EDOF);')
passive = between(t, '    static boolean passivePhaseComplete(', '    /**\n     * Fed from CaptureController')
passive_case = between(t, '                    if (regionLive && Integer.valueOf(CameraMetadata.CONTROL_AF_STATE_PASSIVE_SCAN)', '                case SEQ_WAIT_START_ACK:')
passive_case = passive_case.rsplit('                    break;', 1)[0]

java = r'''
import java.util.*;
public class AuditProbe {
  @interface Nullable {}
  static class CaptureRequest {
    static final int CONTROL_AF_MODE_OFF=0, CONTROL_AF_MODE_AUTO=1,
        CONTROL_AF_MODE_CONTINUOUS_PICTURE=4;
    static final int CONTROL_AF_TRIGGER_IDLE=0, CONTROL_AF_TRIGGER_START=1, CONTROL_AF_TRIGGER_CANCEL=2;
    static final String CONTROL_AF_MODE="afMode", CONTROL_AF_TRIGGER="afTrigger";
    static class Builder {
      Map<String,Object> values=new HashMap<>();
      void set(String key,Object value){values.put(key,value);}
      @SuppressWarnings("unchecked") <T> T get(String key){return (T)values.get(key);}
    }
  }
  static class CameraMetadata extends CaptureRequest {
    static final int CONTROL_AF_STATE_PASSIVE_SCAN=1, CONTROL_AF_STATE_PASSIVE_FOCUSED=2;
  }
  static class Log { static void d(String a,String b){} }
  enum CameraMode { PHOTO, RAWVIDEO }
  static class Settings { CameraMode selectedMode=CameraMode.PHOTO; }
  static class PhotonCamera { static Settings getSettings(){return new Settings();} }
  static class PreferenceKeys { static int getAfMode(){return 4;} static int getAeMode(){return 1;} }
  static class SystemClock { static long elapsedRealtime(){return 100;} }
  static class Param { void setupPreview(){} }
  static final String TAG="probe", CONTROL_AF_MODE=CaptureRequest.CONTROL_AF_MODE;
  static final int CONTROL_AF_MODE_CONTINUOUS_VIDEO=3, STATE_PREVIEW=0;
  CaptureRequest.Builder mPreviewRequestBuilder=new CaptureRequest.Builder();
  Object mCaptureSession=new Object();
  Param paramController=new Param();
  int mState=3,mPreviewAFMode;
  List<Integer> repeating=new ArrayList<>(), oneShot=new ArrayList<>();
  boolean isVideoMode(){return false;}
  void setAEMode(CaptureRequest.Builder b,int mode){}
  void setAFMode(CaptureRequest.Builder b,int mode){b.set(CONTROL_AF_MODE,mode);}
  void rebuildPreviewBuilder(){repeating.add(mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AF_TRIGGER));}
  void rebuildPreviewBuilderOneShot(){oneShot.add(mPreviewRequestBuilder.get(CaptureRequest.CONTROL_AF_TRIGGER));}
  boolean passiveScanSeen=true; long dwellDeadlineElapsed=400,seqDeadlineElapsed=2000; int starts;
  void sendAfStartLocked(){starts++;}
  // Full unlock/reset methods and actual passive-phase branch follow unchanged.
''' + unlock + reset + passive + '\n  void passiveStep(Integer afState,boolean regionLive){\n' + passive_case + '\n  }\n' + '\n  CaptureRequest.Builder monoStill(int selectedMode){\n' + '''
    mPreviewRequestBuilder.set(CONTROL_AF_MODE,selectedMode);
    CaptureRequest.Builder captureBuilder=new CaptureRequest.Builder();
''' + mono_af + '''
    return captureBuilder;
  }
  static void require(boolean result,String message){if(!result)throw new AssertionError(message);}
  public static void main(String[] args){
    AuditProbe a=new AuditProbe();
    a.mPreviewRequestBuilder.set(CONTROL_AF_MODE,4);
    a.mPreviewRequestBuilder.set(CaptureRequest.CONTROL_AF_TRIGGER,0);
    a.unlockFocus();
    require(a.oneShot.equals(Arrays.asList(2,1,2)),"unexpected unlock one-shots");
    require(a.repeating.get(a.repeating.size()-1)==2,"no leaked CANCEL");
    System.out.println("REPRODUCED legacy unlock: oneShot="+a.oneShot+" repeating="+a.repeating+" finalTrigger=CANCEL");
    CaptureRequest.Builder s=a.monoStill(4);
    require(Integer.valueOf(1).equals(s.get(CONTROL_AF_MODE)),"continuous mode preserved unexpectedly");
    require(Integer.valueOf(2).equals(s.get(CaptureRequest.CONTROL_AF_TRIGGER)),"no still CANCEL");
    System.out.println("REPRODUCED Monochrom continuous-picture preview -> still AUTO + CANCEL");
    s=a.monoStill(0);
    require(Integer.valueOf(1).equals(s.get(CONTROL_AF_MODE)),"manual mode preserved unexpectedly");
    System.out.println("REPRODUCED Monochrom manual preview -> still AUTO + CANCEL");
    AuditProbe b=new AuditProbe();
    b.passiveStep(CameraMetadata.CONTROL_AF_STATE_PASSIVE_SCAN,true);
    require(b.starts==0,"live scan should not start lock");
    b.passiveStep(CameraMetadata.CONTROL_AF_STATE_PASSIVE_FOCUSED,false);
    require(b.starts==1,"stale settled result did not start lock");
    System.out.println("REPRODUCED stale settled result ends current tap passive scan before dwell/deadline");
  }
}
'''
with tempfile.TemporaryDirectory(prefix='af-audit-') as tmp:
    p = Path(tmp)
    (p/'AuditProbe.java').write_text(java)
    subprocess.run(['java','com.sun.tools.javac.Main','-d',tmp,str(p/'AuditProbe.java')],check=True)
    result = subprocess.run(['java','-cp',tmp,'AuditProbe'],check=True,capture_output=True,text=True)
    print(json.dumps({
        'status':'reproduced',
        'sourceCommit':'83a421a4b47533135628b8d69c9f92338dea2ac6',
        'sourceSha256':pins,
        'method':'unmodified method/branch extraction with request-recording and clock stubs',
        'limits':'Not a full Android test; no HAL, lens, image, UI or timing validation. ParamController.setupPreview is a no-op in the unlock probe.',
        'observations':result.stdout.strip().splitlines(),
    },indent=2))
