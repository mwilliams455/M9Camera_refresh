"""Compile the candidate policy unchanged; diagnostic JSON stubs only."""
from pathlib import Path
import json, subprocess, sys
HERE=Path(__file__).resolve().parent
build=Path(sys.argv[1]).resolve();build.mkdir(parents=True,exist_ok=True)
stubs={
 'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
 'org/json/JSONObject.java':'package org.json; public class JSONObject { public JSONObject put(String k,Object v) throws JSONException{return this;} public String toString(){return "{}";} }',
 'org/json/JSONArray.java':'package org.json; public class JSONArray { public JSONArray put(Object v){return this;} }',
}
for name,s in stubs.items():
 p=build/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
source=r'''
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D;
import com.particlesdevs.photoncamera.m9.preview.M9AutoExposure2D.*;
public class PolicyTest {
 static int count=0;static long now=1000000000L;
 static void check(double value,double expected,String message){
  if(Math.abs(value-expected)>1e-12)throw new AssertionError(message+": "+value+" != "+expected);
  count++;System.out.println("PASS "+message);
 }
 static Stats[] scene(int median,int firstUnsafe){
  Stats[] s=new Stats[7];
  for(int i=0;i<7;i++)s[i]=new Stats(median+5*i,.82,.004,i>=firstUnsafe?.1:0);
  return s;
 }
 static void publish(Stats[] s){now+=250000000L;M9AutoExposure2D.publish(new Sample("2","PHOTO",now,now,now,1,s));}
 static double decide(double legacy,double user,long shutter,int iso){return M9AutoExposure2D.decide("2","PHOTO",now,1,user,shutter,iso,legacy).appliedEv;}
 static double fresh(Stats[] s,double legacy){M9AutoExposure2D.reset();publish(s);return decide(legacy,0,0,0);}
 public static void main(String[] args){
  check(M9AutoExposure2D.positiveHeadroomLimit(scene(12,1)),0,"first positive step unsafe");
  check(fresh(scene(12,1),.5),0,"clipping vetoes inherited positive Auto bias");
  check(fresh(scene(100,1),.5),0,"bright scene still vetoes unsafe inherited bias");
  check(fresh(scene(100,7),.5),.5,"safe inherited bias retained without shadow lift");
  check(fresh(scene(12,2),.75),.25,"total bias limited to last safe bracket");
  check(fresh(scene(12,1),-.5),-.5,"negative baseline retained");
  M9AutoExposure2D.reset();check(decide(.5,0,0,0),0,"missing meter cannot justify positive assist");
  check(decide(-.5,0,0,0),-.5,"missing meter preserves negative baseline");
  fresh(scene(12,7),0);now+=1300000000L;check(decide(.5,0,0,0),0,"stale meter releases positive assist");
  M9AutoExposure2D.reset();publish(scene(12,7));check(decide(0,0,0,0),.25,"positive rise remains quarter stop");
  check(decide(0,0,0,0),.25,"reusing sample cannot ratchet exposure");
  publish(scene(12,7));check(decide(0,0,0,0),.5,"fresh sample permits next quarter stop");
  publish(scene(12,1));check(decide(.75,0,0,0),0,"unsafe scene releases previous lift immediately");
  fresh(scene(100,7),.5);publish(scene(12,1));check(decide(.75,.25,0,0),.5,"explicit user EV retains displayed Auto baseline");
  check(decide(.75,0,1000000,0),0,"manual shutter disables automatic assist");
  check(decide(.75,0,0,200),0,"manual ISO disables automatic assist");
  M9AutoExposure2D.reset();publish(scene(12,7));
  check(M9AutoExposure2D.decide("other","PHOTO",now,1,0,0,0,.5).appliedEv,0,"foreign camera sample cannot justify bias");
  Stats[] invalid=scene(12,7);invalid[3]=new Stats(20,Double.NaN,0,0);
  check(fresh(invalid,.5),0,"invalid bracket cannot justify positive bias");
  Stats[] brightness=scene(12,7);brightness[1]=new Stats(17,.8,.05,0);
  check(fresh(brightness,.5),0,"broad-brightening budget also caps inherited bias");
  Stats[] bounded=scene(12,3);
  check(fresh(bounded,0),.25,"safe half-stop bracket initial slew");
  publish(bounded);check(decide(0,0,0,0),.5,"safe half-stop bracket final selection");
  System.out.println("ASSERTIONS "+count);
 }
}
'''
(build/'PolicyTest.java').write_text(source)
subprocess.run(['java','com.sun.tools.javac.Main','-d',str(build),str(HERE/'M9AutoExposure2D.java'),str(build/'PolicyTest.java'),*[str(build/p) for p in stubs]],check=True)
result=subprocess.check_output(['java','-cp',str(build),'PolicyTest'],text=True)
(build.parent/'auto_tests.json').write_text(json.dumps(dict(assertions=int(result.strip().splitlines()[-1].split()[-1]),output=result),indent=2)+'\n')
print(result,end='')
