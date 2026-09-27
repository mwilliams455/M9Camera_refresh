#!/usr/bin/env python3
"""Full-class inherited tests plus synthetic SUBJECTHEADROOM1A tests; no private fixtures."""
from pathlib import Path
import ast,json,subprocess,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
REV='M9AUTOEXPOSUREFINISH1N_BODYQUAL1A_SUBJECTHEADROOM1A'
root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=True)
source=Path(sys.argv[2]).resolve()
# Reuse the existing 125-assertion test body; only the identity expectation changes.
parent=REPO/'patches/autoexposurefinish1l/test.py'
tree=ast.parse(parent.read_text())
runner=None
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='source' for t in node.targets):
        runner=ast.literal_eval(node.value)
if runner is None:raise SystemExit('inherited runner not found')
runner=runner.replace('M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A',REV)
(root/'PolicyTest.java').write_text(runner)
# Parent FINISH1M boundary/regression checks also run against the new class.
mtree=ast.parse((REPO/'patches/autoexposurefinish1m/test.py').read_text())
for node in mtree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='runner' for t in node.targets):
        mrunner=ast.literal_eval(node.value).replace('M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A',REV)
        (root/'HighlightGrandfatherTest.java').write_text(mrunner)
        break
else:raise SystemExit('FINISH1M runner not found')
stubs={
'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
'org/json/JSONObject.java':'package org.json; public class JSONObject { public static final Object NULL=new Object(); public JSONObject put(String k,Object v) throws JSONException{return this;} public String toString(){return "{}";} }',
'org/json/JSONArray.java':'package org.json; public class JSONArray {public JSONArray put(Object v){return this;}}'}
for name,text in stubs.items():
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
extra=r'''
package com.particlesdevs.photoncamera.m9.preview;
import java.util.*;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public class SubjectHeadroomTest {
 static int count;static long now=1000000000L;
 static void yes(boolean b,String msg){if(!b)throw new AssertionError(msg);count++;}
 static void eq(double a,double b,String msg){yes(Math.abs(a-b)<1e-10,msg+" "+a+" != "+b);}
 static int[] ints(int x){int[] a=new int[24];Arrays.fill(a,x);return a;}
 static double[] ds(double x){double[] a=new double[24];Arrays.fill(a,x);return a;}
 static Stats stats(int median,int[] fm,int[] fq,int[] fh,double[] fb,double[] fc,double bright,double clip){
  return new Stats(median,.6,bright,clip,20,5,210,.7,.10,.01,.001,.02,fm,fq,fh,fb,fc);
 }
 static Stats[] scene(int mode){
  Stats[] a=new Stats[11];int[] body={7,8,13,14};
  for(int i=0;i<11;i++){
   int[] fm=ints(130),fq=ints(40),fh=ints(mode==4?65:205);
   double[] fb=ds(0),fc=ds(0);
   for(int f:body){fm[f]=12+(mode==3?0:5*i);fq[f]=3+(mode==3?0:2*i);fh[f]=55+(mode==3?0:7*i);}
   if(i>=3){fc[0]=fc[5]=.10;}
   if(mode==1&&i>=3){fc[7]=fc[8]=.10;}
   if(mode==2&&i>=3){fb[0]=fb[5]=.60;}
   double clip=(mode==5&&i>=3)?.09:.005+.003*i;
   a[i]=stats(20,fm,fq,fh,fb,fc,.02,clip);
   if(mode==4)a[i]=new Stats(20,.6,.0,clip,20,5,65,.7,0,0,0,0,fm,fq,fh,fb,fc);
  }
  return a;
 }
 static Stats invalidBest(){
  int[] fm=ints(1),fq=ints(0),fh=ints(3);double[] b=ds(0),c=ds(0);
  // A large mixed region consumes the bright evidence and fails final confidence.
  for(int row=0;row<4;row++)for(int col=3;col<6;col++){int f=row*6+col;fm[f]=40;fq[f]=20;fh[f]=210;}
  for(int f:new int[]{6,7,12,13}){fm[f]=10;fq[f]=4;fh[f]=60;}
  return stats(20,fm,fq,fh,b,c,.02,.005);
 }
 static BodyCandidate body(Stats[] s){return M9AutoExposure2D.multifieldBodyCandidate(s[0]);}
 static double limit(Stats[] s){return M9AutoExposure2D.subjectHighlightRetentionLimit(s,body(s));}
 static Decision decide(Stats[] s){now+=100000000L;M9AutoExposure2D.publish(new Sample("T","PHOTO",now,now,now,1,s));return M9AutoExposure2D.decide("T","PHOTO",now+1,1,0,0,0,0,true);}
 public static void main(String[] args){
  BodyCandidate q=M9AutoExposure2D.multifieldBodyCandidate(invalidBest());
  yes(q.valid,"invalid geometric winner no longer hides alternative");
  eq(q.mask,(1<<6)|(1<<7)|(1<<12)|(1<<13),"synthetic valid alternative mask");
  Stats[] s=scene(0);BodyCandidate b=body(s);
  yes(b.valid&&M9AutoExposure2D.subjectHighlightEligible(s[0],b),"strong coherent body qualifies");
  eq(M9AutoExposure2D.highlightRetentionLimit(s),.5,"baseline regional clipping cap retained");
  eq(limit(s),1.75,"background-only channel clipping deferred only through first target step");
  eq(limit(scene(1)),.5,"two subject fields still protected");
  eq(limit(scene(2)),.5,"broad near-white regions always protected");
  eq(limit(scene(3)),.5,"no useful body progress means no extra highlight sacrifice");
  eq(limit(scene(4)),.5,"weak absolute background keeps inherited highlight limit");
  eq(limit(scene(5)),.5,"global clip growth is never bypassed");
  eq(M9AutoExposure2D.subjectHighlightRetentionLimit(s,null),.5,"missing body keeps baseline");
  Stats[] absent=new Stats[11];Arrays.fill(absent,new Stats(20,.8,.01,.005));
  eq(M9AutoExposure2D.subjectHighlightRetentionLimit(absent,b),M9AutoExposure2D.highlightRetentionLimit(absent),"missing field map keeps baseline");
  M9AutoExposure2D.reset();Decision d=decide(s);
  for(int i=0;i<12;i++)d=decide(s);
  eq(d.appliedEv,1.75,"controller uses qualified subject ceiling");
  double held=d.appliedEv;
  d=M9AutoExposure2D.decide("T","PHOTO",now+2,1,0,0,0,0,true);
  eq(d.appliedEv,held,"same sample does not pump exposure");
  d=M9AutoExposure2D.decide("T","PHOTO",now+M9AutoExposure2D.MAX_AGE_NS+1,1,0,0,0,0,true);
  eq(d.appliedEv,0,"stale meter cannot preserve positive assist");
  Random r=new Random(61039);
  for(int trial=0;trial<500;trial++){
   Stats[] x=scene(0);
   for(int i=0;i<x.length;i++){
    Stats v=x[i];double[] fc=v.fieldClipped.clone(),fb=v.fieldBright.clone();
    for(int f=0;f<24;f++){fc[f]=r.nextDouble()*.20;fb[f]=r.nextDouble()*.65;}
    x[i]=new Stats(v.median,v.dark,v.bright,v.clipped,v.centerMedian,v.centerQ25,v.outerQ90,v.centerDark,v.outerBright,v.centerBright,v.centerClipped,v.outerClipped,v.fieldMedian,v.fieldQ25,v.fieldQ90,fb,fc);
   }
   BodyCandidate xb=body(x);double old=M9AutoExposure2D.highlightRetentionLimit(x),hl=M9AutoExposure2D.subjectHighlightRetentionLimit(x,xb);
   yes(hl>=old-1e-9,"subject policy cannot create a stricter ceiling");
   yes(hl>=0&&hl<=2.5&&Math.abs(hl*4-Math.rint(hl*4))<1e-9,"bounded quarter-stop lattice");
   if(!M9AutoExposure2D.subjectHighlightEligible(x[0],xb))eq(old,hl,"ineligible exact fallback");
  }
  System.out.println("SUBJECT_ASSERTIONS "+count);
 }
}
'''
(root/'SubjectHeadroomTest.java').write_text(extra)
sources=[str(source),*[str(root/n) for n in stubs],str(root/'PolicyTest.java'),str(root/'HighlightGrandfatherTest.java'),str(root/'SubjectHeadroomTest.java')]
subprocess.run(['javac','-d',str(root/'classes'),*sources],check=True)
results={}
for runner in ['PolicyTest','HighlightGrandfatherTest','com.particlesdevs.photoncamera.m9.preview.SubjectHeadroomTest']:
    out=subprocess.check_output(['java','-ea','-cp',str(root/'classes'),runner],text=True)
    results[runner]=out;print(out,end='')
(root/'full_class_tests.json').write_text(json.dumps({'revision':REV,'runners':results,'private_capture_fixtures_published':False},indent=2)+'\n')
