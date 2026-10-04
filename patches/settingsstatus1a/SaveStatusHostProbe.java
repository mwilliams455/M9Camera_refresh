import com.particlesdevs.photoncamera.m9.*;
import com.particlesdevs.photoncamera.m9.render.*;
import com.particlesdevs.photoncamera.processing.*;
import com.particlesdevs.photoncamera.settings.PreferenceKeys;
import java.nio.file.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class SaveStatusHostProbe {
    static int cases;
    static final M9SaveStatus status = M9SaveStatus.INSTANCE;
    static void require(boolean ok, String message) { if (!ok) throw new AssertionError(message); }
    static void reset() {
        M9SaveStatus.Snapshot s = status.snapshot();
        require(s.pending == 0, "pending captures at reset"); status.acknowledge(s.revision);
    }
    static ThreadPoolExecutor executor(String name) throws Exception {
        java.lang.reflect.Field field = M9PrimaryRenderQueue.class.getDeclaredField(name);
        field.setAccessible(true); return (ThreadPoolExecutor)field.get(null);
    }
    static ImageFrame enqueue(Path base, String name, int mode, boolean extra, boolean badPublish) throws Exception {
        Path dir = base.resolve(name); Files.createDirectories(dir);
        PreferenceKeys.mode = mode; M9OutputSettings.extra = extra;
        ImageFrame frame = new ImageFrame();
        boolean accepted = M9PrimaryRenderQueue.enqueue(dir.resolve("photo.dng"), frame,
                null, null, null, 90, 0, 0, (success, path) -> {
                    if (badPublish && path.toString().endsWith(".dng")) throw new IllegalStateException("gallery failed");
                });
        require(accepted, "unexpected queue rejection"); return frame;
    }
    static void drain(ImageFrame... frames) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (System.nanoTime() < deadline) {
            boolean done = status.snapshot().pending == 0;
            for (ImageFrame frame : frames) done &= frame.closes.get() > 0;
            if (done && executor("EXECUTOR").getActiveCount() == 0
                    && executor("DNG_EXECUTOR").getActiveCount() == 0) {
                for (ImageFrame frame : frames) require(frame.closes.get() == 1, "RAW closed twice");
                return;
            }
            Thread.sleep(2);
        }
        throw new AssertionError("save did not finish");
    }
    static void result(int saved, int failed, int issues) {
        M9SaveStatus.Snapshot s = status.snapshot();
        require(s.pending == 0 && s.saved == saved && s.failed == failed && s.issues == issues,
                "wrong status: " + s.pending + "/" + s.saved + "/" + s.failed + "/" + s.issues);
        cases++; reset();
    }
    public static void main(String[] args) throws Exception {
        Path base = Path.of(args[0]); require(!Files.exists(base), "fresh test directory required");
        for (int mode = 0; mode < 3; mode++) for (boolean extra : new boolean[]{false,true}) {
            drain(enqueue(base, "mode"+mode+extra, mode, extra, false)); result(1,0,0);
        }
        // Finished payload is not finished EXIF; two captures remain owned across rearm/settings changes.
        M9JpegFinalizeQueue.entered = new CountDownLatch(1); M9JpegFinalizeQueue.release = new CountDownLatch(1);
        ImageFrame a = enqueue(base,"wait_jpeg_a",0,false,false);
        require(M9JpegFinalizeQueue.entered.await(5,TimeUnit.SECONDS),"no JPEG finalizer");
        ImageFrame b = enqueue(base,"wait_jpeg_b",0,false,false);
        require(status.snapshot().pending == 2,"capture counter does not include finalization");
        PreferenceKeys.mode = 2; M9OutputSettings.extra = true;
        long oldRevision = status.snapshot().revision;
        status.acknowledge(oldRevision); require(status.snapshot().pending == 2,"cleared active saves");
        M9JpegFinalizeQueue.release.countDown(); drain(a,b);
        M9JpegFinalizeQueue.entered = null; M9JpegFinalizeQueue.release = null;
        result(2,0,0);
        // DNG is not complete until profile embedding ends; observers may leave and rejoin.
        AtomicInteger events = new AtomicInteger(); M9SaveStatus.Observer observer = events::incrementAndGet;
        status.addObserver(observer);
        M9DngProfileExport.entered = new CountDownLatch(1); M9DngProfileExport.release = new CountDownLatch(1);
        a = enqueue(base,"wait_profile",2,false,false);
        require(M9DngProfileExport.entered.await(5,TimeUnit.SECONDS),"no profile worker");
        require(status.snapshot().pending == 1 && status.snapshot().saved == 0,"early DNG success");
        status.removeObserver(observer); int detached = events.get();
        M9DngProfileExport.release.countDown(); drain(a);
        require(events.get() == detached,"detached observer retained");
        status.addObserver(observer); require(status.snapshot().saved == 1,"resume lost completion");
        status.removeObserver(observer); M9DngProfileExport.entered = null; M9DngProfileExport.release = null;
        result(1,0,0);
        drain(enqueue(base,"bad_jpeg",1,false,false)); result(0,1,M9SaveStatus.JPEG);
        drain(enqueue(base,"bad_dng",1,false,false)); result(0,1,M9SaveStatus.DNG);
        drain(enqueue(base,"bad_profile",2,false,false)); result(0,1,M9SaveStatus.PROFILE);
        drain(enqueue(base,"bad_extra",1,true,false)); result(0,1,M9SaveStatus.UNFILTERED);
        drain(enqueue(base,"bad_publish",2,false,true)); result(0,1,M9SaveStatus.PUBLICATION);
        drain(enqueue(base,"throw_render",0,false,false)); result(0,1,M9SaveStatus.PROCESSING);
        drain(enqueue(base,"bad_render",2,false,false)); result(0,1,M9SaveStatus.PROFILE);
        // Stale completion acknowledgement and duplicate terminal callbacks are harmless.
        M9SaveStatus.Ticket ticket = status.begin(M9SaveSelection.fromMode(0,false));
        long stale = status.snapshot().revision; ticket.complete(true,false,false,false,true);
        status.acknowledge(stale); ticket.fail(M9SaveStatus.PROCESSING);
        result(1,0,0);
        executor("DNG_EXECUTOR").shutdown();
        drain(enqueue(base,"fallback_pair",1,true,false)); result(1,0,0);
        drain(enqueue(base,"fallback_raw",2,true,false)); result(1,0,0);
        // A race at actual enqueue reports failure without taking RAW ownership.
        executor("EXECUTOR").shutdown(); ImageFrame rejected = new ImageFrame();
        require(!M9PrimaryRenderQueue.enqueue(base.resolve("reject.dng"),rejected,null,null,null,0,0,0,(s,p)->{}),"rejection missing");
        require(rejected.closes.get() == 0,"queue closed caller-owned rejected RAW"); rejected.close();
        result(0,1,M9SaveStatus.QUEUE);
        require(cases == 19,"wrong case count"); System.out.println("SAVE_STATUS_CASES="+cases);
    }
}
