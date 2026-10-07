"""Run the complete production spool with real files/executors and Android I/O stubs."""
from pathlib import Path
import argparse, json, shutil, subprocess

p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();here=Path(__file__).resolve().parent
work=a.output.resolve();work.mkdir(parents=True,exist_ok=True)
src=work/'src';classes=work/'classes';classes.mkdir(exist_ok=True)
stubs={
'android/content/Context.java':'''package android.content;
public class Context { public java.io.File files; public java.io.File getFilesDir(){return files;} }''',
'android/os/Process.java':'''package android.os;
public class Process { public static final int THREAD_PRIORITY_BACKGROUND=10; public static void setThreadPriority(int i){} }''',
'com/particlesdevs/photoncamera/app/PhotonCamera.java':'''package com.particlesdevs.photoncamera.app;
public class PhotonCamera { public static android.content.Context context; public static android.content.Context getAppContext(){return context;} }''',
'com/particlesdevs/photoncamera/m9/M9OutputSettings.java':'''package com.particlesdevs.photoncamera.m9;
public class M9OutputSettings { public static volatile boolean enabled=true; public static boolean diagnosticsEnabled(){return enabled;} }''',
'com/particlesdevs/photoncamera/util/Log.java':'''package com.particlesdevs.photoncamera.util;
public class Log { public static void d(String a,String b){} public static void w(String a,String b){}
public static void e(String a,String b,Throwable t){} }''',
'org/json/JSONObject.java':'''package org.json;
public class JSONObject { public final java.util.Map<String,Object> values=new java.util.LinkedHashMap<>();
public JSONObject put(String key,Object value){values.put(key,value);return this;}
public String toString(){return values.toString();} public String toString(int indent){return toString();} }''',
'org/json/JSONArray.java':'''package org.json;
public class JSONArray { public final java.util.List<Object> values=new java.util.ArrayList<>();
public JSONArray put(Object value){values.add(value);return this;} }''',
}
for name,content in stubs.items():
 target=src/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
name='com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
target=src/name;target.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(a.source/'app/src/main/java'/name,target)
for name in ['SpoolTest.java','SimpleStorageHelper.java']:
 shutil.copyfile(here/name,src/name)
java=['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(classes)]
subprocess.run(java+[str(f) for f in src.rglob('*.java')],check=True)
results=[]
for scenario in ['backlog','coalesce','retry','lifecycle']:
 result=subprocess.run(['java','-cp',str(classes),'SpoolTest',scenario],check=True,text=True,capture_output=True,timeout=45)
 print(result.stdout.strip());results.append(json.loads(result.stdout))
report=dict(status='PASS',productionClass='M9DiagnosticBurstSpool.java',
 realFilesystemAndExecutors=True,androidSafAndJsonSerializationStubbed=True,
 scenarios=results,assertions=sum(r['assertions'] for r in results),phoneStorageProviderUntested=True)
(work/'HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
