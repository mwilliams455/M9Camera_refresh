"""Run production queues/status with deterministic Android/renderer/storage adapters.
Production Monochrom queues and durable spool; deterministic I/O adapters. Not a phone benchmark.
"""
from pathlib import Path
import argparse, json, shutil, subprocess
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--json-jar',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.source.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);src=out/'src';classes=out/'classes';classes.mkdir(exist_ok=True)
pkg='com.particlesdevs.photoncamera.'
def write(name,body):
 path=src/Path(name.replace('.','/')+'.java');path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text('package '+name.rsplit('.',1)[0]+';\n'+body)
def stub(name,body):write(pkg+name,body)
stub('api.ParseExif','''public class ParseExif {
 public static class ExifData {public String DATETIME="2026:10:05 08:00:00", F_NUMBER="1.6", PHOTOGRAPHIC_SENSITIVITY="1600";}
 public static androidx.exifinterface.media.ExifInterface setAllAttributes(java.io.File f,ExifData e){return new androidx.exifinterface.media.ExifInterface(f.toString());}
}''')
write('androidx.exifinterface.media.ExifInterface','''public class ExifInterface {
 public static final String TAG_DATETIME="dt",TAG_DATETIME_ORIGINAL="dto",TAG_DATETIME_DIGITIZED="dtd",TAG_ORIENTATION="or",TAG_COMPRESSION="co",TAG_SOFTWARE="sw",TAG_APERTURE_VALUE="av";public static final int ORIENTATION_NORMAL=1;
 private final String path;public ExifInterface(String p){path=p;}public void setAttribute(String k,String v){}
 public void saveAttributes(){com.particlesdevs.photoncamera.monochrom.render.QueueHarness.exif(path);}
}''')
for name in ['monochrom.render.MonoSaveQueue','monochrom.render.M9JpegFinalizeQueue','m9.M9SaveSelection','m9.M9SaveStatus','monochrom.export.MonoDngPublisherWake','monochrom.export.MonoDngSpool1B']:
 rel=Path((pkg+name).replace('.','/')+'.java');dest=src/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'app/src/main/java'/rel,dest)
