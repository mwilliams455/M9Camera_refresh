"""Compile real frame history, exposure plan, frame state and tone math with metadata adapters."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();here=Path(__file__).resolve().parent;out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
pkg='com/particlesdevs/photoncamera/';src=a.source/'app/src/main/java'
names=[pkg+'m9/M9ExposurePlan1A.java']+[pkg+'m9/preview/'+n+'.java' for n in
       ['M9PreviewFrameHistory1A','M9PreviewFrameState1W','M9PreviewTc20Math1A']]
hashes={}
def write(name,text):
    f=out/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text)
for n in names:
    write(n,(src/n).read_text());hashes[n]=hashlib.sha256((src/n).read_bytes()).hexdigest()
stubs={
 'org/json/JSONException.java':'package org.json;public class JSONException extends Exception {}',
 'org/json/JSONObject.java':'package org.json;public class JSONObject {public static final Object NULL=new Object();public JSONObject put(String k,Object v)throws JSONException{return this;}}',
 'org/json/JSONArray.java':'package org.json;public class JSONArray {public JSONArray put(Object v){return this;}}',
 pkg+'m9/M9Bracket1A.java':'package com.particlesdevs.photoncamera.m9;public class M9Bracket1A {public static class Frame {}}',
 pkg+'m9/preview/M9GpuPreview2A.java':'''package com.particlesdevs.photoncamera.m9.preview;
 public class M9GpuPreview2A {public static class Frame {
 public final boolean ready,continuityHeld;public final String cameraId;
 public Frame(boolean r,boolean h,String c){ready=r;continuityHeld=h;cameraId=c;}
 public static Frame fallback(String s){return new Frame(false,false,"");}
 public org.json.JSONObject diagnostics(){return new org.json.JSONObject();}}}'''
}
for n,t in stubs.items():write(n,t)
write('FrameHistoryTest.java',(here/'FrameHistoryTest.java').read_text())
files=[str(f) for f in out.rglob('*.java')]
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out/'classes'),*files],check=True)
result=subprocess.check_output(['java','-cp',str(out/'classes'),'FrameHistoryTest'],text=True)
report=dict(status='PASS',scope='metadata join and isolated exposure multiplication; synthetic frames, not phone validation',
            sourceSha256=hashes,results=[json.loads(line) for line in result.splitlines()])
(out/'HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
