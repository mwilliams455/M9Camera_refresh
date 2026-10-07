import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;
import com.particlesdevs.photoncamera.m9.M9OutputSettings;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.BooleanSupplier;

public class SpoolTest {
    static int checks;
    static Path root,files,pub,spool;
    static void check(boolean ok,String reason){checks++;if(!ok)throw new AssertionError(reason);}
    static void await(BooleanSupplier condition,long timeout,String reason)throws Exception {
        long end=System.nanoTime()+timeout*1_000_000L;
        while(!condition.getAsBoolean() && System.nanoTime()<end)Thread.sleep(10);
        check(condition.getAsBoolean(),reason);
    }
    static Object field(Object object,String name)throws Exception {
        Class<?> c=object instanceof Class?(Class<?>)object:object.getClass();
        Field f=c.getDeclaredField(name);f.setAccessible(true);return f.get(object instanceof Class?null:object);
    }
    @SuppressWarnings("unchecked") static Map<String,Object> pending()throws Exception {
        return (Map<String,Object>)field(M9DiagnosticBurstSpool.class,"INDIVIDUAL_PENDING");
    }
    static long metric(String key){return ((Number)M9DiagnosticBurstSpool.snapshotJson().values.get(key)).longValue();}
    static void seed(String name,String role,long time,byte[] bytes)throws Exception {
        Path f=spool.resolve(name+".stage");Files.write(f,bytes);
        Properties p=new Properties();p.setProperty("publicPath",pub.resolve(name+".json").toString());
        p.setProperty("role",role);p.setProperty("stagedEpochMs",Long.toString(time));
        try(var out=Files.newOutputStream(f.resolveSibling(f.getFileName()+".meta"))){p.store(out,"");}
    }
    static byte[] bytes(String s){return s.getBytes(java.nio.charset.StandardCharsets.UTF_8);}
    static boolean content(Path p,byte[] b){try{return Arrays.equals(Files.readAllBytes(p),b);}catch(Exception e){return false;}}
    static void start()throws Exception {
        M9DiagnosticBurstSpool.setAppVisible(true);
        await(()->Boolean.TRUE.equals(M9DiagnosticBurstSpool.snapshotJson().values.get("spoolResetCompleted")),3000,"recovery initialized");
    }
    static void backlog()throws Exception {
        long now=System.currentTimeMillis();
        for(int i=0;i<1709;i++)seed("old_"+i,"capture_metadata",now-100000-i,bytes("old"));
        seed("trace_old","shutter_trace",now-3000,bytes("old trace"));
        seed("trace_middle","shutter_trace",now-2000,bytes("middle trace"));
        byte[] latest=new byte[12_013_236];new Random(42).nextBytes(latest);
        seed("trace_latest","shutter_trace",now-1000,latest);
        start();await(()->metric("recoveredEntries")==1712,3000,"metadata recovery of backlog and traces");
        Object blocked=pending().get(pub.resolve("old_0.json").toString());
        SimpleStorageHelper.blockedName="old_0.json";
        Method export=M9DiagnosticBurstSpool.class.getDeclaredMethod("exportIndividual",blocked.getClass(),boolean.class,boolean.class);export.setAccessible(true);
        ScheduledThreadPoolExecutor normal=(ScheduledThreadPoolExecutor)field(M9DiagnosticBurstSpool.class,"INDIVIDUAL_EXPORTER");
        normal.execute(()->{try{export.invoke(null,blocked,false,false);}catch(Exception e){throw new RuntimeException(e);}});
        check(SimpleStorageHelper.entered.await(2,TimeUnit.SECONDS),"old provider call is blocked");
        await(()->content(pub.resolve("trace_latest.json"),latest),4000,"latest recovered 12MB trace exported despite blocked backlog");
        List<String> traceOrder;
        synchronized(SimpleStorageHelper.opened){traceOrder=SimpleStorageHelper.opened.stream().filter(n->n.startsWith("trace")).toList();}
        check(traceOrder.get(0).equals("trace_latest.json"),"recovery newest first independent of directory order");
        check(metric("pendingIndividualEntries")>=1709,"historical diagnostics preserved");
        check(metric("recoveredPayloadBytesHeldInJavaHeap")==0,"metadata-only recovery");
        check(SimpleStorageHelper.largestWrite.get()<=65536,"64KiB streaming including large trace");
        check(metric("shutterTraceScheduledTasks")<=1,"one scheduled trace pump");
        await(()->Files.exists(pub.resolve("trace_old.json")),4000,"older traces also recovered");
        SimpleStorageHelper.release.countDown();
        check(metric("shutterTraceWrites")==3,"three recovered traces exported");
    }
    static void coalesce()throws Exception {
        start();Path target=pub.resolve("trace_race.json");
        SimpleStorageHelper.blockedName="trace_race.json";SimpleStorageHelper.blockOnce=true;
        byte[] initial=bytes("initial snapshot");
        check(M9DiagnosticBurstSpool.stage(target,initial,"shutter_trace"),"initial private stage");
        check(SimpleStorageHelper.entered.await(3,TimeUnit.SECONDS),"trace stream claims current payload before provider open");
        Object old=pending().get(target.toString());Path active=(Path)field(old,"privatePath");
        byte[] latest=null;
        for(int i=0;i<60;i++){
            latest=bytes("latest snapshot "+i);
            check(M9DiagnosticBurstSpool.stage(target,latest,"shutter_trace"),"snapshot stage "+i);
            check(Files.exists(active),"active payload survives replacement "+i);
            check(metric("shutterTraceScheduledTasks")<=1,"updates do not queue individual trace jobs "+i);
        }
        check(metric("shutterTracePendingEntries")==1,"one pending entry per public trace");
        // Pause and resume during an active provider call: no concurrent writer or lost latest update.
        M9DiagnosticBurstSpool.setAppVisible(false);M9DiagnosticBurstSpool.setAppVisible(true);
        byte[] expected=latest;SimpleStorageHelper.release.countDown();
        await(()->content(target,expected),5000,"newest snapshot ultimately replaces in-flight older snapshot");
        await(()->!Files.exists(active),2000,"superseded active private file reclaimed after stream");
        await(()->metric("shutterTracePendingEntries")==0,2000,"latest private trace cleared only after successful export");
        check(SimpleStorageHelper.traceMaxActive.get()==1,"single trace writer across lifecycle transition");
        check(metric("shutterTraceWrites")==2,"many updates coalesced into two writes");
        check(metric("shutterTraceFailed")==0,"no missing private-file race");
    }
    static void retry()throws Exception {
        start();Path target=pub.resolve("missing/trace_retry.json");
        SimpleStorageHelper.failingName="trace_retry.json";byte[] wanted=bytes("retained on failure");
        check(M9DiagnosticBurstSpool.stage(target,wanted,"shutter_trace"),"failing payload staged");
        await(()->metric("shutterTraceFailed")==1,4000,"both provider and direct paths fail");
        Object retained=pending().get(target.toString());
        check(retained!=null,"failed entry retained in queue");
        Path privatePath=(Path)field(retained,"privatePath");
        check(content(privatePath,wanted),"failed payload retained byte-identically");
        check(Files.exists(privatePath.resolveSibling(privatePath.getFileName()+".meta")),"restart manifest retained");
        Path other=pub.resolve("trace_other.json");byte[] second=bytes("other trace");
        check(M9DiagnosticBurstSpool.stage(other,second,"shutter_trace"),"other trace staged");
        await(()->content(other,second),4000,"failed destination does not starve other traces");
        check(metric("shutterTraceFailed")==1,"failed destination has bounded retry delay");
        Files.createDirectories(target.getParent());SimpleStorageHelper.failingName=null;
        await(()->content(target,wanted),13000,"failure retries automatically without another capture or resume");
        await(()->!Files.exists(privatePath),2000,"successful retry releases private payload");
        check(metric("shutterTracePendingEntries")==0,"retry queue drained");
    }
    static void lifecycle()throws Exception {
        start();M9DiagnosticBurstSpool.setAppVisible(false);
        Path hidden=pub.resolve("trace_hidden.json");byte[] value=bytes("background");
        check(M9DiagnosticBurstSpool.stage(hidden,value,"shutter_trace"),"hidden trace staged privately");
        Thread.sleep(1300);check(!Files.exists(hidden),"no background public export");
        check(metric("shutterTraceScheduledTasks")==0,"pump cancelled in background");
        M9OutputSettings.enabled=false;M9DiagnosticBurstSpool.setAppVisible(true);
        Path off=pub.resolve("trace_disabled.json");long staged=metric("privateStaged");
        check(M9DiagnosticBurstSpool.stage(off,bytes("off"),"shutter_trace"),"disabled write handled without fallback");
        check(metric("privateStaged")==staged,"disabled diagnostics do not stage payloads");
        Thread.sleep(1300);check(!Files.exists(hidden)&&!Files.exists(off),"disabled diagnostics do not export pending/new traces");
        M9OutputSettings.enabled=true;M9DiagnosticBurstSpool.onDiagnosticPreferenceChanged();
        await(()->content(hidden,value),4000,"pre-existing trace resumes after preference enabled");
        Path primary=pub.resolve("primary.json");byte[] primaryBytes=bytes("primary timing");
        check(M9DiagnosticBurstSpool.stage(primary,primaryBytes,"primary_timing"),"PRIMARY stages normally");
        await(()->content(primary,primaryBytes),2000,"existing priority PRIMARY path remains functional");
        check(metric("freshPrimaryWrites")==1,"PRIMARY accounting preserved");
        check(!Files.exists(off),"disabled trace never exported later");
    }
    public static void main(String[] args)throws Exception {
        root=Files.createTempDirectory("m9-shutter-export-test-");files=root.resolve("private");pub=root.resolve("public");spool=files.resolve("m9diag_spool");
        Files.createDirectories(spool);Files.createDirectories(pub);
        // Existing installs already have this marker, as shown by the supplied diagnostics.
        Files.writeString(files.resolve("m9diag_spool_reset1a.done"),"existing installation");
        android.content.Context c=new android.content.Context();c.files=files.toFile();PhotonCamera.context=c;
        try {
            switch(args[0]){case "backlog"->backlog();case "coalesce"->coalesce();case "retry"->retry();case "lifecycle"->lifecycle();default->throw new AssertionError(args[0]);}
            System.out.println("{\"scenario\":\""+args[0]+"\",\"status\":\"PASS\",\"assertions\":"+checks+"}");
        } finally {
            M9DiagnosticBurstSpool.setAppVisible(false);SimpleStorageHelper.release.countDown();
            for(String name:List.of("BUNDLE_EXECUTOR","INDIVIDUAL_EXPORTER","FRESH_PRIMARY_EXPORTER","RECOVERED_PRIMARY_EXPORTER","SHUTTER_TRACE_EXPORTER")){
                ScheduledThreadPoolExecutor ex=(ScheduledThreadPoolExecutor)field(M9DiagnosticBurstSpool.class,name);ex.shutdownNow();ex.awaitTermination(2,TimeUnit.SECONDS);
            }
            try(var paths=Files.walk(root)){for(Path path:paths.sorted(Comparator.reverseOrder()).toList())Files.deleteIfExists(path);}
        }
    }
}