write('android.os.Process','public class Process {public static final int THREAD_PRIORITY_BACKGROUND=10;public static void setThreadPriority(int p){}}')
write('android.graphics.Point','public class Point {public Point(int x,int y){}}')
write('android.hardware.camera2.CameraCharacteristics','public class CameraCharacteristics {}')
write('android.hardware.camera2.CaptureResult','public class CaptureResult {public static final Object SENSOR_SENSITIVITY=new Object();public Integer get(Object k){return 100;}}')
write('android.hardware.camera2.CaptureRequest','public class CaptureRequest {}')
stub('util.Log','public class Log {public static void d(String t,String m){}public static void e(String t,String m,Throwable e){}}')
stub('app.PhotonCamera','public class PhotonCamera {public static com.particlesdevs.photoncamera.capture.CaptureController getCaptureController(){return new com.particlesdevs.photoncamera.capture.CaptureController();}public static void showToast(String s){}}')
stub('capture.CaptureController','public class CaptureController {public void onMonoSaveCompleted(int issues){com.particlesdevs.photoncamera.monochrom.render.QueueHarness.callback(issues);}}')
stub('processing.render.M9CaptureParameters','public class M9CaptureParameters {public static M9CaptureParameters freeze(Object c){return new M9CaptureParameters();}public Scope open(){return new Scope();}public static class Scope implements AutoCloseable {public void close(){}}}')
stub('renderprofile.ProfileCapture','''public class ProfileCapture {
 public static volatile int mode;public static volatile boolean original,diagnostics=true;
 public static final ThreadLocal<Snapshot> active=new ThreadLocal<>();
 public static Snapshot forRequest(Object r){return new Snapshot(mode,original,diagnostics);}
 public static class Snapshot {public final int mode;public final boolean original,diagnostics;Snapshot(int m,boolean o,boolean d){mode=m;original=o;diagnostics=d;}public Scope open(){return new Scope(this);}}
 public static class Scope implements AutoCloseable {final Snapshot old;Scope(Snapshot s){old=active.get();active.set(s);}public void close(){if(old==null)active.remove();else active.set(old);}}
}''')
stub('settings.PreferenceKeys','''public class PreferenceKeys {
 public static int getMonoSaveMode(){return com.particlesdevs.photoncamera.renderprofile.ProfileCapture.active.get().mode;}
 public static boolean isMonoOriginalSensorRawEnabled(){return com.particlesdevs.photoncamera.renderprofile.ProfileCapture.active.get().original;}
 public static boolean isMonoDiagnosticsEnabled(){return com.particlesdevs.photoncamera.renderprofile.ProfileCapture.active.get().diagnostics;}
}''')
stub('processing.ImageFrame','''public class ImageFrame {
 public java.nio.ByteBuffer buffer=java.nio.ByteBuffer.allocate(32);public int width=4,height=4,cropOriginX,cropOriginY,fullWidth,fullHeight,id;
 public final java.util.concurrent.atomic.AtomicInteger closes=new java.util.concurrent.atomic.AtomicInteger();
 public void close(){if(closes.incrementAndGet()!=1)throw new AssertionError("double close");buffer=null;}
 public void live(){if(buffer==null)throw new AssertionError("use after close");}
}''')
stub('processing.Parameters','public class Parameters {public int cameraRotation;public void FillConstParameters(Object c,Object p){}public void setCropDetails(int x,int y){}public void setFullRawSize(int w,int h){}public void FillDynamicParameters(Object r,Object q,int iso){}}')
stub('processing.ProcessingEventsListener','public interface ProcessingEventsListener {void notifyImageSavedStatus(boolean ok,java.nio.file.Path p);void onProcessingError(String s);}')
stub('processing.ImageSaver','''public class ImageSaver {public static class Util {public static boolean saveSingleRaw(java.nio.file.Path p,java.nio.ByteBuffer b,Parameters data){if(b==null)throw new AssertionError("closed before original RAW");com.particlesdevs.photoncamera.monochrom.render.QueueHarness.raws.incrementAndGet();return !com.particlesdevs.photoncamera.monochrom.render.QueueHarness.scenario.equals("raw_failure");}}}''')
stub('monochrom.M9DeferredMetadataStore','''public class M9DeferredMetadataStore {public static void persistAsyncForDng(java.nio.file.Path p,org.json.JSONObject d){if(com.particlesdevs.photoncamera.renderprofile.ProfileCapture.active.get()==null)throw new AssertionError("missing frozen scope");com.particlesdevs.photoncamera.monochrom.render.QueueHarness.metadata.incrementAndGet();if(com.particlesdevs.photoncamera.monochrom.render.QueueHarness.scenario.equals("metadata_failure"))throw new IllegalStateException("metadata");}}''')
stub('monochrom.M9DiagnosticBurstSpool','''public class M9DiagnosticBurstSpool {
 public static final java.util.concurrent.ConcurrentHashMap<String,org.json.JSONObject> reports=new java.util.concurrent.ConcurrentHashMap<>();
 public static boolean stage(java.nio.file.Path p,byte[] b,String kind){if(!com.particlesdevs.photoncamera.settings.PreferenceKeys.isMonoDiagnosticsEnabled())throw new AssertionError("diagnostic scope changed");reports.put(p.toString(),new org.json.JSONObject(new String(b,java.nio.charset.StandardCharsets.UTF_8)));return true;}
}''')
stub('monochrom.export.MonoDngExport1A','''public class MonoDngExport1A {public static boolean canAdmitCapture1B(){return true;}public static boolean awaitPublished(String p,long timeout){return com.particlesdevs.photoncamera.monochrom.render.QueueHarness.dng(p);}}''')
stub('monochrom.render.M9R35Renderer','''public class M9R35Renderer {
 public static class Result {public java.nio.file.Path jpegPath;public boolean success;public String error;public org.json.JSONObject diagnostics;public com.particlesdevs.photoncamera.api.ParseExif.ExifData jpegExifData;}
 public static Result renderAndSavePrimary(java.nio.file.Path p,com.particlesdevs.photoncamera.processing.ImageFrame f,Object c,Object r,Object q,int rot){
 f.live();QueueHarness.renders.incrementAndGet();if(QueueHarness.scenario.equals("render_throw"))throw new IllegalStateException("render");
 Result v=new Result();v.success=!QueueHarness.scenario.equals("render_failure");v.error="render failed";
 v.jpegPath=java.nio.file.Paths.get(p.toString()+".jpg");v.jpegExifData=QueueHarness.scenario.equals("missing_exif")?null:new com.particlesdevs.photoncamera.api.ParseExif.ExifData();
 v.diagnostics=new org.json.JSONObject().put("frameId",f.id).put("frozenMode",com.particlesdevs.photoncamera.settings.PreferenceKeys.getMonoSaveMode())
 .put("monoDngExport",new org.json.JSONObject().put("outputPath",p.toString()).put("privateStageComplete",!QueueHarness.scenario.equals("stage_failure")));
 return v;}
}''')
stub('monochrom.render.QueueHarness',r'''
import java.nio.file.*;import java.util.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;import java.util.function.*;
import com.particlesdevs.photoncamera.processing.*;import com.particlesdevs.photoncamera.renderprofile.ProfileCapture;import com.particlesdevs.photoncamera.m9.*;import com.particlesdevs.photoncamera.monochrom.M9DiagnosticBurstSpool;
public class QueueHarness {
 public static String scenario;public static final AtomicInteger renders=new AtomicInteger(),raws=new AtomicInteger(),publications=new AtomicInteger(),callbacks=new AtomicInteger(),metadata=new AtomicInteger(),dngs=new AtomicInteger();
 public static final CountDownLatch entered=new CountDownLatch(1),gate=new CountDownLatch(1);
 public static final Set<String> exifDone=ConcurrentHashMap.newKeySet();public static final List<ImageFrame> frames=new ArrayList<>();
 public static volatile boolean holdExif,holdPublish,holdDng;
 static void check(boolean ok,String m){if(!ok)throw new AssertionError(m);}
 public static void await(CountDownLatch l){try{check(l.await(8,TimeUnit.SECONDS),"latch timeout");}catch(InterruptedException e){throw new AssertionError(e);}}
 static void until(BooleanSupplier b,String m){long end=System.nanoTime()+8_000_000_000L;while(!b.getAsBoolean()){if(System.nanoTime()>end)throw new AssertionError(m);Thread.yield();}}
 public static void exif(String p){if(holdExif){entered.countDown();await(gate);}if(scenario.equals("exif_failure"))throw new IllegalStateException("disk full");exifDone.add(p);}
 public static boolean dng(String p){dngs.incrementAndGet();if(holdDng){entered.countDown();await(gate);}return !scenario.equals("dng_timeout");}
 public static void callback(int issues){callbacks.incrementAndGet();if(scenario.equals("callback_throw"))throw new IllegalStateException("detached UI");}
 static ProcessingEventsListener events=new ProcessingEventsListener(){public void notifyImageSavedStatus(boolean ok,Path p){if(p.toString().endsWith(".jpg")){check(exifDone.contains(p.toString()),"published before EXIF");if(holdPublish){entered.countDown();await(gate);}if(scenario.equals("publish_failure"))throw new IllegalStateException("publication");publications.incrementAndGet();}}public void onProcessingError(String s){}};
 static ImageFrame shot(int n){ImageFrame f=new ImageFrame();f.id=n;frames.add(f);check(MonoSaveQueue.enqueue(Paths.get("shot"+n+".dng"),f,new android.hardware.camera2.CameraCharacteristics(),new android.hardware.camera2.CaptureResult(),new android.hardware.camera2.CaptureRequest(),0,1,2,events),"enqueue failed");return f;}
 static void released(int index){until(()->frames.get(index-1).closes.get()==1,"RAW not released");}
 static void drained(int n){until(()->callbacks.get()==n,"missing or premature callback");until(()->M9SaveStatus.INSTANCE.snapshot().pending==0,"pending tickets");until(()->frames.stream().allMatch(f->f.closes.get()==1),"RAW ownership");until(MonoSaveQueue::preflightCaptureAdmission,"capacity not restored");}
 static void reports(int count,int mode){for(int i=1;i<=count;i++){org.json.JSONObject d=M9DiagnosticBurstSpool.reports.get("shot"+i+"_MONO_PRIMARY.json");check(d!=null,"missing diagnostics");check(d.getJSONObject("rendererDiagnostics").getInt("frameId")==i,"mixed diagnostic");check(d.getJSONObject("rendererDiagnostics").getInt("frozenMode")==mode,"settings leaked");check(!d.getBoolean("completionRetainsRaw"),"RAW retained");check(d.getLong("saveElapsedMs")>=0&&d.getLong("renderQueueWaitMs")>=0,"timings absent");}}
 static ThreadPoolExecutor executor(String field)throws Exception {var f=MonoSaveQueue.class.getDeclaredField(field);f.setAccessible(true);return (ThreadPoolExecutor)f.get(null);}
 public static void main(String[] args)throws Exception {
 scenario=args[0];ProfileCapture.mode=0;
 if(scenario.startsWith("delay_")) {
  holdExif=scenario.equals("delay_exif");holdPublish=scenario.equals("delay_publish");holdDng=scenario.equals("delay_dng");if(holdDng)ProfileCapture.mode=1;
  int mode=ProfileCapture.mode;shot(1);await(entered);shot(2);released(2);
  check(renders.get()==2,"second render blocked by first save");check(callbacks.get()==0&&M9SaveStatus.INSTANCE.snapshot().saved==0,"saved before final I/O");released(1);
  until(MonoSaveQueue::preflightCaptureAdmission,"capacity held by final I/O");
  ProfileCapture.mode=2;ProfileCapture.original=true;ProfileCapture.diagnostics=false;gate.countDown();drained(2);reports(2,mode);check(raws.get()==0,"output settings changed after shutter");check(M9SaveStatus.INSTANCE.snapshot().saved==2,"save count");
 } else if(scenario.equals("completion_saturation")||scenario.equals("exif_saturation")) {
  boolean completion=scenario.startsWith("completion");holdDng=completion;holdExif=!completion;ProfileCapture.mode=completion?2:0;
  shot(1);await(entered);shot(2);released(2);until(()->executorUnchecked("completionWorker").getQueue().size()==1,"second completion");shot(3);released(3);until(()->executorUnchecked("completionWorker").getQueue().size()==2,"third completion");shot(4);
  if(completion){released(4);until(()->dngs.get()==2,"sync completion fallback absent");}else until(()->renders.get()==4,"fourth render");
  until(()->executorUnchecked("worker").getQueue().isEmpty(),"fourth render not started");shot(5);shot(6);check(!MonoSaveQueue.preflightCaptureAdmission(),"RAW limit exceeded");
  ImageFrame rejected=new ImageFrame();check(!MonoSaveQueue.enqueue(Paths.get("reject.dng"),rejected,null,null,null,0,0,0,events),"unbounded render queue");check(rejected.closes.get()==0,"stolen rejected RAW");rejected.close();
  check(callbacks.get()==1,"pending photos completed early");gate.countDown();drained(7);check(M9SaveStatus.INSTANCE.snapshot().saved==6,"save lost");check(M9SaveStatus.INSTANCE.snapshot().failed==1,"rejection unreported");reports(6,ProfileCapture.mode);
  check(M9DiagnosticBurstSpool.reports.get("shot4_MONO_PRIMARY.json").getBoolean(completion?"completionSyncFallback":"jpegExifSyncFallback"),"fallback not recorded");
 } else if(scenario.startsWith("output_")) {
  ProfileCapture.mode=Integer.parseInt(scenario.substring(7,8));ProfileCapture.original=scenario.endsWith("raw");shot(1);drained(1);reports(1,ProfileCapture.mode);
  check(publications.get()==(ProfileCapture.mode==2?0:1),"JPEG selection");check(dngs.get()==(ProfileCapture.mode==0?0:1),"linear DNG selection");check(raws.get()==(ProfileCapture.original?1:0),"sensor RAW selection");check(M9SaveStatus.INSTANCE.snapshot().saved==1,"output completion");
 } else if(scenario.equals("fast")) {
  for(int i=1;i<=250;i++){shot(i);drained(i);}reports(250,0);check(M9SaveStatus.INSTANCE.snapshot().saved==250,"fast completion lost");
 } else if(scenario.equals("diagnostics_off")) {
  ProfileCapture.diagnostics=false;shot(1);drained(1);check(M9DiagnosticBurstSpool.reports.isEmpty(),"unexpected diagnostic files");check(metadata.get()==1,"metadata flush skipped");
 } else {
  if(scenario.equals("raw_failure"))ProfileCapture.original=true;
  if(scenario.equals("dng_timeout")||scenario.equals("stage_failure"))ProfileCapture.mode=1;
  shot(1);drained(1);boolean success=scenario.equals("callback_throw");check(M9SaveStatus.INSTANCE.snapshot().saved==(success?1:0),"incorrect saved state");check(M9SaveStatus.INSTANCE.snapshot().failed==(success?0:1),"incorrect failed state");
 }
 // The completion carrier is static and cannot retain a camera buffer or renderer result.
 Class<?> c=Class.forName("com.particlesdevs.photoncamera.monochrom.render.MonoSaveQueue$Completion");
 Set<String> allowed=Set.of("java.nio.file.Path","com.particlesdevs.photoncamera.renderprofile.ProfileCapture$Snapshot","com.particlesdevs.photoncamera.m9.M9SaveSelection","com.particlesdevs.photoncamera.m9.M9SaveStatus$Ticket","com.particlesdevs.photoncamera.monochrom.render.M9JpegFinalizeQueue$Ticket","com.particlesdevs.photoncamera.processing.ProcessingEventsListener","boolean","java.lang.String","long");
 for(var field:c.getDeclaredFields())check(allowed.contains(field.getType().getName()),"completion retains "+field.getType());
 check(executor("worker").getMaximumPoolSize()==1&&executor("worker").getQueue().remainingCapacity()==2,"renderer bound changed");
 check(executor("completionWorker").getMaximumPoolSize()==1&&executor("completionWorker").getQueue().remainingCapacity()==2,"completion bound changed");
 System.out.println("PASS "+scenario);
 }
 static ThreadPoolExecutor executorUnchecked(String n){try{return executor(n);}catch(Exception e){throw new RuntimeException(e);}}
}
''')
stub('monochrom.export.WakeHarness',r'''
import java.nio.file.*;import java.util.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;
public class WakeHarness {
 static void check(boolean b){if(!b)throw new AssertionError();}
 static class Manual implements Executor {ArrayDeque<Runnable> q=new ArrayDeque<>();boolean reject;public void execute(Runnable r){if(reject)throw new RejectedExecutionException();q.add(r);}void run(){q.remove().run();}}
 public static void main(String[] args)throws Exception {
  Manual e=new Manual();AtomicInteger calls=new AtomicInteger();MonoDngPublisherWake[] ref=new MonoDngPublisherWake[1];
  ref[0]=new MonoDngPublisherWake(e,()->{if(calls.incrementAndGet()==1)for(int i=0;i<1000;i++)ref[0].request();});
  for(int i=0;i<10000;i++)ref[0].request();check(e.q.size()==1);e.run();check(calls.get()==1&&e.q.size()==1);e.run();check(calls.get()==2&&e.q.isEmpty());
  e.reject=true;ref[0].request();e.reject=false;ref[0].request();check(e.q.size()==1);e.run();
  MonoDngPublisherWake failing=new MonoDngPublisherWake(e,()->{throw new IllegalStateException();});failing.request();try{e.run();throw new AssertionError();}catch(IllegalStateException ok){}failing.request();check(e.q.size()==1);e.q.clear();
  AtomicLong clock=new AtomicLong(10000);AtomicInteger attempts=new AtomicInteger();Path root=Files.createTempDirectory("mono-wake-");
  try(MonoDngSpool1B s=new MonoDngSpool1B(root,MonoDngSpool1B.Policy.normal(),clock::get,()->Long.MAX_VALUE,job->{attempts.incrementAndGet();throw new java.io.IOException("offline");},status->true)) {
   s.recover();s.stage(root.resolve("photo_MONO_LINEAR1A.dng"),"{}",64,out->{out.write(new byte[32]);return 32;});
   MonoDngPublisherWake wake=new MonoDngPublisherWake(e,()->{try{s.pump();}catch(Exception x){throw new RuntimeException(x);}});
   wake.request();e.run();check(attempts.get()==1);
   for(int i=0;i<100;i++){wake.request();e.run();}check(attempts.get()==1); // immediate wakes cannot bypass retry deadline
   clock.addAndGet(60000);wake.request();e.run();check(attempts.get()==2);check(Files.walk(root).anyMatch(p->p.getFileName().toString().equals("payload.dng")));
  }
  System.out.println("PASS wake_coalescing_during_pump_rejection_retry_retention");
 }
}
''')
javafiles=[str(x) for x in src.rglob('*.java')]
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',str(a.json_jar.resolve()),'-d',str(classes),*javafiles],check=True)
scenarios=['delay_exif','delay_publish','delay_dng','completion_saturation','exif_saturation']+[f'output_{m}_{r}' for m in range(3) for r in ['plain','raw']]+['render_throw','render_failure','missing_exif','exif_failure','publish_failure','raw_failure','dng_timeout','stage_failure','metadata_failure','callback_throw','diagnostics_off','fast']
passed=[]
for case in scenarios:
 subprocess.run(['java','-cp',str(classes)+':'+str(a.json_jar.resolve()),pkg+'monochrom.render.QueueHarness',case],check=True,timeout=25);passed.append(case)
subprocess.run(['java','-cp',str(classes)+':'+str(a.json_jar.resolve()),pkg+'monochrom.export.WakeHarness'],check=True,timeout=25);passed.append('wake_coalescing_during_pump_rejection_retry_retention')
(out/'QUEUE_TEST_RESULTS.json').write_text(json.dumps({'status':'PASS','scenarios':passed,'count':len(passed),'phoneBenchmark':False},indent=2)+'\n')
