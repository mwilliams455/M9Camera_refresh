import com.particlesdevs.photoncamera.util.M9LocalLog1E;
import java.io.*;import java.nio.file.*;import java.util.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;
public class JournalTest {
 static void check(boolean b,String m){if(!b)throw new AssertionError(m);}
 public static void main(String[] a)throws Exception{
  File dir=Files.createTempDirectory("m9-journal-test").toFile();M9LocalLog1E j=new M9LocalLog1E(dir);long date=1700000000000L;
  for(int i=0;i<18000;i++)j.append(date,"I","Test","row "+i+" αβ猫 "+"z".repeat(30));j.append(date+86400000L,"W","Next","next day");j.flush();
  Map<String,byte[]> expected=new TreeMap<>();for(File f:dir.listFiles((d,n)->n.endsWith(".txt")))expected.put(f.getName(),Files.readAllBytes(f.toPath()));
  AtomicInteger calls=new AtomicInteger();check(!j.exportOne(()->false,(n,b)->{calls.incrementAndGet();return true;}),"background result");check(calls.get()==0,"background must never publish");
  AtomicInteger visibility=new AtomicInteger();check(!j.exportOne(()->visibility.incrementAndGet()==1,(n,b)->{throw new AssertionError("backgrounded before sink");}),"recheck visibility");
  check(!j.exportOne(()->true,(n,b)->false),"failed sink");try{j.exportOne(()->true,(n,b)->{throw new IOException("dead provider");});throw new AssertionError("exception");}catch(IOException ok){}
  Map<String,ByteArrayOutputStream> published=new TreeMap<>();M9LocalLog1E.Sink sink=(n,b)->{check(b.length<=262144,"bounded packet");published.computeIfAbsent(n,k->new ByteArrayOutputStream()).write(b);calls.incrementAndGet();return true;};
  check(j.exportOne(()->true,sink),"first packet");j.close();j=new M9LocalLog1E(dir);while(j.exportOne(()->true,sink)){}check(calls.get()>2,"multi packet");
  for(String n:expected.keySet())check(Arrays.equals(expected.get(n),published.get(n).toByteArray()),"exact UTF8 including failed export/restart/day rollover "+n);
  check(!j.exportOne(()->true,sink),"no duplicate after completion");
  j.append(date+86400000L,"D","Concurrent","before");M9LocalLog1E finalJ=j;CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
  ExecutorService workers=Executors.newFixedThreadPool(2);Future<?> export=workers.submit(()->{try{finalJ.exportOne(()->true,(n,b)->{entered.countDown();check(release.await(5,TimeUnit.SECONDS),"release");return sink.append(n,b);});}catch(Exception e){throw new RuntimeException(e);}});
  check(entered.await(5,TimeUnit.SECONDS),"sink entered");Future<?> append=workers.submit(()->{try{finalJ.append(date+86400000L,"D","Concurrent","during slow provider");finalJ.flush();}catch(Exception e){throw new RuntimeException(e);}});append.get(2,TimeUnit.SECONDS);release.countDown();export.get(5,TimeUnit.SECONDS);workers.shutdown();while(j.exportOne(()->true,sink)){}
  for(File f:dir.listFiles((d,n)->n.endsWith(".txt")))check(Arrays.equals(Files.readAllBytes(f.toPath()),published.get(f.getName()).toByteArray()),"concurrent exact bytes");
  j.close();File oldest=Arrays.stream(dir.listFiles((d,n)->n.endsWith(".txt"))).min(Comparator.comparing(File::getName)).get();oldest.setLastModified(1);j.cleanup(System.currentTimeMillis());check(!oldest.exists(),"acknowledged old log cleaned");
  j.append(date-86400000L,"D","Unsent","keep");j.close();File unsent=Arrays.stream(dir.listFiles((d,n)->n.endsWith(".txt"))).min(Comparator.comparing(File::getName)).get();unsent.setLastModified(1);new M9LocalLog1E(dir).cleanup(System.currentTimeMillis());check(unsent.exists(),"unexported old log retained");
  System.out.println("PASS journal: bounded exact UTF8, visibility race, failure, restart, dates, concurrent slow sink, retention");
 }
}
