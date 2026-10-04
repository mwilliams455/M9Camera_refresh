import android.hardware.camera2.*;
import com.particlesdevs.photoncamera.m9.*;
import com.particlesdevs.photoncamera.m9.render.*;
import com.particlesdevs.photoncamera.processing.*;
import com.particlesdevs.photoncamera.processing.render.M9CaptureParameters;
import com.particlesdevs.photoncamera.settings.PreferenceKeys;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public class CaptureQueueHostProbe extends SaveStatusHostProbe {
 static final ConcurrentMap<Path,Integer> published=new ConcurrentHashMap<>();
 static ImageFrame shot(Path base,String name,int id,int rotation,int mode) throws Exception {
  Path dir=base.resolve(name);Files.createDirectories(dir);
  ImageFrame f=new ImageFrame();f.checkCapture=true;f.expectedId=id;f.expectedRotation=rotation;
  CameraCharacteristics c=new CameraCharacteristics();CaptureResult r=new CaptureResult();CaptureRequest q=new CaptureRequest();
  f.expectedC=c;f.expectedR=r;f.expectedQ=q;M9CaptureParameters.selected=id;PreferenceKeys.mode=mode;M9OutputSettings.extra=false;
  require(M9PrimaryRenderQueue.enqueue(dir.resolve("photo.dng"),f,c,r,q,rotation,0,0,(ok,p)->published.merge(p,1,Integer::sum)),"shot rejected");return f;
 }
 static void await(java.util.function.BooleanSupplier test) throws Exception {long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(5);while(!test.getAsBoolean()){if(System.nanoTime()>end)throw new AssertionError("wait timeout");Thread.sleep(2);}}
 public static void main(String[] args) throws Exception {
  Path base=Path.of(args[0]);require(!Files.exists(base),"fresh destination");
  // Three jobs wait behind renderer A; selected lens and rotation change per capture.
  M9R35Renderer.entered=new CountDownLatch(1);M9R35Renderer.release=new CountDownLatch(1);
  ImageFrame a=shot(base,"jpeg",0,0,0);require(M9R35Renderer.entered.await(5,TimeUnit.SECONDS),"render gate");
  ImageFrame b=shot(base,"pair",2,90,1),c=shot(base,"raw",3,270,2);
  require(!M9PrimaryRenderQueue.preflightCaptureAdmission(),"full renderer admitted another shot");
  M9CaptureParameters.selected=77;M9R35Renderer.release.countDown();drain(a,b,c);
  M9R35Renderer.entered=null;M9R35Renderer.release=null;
  require(Files.exists(base.resolve("jpeg/photo.jpg"))&&!Files.exists(base.resolve("jpeg/photo.dng")),"JPEG selection mixed");
  require(Files.exists(base.resolve("pair/photo.jpg"))&&Files.exists(base.resolve("pair/photo.dng")),"pair selection mixed");
  require(!Files.exists(base.resolve("raw/photo.jpg"))&&Files.exists(base.resolve("raw/photo.dng")),"RAW selection mixed");
  require(published.size()==4&&published.values().stream().allMatch(n->n==1),"missing/duplicate publication");result(3,0,0);

  // Genuine saturation: one active DNG, one pending, then render-thread fallback.
  M9DngProfileExport.entered=new CountDownLatch(3);M9DngProfileExport.release=new CountDownLatch(1);
  a=shot(base,"dng_active",0,0,2);
  await(()->M9DngProfileExport.entered.getCount()==2&&status.snapshot().pending==1);
  b=shot(base,"dng_pending",2,90,2);
  await(()->{try{return executor("DNG_EXECUTOR").getQueue().size()==1;}catch(Exception e){throw new RuntimeException(e);}});
  c=shot(base,"dng_fallback",3,180,2);
  await(()->M9DngProfileExport.entered.getCount()==1);
  M9CaptureParameters.selected=99;require(status.snapshot().pending==3,"early completion under saturation");
  M9DngProfileExport.release.countDown();drain(a,b,c);M9DngProfileExport.entered=null;M9DngProfileExport.release=null;
  result(3,0,0);

  // Reuse workers following a render exception: the next capture owns its inputs.
  a=shot(base,"throw_render",4,0,0);drain(a);result(0,1,M9SaveStatus.PROCESSING);
  a=shot(base,"after_exception",5,270,1);drain(a);result(1,0,0);

  // Snapshot failure is visible and ownership stays with DefaultSaver.
  M9CaptureParameters.failFreeze=true;ImageFrame rejected=new ImageFrame();
  try{M9PrimaryRenderQueue.enqueue(base.resolve("snapshot_failed.dng"),rejected,null,null,null,0,0,0,(s,p)->{});throw new AssertionError("missing failure");}catch(IllegalStateException expected){}
  require(rejected.closes.get()==0,"closed rejected RAW");rejected.close();result(0,1,M9SaveStatus.PROCESSING);
  require(published.values().stream().allMatch(n->n==1),"duplicate publication");
  System.out.println("CAPTURE_QUEUE_CASES=5: mixed lenses/rotation/output modes; real render capacity; real DNG saturation and synchronous fallback; exception recovery; snapshot failure ownership.");
 }
}
