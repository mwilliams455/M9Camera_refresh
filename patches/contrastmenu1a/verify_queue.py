#!/usr/bin/env python3
"""Execute the production queue with controlled platform, rendering and storage adapters."""
from pathlib import Path
import json,subprocess,sys,urllib.request
HERE=Path(__file__).resolve().parent;root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
src=root/'app/src/main/java/com/particlesdevs/photoncamera';stub=out/'stubs';classes=out/'classes';classes.mkdir(exist_ok=True)
jar=out/'json.jar'
if not jar.exists():
 with urllib.request.urlopen('https://repo.maven.apache.org/maven2/org/json/json/20250517/json-20250517.jar',timeout=30) as r:jar.write_bytes(r.read())
stubs={
'android/hardware/camera2/CameraCharacteristics.java':'package android.hardware.camera2; public class CameraCharacteristics {}',
'android/hardware/camera2/CaptureResult.java':'package android.hardware.camera2; public class CaptureResult {}',
'android/hardware/camera2/CaptureRequest.java':'package android.hardware.camera2; public class CaptureRequest {}',
'android/os/Process.java':'package android.os;public class Process {public static final int THREAD_PRIORITY_BACKGROUND=10,THREAD_PRIORITY_DEFAULT=0;public static void setThreadPriority(int n){}}',
'android/media/MediaScannerConnection.java':'package android.media; public class MediaScannerConnection {public static void scanFile(Object c,String[] p,String[] m,Object cb){}}',
'com/particlesdevs/photoncamera/app/PhotonCamera.java':'package com.particlesdevs.photoncamera.app;public class PhotonCamera {public static Object getAppContext(){return null;} public static String getVersion(){return "test";}}',
'com/particlesdevs/photoncamera/settings/PreferenceKeys.java':'package com.particlesdevs.photoncamera.settings;public class PreferenceKeys {public static volatile int mode;public static int isSaveRaw(){return mode;}}',
'com/particlesdevs/photoncamera/m9/M9OutputSettings.java':'package com.particlesdevs.photoncamera.m9;public class M9OutputSettings {public static volatile boolean extra;public static boolean saveUnfilteredDng(){return extra;}}',
'com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java':'package com.particlesdevs.photoncamera.m9;public class M9DeferredMetadataStore {public static boolean persistAsyncForDng(java.nio.file.Path p){return false;}}',
'com/particlesdevs/photoncamera/m9/capture/M9CaptureRequestAudit1A.java':'package com.particlesdevs.photoncamera.m9.capture;public class M9CaptureRequestAudit1A {public static org.json.JSONObject take(long t,Object r){return new org.json.JSONObject();}}',
'com/particlesdevs/photoncamera/m9/render/M9ContrastSettings.java':'package com.particlesdevs.photoncamera.m9.render;public class M9ContrastSettings {public static volatile int value=2;public static int selected(){return value;}}',
'com/particlesdevs/photoncamera/m9/render/M9SaturationSettings.java':'package com.particlesdevs.photoncamera.m9.render;public class M9SaturationSettings {public static int selected(){return 3;}}',
'com/particlesdevs/photoncamera/m9/render/M9PhotonBoundary2Q.java':'package com.particlesdevs.photoncamera.m9.render;public class M9PhotonBoundary2Q {public static void frame(Object f,String s,Object r,Object x){}public static java.nio.file.Path savedRawPairPath(Object f){return null;}public static org.json.JSONObject finish(Object f,boolean d){return new org.json.JSONObject();}}',
'com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java':'package com.particlesdevs.photoncamera.m9.render;public class M9PrimaryTimingWriter {public static boolean freezeAndWriteAsync(Object... a){return false;}public static void writeRejectedAsync(Object... a){}}',
'com/particlesdevs/photoncamera/util/Log.java':'package com.particlesdevs.photoncamera.util;public class Log {public static void d(String a,String b){}public static void e(String a,String b){}public static void e(String a,String b,Throwable t){}}',
'com/particlesdevs/photoncamera/processing/ImageFrame.java':'''package com.particlesdevs.photoncamera.processing;public class ImageFrame {public java.nio.ByteBuffer buffer=java.nio.ByteBuffer.allocate(8);public long timestamp=1;public int packedBits=16;public final java.util.concurrent.atomic.AtomicInteger closes=new java.util.concurrent.atomic.AtomicInteger();public void close(){closes.incrementAndGet();}}''',
'com/particlesdevs/photoncamera/processing/ProcessingEventsListener.java':'package com.particlesdevs.photoncamera.processing;public interface ProcessingEventsListener {void notifyImageSavedStatus(boolean success,java.nio.file.Path p);}',
'com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java':'''package com.particlesdevs.photoncamera.m9.render;
import java.nio.file.*;import java.util.concurrent.*;import org.json.*;
public class M9R35Renderer {
 public static volatile CountDownLatch entered,release;
 public static class Result {public boolean success;public Path jpegPath;public Object jpegExifData;public JSONObject diagnostics;public String error;}
 public static Result renderAndSavePrimary(Path p,Object f,Object c,Object cr,Object rq,int rotation,int bank,int contrast,boolean jpeg) {
  try { if(entered!=null){entered.countDown();if(!release.await(5,TimeUnit.SECONDS))throw new AssertionError("render wait");}
   Result r=new Result();r.success=!p.toString().contains("bad_render");r.error=r.success?null:"synthetic render failure";
   r.diagnostics=new JSONObject().put("bank",bank).put("contrast",contrast);
   if(jpeg&&r.success){r.jpegPath=Path.of(p.toString().replace(".dng",".jpg"));Files.writeString(r.jpegPath,"jpeg");}
   return r;
  }catch(Exception e){throw new RuntimeException(e);}
 }
}''',
'com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java':'''package com.particlesdevs.photoncamera.m9.render;
import com.particlesdevs.photoncamera.processing.ProcessingEventsListener;import java.nio.file.Path;
public class M9JpegFinalizeQueue {public static final java.util.concurrent.atomic.AtomicInteger calls=new java.util.concurrent.atomic.AtomicInteger();
 public static class Ticket {public void awaitCompletion(){}public boolean isSuccess(){return true;}public String error(){return null;}public void appendDiagnostics(org.json.JSONObject d){}}
 public static Ticket submit(Path p,Object e,ProcessingEventsListener l){calls.incrementAndGet();l.notifyImageSavedStatus(true,p);return new Ticket();}
}''',
'com/particlesdevs/photoncamera/processing/ImageSaver.java':'''package com.particlesdevs.photoncamera.processing;
import java.nio.file.*;
public class ImageSaver {public static class Util {
 public static final java.util.concurrent.atomic.AtomicInteger calls=new java.util.concurrent.atomic.AtomicInteger();
 public static boolean saveSingleRawM9PhysicalCfa(Path p,ImageFrame f,Object c,Object cr,int rotation,boolean extra){
  calls.incrementAndGet();try {if(p.toString().contains("bad_dng"))return false;Files.writeString(p,"raw");if(extra)Files.writeString(Path.of(p.toString().replace(".dng","_RAW_UNFILTERED.dng")),"original");return true;}catch(Exception e){throw new RuntimeException(e);}
 }
}}''',
'com/particlesdevs/photoncamera/processing/M9DngProfileExport.java':'''package com.particlesdevs.photoncamera.processing;
import java.nio.file.*;import java.util.concurrent.*;import org.json.*;
public class M9DngProfileExport {
 public static final ConcurrentMap<Path,Boolean> calls=new ConcurrentHashMap<>();
 public static JSONObject embed(Path p,String json,boolean succeeded){calls.put(p,succeeded);try {if(succeeded){if(new JSONObject(json).getInt("bank")!=3)throw new AssertionError("capture bank lost");Files.writeString(p,"+profile",StandardOpenOption.APPEND);}return new JSONObject();}catch(Exception e){throw new RuntimeException(e);}}
}'''
}

