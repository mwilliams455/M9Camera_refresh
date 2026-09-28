#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
srcroot=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/preview'
stubs={
'org/json/JSONException.java':'package org.json; public class JSONException extends Exception {}',
'org/json/JSONObject.java':'package org.json; import java.util.*; public class JSONObject { public static final Object NULL=new Object(); private final Map<String,Object>d=new LinkedHashMap<>(); public JSONObject put(String k,Object v)throws JSONException{d.put(k,v);return this;} public String toString(){return d.toString();}}',
'org/json/JSONArray.java':'package org.json; import java.util.*; public class JSONArray { private final List<Object>d=new ArrayList<>(); public JSONArray put(Object v){d.add(v);return this;} public String toString(){return d.toString();}}'}
files=[]
for name,body in stubs.items():
    p=out/'stubs'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);files.append(str(p))
files += [str(srcroot/'M9AutoExposure2D.java'),str(srcroot/'M9TapMeter1A.java'),
          str(Path(__file__).with_name('TargetStabilityTest.java'))]
classes=out/'classes'
subprocess.run(['javac','--release','17','-d',str(classes),*files],check=True,timeout=60)
r=subprocess.run(['java','-ea','-cp',str(classes),
                  'com.particlesdevs.photoncamera.m9.preview.TargetStabilityTest'],
                 capture_output=True,text=True,check=True,timeout=30)
(out/'AETARGETSTABILITY_TESTS.txt').write_text(r.stdout);print(r.stdout,end='')
(out/'TEST_SCOPE.json').write_text(json.dumps({
 'actualSourceClasses':['M9AutoExposure2D','M9TapMeter1A'],
 'syntheticOnly':True,'privateCaptureFixtures':False,
 'photographicThresholdsRetuned':False,'phoneValidationPending':True},indent=2)+'\n')
