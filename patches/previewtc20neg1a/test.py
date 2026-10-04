"""Test preview-only TC20 math and assembled source boundaries."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
assembled=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None

source=r'''
import com.particlesdevs.photoncamera.m9.preview.M9PreviewTc20Math1A;
public class PreviewTc20Test {
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
  near(neutral.boundedEv,0,.002,"target median holds unity");
  near(neutral.boundedGain,1,.002,"target median gain unity");

  M9PreviewTc20Math1A.Result bright=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET*2,w,h),w,h,1,0);
  near(bright.requestedGain,.5,.003,"two-times target requests half gain");
  near(bright.boundedEv,-.5,.003,"darkening bounded at minus half EV");
  near(bright.boundedGain,Math.pow(2,-.5),.003,"minus half EV gain");

  M9PreviewTc20Math1A.Result veryBright=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET*4,w,h),w,h,1,0);
  near(veryBright.boundedEv,-.5,.003,"strong bright scene remains half-EV bounded");

  M9PreviewTc20Math1A.Result dark=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET*.5,w,h),w,h,1,0);
  near(dark.boundedEv,0,.003,"positive TC20 lift deliberately not predicted");
  near(dark.boundedGain,1,.003,"dark panel stays unity in negative-only v1A");

  yes(!M9PreviewTc20Math1A.analyzePackedPanel(new byte[3],w,h,1,0).valid,
      "invalid panel fails closed");
  near(M9PreviewTc20Math1A.slewEv(0,-.5),-.25,1e-12,"first darkening slew quarter EV");
  near(M9PreviewTc20Math1A.slewEv(-.25,-.5),-.5,1e-12,"second darkening slew reaches bound");
  near(M9PreviewTc20Math1A.slewEv(-.5,0),-.25,1e-12,"release slews quarter EV");
  near(M9PreviewTc20Math1A.slewEv(-.25,0),0,1e-12,"release reaches unity");

  // Gaussian weighting: a bright central majority by weight should control the median
  // even with darker outer pixels.
  byte[] spatial=uniform(M9PreviewTc20Math1A.METER_TARGET*.5,w,h);
  int q=(int)Math.round(M9PreviewTc20Math1A.METER_TARGET*2*65535);
  for(int y=4;y<20;y++)for(int x=5;x<27;x++){int i=(y*w+x)*4;spatial[i]=(byte)(q>>>8);spatial[i+1]=(byte)q;}
  M9PreviewTc20Math1A.Result weighted=M9PreviewTc20Math1A.analyzePackedPanel(spatial,w,h,1,0);
  yes(weighted.weightedMedian>M9PreviewTc20Math1A.METER_TARGET,
      "centre-weighted median follows broad bright body");
  yes(weighted.boundedEv<0,"broad bright body predicts darkening");

  System.out.println("ASSERTIONS "+count);
 }
}
'''
(out/'PreviewTc20Test.java').write_text(source)
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out),
                str(HERE/'M9PreviewTc20Math1A.java'),str(out/'PreviewTc20Test.java')],check=True)
result=subprocess.check_output(['java','-ea','-cp',str(out),'PreviewTc20Test'],text=True)
assertions=int(result.strip().splitlines()[-1].split()[-1])
if assertions<15: raise SystemExit('too few assertions')

integration={}
if assembled is not None:
 shader=(assembled/'app/src/main/assets/shaders/preview/main_fs.glsl').read_text()
 main=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java').read_text()
 meter=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java').read_text()
 evidence=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java'
 math=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java'
 proof=json.loads((assembled/'M9PREVIEWTC20NEG1A_SOURCE_PROOF.json').read_text())
 if evidence.read_bytes()!=(HERE/'M9PreviewEvidence2E.java').read_bytes(): raise SystemExit('assembled evidence mismatch')
 if math.read_bytes()!=(HERE/'M9PreviewTc20Math1A.java').read_bytes(): raise SystemExit('assembled math mismatch')
 anchors=[
   'uniform float uM9PreviewTc20Gain1A;',
   'previewTc20Probe1A',
   'm9*=clamp(uM9PreviewTc20Gain1A,0.70710678,1.0);',
   'uM9EvidenceStage2E == 2',
   'PP_D50_TO_SRGB_D65',
 ]
 for a in anchors:
  if a not in shader: raise SystemExit('shader anchor missing '+a)
 if main.count('predictedTc20Gain(frame1W)')!=1: raise SystemExit('single live TC20 owner expected')
 if 'GLES30.glUniform1f(tc20Uniform,1.0f);' not in meter: raise SystemExit('Auto meter feedback isolation missing')
 frozen=[
  'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
  'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
  'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
  'app/src/main/cpp/m9color_jni.cpp',
 ]
 for rel in frozen:
  if proof['before'][rel]!=proof['after'][rel]: raise SystemExit('frozen photographic seam changed '+rel)
 integration={'candidate_exact':True,'auto_meter_forced_unity':True,'precurve_gain':True,
              'auto_capture_still_native_frozen':True}

receipt={'revision':'M9PREVIEWTC20NEG1A','assertions':assertions,
 'authority_ev':[-.5,0.0],'positive_prediction':False,
 'meter_target':0.107*(8192.0/10000.0),'integration':integration,'output':result}
(out.parent/'previewtc20neg1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result,end='')
print(json.dumps({k:v for k,v in receipt.items() if k!='output'}))
