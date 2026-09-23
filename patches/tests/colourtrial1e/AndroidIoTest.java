import com.particlesdevs.photoncamera.util.*;import com.particlesdevs.photoncamera.util.log.*;import com.particlesdevs.photoncamera.m9.*;import com.particlesdevs.photoncamera.app.*;
import android.os.Looper;import android.content.*;import android.app.Activity;import java.io.*;import java.nio.file.*;import java.lang.reflect.*;import java.util.*;import java.util.concurrent.*;
public class AndroidIoTest {
 static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
 static Object field(String name)throws Exception{Field f=M9DiagnosticBurstSpool.class.getDeclaredField(name);f.setAccessible(true);return f.get(null);}
 static Map<?,?> pending()throws Exception{return (Map<?,?>)field("INDIVIDUAL_PENDING");}
 static void invoke(String name,Object...args)throws Exception{Method m=Arrays.stream(M9DiagnosticBurstSpool.class.getDeclaredMethods()).filter(x->x.getName().equals(name)).findFirst().get();m.setAccessible(true);m.invoke(null,args);}
 static void barrier()throws Exception{((ScheduledThreadPoolExecutor)field("BUNDLE_EXECUTOR")).submit(()->{}).get(5,TimeUnit.SECONDS);}
 static byte[] concat(Map<String,ByteArrayOutputStream> data)throws Exception{ByteArrayOutputStream b=new ByteArrayOutputStream();for(ByteArrayOutputStream s:data.values())b.write(s.toByteArray());return b.toByteArray();}
 static String local(Context c)throws Exception{ByteArrayOutputStream b=new ByteArrayOutputStream();for(File f:new File(c.getFilesDir(),"m9_logs").listFiles((d,n)->n.endsWith(".txt")))b.write(Files.readAllBytes(f.toPath()));return b.toString("UTF-8");}
 public static void main(String[] args)throws Exception{
  Path dir=args.length==2?Paths.get(args[1]):Files.createTempDirectory("m9-android-io");Files.createDirectories(dir);Context c=new Context(dir.toFile());PhotonCamera.context=c;
  if(args[0].equals("logger")){
   Log.initPrivate(c);Log.setLogFolder(c);Looper writer=Looper.all.get("LogWriterThread"),exporter=Looper.all.get("LogExport1E");
   for(int i=0;i<10000;i++)Log.d("Test","entry "+i+" αβ");check(SimpleStorageHelper.checks==0,"logging caller has no permission IPC");writer.advance(0);writer.advance(1000);check(exporter.size()==0,"background has no export timer");check(SimpleStorageHelper.checks==0&&ContentResolver.opens==0,"background logging zero provider IO");
   ActivityLifecycleMonitor life=new ActivityLifecycleMonitor();Activity first=new Activity(),second=new Activity();life.onActivityStarted(first);life.onActivityStarted(second);barrier();life.onActivityStopped(first);check((Boolean)field("appVisible"),"second activity retains visibility with DEBUG false");
   exporter.advance(1000);check(SimpleStorageHelper.checks==1&&ContentResolver.opens==1,"one permission query per bounded batch, not per 10000 logs");check(ContentResolver.active==0&&ContentResolver.closes==1,"close public descriptor each packet");
   life.onActivityStopped(second);check(!(Boolean)field("appVisible"),"all stopped");writer.advance(0);exporter.advance(30000);check(SimpleStorageHelper.checks==1,"background cancels scheduled IPC");
   Log.setAppVisible(true);ContentResolver.fail=true;exporter.advance(1000);check(ContentResolver.active==0&&ContentResolver.opens==ContentResolver.closes,"provider failure closes descriptor");ContentResolver.fail=false;
   for(int i=0;i<10;i++)exporter.advance(5000);writer.advance(0);writer.advance(1000);
   check(Arrays.equals(local(c).getBytes("UTF-8"),concat(ContentResolver.data)),"public log exactly matches local after retry");
   SimpleStorageHelper.permissionFailure=true;Log.d("Test","permission error");writer.advance(0);writer.advance(1000);int before=SimpleStorageHelper.checks;exporter.advance(5000);writer.advance(0);check(SimpleStorageHelper.checks==before+1,"permission error logging cannot recurse");SimpleStorageHelper.permissionFailure=false;
   for(int i=0;i<50;i++)Log.setAppVisible(true);check(exporter.size()==1,"visibility changes cannot multiply timers");
   for(int i=0;i<1000;i++)Log.d("Bound","x".repeat(4000));check(writer.size()<400,"bounded queue under stalled writer");writer.advance(0);writer.advance(1000);check(local(c).contains("log queue overflow; dropped entries="),"explicit overflow evidence");
   Log.setAppVisible(false);Log.shutdown();M9DiagnosticBurstSpool.setAppVisible(false);System.out.println("PASS logger/lifecycle: 10000 entries zero caller/background IPC; bounded batch/queue; failure cleanup; no recursion; activity overlap");
  }else if(args[0].equals("stage")){
   Path target=Paths.get("/nonexistent-m9-test-private-parent/diagnostic.json");
   check(M9DiagnosticBurstSpool.stage(target,"{\"value\":\"old\"}".getBytes("UTF-8"),"test"),"stage old");check(M9DiagnosticBurstSpool.stage(target,"{\"value\":\"latest\"}".getBytes("UTF-8"),"test"),"stage latest");
   invoke("flushBundle");invoke("exportIndividual",pending().values().iterator().next());check(SimpleStorageHelper.opens==0,"spool background has zero public IO");check(pending().size()==1,"deduplicate by target");
   try(var files=Files.list(dir.resolve("m9diag_spool"))){check(files.count()==2,"one latest durable payload and manifest");}
   System.out.println("PASS spool private stage: background zero IPC, durable newest destination payload");
  }else{
   check(pending().isEmpty(),"fresh JVM has no old static entries");M9DiagnosticBurstSpool.setAppVisible(true);barrier();check(pending().size()==1,"restart manifest recovers entry");Object entry=pending().values().iterator().next();
   SimpleStorageHelper.fail=true;invoke("exportIndividual",entry);check(pending().size()==1,"failed provider/direct routes retain payload");
   M9DiagnosticBurstSpool.setAppVisible(false);int opens=SimpleStorageHelper.opens;invoke("flushBundle");invoke("exportIndividual",entry);check(opens==SimpleStorageHelper.opens,"resume/pause gate");
   SimpleStorageHelper.fail=false;M9DiagnosticBurstSpool.setAppVisible(true);barrier();invoke("flushBundle");invoke("exportIndividual",entry);
   check(pending().isEmpty(),"successful retry acknowledged");check(SimpleStorageHelper.active==0&&SimpleStorageHelper.closes==2,"bundle and individual descriptors closed");
   check(SimpleStorageHelper.data.get("/nonexistent-m9-test-private-parent/diagnostic.json").toString("UTF-8").equals("{\"value\":\"latest\"}"),"exact newest payload after restart");
   try(var files=Files.list(dir.resolve("m9diag_spool"))){check(files.count()==0,"private removal only after success");}M9DiagnosticBurstSpool.setAppVisible(false);
   System.out.println("PASS spool fresh process: restart recovery, failure retention, background gate, exact latest individual, resource closure");
  }
 }
}
