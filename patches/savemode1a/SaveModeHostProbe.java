import com.particlesdevs.photoncamera.m9.*;
import com.particlesdevs.photoncamera.m9.render.*;
import com.particlesdevs.photoncamera.processing.*;
import com.particlesdevs.photoncamera.settings.PreferenceKeys;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public class SaveModeHostProbe {
 static int cases;
 static ThreadPoolExecutor executor(String name)throws Exception {
  java.lang.reflect.Field f=M9PrimaryRenderQueue.class.getDeclaredField(name);f.setAccessible(true);return (ThreadPoolExecutor)f.get(null);
 }
 static void require(boolean v,String why){if(!v)throw new AssertionError(why);}
 static void drain()throws Exception {
  long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(5);
  while(System.nanoTime()<deadline){
   ThreadPoolExecutor a=executor("EXECUTOR"),b=executor("DNG_EXECUTOR");
   if(a.getActiveCount()==0&&a.getQueue().isEmpty()&&b.getActiveCount()==0&&b.getQueue().isEmpty())return;
   Thread.sleep(2);
  }throw new AssertionError("queue stuck");
 }
 static void run(Path base,String name,int mode,boolean extra,boolean flip,boolean badRender,boolean badDng)throws Exception {
  Path dir=base.resolve(name);Files.createDirectories(dir);Path dng=dir.resolve("photo.dng");
  PreferenceKeys.mode=mode;M9OutputSettings.extra=extra;
  int rawBefore=ImageSaver.Util.calls.get(),jpegBefore=M9JpegFinalizeQueue.calls.get();
  List<Path> published=new CopyOnWriteArrayList<>();ImageFrame frame=new ImageFrame();
  if(flip){M9R35Renderer.entered=new CountDownLatch(1);M9R35Renderer.release=new CountDownLatch(1);}
  boolean accepted=M9PrimaryRenderQueue.enqueue(dng,frame,null,null,null,90,0,0,(success,p)->{require(success,"false success callback");published.add(p);});
  require(accepted,"unexpected rejection");
  if(flip){require(M9R35Renderer.entered.await(5,TimeUnit.SECONDS),"renderer did not start");PreferenceKeys.mode=2;M9OutputSettings.extra=true;M9R35Renderer.release.countDown();}
  long closeDeadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(5);
  while(frame.closes.get()==0&&System.nanoTime()<closeDeadline)Thread.sleep(2);
  require(frame.closes.get()>0,"frame never completed "+name);
  drain();M9R35Renderer.entered=null;M9R35Renderer.release=null;
  boolean jpeg=mode!=2&&!badRender,raw=mode!=0&&!badDng;
  require(Files.exists(dir.resolve("photo.jpg"))==jpeg,"JPEG existence "+name);
  require(Files.exists(dng)==raw,"DNG existence "+name);
  require(Files.exists(dir.resolve("photo_RAW_UNFILTERED.dng"))==(raw&&extra),"comparison existence "+name);
  require(ImageSaver.Util.calls.get()-rawBefore==(mode==0?0:1),"DNG writer calls "+name);
  require(M9JpegFinalizeQueue.calls.get()-jpegBefore==(jpeg?1:0),"JPEG finalizer calls "+name);
  require(published.size()==(jpeg?1:0)+(raw?1:0),"publication count "+name);
  require(published.contains(dng)==raw,"DNG publication "+name);
  if(raw){require(M9DngProfileExport.calls.get(dng)==!badRender,"profile success flag "+name);require(Files.readString(dng).contains("+profile")==!badRender,"profile retained "+name);}
  else require(!M9DngProfileExport.calls.containsKey(dng),"unexpected profile generation "+name);
  require(frame.closes.get()==1,"RAW frame close count "+name+": "+frame.closes);
  cases++;
 }
 public static void main(String[] args)throws Exception {
  Path base=Path.of(args[0]);require(!Files.exists(base),"use new case directory");
  for(int mode=0;mode<3;mode++)for(boolean extra:new boolean[]{false,true})run(base,"mode"+mode+"_extra"+extra,mode,extra,false,false,false);
  run(base,"frozen_jpeg",0,false,true,false,false);
  run(base,"bad_dng",2,false,false,false,true);
  run(base,"bad_render",2,false,false,true,false);
  // A rejected DNG executor must preserve both RAW modes synchronously.
  executor("DNG_EXECUTOR").shutdown();
  run(base,"fallback_pair",1,true,false,false,false);
  run(base,"fallback_raw",2,true,false,false,false);
  System.out.println("SAVE_MODE_CASES="+cases);
 }
}
