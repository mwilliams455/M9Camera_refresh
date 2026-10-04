#!/usr/bin/env python3
"""Host policy test for FINISH1M HIGHLIGHTGRANDFATHER1A."""
from pathlib import Path
import json, shutil, subprocess, sys

HERE=Path(__file__).resolve().parent
build=Path(sys.argv[1]).resolve()
assembled=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else None
if build.exists(): shutil.rmtree(build)
build.mkdir(parents=True)

stubs={
 'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
 'org/json/JSONObject.java':'package org.json; public class JSONObject { public static final Object NULL=new Object(); public JSONObject put(String k,Object v) throws JSONException{return this;} public String toString(){return "{}";} }',
 'org/json/JSONArray.java':'package org.json; public class JSONArray { public JSONArray put(Object v){return this;} }',
}
for name,src in stubs.items():
    p=build/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(src)

candidate=(assembled/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
           if assembled else HERE/'M9AutoExposure2D.java')
dst=build/'com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
dst.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(candidate,dst)

runner=r'''
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.Stats;

public class HighlightGrandfatherTest {
 static int count=0;
 static void check(double got,double want,String msg){
   if(Math.abs(got-want)>1e-12)throw new AssertionError(msg+": "+got+" != "+want);
   count++;System.out.println("PASS "+msg+" = "+got);
 }
 static void yes(boolean v,String msg){
   if(!v)throw new AssertionError(msg);count++;System.out.println("PASS "+msg);
 }
 static int[] ints(int v){int[] a=new int[24];for(int i=0;i<24;i++)a[i]=v;return a;}
 static double[] ds(double v){double[] a=new double[24];for(int i=0;i<24;i++)a[i]=v;return a;}

 static Stats currentWindowStep(int i){
   // Reduced from IMG_20260926_121814 FINISH1J phone bracket.
   int[] med=ints(80),q25=ints(50),q90=ints(120);
   double[] bright=ds(0),clip=ds(0);
   q90[5]=233; q90[17]=237; bright[5]=bright[17]=1.0/6.0;
   if(i>=2){clip[5]=1.0/6.0;clip[17]=.10;}
   // Genuine newly-emerging highlight fields remain protected.
   q90[4]=104; q90[15]=185;
   if(i>=4)clip[4]=.10;
   if(i>=7)clip[15]=.10;
   double[] globalClip={.005208333333333333,.013020833333333334,.01953125,.0234375,
       .03125,.0390625,.052083333333333336,.07682291666666667,.10026041666666667,
       .12109375,.15104166666666666};
   double[] globalBright={.024739583333333332,.029947916666666668,.040364583333333336,
       .052083333333333336,.07291666666666667,.08854166666666667,.11979166666666667,
       .15494791666666666,.16927083333333334,.1953125,.2265625};
   return new Stats(12+6*i,.60,globalBright[i],globalClip[i],
       13+7*i,3+2*i,146+Math.min(10*i,106),.55,.10,.02,.01,.02,
       med,q25,q90,bright,clip);
 }

 static Stats boundaryStep(int i,int baseQ90){
   int[] med=ints(80),q25=ints(50),q90=ints(120);
   double[] bright=ds(0),clip=ds(0);
   q90[5]=baseQ90;q90[17]=baseQ90;
   if(i>=2){clip[5]=.10;clip[17]=.10;}
   return new Stats(80,.20,.02,.01,80,50,160,.10,.03,.02,.01,.01,
       med,q25,q90,bright,clip);
 }

 static Stats[] currentWindow(){
   Stats[] s=new Stats[11];for(int i=0;i<11;i++)s[i]=currentWindowStep(i);return s;
 }
 static Stats[] boundary(int q90){
   Stats[] s=new Stats[11];for(int i=0;i<11;i++)s[i]=boundaryStep(i,q90);return s;
 }

 public static void main(String[] args){
   yes(M9AutoExposure2D.REVISION.equals("M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A"),
       "FINISH1M revision");
   // The real phone pattern no longer stops at +0.25 merely because two window
   // cells that already had q90 233/237 start clipping. It remains bounded by
   // later genuinely-emerging fields at +1.75, yielding +1.50 EV safe authority.
   check(M9AutoExposure2D.highlightRetentionLimit(currentWindow()),1.50,
       "20260926 window regression bounded at +1.50 EV");
   // Exact policy boundary: q90 220 is already near-white structure; q90 219 is not.
   check(M9AutoExposure2D.highlightRetentionLimit(boundary(220)),2.50,
       "q90 220 pre-existing highlight is grandfathered");
   check(M9AutoExposure2D.highlightRetentionLimit(boundary(219)),0.25,
       "q90 219 emerging highlight remains protected");
   System.out.println("FINISH1M TESTS PASS "+count);
 }
}
'''
(build/'HighlightGrandfatherTest.java').write_text(runner)
sources=[str(p) for p in build.rglob('*.java')]
subprocess.run(['javac','-d',str(build/'classes'),*sources],check=True)
out=subprocess.check_output(['java','-cp',str(build/'classes'),'HighlightGrandfatherTest'],text=True)
print(out,end='')
summary={'revision':'M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A',
         'assertions':3,'phoneRegressionExpectedHighlightRetentionEv':1.5,
         'preexistingQ90Boundary':220}
(build/'autoexposurefinish1m_tests.json').write_text(json.dumps(summary,indent=2)+'\n')
