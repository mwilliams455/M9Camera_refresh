import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import android.content.Context;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;
import java.nio.file.*;import java.lang.reflect.*;import java.util.*;import java.util.concurrent.*;
public class HeapIoTest {
 static Object field(String n)throws Exception{Field f=M9DiagnosticBurstSpool.class.getDeclaredField(n);f.setAccessible(true);return f.get(null);}
 static void call(String name,Object...args)throws Exception{Method m=Arrays.stream(M9DiagnosticBurstSpool.class.getDeclaredMethods()).filter(x->x.getName().equals(name)).findFirst().get();m.setAccessible(true);m.invoke(null,args);}
 static void check(boolean b,String s){if(!b)throw new AssertionError(s);}
 static Map<?,?> pending()throws Exception{return (Map<?,?>)field("INDIVIDUAL_PENDING");}
 static void idle()throws Exception{((ScheduledThreadPoolExecutor)field("BUNDLE_EXECUTOR")).submit(()->{}).get(10,TimeUnit.SECONDS);}
 static byte[] data(int id){byte[] b=new byte[2*1024*1024];Arrays.fill(b,(byte)'x');byte[] head=("{\"id\":"+id+",\"body\":\"").getBytes(java.nio.charset.StandardCharsets.UTF_8);System.arraycopy(head,0,b,0,head.length);b[b.length-2]='"';b[b.length-1]='}';return b;}
 public static void main(String[] args)throws Exception {
  Path root=Paths.get(args[1]);Files.createDirectories(root);PhotonCamera.context=new Context(root.toFile());
  if(args[0].equals("stage")) {
   for(int i=0;i<80;i++)check(M9DiagnosticBurstSpool.stage(root.resolve("public/p"+i+".json"),data(i),"stress"),"stage "+i);
   check(pending().size()==80,"all payloads retained on disk");
   for(Object e:pending().values())for(Field f:e.getClass().getDeclaredFields())check(f.getType()!=byte[].class,"payload retained on Java heap");
   System.out.println("PASS stage 160 MiB diagnostic payloads under 64 MiB heap");
  } else if(args[0].equals("recover")) {
   M9DiagnosticBurstSpool.setAppVisible(true);idle();check(pending().size()==80,"recover all pending paths");
   SimpleStorageHelper.fail=true;call("flushBundle");check(pending().size()==80,"failure retains durable data");SimpleStorageHelper.fail=false;
   for(int i=0;i<5;i++)call("flushBundle");
   for(Object e:new ArrayList<>(pending().values()))call("exportIndividual",e);
   check(pending().isEmpty(),"drained");check(SimpleStorageHelper.active==0,"closed descriptors");
   M9DiagnosticBurstSpool.setAppVisible(false);
   System.out.println("PASS recover and stream 160 MiB under 64 MiB heap; exact exports, failure retention");
  } else if(args[0].equals("updates")) {
   M9DiagnosticBurstSpool.setAppVisible(true);idle();SimpleStorageHelper.fail=true;
   Path dst=root.resolve("public/latest.json");
   for(int i=0;i<100;i++)check(M9DiagnosticBurstSpool.stage(dst,data(i),"updates"),"update "+i);
   check(pending().size()==1,"coalesced latest target");
   check(((ScheduledThreadPoolExecutor)field("INDIVIDUAL_EXPORTER")).getQueue().size()<=2,"bounded export tasks");
   M9DiagnosticBurstSpool.setAppVisible(false);int opens=SimpleStorageHelper.opens;
   call("flushBundle");check(opens==SimpleStorageHelper.opens,"no background provider calls");
   SimpleStorageHelper.fail=false;M9DiagnosticBurstSpool.setAppVisible(true);idle();call("flushBundle");
   for(Object e:new ArrayList<>(pending().values()))call("exportIndividual",e);
   check(pending().isEmpty(),"latest acknowledged");M9DiagnosticBurstSpool.setAppVisible(false);
   System.out.println("PASS 100 superseding 2 MiB reports; at most two tasks; background zero provider calls");
  }
 }
}