# Reuse the accepted harness adapters, extending only timing/failure controls.
stubs['com/particlesdevs/photoncamera/m9/M9SaveFeedback.java']='package com.particlesdevs.photoncamera.m9;public class M9SaveFeedback {public static void initialize(){}}'
stubs['com/particlesdevs/photoncamera/processing/ImageFrame.java']=stubs['com/particlesdevs/photoncamera/processing/ImageFrame.java'].replace('public long timestamp=1;','public java.nio.file.Path rawPair;public long timestamp=1;')
stubs['com/particlesdevs/photoncamera/m9/render/M9PhotonBoundary2Q.java']=stubs['com/particlesdevs/photoncamera/m9/render/M9PhotonBoundary2Q.java'].replace('savedRawPairPath(Object f){return null;}','savedRawPairPath(Object f){return ((com.particlesdevs.photoncamera.processing.ImageFrame)f).rawPair;}')
stubs['com/particlesdevs/photoncamera/processing/ImageSaver.java']=stubs['com/particlesdevs/photoncamera/processing/ImageSaver.java'].replace('if(extra)Files.writeString(Path.of(p.toString().replace(".dng","_RAW_UNFILTERED.dng")),"original");','if(extra&&!p.toString().contains("bad_extra")){f.rawPair=Path.of(p.toString().replace(".dng","_RAW_UNFILTERED.dng"));Files.writeString(f.rawPair,"original");}')
stubs['com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java']=stubs['com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'].replace('Result r=new Result();','if(p.toString().contains("throw_render"))throw new RuntimeException("synthetic render exception");Result r=new Result();')
stubs['com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java']='''package com.particlesdevs.photoncamera.m9.render;
import java.nio.file.Path;import java.util.concurrent.*;import com.particlesdevs.photoncamera.processing.ProcessingEventsListener;
public class M9JpegFinalizeQueue {
 public static final java.util.concurrent.atomic.AtomicInteger calls=new java.util.concurrent.atomic.AtomicInteger();
 public static volatile CountDownLatch entered,release;
 public static class Ticket {
  private final CountDownLatch done=new CountDownLatch(1);private volatile boolean success;
  public void awaitCompletion(){try{if(!done.await(5,TimeUnit.SECONDS))throw new AssertionError("JPEG timeout");}catch(InterruptedException e){throw new AssertionError(e);}}
  public boolean isSuccess(){return success;}public String error(){return "synthetic EXIF failure";}public void appendDiagnostics(org.json.JSONObject d){}
 }
 public static Ticket submit(Path p,Object e,ProcessingEventsListener listener){calls.incrementAndGet();Ticket t=new Ticket();
  Thread thread=new Thread(()->{try{if(entered!=null){entered.countDown();if(!release.await(5,TimeUnit.SECONDS))throw new AssertionError("JPEG gate");}t.success=!p.toString().contains("bad_jpeg");if(t.success)listener.notifyImageSavedStatus(true,p);}catch(Throwable failure){t.success=false;}finally{t.done.countDown();}},"TestExif");thread.setDaemon(true);thread.start();return t;}
}'''
stubs['com/particlesdevs/photoncamera/processing/M9DngProfileExport.java']='''package com.particlesdevs.photoncamera.processing;
import java.nio.file.*;import java.util.concurrent.*;import org.json.*;
public class M9DngProfileExport {
 public static final ConcurrentMap<Path,Boolean> calls=new ConcurrentHashMap<>();public static volatile CountDownLatch entered,release;
 public static JSONObject embed(Path p,String json,boolean succeeded){calls.put(p,succeeded);try{
  if(entered!=null){entered.countDown();if(!release.await(5,TimeUnit.SECONDS))throw new AssertionError("profile gate");}
  boolean ok=succeeded&&!p.toString().contains("bad_profile");
  if(ok){if(new JSONObject(json).getInt("bank")!=3)throw new AssertionError("capture bank lost");Files.writeString(p,"+profile",StandardOpenOption.APPEND);}
  return new JSONObject().put("status",ok?"embedded":"bypassed_original_raw_preserved");
 }catch(Exception e){throw new RuntimeException(e);}}
}'''

