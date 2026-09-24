"""Compile AUTOEXPOSUREFINISH1I and exercise SAFE075 acquisition plus inherited 1H policy."""
from pathlib import Path
import json, subprocess, sys
HERE=Path(__file__).resolve().parent
build=Path(sys.argv[1]).resolve();build.mkdir(parents=True,exist_ok=True)
assembled=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None

stubs={
 'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
 'org/json/JSONObject.java':'package org.json; public class JSONObject { public static final Object NULL=new Object(); public JSONObject put(String k,Object v) throws JSONException{return this;} public String toString(){return "{}";} }',
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
 static Stats gridStat(int med,int cm,int cq,int oq,double dark,double bright,double clip,
                   double cd,double ob,double cb,double cc,double oc,
                   int[] fm,int[] fq25,int[] fq90,double[] fb,double[] fc){
  return new Stats(med,dark,bright,clip,cm,cq,oq,cd,ob,cb,cc,oc,fm,fq25,fq90,fb,fc);
 }
 static int[] ints(int v){int[] a=new int[24];for(int i=0;i<a.length;i++)a[i]=v;return a;}
 static double[] doubles(double v){double[] a=new double[24];for(int i=0;i<a.length;i++)a[i]=v;return a;}
 static void fields(int[] fm,int[] fq,int[] fh,double[] fb,double[] fc,int[] which,
                    int med,int low,int hi,double bright,double clip){
  for(int f:which){fm[f]=med;fq[f]=low;fh[f]=hi;fb[f]=bright;fc[f]=clip;}
 }
 static Stats[] offCenterBody(){
  Stats[] s=new Stats[11];int[] body={6,7,12,13};
  for(int i=0;i<11;i++){
   int[] fm=ints(Math.min(250,160+2*i)),fq=ints(Math.min(240,125+2*i)),fh=ints(Math.min(255,240+2*i));
   double[] fb=doubles(Math.min(.80,.15+.02*i)),fc=doubles(Math.min(.65,.06+.015*i));
   fields(fm,fq,fh,fb,fc,body,22+5*i,7+3*i,45+7*i,.004+.002*i,.003+.002*i);
   s[i]=gridStat(70+3*i,100+2*i,70+2*i,245,.35,.14+.015*i,.06+.012*i,
       .15,.16,.08,.04,.08,fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] offCenterBodyShifted(){
  Stats[] s=new Stats[11];int[] body={7,8,13,14};
  for(int i=0;i<11;i++){
   int[] fm=ints(Math.min(250,164+2*i)),fq=ints(Math.min(240,128+2*i)),fh=ints(Math.min(255,240+2*i));
   double[] fb=doubles(Math.min(.80,.15+.02*i)),fc=doubles(Math.min(.65,.06+.015*i));
   fields(fm,fq,fh,fb,fc,body,30+5*i,12+3*i,52+7*i,.004+.002*i,.003+.002*i);
   s[i]=gridStat(73+3*i,102+2*i,72+2*i,245,.33,.14+.015*i,.06+.012*i,
       .14,.16,.08,.04,.08,fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] disjointNewBody(){
  Stats[] s=new Stats[11];int[] body={16,17,22,23};
  for(int i=0;i<11;i++){
   int[] fm=ints(Math.min(250,172+2*i)),fq=ints(Math.min(240,135+2*i)),fh=ints(Math.min(255,242+2*i));
   double[] fb=doubles(Math.min(.82,.17+.02*i)),fc=doubles(Math.min(.66,.06+.015*i));
   fields(fm,fq,fh,fb,fc,body,20+5*i,6+3*i,44+7*i,.003+.002*i,.002+.002*i);
   s[i]=gridStat(74+3*i,104+2*i,74+2*i,246,.34,.15+.015*i,.06+.012*i,
       .14,.17,.08,.04,.08,fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] openAnchorWithDarkMaterial(){
  Stats[] s=new Stats[11];int[] dark={6,12,18,19,20};int[] anchor={2,3,8,9,14,15};
  for(int i=0;i<11;i++){
   int[] fm=ints(125+2*i),fq=ints(78+2*i),fh=ints(185+2*i);
   double[] fb=doubles(.02),fc=doubles(.002);
   fields(fm,fq,fh,fb,fc,dark,24+4*i,10+3*i,58+5*i,.001,.001);
   fields(fm,fq,fh,fb,fc,anchor,155+2*i,92+2*i,220+Math.min(i,3),.07,.002);
   s[i]=gridStat(92+2*i,160+2*i,80+2*i,220+Math.min(i,4),.27,.035,.004,
       .10,.04,.03,.002,.004,fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] openAnchorSevereBacklight(){
  Stats[] s=new Stats[11];
  int[] dark={12,18,19,20};int[] anchor={2,3,8,9};int[] window={4,5,10,11,16,17};
  for(int i=0;i<11;i++){
   int[] fm=ints(110+2*i),fq=ints(70+2*i),fh=ints(160+2*i);
   double[] fb=doubles(.01),fc=doubles(.001);
   fields(fm,fq,fh,fb,fc,dark,20+4*i,7+3*i,48+5*i,.001,.001);
   fields(fm,fq,fh,fb,fc,anchor,145+2*i,88+2*i,214+Math.min(i,3),.06,.002);
   fields(fm,fq,fh,fb,fc,window,238+Math.min(2*i,12),210+Math.min(2*i,12),255,
       Math.min(.92,.72+.015*i),Math.min(.70,.38+.018*i));
   s[i]=gridStat(70+3*i,48+5*i,16+3*i,252,
       Math.max(.20,.48-.025*i),.14+.014*i,.075+.010*i,
       Math.max(.18,.46-.025*i),.22+.012*i,.08+.010*i,.03+.006*i,.10+.010*i,
       fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] centralWindowGrid(){
  Stats[] s=new Stats[11];int[] body={12,13,14,15,16};
  for(int i=0;i<11;i++){
   int[] fm=ints(Math.min(252,185+3*i)),fq=ints(Math.min(245,145+3*i)),fh=ints(250);
   double[] fb=doubles(Math.min(.85,.22+.025*i)),fc=doubles(Math.min(.72,.18+.02*i));
   fields(fm,fq,fh,fb,fc,body,22+5*i,6+3*i,40+6*i,.003+.002*i,.002+.001*i);
   s[i]=gridStat(25+3*i,26+5*i,8+3*i,246,Math.max(.30,.58-.025*i),
       .16+.012*i,.11+.012*i,.55,.22,.17,.15+.006*i,.10+.014*i,fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] isolatedEdgeShadowGrid(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++){
   int[] fm=ints(125),fq=ints(90),fh=ints(190);double[] fb=doubles(.04),fc=doubles(.01);
   fields(fm,fq,fh,fb,fc,new int[]{23},12+3*i,5+2*i,45+3*i,0,0);
   s[i]=gridStat(112,120,88,195,.12,.04,.01,.08,.04,.02,.01,.01,fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] highKeyDarkPatchGrid(){
  Stats[] s=new Stats[11];int[] body={16,17,22,23};
  for(int i=0;i<11;i++){
   int[] fm=ints(238),fq=ints(220),fh=ints(255);double[] fb=doubles(.60),fc=doubles(.35);
   fields(fm,fq,fh,fb,fc,body,35+3*i,20+2*i,70+4*i,0,0);
   s[i]=gridStat(135,150,80,250,.10,.30,.20,.08,.35,.20,.10,.22,fm,fq,fh,fb,fc);
  }return s;
 }
 static Stats[] lowKeyGrid(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++){
   int[] fm=ints(34+2*i),fq=ints(22+2*i),fh=ints(70+3*i);double[] fb=doubles(.01),fc=doubles(0);
   fields(fm,fq,fh,fb,fc,new int[]{10,11},80+2*i,55+2*i,220,.05,.02);
   s[i]=gridStat(30+3*i,66+3*i,44+2*i,100+4*i,.48,.025+.005*i,.004,
       .16,.03,.02,.003,.004,fm,fq,fh,fb,fc);
  }return s;
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
      Math.max(.25,.82-.055*i),.003+.004*i,.001+.001*i,
      Math.max(.20,.78-.05*i),.004+.004*i,.002+.002*i,.001+.001*i,.001+.004*i);
  return s;
 }
 static Stats[] darkLamp(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(10+5*i,16+6*i,5+4*i,35+6*i,
      Math.max(.25,.84-.05*i),.015+.018*i,.02+.025*i,
      Math.max(.20,.80-.05*i),.02+.015*i,.01+.012*i,.01+.012*i,.03+.025*i);
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
      .55,.15,.12,.50,.18,.35,.20+.02*i,.10);
  return s;
 }
 static Stats[] m9CharacterLoss(){
  Stats[] s=backlight();
  for(int i=1;i<11;i++)s[i]=stat(38+4*i,22+6*i,10+4*i,220+2*i,
      Math.max(.25,.62-.035*i),.12+.025*i,.10+.015*i,
      Math.max(.15,.72-.045*i),.15+.025*i,.08+.015*i,.015+.012*i,.05+.025*i);
  return s;
 }
 static Stats[] centralWindowStarvedBody(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(22+4*i,26+5*i,8+3*i,246,
      Math.max(.35,.61-.03*i),.15+.015*i,.11+.012*i,
      Math.max(.25,.75-.04*i),.16+.015*i,.17+.012*i,.15+.010*i,.095+.014*i);
  return s;
 }
 static Stats[] openPortraitPressure(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(78+6*i,88+4*i,36+3*i,230+2*i,
      .20,.12+.025*i,.06+.02*i,.16,.18+.02*i,.15+.018*i,.06+.018*i,.06+.02*i);
  return s;
 }
 static Stats[] noBacklight(){
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++)s[i]=stat(55+3*i,38+4*i,20+3*i,45+3*i,
      .30,.01,.002,.30,.005,.003,.001,.002);
  return s;
 }
 // Reproduces the 2026-09-24 woodland classification failure in reduced form:
 // the frame is globally and centrally starved, the old centre/surround score
 // looks backlit, but the 4x6 map is one broad dark scene rather than a coherent
 // subject component. 1G let neither branch own it; 1H must fall through to scene key.
 static Stats[] woodlandDeadZone(){
  int[] med={11,14,18,22,27,33,39,47,57,68,80};
  int[] cm ={9,12,14,18,23,28,34,41,49,58,70};
  int[] cq ={5,6,8,11,13,16,20,25,30,37,44};
  int[] oq ={66,79,91,103,117,130,143,157,170,183,196};
  double[] dark={.801,.750,.690,.616,.540,.444,.361,.296,.236,.174,.128};
  double[] bright={.026,.027,.029,.031,.034,.035,.039,.042,.047,.055,.060};
  double[] clip={.017,.020,.022,.026,.026,.029,.030,.034,.035,.038,.042};
  double[] cclip={.016,.021,.021,.031,.031,.031,.036,.047,.047,.047,.047};
  Stats[] s=new Stats[11];
  for(int i=0;i<11;i++){
   int[] fm=ints(Math.min(90,12+5*i));
   int[] fq=ints(Math.min(70,6+4*i));
   int[] fh=ints(Math.min(220,35+7*i));
   double[] fb=doubles(.03),fc=doubles(.005);
   s[i]=gridStat(med[i],cm[i],cq[i],oq[i],dark[i],bright[i],clip[i],
       Math.min(.83,dark[i]+.03),Math.min(.08,bright[i]),Math.min(.06,bright[i]),
       cclip[i],Math.min(.05,clip[i]),fm,fq,fh,fb,fc);
  }return s;
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

  M9AutoExposure2D.reset();publish(dark());check(decide(0,0,0,0,true),.75,
      "very severe fresh dark-scene deficit may acquire by guarded three-quarter stop");
  check(decide(0,0,0,0,true),.75,"reusing sample cannot ratchet exposure");
  publish(dark());check(decide(0,0,0,0,true),1.50,
      "fresh severe deficit permits the second guarded three-quarter-stop acquisition step");
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
  yes(M9AutoExposure2D.positiveHeadroomLimit(darkLamp())==0,
      "ordinary strict guard rejects first isolated-lamp growth");
  yes(M9AutoExposure2D.sceneKeyHeadroomLimit(darkLamp())>=1.0,
      "starved whole-scene path permits bounded isolated-lamp loss");
  yes(M9AutoExposure2D.selectSceneKey(darkLamp())>=4,
      "starved scene with a lamp can brighten beyond old half-stop behavior");

  yes(M9AutoExposure2D.selectSceneKey(night())==0,
      "low-key night-like scene with adequate central body is not globally lifted");
  yes(M9AutoExposure2D.selectBacklight(night())==0,
      "adequately placed low-key night body is not misclassified as backlight");
  check(fresh(night(),0),0,"acceptable low-key night scene stays at neutral Auto");

  Stats[] back=backlight();
  Stats[] moderateBack=moderateBacklight();

  yes(M9AutoExposure2D.FIELD_ROWS==4&&M9AutoExposure2D.FIELD_COLS==6
          &&M9AutoExposure2D.FIELD_COUNT==24,
      "rendered body meter uses 4x6 / 24-region topology");

  Stats[] off=offCenterBody();
  BodyCandidate offBody=M9AutoExposure2D.multifieldBodyCandidate(off[0]);
  yes(offBody.valid&&offBody.fieldCount>=4,
      "coherent off-centre dark body is detected without centre ownership");
  yes(offBody.bodyMedian<30&&offBody.targetMedian>=44&&offBody.targetMedian<=60,
      "body readability target is relative and remains M9-dense");
  int offStep=M9AutoExposure2D.selectBacklight(off);
  yes(offStep>=3&&offStep<=6,
      "off-centre body receives useful but bounded global exposure");
  yes(M9AutoExposure2D.backlightHeadroomLimit(off)>=M9AutoExposure2D.ev(offStep),
      "body target remains inside multi-field highlight allowance");

  Stats[] windowGrid=centralWindowGrid();
  BodyCandidate windowCandidate=M9AutoExposure2D.multifieldBodyCandidate(windowGrid[0]);
  yes(windowCandidate.valid&&windowCandidate.bodyMedian<30,
      "dark body is separated from bright central window");
  yes(M9AutoExposure2D.selectBacklight(windowGrid)>=3,
      "central clipped background does not prevent subject readability lift");

  yes(!M9AutoExposure2D.multifieldBodyCandidate(isolatedEdgeShadowGrid()[0]).valid,
      "isolated outer-edge shadow is not promoted to subject");
  yes(!M9AutoExposure2D.multifieldBodyCandidate(highKeyDarkPatchGrid()[0]).valid,
      "already high-key scene does not chase one remaining dark patch");
  yes(!M9AutoExposure2D.multifieldBodyCandidate(lowKeyGrid()[0]).valid,
      "accepted broad low-key scene is not converted into a backlight subject");
  yes(M9AutoExposure2D.selectBacklight(lowKeyGrid())==0,
      "multi-field path preserves low-key night-style neutrality");

  Stats[] woods=woodlandDeadZone();
  yes(!M9AutoExposure2D.multifieldBodyCandidate(woods[0]).valid,
      "broad woodland darkness is not mis-promoted to a coherent backlight body");
  yes(M9AutoExposure2D.selectBacklight(woods)==0,
      "woodland scene has no multi-field backlight owner");
  yes(M9AutoExposure2D.selectSceneKey(woods)==7,
      "field ownership lets globally starved woodland fall through to the 1.75-EV scene target");
  yes(M9AutoExposure2D.sceneKeyHeadroomLimit(woods)>=1.75,
      "woodland scene target remains inside the existing dark-scene highlight budget");
  M9AutoExposure2D.reset();publish(woods);
  check(decide(0,0,0,0,true),.75,
      "woodland dead-zone closes with guarded three-quarter-stop acquisition");
  publish(woods);
  check(decide(0,0,0,0,true),1.50,
      "woodland severe deficit advances a second guarded three-quarter stop");
  publish(woods);
  check(decide(0,0,0,0,true),1.75,
      "woodland final approach returns to the exact rendered target without overshoot");

  M9AutoExposure2D.reset();publish(woods);now+=300000000L;
  check(decide(0,0,0,0,true),.50,
      "sample older than 250 ms cannot use 0.75-EV tier and falls back to half-stop acquisition");

  Stats[] anchorScene=openAnchorWithDarkMaterial();
  yes(M9AutoExposure2D.protectedOpenAnchorFieldCount(anchorScene[0])>=2,
      "coherent already-open textured region is detected");
  BodyCandidate anchorBody=M9AutoExposure2D.multifieldBodyCandidate(anchorScene[0]);
  yes(anchorBody.valid,
      "1G keeps the coherent dark-body candidate instead of hard-vetoing it");
  yes(!M9AutoExposure2D.protectedOpenAnchorSevereBacklight(anchorScene[0],anchorBody),
      "ordinary open-anchor scene is not promoted to severe backlight");
  check(M9AutoExposure2D.protectedOpenAnchorLiftCap(anchorScene[0],anchorBody),.25,
      "ordinary protected anchor caps extra Auto lift at one quarter stop");
  M9AutoExposure2D.reset();double anchorApplied=0;
  for(int i=0;i<6;i++){publish(anchorScene);anchorApplied=decide(0,0,0,0,true);}
  check(anchorApplied,.25,
      "ordinary open-anchor portrait pressure converges no higher than +0.25 EV");

  Stats[] severeAnchor=openAnchorSevereBacklight();
  yes(M9AutoExposure2D.protectedOpenAnchorFieldCount(severeAnchor[0])>=2,
      "severe backlight can coexist with a protected textured anchor");
  BodyCandidate severeAnchorBody=M9AutoExposure2D.multifieldBodyCandidate(severeAnchor[0]);
  yes(severeAnchorBody.valid,
      "severe anchored scene retains coherent dark-body evidence");
  yes(M9AutoExposure2D.protectedOpenAnchorSevereBacklight(severeAnchor[0],severeAnchorBody),
      "strong bright-background evidence qualifies the severe soft-anchor branch");
  check(M9AutoExposure2D.protectedOpenAnchorLiftCap(severeAnchor[0],severeAnchorBody),.50,
      "severe protected-anchor backlight may recover up to half a stop");
  yes(M9AutoExposure2D.selectBacklight(severeAnchor)>=2,
      "severe anchored body requests at least a half-stop before the soft cap");
  M9AutoExposure2D.reset();double severeAnchorApplied=0;
  for(int i=0;i<7;i++){publish(severeAnchor);severeAnchorApplied=decide(0,0,0,0,true);}
  check(severeAnchorApplied,.50,
      "severe protected-anchor scene converges to the +0.50 EV middle-ground ceiling");

  // BODYLOCK1A: hold the same spatial body and original readability target
  // across meter noise / a one-field boundary shift.
  M9AutoExposure2D.reset();
  publish(off);
  decide(0,0,0,0,true);
  int lockedMask=M9AutoExposure2D.bodyLockMaskForDiagnostics();
  int lockedMedian=M9AutoExposure2D.bodyLockTargetMedianForDiagnostics();
  int lockedQ25=M9AutoExposure2D.bodyLockTargetQ25ForDiagnostics();
  yes(lockedMask!=0,"first confident multi-field sample latches a body mask");
  publish(offCenterBodyShifted());
  decide(0,0,0,0,true);
  yes(M9AutoExposure2D.bodyLockMaskForDiagnostics()==lockedMask,
      "overlapping field-boundary jitter keeps the original body mask");
  yes(M9AutoExposure2D.bodyLockTargetMedianForDiagnostics()==lockedMedian
          &&M9AutoExposure2D.bodyLockTargetQ25ForDiagnostics()==lockedQ25,
      "overlapping body jitter keeps the original readability target");

  // A genuinely disjoint body cannot switch on one fresh sample.
  publish(disjointNewBody());
  decide(0,0,0,0,true);
  yes(M9AutoExposure2D.bodyLockMaskForDiagnostics()==lockedMask
          &&M9AutoExposure2D.bodyLockPendingConfirmationsForDiagnostics()==1,
      "disjoint new body requires a second fresh confirmation");
  publish(disjointNewBody());
  decide(0,0,0,0,true);
  yes(M9AutoExposure2D.bodyLockMaskForDiagnostics()!=0
          &&M9AutoExposure2D.bodyLockMaskForDiagnostics()!=lockedMask,
      "second fresh confirmation switches to the genuinely new body");
  yes(M9AutoExposure2D.backlightPlacementSeverity(back[0])
          > M9AutoExposure2D.backlightPlacementSeverity(moderateBack[0]),
      "severe backlight has greater placement severity than moderate backlight");
  yes(M9AutoExposure2D.backlightCenterTarget(back[0])
          > M9AutoExposure2D.backlightCenterTarget(moderateBack[0]),
      "severe backlight receives a higher centre target");
  yes(M9AutoExposure2D.backlightCenterQ25Target(back[0])
          > M9AutoExposure2D.backlightCenterQ25Target(moderateBack[0]),
      "severe backlight receives a higher lower-quartile target");
  yes(M9AutoExposure2D.backlightCenterTarget(back[0])<=72
          && M9AutoExposure2D.backlightCenterQ25Target(back[0])<=32,
      "adaptive backlight target remains inside M9-like dense-body ceiling");
  yes(M9AutoExposure2D.backlightCenterTarget(moderateBack[0])>=58
          && M9AutoExposure2D.backlightCenterQ25Target(moderateBack[0])>=22,
      "moderate backlight target never falls below the low-key floor");
  yes(M9AutoExposure2D.positiveHeadroomLimit(back)==0,
      "ordinary strict guard rejects first severe-backlight step");
  yes(M9AutoExposure2D.backlightHeadroomLimit(back)>=1.5,
      "backlight-specific headroom permits substantial background sacrifice");
  yes(!M9AutoExposure2D.m9CharacterHighlightUnsafe(back[0],back[8]),
      "severe backlight may still reach two stops when central highlights remain dense");
  yes(M9AutoExposure2D.m9CharacterHighlightUnsafe(back[0],back[9]),
      "M9-character guard stops the next step once full-frame highlight loss becomes excessive");

  Stats[] windowBody=centralWindowStarvedBody();
  yes(!M9AutoExposure2D.m9CharacterHighlightUnsafe(windowBody[0],windowBody[2]),
      "central clipped window does not veto lift while body remains deeply starved");
  yes(M9AutoExposure2D.selectBacklight(windowBody)>=2,
      "dark body can still gain exposure despite central background clipping");

  Stats[] openPortrait=openPortraitPressure();
  yes(M9AutoExposure2D.m9CharacterHighlightUnsafe(openPortrait[0],openPortrait[4]),
      "open body plus highlight pressure trips M9-character ceiling");
  yes(M9AutoExposure2D.backlightHeadroomLimit(m9CharacterLoss())>=1.0
          && M9AutoExposure2D.backlightHeadroomLimit(m9CharacterLoss())<=1.5,
      "modest central highlight growth limits backlight before catastrophic clipping");
  int backStep=M9AutoExposure2D.selectBacklight(back);
  yes(backStep>=8,"severe backlight can request at least 2.0 EV when body remains starved");
  M9AutoExposure2D.reset();publish(back);
  check(decide(0,0,0,0,true),.50,
      "severe confident backlight begins with half-stop fast acquisition");
  double applied=.50;
  for(int i=0;i<8;i++){publish(back);applied=decide(0,0,0,0,true);}
  yes(applied>.5,"backlight converges beyond old half-stop ceiling");
  yes(applied<=M9AutoExposure2D.ev(backStep),"backlight never exceeds rendered target");

  int moderate=M9AutoExposure2D.selectBacklight(moderateBack);
  yes(moderate>0&&moderate<backStep,"moderate backlight chooses less exposure than severe backlight");
  yes(M9AutoExposure2D.ev(backStep)-M9AutoExposure2D.ev(moderate)>=.75,
      "adaptive target materially separates severe and moderate backlight placement");

  // Converge part-way on severe backlight, then present a lower but still safe target.
  // One low sample must not toggle the preview down; the second confirms a 0.25-EV release.
  M9AutoExposure2D.reset();
  double before=0;
  // FASTACQUIRE1A reaches the same ~1.5-EV partial baseline in three fresh
  // severe samples that previously required six quarter-stop samples.
  for(int i=0;i<3;i++){publish(back);before=decide(0,0,0,0,true);}
  yes(before>1.0&&before<=1.5,"severe backlight establishes a partial positive displayed baseline");
  publish(moderateBack);double firstLower=decide(0,0,0,0,true);
  check(firstLower,before,"single lower target sample is held to prevent EV ping-pong");
  publish(moderateBack);double secondLower=decide(0,0,0,0,true);
  check(secondLower,before-.25,"second confirming lower sample releases one quarter stop");
  publish(destructiveCenter());double safetyRelease=decide(0,0,0,0,true);
  check(safetyRelease,0,"real central highlight safety loss releases immediately");
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
  yes(measured.fieldMapValid&&measured.fieldMedian.length==24,
      "meter publishes complete 24-field rendered map");
  check(measured.fieldMedian[0],180,"outer field median preserved in 4x6 map");
  check(measured.fieldQ90[0],180,"outer field upper quantile preserved in 4x6 map");

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
if assertions < 97: raise SystemExit(f'expected at least 97 assertions, got {assertions}')

integration={}
if assembled is not None:
 target=assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
 if target.read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
  raise SystemExit('assembled Auto policy mismatch')
 integration={'assembled_candidate_exact':True}

receipt={
 'revision':'M9AUTOEXPOSUREFINISH1I_FASTACQUIRE1B_SAFE075',
 'assertions':assertions,
 'positive_search_max_ev':2.5,
 'scene_median_target_code':46,
 'scene_center_target_code':54,
 'scene_center_q25_target_code':22,
 'backlight_center_target_range_code':[58,72],
 'backlight_center_q25_target_range_code':[22,32],
 'adaptive_backlight_target':True,
 'multifield_topology':[4,6],
 'body_lock_overlap_fraction':0.50,
 'body_switch_fresh_confirmations':2,
 'body_target_locked_with_mask':True,
 'protected_open_anchor_guard':True,
 'protected_open_anchor_policy':'soft_positive_lift_cap',
 'protected_open_anchor_ordinary_max_ev':0.25,
 'protected_open_anchor_severe_max_ev':0.50,
 'hard_open_anchor_veto_removed':True,
 'field_map_owns_backlight_classification':True,
 'no_qualified_body_scene_fallback':True,
 'normal_positive_slew_ev':0.25,
 'fast_positive_slew_ev':0.50,
 'safe_fast_positive_slew_ev':0.75,
 'safe_fast_max_sample_age_ms':250,
 'safe_fast_minimum_remaining_gap_ev':1.25,
 'safe_fast_open_anchor_allowed':False,
 'fast_acquire_large_deficit_only':True,
 'open_anchor_requires_coherent_textured_fields':True,
 'body_target_relative_to_baseline':True,
 'coherent_body_component_required':True,
 'high_key_dark_patch_suppression':True,
 'm9_character_highlight_guard':True,
 'backlight_confidence_hysteresis':[0.12,0.22],
 'lower_target_requires_fresh_confirmations':2,
 'ordinary_highlight_budget_preserved':True,
 'backlight_background_loss_center_protected':True,
 'low_key_night_body_protection':True,
 'integration':integration,
 'output':result,
}
(build.parent/'autoexposurefinish1i_tests.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(result,end='')
print(json.dumps({k:v for k,v in receipt.items() if k!='output'}))
