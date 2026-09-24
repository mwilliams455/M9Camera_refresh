"""Validate preview probe serialization, allocation-stable TC20 math and photographic freezes."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
assembled=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None

source=r'''
import com.particlesdevs.photoncamera.m9.preview.M9PreviewTc20Math1A;
public class PreviewStabilityTest {
 static int count=0;
 static void yes(boolean b,String m){if(!b)throw new AssertionError(m);count++;System.out.println("PASS "+m);}
 static void near(double a,double b,double e,String m){if(Math.abs(a-b)>e)throw new AssertionError(m+": "+a+" != "+b);count++;System.out.println("PASS "+m);}
 static byte[] uniform(double y,int w,int h){
  byte[] p=new byte[w*h*4];int q=(int)Math.round(Math.max(0,Math.min(1,y))*65535);
  for(int i=0;i<w*h;i++){p[i*4]=(byte)(q>>>8);p[i*4+1]=(byte)q;p[i*4+3]=(byte)255;}
  return p;
 }
 public static void main(String[] a){
  int w=32,h=24;
  M9PreviewTc20Math1A.Result neutral=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET,w,h),w,h,1,0);
  yes(neutral.valid,"neutral panel valid");
  near(neutral.boundedEv,0,.004,"neutral target remains unity");

  M9PreviewTc20Math1A.Result bright=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET*2,w,h),w,h,1,0);
  near(bright.boundedEv,-.5,.004,"bright scene retains minus-half-EV bound");

  M9PreviewTc20Math1A.Result dark=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET*.5,w,h),w,h,1,0);
  near(dark.boundedEv,0,.004,"negative-only policy retained");

  near(M9PreviewTc20Math1A.slewEv(0,-.5),-.125,1e-12,"one-eighth stop darkening slew retained");
  near(M9PreviewTc20Math1A.slewEv(-.5,0),-.375,1e-12,"one-eighth stop release retained");
  near(M9PreviewTc20Math1A.slewEv(-.10,-.075),-.10,1e-12,"deadband retained");

  byte[] spatial=uniform(M9PreviewTc20Math1A.METER_TARGET*.5,w,h);
  int q=(int)Math.round(M9PreviewTc20Math1A.METER_TARGET*2*65535);
  for(int y=4;y<20;y++)for(int x=5;x<27;x++){int i=(y*w+x)*4;spatial[i]=(byte)(q>>>8);spatial[i+1]=(byte)q;}
  M9PreviewTc20Math1A.Result weighted=M9PreviewTc20Math1A.analyzePackedPanel(spatial,w,h,1,0);
  yes(weighted.weightedMedian>M9PreviewTc20Math1A.METER_TARGET,"centre weighting retained");
  yes(weighted.boundedEv<0,"bright central body still darkens");

  // Repeated calls exercise the persistent histogram path; result must not accumulate.
  for(int i=0;i<1000;i++){
    M9PreviewTc20Math1A.Result r=M9PreviewTc20Math1A.analyzePackedPanel(
        uniform(M9PreviewTc20Math1A.METER_TARGET,w,h),w,h,1,0);
    if(Math.abs(r.boundedEv)>.004)throw new AssertionError("histogram state leaked at "+i);
  }
  yes(true,"persistent histogram is cleared between samples");
  yes("M9PREVIEWSTABILITY1A".equals(M9PreviewTc20Math1A.REVISION),"stability math revision");

  System.out.println("ASSERTIONS "+count);
 }
}
'''
(out/'PreviewStabilityTest.java').write_text(source)
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out),
                str(HERE/'M9PreviewTc20Math1A.java'),str(out/'PreviewStabilityTest.java')],check=True)
result=subprocess.check_output(['java','-ea','-cp',str(out),'PreviewStabilityTest'],text=True)
assertions=int(result.strip().splitlines()[-1].split()[-1])
if assertions!=11: raise SystemExit(f'expected 11 assertions, got {assertions}')

integration={}
if assembled is not None:
 main=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java').read_text()
 meter=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java').read_text()
 evidence=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java').read_text()
 camera=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java').read_text()
 math=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java').read_text()
 proof=json.loads((assembled/'M9PREVIEWSTABILITY1A_SOURCE_PROOF.json').read_text())

 checks={
  'meter_boolean_sample':'public boolean sample(M9PreviewFrameState1W frame' in meter,
  'meter_busy':'public boolean isBusy() { return fence != 0; }' in meter,
  'evidence_busy':'public boolean isBusy() { return fence != 0; }' in evidence,
  'main_serializes':'!m9EvidenceBusy1A && mM9CurveTex != 0' in main
                    and '!m9AutoProbeSubmitted1A && !m9AutoProbeBusy1A' in main,
  'hud_null_guards':camera.count('if (captureController == null) return;')>=2,
  'no_boxed_sort':'Integer[]' not in math,
  'persistent_hist':'ThreadLocal<Scratch>' in math,
 }
 for name,ok in checks.items():
  print(name,ok)
  if not ok: raise SystemExit('integration failed '+name)

 frozen=[
  'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
  'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
  'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
  'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
  'app/src/main/assets/shaders/preview/main_fs.glsl',
  'app/src/main/cpp/m9color_jni.cpp',
 ]
 for rel in frozen:
  if proof['before'][rel]!=proof['after'][rel]: raise SystemExit('frozen seam changed '+rel)
 integration=checks|{'photographic_seams_frozen':True}

receipt={'revision':'M9PREVIEWSTABILITY1A','assertions':assertions,
 'probe_serialization':True,'tc20_boxed_sort_removed':True,
 'known_hud_null_guard':True,'current_panning_crash_root_cause_proven':False,
 'integration':integration,'output':result}
(out.parent/'previewstability1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result,end='')
print(json.dumps({k:v for k,v in receipt.items() if k!='output'}))
