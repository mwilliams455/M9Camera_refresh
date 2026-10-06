"""Run actual M9 probe classes and MainRenderer's scheduling block with a deterministic GL adapter.

The adapter simulates fence latency and packed readback pixels, not Android GPU
performance. Before/after only differ in the production M9PreviewMeter2D source.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil, subprocess

p=argparse.ArgumentParser()
p.add_argument('parent',type=Path);p.add_argument('candidate',type=Path)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();here=Path(__file__).resolve().parent
pkg='com/particlesdevs/photoncamera/'
preview=pkg+'m9/preview/'
production=['M9PreviewMeter2D.java','M9PreviewEvidence2E.java','M9PreviewTc20Math1A.java']
report={'scope':'host scheduling regression; synthetic GL readback, not phone validation','runs':{}}
for label,root in [('parent',a.parent),('candidate',a.candidate)]:
 out=a.output/label;out.mkdir(parents=True,exist_ok=True)
 def write(name,s):
  dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(s)
 hashes={}
 for name in production:
  raw=(root/'app/src/main/java'/preview/name).read_bytes()
  write(preview+name,raw.decode());hashes[name]=hashlib.sha256(raw).hexdigest()
 main=(root/'app/src/main/java'/pkg/'ui/camera/views/viewfinder/MainRenderer.java').read_text()
 start=main.index('            final boolean m9EvidenceBusy1A =')
 end=main.index('            com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.draw',start)
 schedule=main[start:end]
 hashes['MainRendererSchedule']=hashlib.sha256(schedule.encode()).hexdigest()
 write(preview+'ProductionSchedule.java','''package com.particlesdevs.photoncamera.m9.preview;
public final class ProductionSchedule {
 public static float draw(M9PreviewMeter2D mM9Meter2D,M9PreviewEvidence2E mM9Evidence2E,
 M9PreviewFrameState1W frame1W,long textureTimestamp1W) {
 int mM9CurveTex=1,uM9ExposureScale1B=1,enablePeak=2,peakEnabled=0,
 uM9PreviewTc20Gain1A=3,uM9EvidenceStage2E=4;
 android.graphics.SurfaceTexture mSTexture=null;
 float previewTc20Gain1A=mM9Evidence2E.predictedTc20Gain(frame1W);
 '''+schedule+'\nreturn previewTc20Gain1A;}}\n')
 stubs={
 'android/os/SystemClock.java':'''package android.os; public class SystemClock {
 public static long now;public static long elapsedRealtimeNanos(){return now;}}''',
 'android/os/Build.java':'''package android.os;public class Build {
 public static class VERSION {public static final int SDK_INT=32;}}''',
 'android/graphics/SurfaceTexture.java':'''package android.graphics;
 public class SurfaceTexture {public int getDataSpace(){return 0;}}''',
 pkg+'util/Log.java':'''package com.particlesdevs.photoncamera.util;
 public class Log {public static void w(String a,String b){}}''',
 'org/json/JSONException.java':'''package org.json;public class JSONException extends Exception {}''',
 'org/json/JSONObject.java':'''package org.json;import java.util.*;public class JSONObject {
 public static final Object NULL=new Object();private final Map<String,Object> data=new HashMap<>();
 public JSONObject put(String k,Object v)throws JSONException {data.put(k,v);return this;}
 public Object value(String k){return data.get(k);}}''',
 'org/json/JSONArray.java':'''package org.json;public class JSONArray {
 public JSONArray put(Object v){return this;}}''',
 pkg+'m9/M9ExposurePlan1A.java':'''package com.particlesdevs.photoncamera.m9;
 public class M9ExposurePlan1A {public String cameraId="0",mode="PHOTO";
 public int referenceIso=100,observedIso=100,manualIso;
 public long referenceExposureNs=10000000,observedExposureNs=10000000,manualExposureNs,id;
 public double userEv,autoEv;
 public static double energy(int iso,long time){return (double)iso*time;}
 public static boolean supportsMode1B(String s){return "PHOTO".equals(s);}}''',
 preview+'M9PreviewFrameState1W.java':'''package com.particlesdevs.photoncamera.m9.preview;
 import com.particlesdevs.photoncamera.m9.M9ExposurePlan1A;
 public class M9PreviewFrameState1W {
 public M9ExposurePlan1A plan=new M9ExposurePlan1A();public Source source2A=new Source();
 public long resultTimestampNs;public float exposureScale=1;
 public static class Source {public boolean ready=true,continuityHeld;public String cameraId="0";
 public org.json.JSONObject diagnostics(){return new org.json.JSONObject();}}}''',
 preview+'M9AutoExposure2D.java':'''package com.particlesdevs.photoncamera.m9.preview;
 public class M9AutoExposure2D {public static final int WIDTH=32,HEIGHT=24,STEPS=11;
 public static final long MAX_AGE_NS=1200000000L;public static int publications;
 public static double ev(int i){return i*.25;}public static class Stats {}
 public static class Sample {public Sample(String c,String m,long s,long t,long r,double e,Stats[] a,M9TapMeter1A.Probe p){}}
 public static Stats[] measure(java.nio.ByteBuffer b){return new Stats[11];}
 public static void publish(Sample s){publications++;}public static void invalidate(String s){}}''',
 preview+'M9TapMeter1A.java':'''package com.particlesdevs.photoncamera.m9.preview;
 public class M9TapMeter1A {public static class Selection {} public static class Probe {}
 public static Selection selection(long n){return null;}
 public static Probe measure(java.nio.ByteBuffer b,Selection s,long n){return new Probe();}}'''
 }
 for name,s in stubs.items():write(name,s)
 constants=sorted(set(re.findall(r'GLES30\.(GL_[A-Z0-9_]+)', '\n'.join((out/preview/n).read_text() for n in production))))
 gl='package android.opengl;import java.nio.*;import java.util.*;public class GLES30 {\n'
 gl+='\n'.join('public static final int '+n+'='+str(i+1)+';' for i,n in enumerate(constants))
 gl+=(here/'GlesAdapter.java.txt').read_text()+'\n}'
 write('android/opengl/GLES30.java',gl)
 write('ProbeTest.java',(here/'ProbeTest.java').read_text())
 files=[str(x) for x in out.rglob('*.java')]
 subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',str(out)]+files,check=True)
 result=subprocess.check_output(['java','-cp',str(out),'ProbeTest',label],text=True)
 report['runs'][label]={'sourceSha256':hashes,'result':json.loads(result)}
assert report['runs']['parent']['sourceSha256']['MainRendererSchedule']==report['runs']['candidate']['sourceSha256']['MainRendererSchedule']
for n in production[1:]:assert report['runs']['parent']['sourceSha256'][n]==report['runs']['candidate']['sourceSha256'][n]
(a.output/'HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
