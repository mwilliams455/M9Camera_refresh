"""Compile the actual AUTOEXPOSUREFINISH1A policy and exercise backlight/ownership state."""
from pathlib import Path
import json, subprocess, sys

HERE=Path(__file__).resolve().parent
build=Path(sys.argv[1]).resolve();build.mkdir(parents=True,exist_ok=True)
assembled=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
stubs={
 'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
 'org/json/JSONObject.java':'package org.json; public class JSONObject { public JSONObject put(String k,Object v) throws JSONException{return this;} public String toString(){return "{}";} }',
 'org/json/JSONArray.java':'package org.json; public class JSONArray { public JSONArray put(Object v){return this;} }',
}
for name,s in stubs.items():
 p=build/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)

source=r'''
import java.nio.ByteBuffer;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public class PolicyTest {
 static int count=0;static long now=1000000000L;
 static void check(double value,double expected,String message){
  if(Math.abs(value-expected)>1e-12)throw new AssertionError(message+": "+value+" != "+expected);
  count++;System.out.println("PASS "+message);
 }
 static void yes(boolean value,String message){if(!value)throw new AssertionError(message);count++;System.out.println("PASS "+message);}
 static Stats[] scene(int median,int firstUnsafe){
  Stats[] s=new Stats[7];
  for(int i=0;i<7;i++)s[i]=new Stats(median+5*i,.82,.004,i>=firstUnsafe?.1:0);
  return s;
 }
 static Stats[] backlight(double outerBright,int firstUnsafe,int centerBase){
  Stats[] s=new Stats[7];
  for(int i=0;i<7;i++) {
   double clip=i>=firstUnsafe?.10:0;
   s[i]=new Stats(45+4*i,.45,.15+Math.min(.015*i,.03),clip,
       centerBase+8*i,Math.max(.30,.78-.08*i),outerBright);
  }
  return s;
 }
 static void publish(Stats[] s){now+=250000000L;M9AutoExposure2D.publish(new Sample("2","PHOTO",now,now,now,1,s));}
 static double decide(double legacy,double user,long shutter,int iso,boolean eligible){return M9AutoExposure2D.decide("2","PHOTO",now,1,user,shutter,iso,legacy,eligible).appliedEv;}
 static double fresh(Stats[] s,double legacy){M9AutoExposure2D.reset();publish(s);return decide(legacy,0,0,0,true);}
 public static void main(String[] args){
  check(M9AutoExposure2D.positiveHeadroomLimit(scene(12,1)),0,"first positive step unsafe");
  check(fresh(scene(12,1),.5),0,"clipping vetoes inherited positive Auto bias");
  check(fresh(scene(100,1),.5),0,"bright scene still vetoes unsafe inherited bias");
  check(fresh(scene(100,7),.5),.5,"safe inherited bias retained without shadow lift");
  check(fresh(scene(12,2),.75),.25,"total bias limited to last safe bracket");
  check(fresh(scene(12,1),-.5),-.5,"negative baseline retained");
  M9AutoExposure2D.reset();check(decide(.5,0,0,0,true),0,"missing meter cannot justify positive assist");
  check(decide(-.5,0,0,0,true),-.5,"missing meter preserves negative baseline");
  fresh(scene(12,7),0);now+=1300000000L;check(decide(.5,0,0,0,true),0,"stale meter releases positive assist");
  M9AutoExposure2D.reset();publish(scene(12,7));check(decide(0,0,0,0,true),.25,"positive rise remains quarter stop");
  check(decide(0,0,0,0,true),.25,"reusing sample cannot ratchet exposure");
  publish(scene(12,7));check(decide(0,0,0,0,true),.5,"fresh sample permits next quarter stop");
  publish(scene(12,1));check(decide(.75,0,0,0,true),0,"unsafe scene releases previous lift immediately");
  fresh(scene(100,7),.5);publish(scene(12,1));check(decide(.75,.25,0,0,false),.5,"explicit user EV retains displayed Auto baseline");
  check(decide(.75,0,1000000,0,true),0,"manual shutter disables automatic assist");
  check(decide(.75,0,0,200,true),0,"manual ISO disables automatic assist");
  M9AutoExposure2D.reset();publish(scene(12,7));
  check(M9AutoExposure2D.decide("other","PHOTO",now,1,0,0,0,.5,true).appliedEv,0,"foreign camera sample cannot justify bias");
  Stats[] invalid=scene(12,7);invalid[3]=new Stats(20,Double.NaN,0,0);
  check(fresh(invalid,.5),0,"invalid bracket cannot justify positive bias");
  Stats[] brightness=scene(12,7);brightness[1]=new Stats(17,.8,.05,0);
  check(fresh(brightness,.5),0,"broad-brightening budget also caps inherited bias");
  Stats[] bounded=scene(12,3);
  check(fresh(bounded,0),.25,"safe half-stop bracket initial slew");
  publish(bounded);check(decide(0,0,0,0,true),.5,"safe half-stop bracket final selection");

  Stats[] back=backlight(.20,7,24);
  yes(M9AutoExposure2D.select(back)==0,"backlight fixture bypasses old global-shadow gate");
  yes(M9AutoExposure2D.selectBacklight(back)==2,"backlight selector finds half-stop subject lift");
  M9AutoExposure2D.reset();publish(back);
  check(decide(0,0,0,0,true),.25,"backlight subject lift slews by quarter stop");
  publish(back);check(decide(0,0,0,0,true),.5,"backlight subject lift reaches bounded half stop");
  check(decide(0,0,0,0,true),.5,"backlight repeated sample cannot ratchet");

  check(fresh(backlight(.01,7,24),0),0,"dark center without bright surround is not backlight assist");
  check(fresh(backlight(.20,7,56),0),0,"healthy center is not lifted by backlight assist");
  check(fresh(backlight(.20,1,24),0),0,"highlight budget vetoes backlight assist");
  M9AutoExposure2D.reset();publish(back);
  check(decide(.5,0,0,0,false),0,"tripod or otherwise ineligible Auto cannot use rendered assist");

  ByteBuffer rgba=ByteBuffer.allocate(M9AutoExposure2D.WIDTH*M9AutoExposure2D.HEIGHT*M9AutoExposure2D.STEPS*4);
  for(int y=0;y<M9AutoExposure2D.HEIGHT;y++)for(int step=0;step<M9AutoExposure2D.STEPS;step++)
   for(int x=0;x<M9AutoExposure2D.WIDTH;x++){
    boolean c=x>=8&&x<24&&y>=6&&y<18;int v=c?20:230;
    int at=4*(y*M9AutoExposure2D.WIDTH*M9AutoExposure2D.STEPS+step*M9AutoExposure2D.WIDTH+x);
    rgba.put(at,(byte)v);rgba.put(at+1,(byte)v);rgba.put(at+2,(byte)v);rgba.put(at+3,(byte)255);
   }
  Stats measured=M9AutoExposure2D.measure(rgba)[0];
  check(measured.centerMedian,20,"meter records center median");
  check(measured.centerDark,1.0,"meter records center dark fraction");
  check(measured.outerBright,1.0,"meter records bright surround fraction");
  System.out.println("ASSERTIONS "+count);
 }
}
'''
(build/'PolicyTest.java').write_text(source)
sources=[str(HERE/'M9AutoExposure2D.java'),str(build/'PolicyTest.java'),*[str(build/p) for p in stubs]]
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(build),*sources],check=True)
result=subprocess.check_output(['java','-ea','-cp',str(build),'PolicyTest'],text=True)
assertions=int(result.strip().splitlines()[-1].split()[-1])
if assertions != 33: raise SystemExit(f'expected 33 assertions, got {assertions}')

integration={}
if assembled is not None:
 target=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
 iso=assembled/'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
 if target.read_bytes() != (HERE/'M9AutoExposure2D.java').read_bytes():
  raise SystemExit('assembled Auto policy does not match candidate')
 text=iso.read_text()
 anchor='manualExposure, manualIso, feedback.appliedEv, eligible);'
 if text.count(anchor)!=1: raise SystemExit('assembled eligibility join missing or duplicated')
 integration={'assembled_candidate_exact':True,'eligibility_join_exact':True}

receipt={'revision':'M9AUTOEXPOSUREFINISH1A_BACKLIGHT','assertions':assertions,
         'backlight_assist_cap_ev':0.5,'existing_positive_headroom_budget_preserved':True,
         'integration':integration,'output':result}
(build.parent/'autoexposurefinish1a_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result,end='')
print(json.dumps({k:v for k,v in receipt.items() if k!='output'}))