stubs['com/particlesdevs/photoncamera/processing/render/M9CaptureParameters.java']='''package com.particlesdevs.photoncamera.processing.render;
public class M9CaptureParameters {
 public static volatile int selected;public static volatile boolean failFreeze;private final int id;
 private static final ThreadLocal<Integer> active=new ThreadLocal<>();
 private M9CaptureParameters(){id=selected;}
 public static M9CaptureParameters freeze(android.hardware.camera2.CameraCharacteristics c){if(failFreeze)throw new IllegalStateException("snapshot failure");return new M9CaptureParameters();}
 public Scope open(){return new Scope(id);}public static class Scope implements AutoCloseable{Integer old;Scope(int id){old=active.get();active.set(id);}public void close(){if(old==null)active.remove();else active.set(old);}}
 public static void check(Object f,Object c,Object r,Object q,int rotation,boolean render){
  com.particlesdevs.photoncamera.processing.ImageFrame frame=(com.particlesdevs.photoncamera.processing.ImageFrame)f;
  if(frame.checkCapture && (!java.util.Objects.equals(active.get(),frame.expectedId)||c!=frame.expectedC||r!=frame.expectedR||rotation!=frame.expectedRotation||(render&&q!=frame.expectedQ)))throw new AssertionError("capture inputs mixed or missing scope");
 }
}'''
stubs['com/particlesdevs/photoncamera/processing/ImageFrame.java']=stubs['com/particlesdevs/photoncamera/processing/ImageFrame.java'].replace('public long timestamp=1;','public boolean checkCapture;public int expectedId,expectedRotation,expectedContrast;public Object expectedC,expectedR,expectedQ;public long timestamp=1;')
stubs['com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java']=stubs['com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'].replace('if(p.toString().contains("throw_render"))','com.particlesdevs.photoncamera.processing.ImageFrame cf=(com.particlesdevs.photoncamera.processing.ImageFrame)f;if(cf.checkCapture&&cf.expectedContrast!=contrast)throw new AssertionError("queued contrast changed");com.particlesdevs.photoncamera.processing.render.M9CaptureParameters.check(f,c,cr,rq,rotation,true);if(p.toString().contains("throw_render"))')
stubs['com/particlesdevs/photoncamera/processing/ImageSaver.java']=stubs['com/particlesdevs/photoncamera/processing/ImageSaver.java'].replace('calls.incrementAndGet();try','com.particlesdevs.photoncamera.processing.render.M9CaptureParameters.check(f,c,cr,null,rotation,false);calls.incrementAndGet();try')
for name,s in stubs.items():p=stub/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
prod=[src/'m9/M9SaveSelection.java',src/'m9/M9SaveStatus.java',src/'m9/render/M9PrimaryRenderQueue.java']
subprocess.run(['java','com.sun.tools.javac.Main','-cp',str(jar),'-d',str(classes),*map(str,stub.rglob('*.java')),*map(str,prod),str(HERE.parent/'savemode1a/SaveModeHostProbe.java'),str(HERE.parent/'settingsstatus1a/SaveStatusHostProbe.java'),str(HERE/'CaptureQueueHostProbe.java')],check=True)
logs=[]
for probe,folder in [('SaveModeHostProbe','save_modes'),('SaveStatusHostProbe','status'),('CaptureQueueHostProbe','capture_queue')]:
 logs.append(subprocess.check_output(['java','-cp',str(classes)+':'+str(jar),probe,str(out/folder)],text=True))
assert 'SAVE_MODE_CASES=11' in logs[0]
assert 'SAVE_STATUS_CASES=19' in logs[1],logs[1]
report=dict(status='passed',productionSaveModeCases=11,productionSaveStatusCases=19,requestedFilesOnly=True,waitsForExifAndProfile=True,overlappingCaptures=True,observerDetachResume=True,partialFailuresVisible=True,queueRejectionVisible=True,staleAcknowledgementSafe=True,frameClosedExactlyOnce=True,handsetValidationPending=True)
(out/'STATUS_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(''.join(logs));print(json.dumps(report))

assert 'CAPTURE_QUEUE_CASES=5' in logs[2],logs[2]
print(logs[2])
(out/'QUEUE_VERIFICATION.json').write_text(json.dumps({'status':'passed','saveModeCases':11,'saveStatusCases':19,'captureQueueCases':5,'captureQueueEvidence':logs[2]},indent=2)+'\n')
