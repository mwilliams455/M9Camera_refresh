"""Test M9PREVIEWTC20NEUTRAL1A math and assembled-source isolation."""
from pathlib import Path
import json,subprocess,sys
HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
assembled=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None

source=r'''
import com.particlesdevs.photoncamera.m9.preview.M9PreviewTc20Math1A;
public class PreviewTc20NeutralTest {
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

  M9PreviewTc20Math1A.Result bright=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET*2,w,h),w,h,1,0);
  near(bright.boundedEv,-.5,.003,"two-times target bounded at minus half EV");

  M9PreviewTc20Math1A.Result dark=M9PreviewTc20Math1A.analyzePackedPanel(
      uniform(M9PreviewTc20Math1A.METER_TARGET*.5,w,h),w,h,1,0);
  near(dark.boundedEv,0,.003,"positive TC20 lift not predicted");

  near(M9PreviewTc20Math1A.slewEv(0,-.5),-.125,1e-12,"first darkening is one eighth stop");
  near(M9PreviewTc20Math1A.slewEv(-.125,-.5),-.25,1e-12,"second darkening reaches quarter stop");
  near(M9PreviewTc20Math1A.slewEv(-.5,0),-.375,1e-12,"release is one eighth stop");
  near(M9PreviewTc20Math1A.slewEv(-.1,-.075),-.1,1e-12,"small target movement stays inside deadband");
  near(M9PreviewTc20Math1A.slewEv(-.1,-.04),-.04,1e-12,"movement outside deadband can settle directly");
  yes(M9PreviewTc20Math1A.MAX_SLEW_EV==.125,"slew constant is one eighth EV");
  yes(M9PreviewTc20Math1A.DEADBAND_EV==.04,"deadband constant retained");

  byte[] spatial=uniform(M9PreviewTc20Math1A.METER_TARGET*.5,w,h);
  int q=(int)Math.round(M9PreviewTc20Math1A.METER_TARGET*2*65535);
  for(int y=4;y<20;y++)for(int x=5;x<27;x++){int i=(y*w+x)*4;spatial[i]=(byte)(q>>>8);spatial[i+1]=(byte)q;}
  M9PreviewTc20Math1A.Result weighted=M9PreviewTc20Math1A.analyzePackedPanel(spatial,w,h,1,0);
  yes(weighted.weightedMedian>M9PreviewTc20Math1A.METER_TARGET,"centre weighting retained");
  yes(weighted.boundedEv<0,"bright centre still predicts darkening");

  System.out.println("ASSERTIONS "+count);
 }
}
'''
(out/'PreviewTc20NeutralTest.java').write_text(source)
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out),
                str(HERE/'M9PreviewTc20Math1A.java'),str(out/'PreviewTc20NeutralTest.java')],check=True)
result=subprocess.check_output(['java','-ea','-cp',str(out),'PreviewTc20NeutralTest'],text=True)
assertions=int(result.strip().splitlines()[-1].split()[-1])
if assertions!=13: raise SystemExit(f'expected 13 assertions, got {assertions}')

integration={}
if assembled is not None:
 e=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java'
 m=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java'
 if e.read_bytes()!=(HERE/'M9PreviewEvidence2E.java').read_bytes(): raise SystemExit('assembled evidence mismatch')
 if m.read_bytes()!=(HERE/'M9PreviewTc20Math1A.java').read_bytes(): raise SystemExit('assembled math mismatch')
 text=e.read_text()
 if '(i==1||i==TC20_PANEL)?referenceScale:frame.exposureScale' not in text:
  raise SystemExit('TC20 probe is not neutral-reference')
 if 'i==1?referenceScale:frame.exposureScale' in text:
  raise SystemExit('old display-intent TC20 probe survived')
 proof=json.loads((assembled/'M9PREVIEWTC20NEUTRAL1A_SOURCE_PROOF.json').read_text())
 frozen=[
  'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
  'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
  'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
  'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
  'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
  'app/src/main/assets/shaders/preview/main_fs.glsl',
 ]
 for rel in frozen:
  if proof['before'][rel]!=proof['after'][rel]: raise SystemExit('frozen seam changed '+rel)
 integration={'candidate_exact':True,'neutral_reference_probe':True,
              'display_intent_decoupled':True,'capture_auto_still_shader_frozen':True}

receipt={'revision':'M9PREVIEWTC20NEUTRAL1A','assertions':assertions,
 'tc20_domain':'neutral_reference','max_slew_ev_per_sample':.125,'deadband_ev':.04,
 'integration':integration,'output':result}
(out.parent/'previewtc20neutral1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result,end='')
print(json.dumps({k:v for k,v in receipt.items() if k!='output'}))
