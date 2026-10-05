"""Run production queues/status with deterministic Android/renderer/storage adapters.
Real ThreadPoolExecutors, bounds, callbacks and frame ownership; no photographic parity claim.
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
for name in ['m9.render.M9PrimaryRenderQueue','m9.render.M9JpegFinalizeQueue','m9.M9SaveSelection','m9.M9SaveStatus']:
 rel=Path((pkg+name).replace('.','/')+'.java');dest=src/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'app/src/main/java'/rel,dest)
write('android.os.Process','public class Process {public static final int THREAD_PRIORITY_BACKGROUND=10, THREAD_PRIORITY_DEFAULT=0; public static void setThreadPriority(int p) {}}')
write('android.hardware.camera2.CameraCharacteristics','public class CameraCharacteristics {}')
write('android.hardware.camera2.CaptureResult','public class CaptureResult {}')
write('android.hardware.camera2.CaptureRequest','public class CaptureRequest {public Object tag; public Object getTag(){return tag;}}')
write('android.media.MediaScannerConnection','public class MediaScannerConnection {public static void scanFile(Object c,String[] p,String[] m,Object cb){}}')
stub('util.Log','public class Log {public static void d(String t,String m){} public static void e(String t,String m){} public static void e(String t,String m,Throwable e){}}')
stub('app.PhotonCamera','public class PhotonCamera {public static Object getAppContext(){return null;} public static String getVersion(){return "host";}}')
stub('settings.PreferenceKeys','public class PreferenceKeys {public static volatile int mode; public static int isSaveRaw(){return mode;}}')
stub('m9.M9OutputSettings','public class M9OutputSettings {public static boolean saveUnfilteredDng(){return false;}}')
stub('m9.M9SaveFeedback','public class M9SaveFeedback {public static void initialize(){}}')
stub('m9.M9DeferredMetadataStore','public class M9DeferredMetadataStore {public static boolean persistAsyncForDng(java.nio.file.Path p){return true;}}')
stub('renderprofile.RenderProfile','public class RenderProfile {public static boolean isMonochrom(){return false;}}')
stub('monochrom.render.MonoSaveQueue','public class MonoSaveQueue {public static boolean preflightCaptureAdmission(){return true;}}')
stub('m9.M9ExposurePlan1A','public class M9ExposurePlan1A {public M9Bracket1A.Frame bracket;}')
stub('m9.M9Bracket1A','public class M9Bracket1A {public static class Frame {public int saturation,contrast,sharpness,saveMode;public boolean unfiltered;}public static class Completion {public final int issues;public Completion(Frame b,int i){issues=i;}}}')
stub('m9.capture.M9CaptureRequestAudit1A','public class M9CaptureRequestAudit1A {public static org.json.JSONObject take(long t,Object r){return new org.json.JSONObject().put("timestamp",t);}}')
for c in ['Saturation','Contrast','Sharpness']:stub('m9.render.M9'+c+'Settings','public class M9'+c+'Settings {public static int selected(){return 2;}}')
stub('processing.render.M9CaptureParameters','public class M9CaptureParameters {public static M9CaptureParameters freeze(Object c){return new M9CaptureParameters();}public Scope open(){return new Scope();}public static class Scope implements AutoCloseable {public void close(){}}}')
stub('processing.ImageFrame','''public class ImageFrame {
 public java.nio.ByteBuffer buffer=java.nio.ByteBuffer.allocate(32);public int packedBits;public long timestamp;
 public final java.util.concurrent.atomic.AtomicInteger closes=new java.util.concurrent.atomic.AtomicInteger();
 public void close(){if(closes.incrementAndGet()!=1)throw new AssertionError("double close");buffer=null;}
 public void live(){if(buffer==null)throw new AssertionError("use after close");}
}''')
stub('processing.ProcessingEventsListener','public interface ProcessingEventsListener {void notifyImageSavedStatus(boolean ok,java.nio.file.Path p); default void onProcessingFinished(Object o){}}')
stub('processing.ImageSaver','''public class ImageSaver {public static class Util {public static boolean saveSingleRawM9PhysicalCfa(java.nio.file.Path p,ImageFrame f,Object c,Object r,int rot,boolean raw){f.live();com.particlesdevs.photoncamera.m9.render.QueueHarness.dngs.incrementAndGet();return true;}}}''')
stub('processing.M9DngProfileExport','public class M9DngProfileExport {public static org.json.JSONObject embed(java.nio.file.Path p,String j,boolean ok){return new org.json.JSONObject().put("status","embedded");}}')
stub('m9.render.M9PhotonBoundary2Q','''public class M9PhotonBoundary2Q {
 public static void frame(com.particlesdevs.photoncamera.processing.ImageFrame f,String s,Object r,Object id){f.live();}
 public static java.nio.file.Path savedRawPairPath(com.particlesdevs.photoncamera.processing.ImageFrame f){f.live();return null;}
 public static org.json.JSONObject finish(com.particlesdevs.photoncamera.processing.ImageFrame f,boolean d){f.live();return new org.json.JSONObject().put("frameId",f.timestamp);}
}''')
stub('m9.render.M9PrimaryTimingWriter','''public class M9PrimaryTimingWriter {
 public static final java.util.concurrent.ConcurrentHashMap<String,org.json.JSONObject> reports=new java.util.concurrent.ConcurrentHashMap<>();
 public static boolean freezeAndWriteAsync(Object... args){reports.put(args[0].toString(),args[26]==null?new org.json.JSONObject():new org.json.JSONObject(args[26].toString()));return true;}
 public static void writeRejectedAsync(Object... args){}
}''')
stub('m9.preview.M9ShutterTrace1A','public class M9ShutterTrace1A {public static void finalized(java.nio.file.Path p,boolean ok){}}')
stub('api.ParseExif','''public class ParseExif {
 public static class ExifData {public String DATETIME="2026:10:05 08:00:00", F_NUMBER="1.6", PHOTOGRAPHIC_SENSITIVITY="1600";}
 public static androidx.exifinterface.media.ExifInterface setAllAttributes(java.io.File f,ExifData e){return new androidx.exifinterface.media.ExifInterface(f.toString());}
}''')
write('androidx.exifinterface.media.ExifInterface','''public class ExifInterface {
 public static final String TAG_DATETIME="dt",TAG_DATETIME_ORIGINAL="dto",TAG_DATETIME_DIGITIZED="dtd",TAG_ORIENTATION="or",TAG_COMPRESSION="co",TAG_SOFTWARE="sw",TAG_APERTURE_VALUE="av";public static final int ORIENTATION_NORMAL=1;
 private final String path;public ExifInterface(String p){path=p;}public void setAttribute(String k,String v){}
 public void saveAttributes(){com.particlesdevs.photoncamera.m9.render.QueueHarness.exif(path);}
}''')
stub('m9.render.M9R35Renderer','''public class M9R35Renderer {
 public static class Result {public java.nio.file.Path jpegPath;public boolean success;public String error;public org.json.JSONObject diagnostics;public com.particlesdevs.photoncamera.api.ParseExif.ExifData jpegExifData;}
 public static Result renderAndSavePrimary(java.nio.file.Path p,com.particlesdevs.photoncamera.processing.ImageFrame f,Object c,Object r,Object q,int rot,int sat,int con,int sharp,boolean jpeg){
 f.live();QueueHarness.renders.incrementAndGet();if(QueueHarness.scenario.equals("render_throw"))throw new IllegalStateException("render");
 Result v=new Result();v.success=!QueueHarness.scenario.equals("render_failure");v.error=v.success?null:"render failed";
 v.jpegPath=jpeg?java.nio.file.Paths.get(p.toString()+".jpg"):null;
 v.diagnostics=new org.json.JSONObject().put("rendererFrameId",f.timestamp);v.jpegExifData=QueueHarness.scenario.equals("missing_exif")?null:new com.particlesdevs.photoncamera.api.ParseExif.ExifData();return v;
 }
}''')
stub('m9.render.QueueHarness',r'''
import java.nio.file.*;import java.util.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;import java.util.function.*;
import com.particlesdevs.photoncamera.processing.*;import com.particlesdevs.photoncamera.settings.PreferenceKeys;import com.particlesdevs.photoncamera.m9.*;
public class QueueHarness {
 public static String scenario;public static final AtomicInteger renders=new AtomicInteger(),dngs=new AtomicInteger(),publications=new AtomicInteger(),completions=new AtomicInteger();
 public static final CountDownLatch exifEntered=new CountDownLatch(1),gate=new CountDownLatch(1),publishEntered=new CountDownLatch(1);
 public static final Set<String> exifDone=ConcurrentHashMap.newKeySet();public static final List<ImageFrame> frames=new ArrayList<>();public static volatile boolean holdExif,holdPublish;
 static void check(boolean ok,String m){if(!ok)throw new AssertionError(m);}
 static void await(CountDownLatch l){try{check(l.await(8,TimeUnit.SECONDS),"latch timeout");}catch(InterruptedException e){throw new AssertionError(e);}}
 static void until(BooleanSupplier b,String m){long end=System.nanoTime()+8_000_000_000L;while(!b.getAsBoolean()){if(System.nanoTime()>end)throw new AssertionError(m);Thread.yield();}}
 public static void exif(String p){exifEntered.countDown();if(holdExif)await(gate);if(scenario.equals("exif_failure"))throw new IllegalStateException("disk full");exifDone.add(p);}
 static ProcessingEventsListener events=new ProcessingEventsListener(){public void notifyImageSavedStatus(boolean ok,Path p){if(p.toString().endsWith(".jpg")){check(exifDone.contains(p.toString()),"published before EXIF");publishEntered.countDown();if(holdPublish)await(gate);if(scenario.equals("publish_failure"))throw new IllegalStateException("publication");}publications.incrementAndGet();}public void onProcessingFinished(Object o){completions.incrementAndGet();}};
 static ImageFrame shot(int n){ImageFrame f=new ImageFrame();f.timestamp=n;frames.add(f);check(M9PrimaryRenderQueue.enqueue(Paths.get("shot"+n+".dng"),f,null,null,null,0,1,2,events),"enqueue failed");return f;}
 static void drained(int expected){until(()->M9SaveStatus.INSTANCE.snapshot().pending==0,"save tickets stuck");until(()->frames.stream().allMatch(f->f.closes.get()==1),"RAW not closed exactly once");until(()->M9PrimaryTimingWriter.reports.size()>=expected,"timing missing");}
 static void jpegReports(int count){for(int i=1;i<=count;i++){org.json.JSONObject d=M9PrimaryTimingWriter.reports.get("shot"+i+".dng");check(d!=null,"missing shot");check(d.getInt("rendererFrameId")==i,"render diagnostics mixed");check(d.getJSONObject("photonBoundary2Q").getInt("frameId")==i,"frame diagnostics mixed");check(d.getJSONObject("photonUpstream2R").getInt("rawBufferCapacityBytes")==32,"snapshot after close");check(!d.getBoolean("jpegOnlyCompletionRetainsRaw"),"RAW retained");}}
 public static void main(String[] args)throws Exception{
 scenario=args[0];PreferenceKeys.mode=0;
 if(scenario.equals("delayed_exif")||scenario.equals("delayed_publish")){
  holdExif=scenario.equals("delayed_exif");holdPublish=!holdExif;shot(1);await(holdExif?exifEntered:publishEntered);shot(2);
  until(()->frames.get(1).closes.get()==1,"second render blocked by save");check(renders.get()==2,"second renderer did not run");check(frames.get(0).closes.get()==1,"first RAW retained");
  check(M9SaveStatus.INSTANCE.snapshot().pending==2,"saved too early");check(M9SaveStatus.INSTANCE.snapshot().saved==0,"early save");check(M9PrimaryRenderQueue.preflightCaptureAdmission(),"capacity retained");
  // Settings changes after enqueue cannot add a DNG or change either frozen result.
  PreferenceKeys.mode=2;gate.countDown();drained(2);check(dngs.get()==0,"settings leaked");check(M9SaveStatus.INSTANCE.snapshot().saved==2,"save count");jpegReports(2);
 }else if(scenario.equals("saturation")){
  holdExif=true;shot(1);await(exifEntered);shot(2);until(()->frames.get(1).closes.get()==1,"second release");shot(3);until(()->frames.get(2).closes.get()==1,"third release");shot(4);
  until(()->renders.get()==4,"fourth render");until(()->{try{java.lang.reflect.Field f=M9JpegFinalizeQueue.class.getDeclaredField("FALLBACK_COUNT");f.setAccessible(true);return ((AtomicLong)f.get(null)).get()==1;}catch(Exception e){throw new RuntimeException(e);}},"fallback missing");
  check(frames.get(3).closes.get()==0,"fallback returned early");shot(5);shot(6);check(!M9PrimaryRenderQueue.preflightCaptureAdmission(),"renderer exceeded bound");
  ImageFrame rejected=new ImageFrame();check(!M9PrimaryRenderQueue.enqueue(Paths.get("rejected.dng"),rejected,null,null,null,0,0,0,events),"unbounded renderer");check(rejected.closes.get()==0,"rejected frame ownership stolen");rejected.close();
  gate.countDown();drained(6);check(M9SaveStatus.INSTANCE.snapshot().saved==6,"dropped save");check(M9SaveStatus.INSTANCE.snapshot().failed==1,"rejection status");jpegReports(6);
  check(M9PrimaryTimingWriter.reports.get("shot4.dng").getBoolean("jpegExifSyncFallback"),"fallback diagnostics missing");
 }else if(scenario.equals("raw_jpeg")||scenario.equals("raw_only")){
  PreferenceKeys.mode=scenario.equals("raw_only")?2:1;holdExif=PreferenceKeys.mode==1;shot(1);
  if(holdExif){await(exifEntered);until(()->dngs.get()==1,"DNG worker did not start");check(frames.get(0).closes.get()==0,"RAW released before DNG finalization");check(M9SaveStatus.INSTANCE.snapshot().pending==1,"RAW+JPEG completed early");gate.countDown();}
  drained(1);check(dngs.get()==1,"DNG missing");check(M9SaveStatus.INSTANCE.snapshot().saved==1,"RAW save failed");check(publications.get()==(PreferenceKeys.mode==2?1:2),"publication count");
 }else if(scenario.equals("bracket")){
  ImageFrame f=new ImageFrame();f.timestamp=1;frames.add(f);android.hardware.camera2.CaptureRequest req=new android.hardware.camera2.CaptureRequest();M9ExposurePlan1A plan=new M9ExposurePlan1A();plan.bracket=new M9Bracket1A.Frame();plan.bracket.saveMode=0;req.tag=plan;
  holdExif=true;check(M9PrimaryRenderQueue.enqueue(Paths.get("shot1.dng"),f,null,null,req,0,0,0,events),"bracket enqueue");await(exifEntered);until(()->f.closes.get()==1,"bracket RAW retained");check(completions.get()==0,"bracket advanced before save");gate.countDown();drained(1);until(()->completions.get()==1,"bracket completion missing");
 }else if(scenario.equals("fast_completions")){
  AtomicInteger callbacks=new AtomicInteger();List<M9JpegFinalizeQueue.Ticket> tickets=new ArrayList<>();
  for(int i=0;i<250;i++)tickets.add(M9JpegFinalizeQueue.submit(Paths.get("fast"+i+".jpg"),new com.particlesdevs.photoncamera.api.ParseExif.ExifData(),events,t->{check(t.isSuccess(),"callback before success");callbacks.incrementAndGet();}));
  for(M9JpegFinalizeQueue.Ticket t:tickets)t.awaitCompletion();until(()->callbacks.get()==250,"lost callback");check(publications.get()==250,"duplicate or missing publication");
 }else if(scenario.equals("callback_failure")){
  M9JpegFinalizeQueue.Ticket first=M9JpegFinalizeQueue.submit(Paths.get("a.jpg"),new com.particlesdevs.photoncamera.api.ParseExif.ExifData(),events,t->{throw new IllegalStateException("callback test");});first.awaitCompletion();
  M9JpegFinalizeQueue.Ticket second=M9JpegFinalizeQueue.submit(Paths.get("b.jpg"),new com.particlesdevs.photoncamera.api.ParseExif.ExifData(),events,t->completions.incrementAndGet());second.awaitCompletion();until(()->completions.get()==1,"worker died");check(second.isSuccess(),"later save failed");
 }else{
  shot(1);drained(1);check(M9SaveStatus.INSTANCE.snapshot().failed==1,"failure hidden");check(M9SaveStatus.INSTANCE.snapshot().saved==0,"failed photo counted saved");check(dngs.get()==0,"unexpected DNG");
  int expected=scenario.equals("render_throw")||scenario.equals("missing_exif")?M9SaveStatus.PROCESSING:M9SaveStatus.JPEG;check(M9SaveStatus.INSTANCE.snapshot().issues==expected,"wrong failure");
 }
 // Structural guard: detached completion fields cannot own RAW, bitmap, renderer result or capture state.
 Class<?> c=Class.forName("com.particlesdevs.photoncamera.m9.render.M9PrimaryRenderQueue$JpegCompletion");
 Set<String> allowed=new HashSet<>(Arrays.asList("java.nio.file.Path","com.particlesdevs.photoncamera.m9.M9SaveStatus$Ticket","java.lang.String","long","com.particlesdevs.photoncamera.m9.render.M9PrimaryRenderQueue$QueueTelemetry"));
 for(java.lang.reflect.Field f:c.getDeclaredFields())check(allowed.contains(f.getType().getName()),"heavy completion field: "+f);
 System.out.println("PASS "+scenario);
 }
}
''')
cp=str(a.json_jar.resolve())
subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-cp',cp,'-d',str(classes)]+[str(f) for f in src.rglob('*.java')],check=True)
cases=['delayed_exif','delayed_publish','saturation','raw_jpeg','raw_only','bracket','fast_completions','callback_failure','exif_failure','publish_failure','render_failure','render_throw','missing_exif']
for case in cases:subprocess.run(['java','-cp',str(classes)+':'+cp,pkg+'m9.render.QueueHarness',case],check=True,timeout=25)
report=dict(status='PASS',cases=cases,caseCount=len(cases),fastFinalizations=250,productionClasses=['M9PrimaryRenderQueue','M9JpegFinalizeQueue','M9SaveStatus','M9SaveSelection'],adapters='Android, renderer, EXIF storage, DNG storage, diagnostic IO',limits='Host concurrency/ownership verification, not device timing or photographic output verification')
(out/'QUEUE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');(Path(__file__).parent/'QUEUE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
