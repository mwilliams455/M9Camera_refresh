import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;
import com.particlesdevs.photoncamera.m9.M9OutputSettings;
import com.particlesdevs.photoncamera.settings.PreferenceKeys;
import java.nio.file.*;
import java.util.concurrent.*;

/** Real file/executor coverage for the imported Mono adapter and shared priority route. */
public final class MonoSpoolScenario {
    public static void run() throws Exception {
        byte[] old=SpoolTest.bytes("preserve existing queued M9 report");
        Path retained=SpoolTest.spool.resolve("legacy-m9-report.stage");
        Files.write(retained,old);
        SpoolTest.start();
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);
        ScheduledThreadPoolExecutor ordinary=(ScheduledThreadPoolExecutor)SpoolTest.field(M9DiagnosticBurstSpool.class,"INDIVIDUAL_EXPORTER");
        ordinary.execute(()->{entered.countDown();try{release.await();}catch(InterruptedException e){Thread.currentThread().interrupt();}});
        SpoolTest.check(entered.await(2,TimeUnit.SECONDS),"ordinary backlog worker blocked");
        try {
            Path target=SpoolTest.pub.resolve("capture_MONO_PRIMARY.json");
            byte[] wanted=SpoolTest.bytes("immutable Monochrom report");
            SpoolTest.check(com.particlesdevs.photoncamera.monochrom.M9DiagnosticBurstSpool.stage(target,wanted,"monochrom_primary"),"Mono report admitted");
            SpoolTest.await(()->SpoolTest.content(target,wanted),2000,"Mono primary bypasses ordinary backlog");
            SpoolTest.check(SpoolTest.content(retained,old),"first Mono stage did not purge existing M9 report");
            SpoolTest.check(!Files.exists(SpoolTest.files.resolve("mmonochrome_diag_spool_reset1b.done")),"legacy destructive Mono reset not invoked");
            SpoolTest.check(SpoolTest.metric("freshPrimaryWrites")==1,"shared priority writer used");
            long staged=SpoolTest.metric("privateStaged");
            PreferenceKeys.enabled=false;M9OutputSettings.enabled=false;
            Path disabled=SpoolTest.pub.resolve("disabled_MONO_PRIMARY.json");
            SpoolTest.check(com.particlesdevs.photoncamera.monochrom.M9DiagnosticBurstSpool.stage(disabled,wanted,"monochrom_primary"),"disabled request handled without fallback");
            SpoolTest.check(SpoolTest.metric("privateStaged")==staged&&!Files.exists(disabled),"off creates no private or public diagnostic");
            PreferenceKeys.enabled=true;M9OutputSettings.enabled=true;
            M9DiagnosticBurstSpool.setAppVisible(false);
            Path paused=SpoolTest.pub.resolve("paused_MONO_PRIMARY.json");
            SpoolTest.check(com.particlesdevs.photoncamera.monochrom.M9DiagnosticBurstSpool.stage(paused,wanted,"monochrom_primary"),"paused report durably staged");
            Object entry=SpoolTest.pending().get(paused.toString());
            SpoolTest.check(entry!=null,"shared queue owns pending Mono report");
            boolean heapPayload=false;
            for(java.lang.reflect.Field f:entry.getClass().getDeclaredFields())heapPayload|=f.getType()==byte[].class;
            SpoolTest.check(!heapPayload,"queue retains metadata rather than a byte array");
            SpoolTest.check(!Files.exists(paused),"background does not publish");
            M9DiagnosticBurstSpool.setAppVisible(true);
            SpoolTest.await(()->SpoolTest.content(paused,wanted),2500,"Mono report exported on resume");
            SpoolTest.check(SpoolTest.content(retained,old),"existing report still preserved");
        } finally {release.countDown();PreferenceKeys.enabled=true;M9OutputSettings.enabled=true;}
    }
}
