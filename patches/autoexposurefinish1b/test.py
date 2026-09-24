"""Compile the actual AUTOEXPOSUREFINISH1B policy and exercise target placement/ownership."""
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
source=r"""
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
 static Stats[] ordinary(int median,int firstUnsafe){
  Stats[] s=new Stats[9];
  for(int i=0;i<9;i++) {
   double clip=i>=firstUnsafe?.10:0;
   s[i]=new Stats(median+5*i,.30,.004+Math.min(.01*i,.03),clip,
      median+5*i,.20,.004,median+5*i,.02);
  }
  return s;
 }
 static Stats[] dark(int start,int inc,double clipInc,double brightInc){
  Stats[] s=new Stats[9];
  for(int i=0;i<9;i++) {
   int med=start+inc*i;
   s[i]=new Stats(med,Math.max(.30,.82-.05*i),.002+brightInc*i,clipInc*i,
      med,Math.max(.30,.82-.05*i),.002,med,.01);
  }
  return s;
 }
 static Stats[] backlight(int cm,int cq,int cmInc,int cqInc,double clipInc,double brightInc,double outer160){
  Stats[] s=new Stats[9];
  for(int i=0;i<9;i++) {
   s[i]=new Stats(42+4*i,.45,.10+brightInc*i,.02+clipInc*i,
      cm+cmInc*i,Math.max(.20,.70-.05*i),.08,cq+cqInc*i,outer160);
  }
  return s;
 }
 static void publish(Stats[] s){now+=250000000L;M9AutoExposure2D.publish(new Sample("2","PHOTO",now,now,now,1,s));}
 static double decide(double legacy,double user,long shutter,int iso,boolean eligible){
  return M9AutoExposure2D.decide("2","PHOTO",now,1,user,shutter,iso,legacy,eligible).appliedEv;
 }
 static double fresh(Stats[] s,double legacy){M9AutoExposure2D.reset();publish(s);return decide(legacy,0,0,0,true);}
 public static void main(String[] args){
  yes(M9AutoExposure2D.STEPS==9,"nine rendered search steps");
  check(M9AutoExposure2D.ev(8),2.0,"positive search reaches two EV");

  check(M9AutoExposure2D.positiveHeadroomLimit(ordinary(100,1)),0,"ordinary first positive step unsafe");
  check(fresh(ordinary(100,1),.5),0,"ordinary clipping vetoes inherited positive Auto bias");
  check(fresh(ordinary(100,9),.5),.5,"safe ordinary inherited bias retained");
  check(fresh(ordinary(100,9),-.5),-.5,"negative baseline retained");
  M9AutoExposure2D.reset();check(decide(.5,0,0,0,true),0,"missing meter cannot justify positive assist");
  check(decide(-.5,0,0,0,true),-.5,"missing meter preserves negative baseline");

  M9AutoExposure2D.reset();publish(dark(20,8,0,0));check(decide(0,0,0,0,true),.25,"positive rise remains quarter stop");
  check(decide(0,0,0,0,true),.25,"reusing sample cannot ratchet exposure");
  publish(dark(20,8,0,0));check(decide(0,0,0,0,true),.5,"fresh sample permits next quarter stop");
  now+=1300000000L;check(decide(.5,0,0,0,true),0,"stale meter releases positive assist");
  fresh(ordinary(100,9),.5);publish(ordinary(100,1));check(decide(.75,.25,0,0,false),.5,"explicit user EV retains displayed Auto baseline");
  check(decide(.75,0,1000000,0,true),0,"manual shutter disables automatic assist");
  check(decide(.75,0,0,200,true),0,"manual ISO disables automatic assist");
  M9AutoExposure2D.reset();publish(dark(20,8,0,0));
  check(M9AutoExposure2D.decide("other","PHOTO",now,1,0,0,0,.5,true).appliedEv,0,"foreign camera sample cannot justify bias");
  Stats[] invalid=ordinary(100,9);invalid[3]=new Stats(20,Double.NaN,0,0);
  check(fresh(invalid,.5),0,"invalid bracket cannot justify positive bias");
  M9AutoExposure2D.reset();publish(dark(20,8,0,0));check(decide(.5,0,0,0,false),0,"ineligible Auto cannot use rendered placement");

  Stats[] dark125=dark(20,8,0,0);
  yes(M9AutoExposure2D.select(dark125)==5,"dark scene selects first low-key target at 1.25 EV");
  Stats[] darkMax=dark(10,6,0,0);
  yes(M9AutoExposure2D.select(darkMax)==8,"very dark scene uses full two-EV search when target remains unmet");
  Stats[] darkLamp=dark(8,7,.025,.03);
  yes(M9AutoExposure2D.positiveHeadroomLimit(darkLamp)==0,"strict ordinary guard rejects dark scene lamp growth");
  yes(M9AutoExposure2D.backlightHeadroomLimit(darkLamp)>=1.0,"severe-dark path permits bounded lamp sacrifice");
  yes(M9AutoExposure2D.select(darkLamp)>=4,"severe-dark scene can brighten beyond half stop");
  Stats[] darkDestructive=dark(8,7,.10,.12);
  yes(M9AutoExposure2D.backlightHeadroomLimit(darkDestructive)<=.5,"severe-dark background-loss budget remains bounded");

  Stats[] back=backlight(20,10,8,5,.04,.05,.25);
  yes(M9AutoExposure2D.positiveHeadroomLimit(back)==0,"strict guard rejects first backlight step");
  yes(M9AutoExposure2D.selectBacklight(back)==5,"backlight rendered target selects 1.25 EV");
  check(M9AutoExposure2D.backlightHeadroomLimit(back),1.25,"backlight loss budget supports target step");
  M9AutoExposure2D.reset();publish(back);
  check(decide(0,0,0,0,true),.25,"backlight target begins with quarter-stop slew");
  for(int i=0;i<4;i++){publish(back);decide(0,0,0,0,true);}
  check(decide(0,0,0,0,true),1.25,"backlight converges beyond old half-stop ceiling");
  check(decide(0,0,0,0,true),1.25,"reused backlight sample cannot ratchet");
  check(fresh(back,.75),1.0,"positive MFM baseline survives relaxed backlight headroom and slews upward");

  Stats[] blueSky=backlight(24,12,7,4,.025,.03,.01);
  for(int i=0;i<9;i++) blueSky[i]=new Stats(35+4*i,.60,.02+.025*i,.005+.02*i,
      24+7*i,.62,.005,12+4*i,.06);
  yes(M9AutoExposure2D.selectBacklight(blueSky)>0,"mid-bright surround at 160 code can qualify before near-white");
  Stats[] noSurround=backlight(20,10,8,5,.02,.02,.0);
  yes(M9AutoExposure2D.selectBacklight(noSurround)==0,"dark centre without bright surround is not backlight");
  Stats[] healthy=backlight(72,45,2,1,.01,.01,.25);
  yes(M9AutoExposure2D.selectBacklight(healthy)==0,"healthy centre receives no backlight lift");

  Stats[] hardCeiling=backlight(50,5,6,0,.015,.02,.25);
  yes(M9AutoExposure2D.selectBacklight(hardCeiling)<=4,"hard centre ceiling prevents chasing intrinsically black lower quartile");
  Stats[] severeBack=backlight(8,4,7,4,.02,.025,.30);
  yes(M9AutoExposure2D.selectBacklight(severeBack)>=6,"severe backlight can request at least 1.5 EV");
  Stats[] destructive=backlight(20,10,8,5,.11,.12,.25);
  yes(M9AutoExposure2D.backlightHeadroomLimit(destructive)<=.5,"catastrophic background loss still blocks large assist");

  ByteBuffer rgba=ByteBuffer.allocate(M9AutoExposure2D.WIDTH*M9AutoExposure2D.HEIGHT*M9AutoExposure2D.STEPS*4);
  for(int y=0;y<M9AutoExposure2D.HEIGHT;y++)for(int step=0;step<M9AutoExposure2D.STEPS;step++)
   for(int x=0;x<M9AutoExposure2D.WIDTH;x++){
    boolean c=x>=8&&x<24&&y>=6&&y<18;
    int v=c?(x<12?20:40):180;
    int at=4*(y*M9AutoExposure2D.WIDTH*M9AutoExposure2D.STEPS+step*M9AutoExposure2D.WIDTH+x);
    rgba.put(at,(byte)v);rgba.put(at+1,(byte)v);rgba.put(at+2,(byte)v);rgba.put(at+3,(byte)255);
   }
  Stats measured=M9AutoExposure2D.measure(rgba)[0];
  check(measured.centerMedian,40,"meter records centre median");
  check(measured.centerQ25,20,"meter records centre lower quartile");
  check(measured.outerBright160,1.0,"meter records 160-code bright surround");
  check(measured.outerBright,0.0,"160-code surround is not mislabeled near-white");

  System.out.println("ASSERTIONS "+count);
 }
}
"""
(build/'PolicyTest.java').write_text(source)
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(build),
                str(HERE/'M9AutoExposure2D.java'),str(build/'PolicyTest.java'),
                *[str(build/p) for p in stubs]],check=True)
result=subprocess.check_output(['java','-ea','-cp',str(build),'PolicyTest'],text=True)
assertions=int(result.strip().splitlines()[-1].split()[-1])
if assertions < 35: raise SystemExit(f'expected at least 35 assertions, got {assertions}')
integration={}
if assembled is not None:
 target=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
 if target.read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes(): raise SystemExit('assembled Auto policy mismatch')
 integration={'assembled_candidate_exact':True}
receipt={'revision':'M9AUTOEXPOSUREFINISH1B_TARGETPLACEMENT','assertions':assertions,
         'positive_search_max_ev':2.0,'scene_target_median_code':60,
         'backlight_target_center_median_code':60,'backlight_target_center_q25_code':30,
         'ordinary_highlight_budget_preserved':True,'integration':integration,'output':result}
(build.parent/'autoexposurefinish1b_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result,end='')
print(json.dumps({k:v for k,v in receipt.items() if k!='output'}))
