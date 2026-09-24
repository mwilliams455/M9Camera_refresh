"""Compile AUTOEXPOSUREFINISH1B and exercise target placement, night key and ownership."""
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
 static void yes(boolean value,String message){
  if(!value)throw new AssertionError(message);count++;System.out.println("PASS "+message);
 }
 static Stats stat(int med,int cm,int cq,int oq,double dark,double bright,double clip,
                   double cd,double ob,double cb,double cc,double oc){
  return new Stats(med,dark,bright,clip,cm,cq,oq,cd,ob,cb,cc,oc);
 }
 static Stats[] ordinary(int median,int firstUnsafe){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++){
   double clip=i>=firstUnsafe?.10:0;
   s[i]=stat(median+4*i,median+4*i,Math.max(0,median-12+4*i),Math.min(255,median+35+4*i),
      .20,.004+Math.min(.008*i,.03),clip,.10,.004,.002,0,clip);
  }
  return s;
 }
 static Stats[] dark(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(12+5*i,18+6*i,6+4*i,26+5*i,
      Math.max(.25,.82-.055*i),.003+.006*i,.001+.003*i,
      Math.max(.20,.78-.05*i),.004+.004*i,.002+.002*i,.001+.001*i,.001+.004*i);
  return s;
 }
 static Stats[] veryDark(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(5+3*i,10+4*i,3+2*i,20+4*i,
      Math.max(.40,.90-.04*i),.002+.002*i,.001,
      Math.max(.35,.88-.04*i),.003+.002*i,.001+.001*i,.001,.001+.002*i);
  return s;
 }
 static Stats[] night(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(30+5*i,66+5*i,44+4*i,92+7*i,
      Math.max(.15,.50-.04*i),.025+.01*i,.004+.004*i,
      Math.max(.05,.18-.015*i),.03+.008*i,.02+.008*i,.003+.002*i,.004+.005*i);
  return s;
 }
 static Stats[] backlight(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(38+4*i,22+6*i,10+4*i,220+2*i,
      Math.max(.25,.62-.035*i),.12+.035*i,.10+.025*i,
      Math.max(.15,.72-.045*i),.15+.04*i,.02+.005*i,.002+.001*i,.05+.03*i);
  return s;
 }
 static Stats[] moderateBacklight(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(40+4*i,42+6*i,28+3*i,205+3*i,
      Math.max(.20,.52-.03*i),.09+.03*i,.05+.02*i,
      Math.max(.10,.38-.025*i),.10+.035*i,.015+.004*i,.002+.001*i,.04+.025*i);
  return s;
 }
 static Stats[] destructiveBackground(){
  Stats[] s=backlight();
  for(int i=1;i<11;i++)s[i]=stat(38+4*i,22+6*i,10+4*i,225,
      .55,.20+.05*i,.12+.07*i,.50,.20+.05*i,.02,.003,.05+.10*i);
  return s;
 }
 static Stats[] destructiveCenter(){
  Stats[] s=backlight();
  for(int i=1;i<11;i++)s[i]=stat(38+4*i,22+6*i,10+4*i,225,
      .55,.15,.12,.50,.18,.03+.03*i,.025+.02*i,.10);
  return s;
 }
 static Stats[] noBacklight(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(55+3*i,38+4*i,20+3*i,45+3*i,
      .30,.01,.002,.30,.005,.003,.001,.002);
  return s;
 }
 static void publish(Stats[] s){
  now+=250000000L;M9AutoExposure2D.publish(new Sample("2","PHOTO",now,now,now,1,s));
 }
 static double decide(double legacy,double user,long shutter,int iso,boolean eligible){
  return M9AutoExposure2D.decide("2","PHOTO",now,1,user,shutter,iso,legacy,eligible).appliedEv;
 }
 static double fresh(Stats[] s,double legacy){
  M9AutoExposure2D.reset();publish(s);return decide(legacy,0,0,0,true);
 }

 public static void main(String[] args){
  yes(M9AutoExposure2D.STEPS==11,"eleven rendered search steps");
  check(M9AutoExposure2D.ev(10),2.5,"positive search reaches 2.5 EV");

  check(M9AutoExposure2D.positiveHeadroomLimit(ordinary(100,1)),0,"ordinary first positive step unsafe");
  check(fresh(ordinary(100,1),.5),0,"ordinary clipping vetoes inherited positive Auto bias");
  check(fresh(ordinary(100,11),.5),.5,"safe ordinary inherited bias retained");
  check(fresh(ordinary(100,11),-.5),-.5,"negative baseline retained");
  M9AutoExposure2D.reset();check(decide(.5,0,0,0,true),0,"missing meter cannot justify positive assist");
  check(decide(-.5,0,0,0,true),-.5,"missing meter preserves negative baseline");

  M9AutoExposure2D.reset();publish(dark());check(decide(0,0,0,0,true),.25,"positive rise remains quarter stop");
  check(decide(0,0,0,0,true),.25,"reusing sample cannot ratchet exposure");
  publish(dark());check(decide(0,0,0,0,true),.5,"fresh sample permits next quarter stop");
  now+=1300000000L;check(decide(.5,0,0,0,true),0,"stale meter releases positive assist");
  fresh(ordinary(100,11),.5);publish(ordinary(100,1));
  check(decide(.75,.25,0,0,false),.5,"explicit user EV retains displayed Auto baseline");
  check(decide(.75,0,1000000,0,true),0,"manual shutter disables automatic assist");
  check(decide(.75,0,0,200,true),0,"manual ISO disables automatic assist");
  M9AutoExposure2D.reset();publish(dark());
  check(M9AutoExposure2D.decide("other","PHOTO",now,1,0,0,0,.5,true).appliedEv,0,
        "foreign camera sample cannot justify bias");
  Stats[] invalid=ordinary(100,11);invalid[3]=new Stats(20,Double.NaN,0,0);
  check(fresh(invalid,.5),0,"invalid bracket cannot justify positive bias");
  M9AutoExposure2D.reset();publish(dark());
  check(decide(.5,0,0,0,false),0,"ineligible Auto cannot use rendered placement");

  int darkStep=M9AutoExposure2D.selectSceneKey(dark());
  yes(darkStep>=6,"genuinely dark scene can request more than 1.25 EV");
  yes(darkStep<11,"dark scene selection remains within rendered search");
  yes(M9AutoExposure2D.selectSceneKey(veryDark())==10,
      "extremely dark scene uses full 2.5-EV search when target remains unmet");

  yes(M9AutoExposure2D.selectSceneKey(night())==0,
      "low-key night-like scene with adequate central body is not globally lifted");
  yes(M9AutoExposure2D.selectBacklight(night())==0,
      "adequately placed low-key night body is not misclassified as backlight");
  check(fresh(night(),0),0,"acceptable low-key night scene stays at neutral Auto");

  Stats[] back=backlight();
  yes(M9AutoExposure2D.positiveHeadroomLimit(back)==0,
      "ordinary strict guard rejects first severe-backlight step");
  yes(M9AutoExposure2D.backlightHeadroomLimit(back)>=1.5,
      "backlight-specific headroom permits substantial background sacrifice");
  int backStep=M9AutoExposure2D.selectBacklight(back);
  yes(backStep>=6,"severe backlight can request at least 1.5 EV");
  M9AutoExposure2D.reset();publish(back);
  check(decide(0,0,0,0,true),.25,"backlight target starts with quarter-stop slew");
  double v=.25;
  for(int i=0;i<8;i++){publish(back);v=decide(0,0,0,0,true);}
  yes(v>.5,"backlight converges beyond old half-stop ceiling");
  yes(v<=M9AutoExposure2D.ev(backStep),"backlight never exceeds rendered target");

  int moderate=M9AutoExposure2D.selectBacklight(moderateBacklight());
  yes(moderate>0&&moderate<backStep,"moderate backlight chooses less exposure than severe backlight");
  yes(M9AutoExposure2D.selectBacklight(noBacklight())==0,
      "dark central object without bright surround is not backlight");
  yes(M9AutoExposure2D.backlightHeadroomLimit(destructiveBackground())<=.75,
      "destructive background loss bounds backlight exposure");
  yes(M9AutoExposure2D.backlightHeadroomLimit(destructiveCenter())==0,
      "central subject clipping vetoes backlight exposure immediately");

  ByteBuffer rgba=ByteBuffer.allocate(
      M9AutoExposure2D.WIDTH*M9AutoExposure2D.HEIGHT*M9AutoExposure2D.STEPS*4);
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
  check(measured.outerQ90,180,"meter records surround upper-tail luminance");
  check(measured.outerBright,0,"180-code surround is not mislabeled near-white");
  check(measured.centerClipped,0,"meter records central clipping separately");
  check(measured.outerClipped,0,"meter records surround clipping separately");

  System.out.println("ASSERTIONS "+count);
 }
}
'''
(build/'PolicyTest.java').write_text(source)
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(build),
                str(HERE/'M9AutoExposure2D.java'),str(build/'PolicyTest.java'),
                *[str(build/p) for p in stubs]],check=True)
result=subprocess.check_output(['java','-ea','-cp',str(build),'PolicyTest'],text=True)
assertions=int(result.strip().splitlines()[-1].split()[-1])
if assertions < 34: raise SystemExit(f'expected at least 34 assertions, got {assertions}')

integration={}
if assembled is not None:
 target=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
 if target.read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
  raise SystemExit('assembled Auto policy mismatch')
 integration={'assembled_candidate_exact':True}

receipt={
 'revision':'M9AUTOEXPOSUREFINISH1B_SCENEKEY',
 'assertions':assertions,
 'positive_search_max_ev':2.5,
 'scene_median_target_code':46,
 'scene_center_target_code':54,
 'scene_center_q25_target_code':22,
 'backlight_center_target_code':56,
 'backlight_center_q25_target_code':22,
 'ordinary_highlight_budget_preserved':True,
 'backlight_background_loss_center_protected':True,
 'low_key_night_body_protection':True,
 'integration':integration,
 'output':result,
}
(build.parent/'autoexposurefinish1b_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result,end='')
print(json.dumps({k:v for k,v in receipt.items() if k!='output'}))
