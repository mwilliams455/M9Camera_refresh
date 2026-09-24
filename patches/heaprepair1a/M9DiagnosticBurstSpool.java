package com.particlesdevs.photoncamera.m9;

import android.content.Context;
import android.os.Process;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.util.Log;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.io.InputStream;
import java.util.Properties;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.nio.file.StandardCopyOption;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * SIDECAR1B diagnostic-only storage spool.
 *
 * Each immutable JSON payload is written immediately to app-private storage. Public camera-folder
 * export is decoupled: one debounced burst bundle is written first, then legacy individual JSON
 * files are exported later for compatibility. No photographic JPEG/DNG storage is routed here.
 */
public final class M9DiagnosticBurstSpool {
    public static final String SCHEMA = "m9cam.sidecarspool.v1.privatebundle1b";
    private static final String TAG = "M9DiagSpool";
    private static volatile boolean appVisible;
    private static final AtomicBoolean recovered = new AtomicBoolean();
    private static final long BUNDLE_IDLE_MS = 3000L;
    private static final long INDIVIDUAL_DELAY_MS = 12000L;
    private static final Object BUNDLE_LOCK = new Object();

    private static final ConcurrentHashMap<String, Entry> INDIVIDUAL_PENDING = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<String, Entry> BUNDLE_PENDING = new ConcurrentHashMap<>();
    private static final AtomicLong SEQ = new AtomicLong();
    private static final AtomicLong PRIVATE_STAGED = new AtomicLong();
    private static final AtomicLong PRIVATE_FAILED = new AtomicLong();
    private static final AtomicLong BUNDLE_WRITES = new AtomicLong();
    private static final AtomicLong BUNDLE_FAILED = new AtomicLong();
    private static final AtomicLong INDIVIDUAL_WRITES = new AtomicLong();
    private static final AtomicLong INDIVIDUAL_FAILED = new AtomicLong();
    private static final AtomicLong PRIVATE_TOTAL_NS = new AtomicLong();
    private static final AtomicLong PRIVATE_LAST_NS = new AtomicLong();
    private static final AtomicLong BUNDLE_TOTAL_NS = new AtomicLong();
    private static final AtomicLong BUNDLE_LAST_NS = new AtomicLong();
    private static volatile String lastBundlePath = null;
    private static volatile ScheduledFuture<?> scheduledBundle = null;
    private static ScheduledFuture<?> scheduledIndividual;

    private static final ScheduledThreadPoolExecutor BUNDLE_EXECUTOR =
            new ScheduledThreadPoolExecutor(1, runnable -> {
                Thread t = new Thread(runnable, "M9DiagBundleIO");
                t.setDaemon(true);
                return t;
            });
    private static final ScheduledThreadPoolExecutor INDIVIDUAL_EXPORTER = BUNDLE_EXECUTOR;

    static {
        BUNDLE_EXECUTOR.setRemoveOnCancelPolicy(true);
        INDIVIDUAL_EXPORTER.setRemoveOnCancelPolicy(true);
    }

    private M9DiagnosticBurstSpool() {}

    public static boolean stage(Path publicPath, byte[] bytes, String role) {
        if (publicPath == null || bytes == null) return false;
        final long startedNs = System.nanoTime();
        try {
            Context context = PhotonCamera.getAppContext();
            if (context == null) throw new IllegalStateException("PhotonCamera app context unavailable");
            Path dir = context.getFilesDir().toPath().resolve("m9diag_spool");
            Files.createDirectories(dir);
            long seq = SEQ.incrementAndGet();
            String base = sanitize(publicPath.getFileName().toString());
            Path privatePath = dir.resolve(String.format("%08d_%s_%s.stage", seq, UUID.randomUUID(), base));
            Files.write(privatePath, bytes);

            Entry entry = new Entry(publicPath, privatePath, bytes.length, role, System.currentTimeMillis(), seq);
            String key = publicPath.toString();
            persistManifest(entry);
            INDIVIDUAL_PENDING.compute(key, (k, older) -> {
                BUNDLE_PENDING.put(k, entry);
                if (older != null) removePrivate(older);
                return entry;
            });
            PRIVATE_STAGED.incrementAndGet();
            long elapsedNs = System.nanoTime() - startedNs;
            PRIVATE_LAST_NS.set(elapsedNs);
            PRIVATE_TOTAL_NS.addAndGet(elapsedNs);
            if (appVisible) {
                scheduleBundle();
                scheduleIndividuals();
            }
            Log.d(TAG, "SIDECAR1B private staged role=" + role + "; elapsedMs="
                    + (elapsedNs / 1_000_000.0) + "; pendingBundle=" + BUNDLE_PENDING.size()
                    + "; pendingIndividual=" + INDIVIDUAL_PENDING.size());
            return true;
        } catch (Throwable t) {
            PRIVATE_FAILED.incrementAndGet();
            Log.e(TAG, "SIDECAR1B private stage failed role=" + role + "; path=" + publicPath, t);
            return false;
        }
    }

    public static void setAppVisible(boolean visible) {
        appVisible = visible;
        if (!visible) {
            synchronized (BUNDLE_LOCK) { if (scheduledBundle != null) scheduledBundle.cancel(false); }
            synchronized (BUNDLE_LOCK) {
                if (scheduledIndividual != null) scheduledIndividual.cancel(false);
                scheduledIndividual = null;
            }
            return;
        }
        BUNDLE_EXECUTOR.execute(() -> {
            if (recovered.compareAndSet(false, true)) recoverPrivate();
            if (!appVisible) return;
            scheduleBundle();
            scheduleIndividuals();
        });
    }
    private static Path manifest(Entry e) { return e.privatePath.resolveSibling(e.privatePath.getFileName()+".meta"); }
    private static void persistManifest(Entry e) throws Exception {
        Properties p = new Properties();p.setProperty("publicPath",e.publicPath.toString());
        p.setProperty("role",e.role==null?"diagnostic":e.role);p.setProperty("stagedEpochMs",Long.toString(e.stagedEpochMs));
        Path m=manifest(e), tmp=m.resolveSibling(m.getFileName()+".tmp");
        try(java.io.FileOutputStream out=new java.io.FileOutputStream(tmp.toFile())) {p.store(out,"M9DIAGIO1E");out.getFD().sync();}
        Files.move(tmp,m,StandardCopyOption.REPLACE_EXISTING);
    }
    private static void removePrivate(Entry e) {
        // Delete manifest first: never recover an incomplete/superseded payload.
        try {Files.deleteIfExists(manifest(e));Files.deleteIfExists(e.privatePath);}catch(Exception ignored){}
    }
    private static void recoverPrivate() {
        try {
            Context c=PhotonCamera.getAppContext();if(c==null)return;
            Path dir=c.getFilesDir().toPath().resolve("m9diag_spool");if(!Files.isDirectory(dir))return;
            try(java.nio.file.DirectoryStream<Path> files=Files.newDirectoryStream(dir,"*.stage.meta")) {
                for(Path m:files) try {
                    Properties p=new Properties();try(InputStream in=Files.newInputStream(m)){p.load(in);}
                    String name=m.getFileName().toString();Path source=m.resolveSibling(name.substring(0,name.length()-5));
                    Entry e=new Entry(java.nio.file.Paths.get(p.getProperty("publicPath")),source,Files.size(source),
                        p.getProperty("role","recovered"),Long.parseLong(p.getProperty("stagedEpochMs")),SEQ.incrementAndGet());
                    String key=e.publicPath.toString();
                    INDIVIDUAL_PENDING.compute(key,(k,old)->{
                        if(old!=null&&old.privatePath.equals(e.privatePath))return old;
                        if(old!=null&&old.stagedEpochMs>=e.stagedEpochMs){removePrivate(e);return old;}
                        if(old!=null)removePrivate(old);BUNDLE_PENDING.put(key,e);return e;
                    });
                }catch(Exception error){Log.w(TAG,"M9DIAGIO1E manifest retained after recovery error: "+error);}
            }
        }catch(Exception error){Log.w(TAG,"M9DIAGIO1E recovery failed: "+error);}
    }
    private static void scheduleBundle() {
        if (!appVisible) return;
        synchronized (BUNDLE_LOCK) {
            if (scheduledBundle != null) scheduledBundle.cancel(false);
            scheduledBundle = BUNDLE_EXECUTOR.schedule(M9DiagnosticBurstSpool::flushBundle,
                    BUNDLE_IDLE_MS, TimeUnit.MILLISECONDS);
        }
    }

    private static void flushBundle() {
        if (!appVisible) return;
        List<Entry> entries = new ArrayList<>(BUNDLE_PENDING.values());
        if (entries.isEmpty()) return;
        entries.sort(Comparator.comparingLong(e -> e.sequence));
        if(entries.size()>16)entries=new ArrayList<>(entries.subList(0,16));
        final long startedNs = System.nanoTime();
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            // M9HEAPREPAIR1A: only paths are retained; a whole bundle is never materialized.
            Path parent = entries.get(0).publicPath.getParent();
            if (parent == null) throw new IllegalStateException("public diagnostic parent missing");
            Path bundlePath = parent.resolve("M9_DIAGNOSTICS_BURST_"
                    + System.currentTimeMillis() + "_" + entries.size() + ".json");
            Path temp = Files.createTempFile(entries.get(0).privatePath.getParent(), "bundle-", ".tmp");
            try {
                try (java.io.Writer out = new java.io.BufferedWriter(new java.io.OutputStreamWriter(
                        Files.newOutputStream(temp), StandardCharsets.UTF_8), 32768)) {
                    out.write("{\"schema\":\"m9cam.diagnosticbundle.v1.sidecar1b\",\"entries\":[");
                    boolean comma = false;
                    for (Entry e : entries) {
                        // Opening pins the immutable inode even if a new stage supersedes it.
                        try (java.io.FileInputStream input = new java.io.FileInputStream(e.privatePath.toFile())) {
                            if (comma) out.write(',');
                            JSONObject meta = new JSONObject().put("role",e.role)
                                .put("publicPath",e.publicPath.toString())
                                .put("publicFilename",e.publicPath.getFileName().toString())
                                .put("stagedEpochMs",e.stagedEpochMs).put("sequence",e.sequence);
                            String head=meta.toString();out.write(head,0,head.length()-1);
                            boolean object=M9DiagnosticStream1A.isObject(input);
                            input.getChannel().position(0);
                            out.write(object ? ",\"payload\":" : ",\"payloadText\":");
                            M9DiagnosticStream1A.copyUtf8(input,out,!object);
                            out.write('}');comma=true;
                        }
                    }
                    out.write("],\"entryCount\":"+entries.size()+",\"createdEpochMs\":"+System.currentTimeMillis());
                    out.write(",\"bundleIdleMs\":"+BUNDLE_IDLE_MS+",\"individualExportDelayMs\":"+INDIVIDUAL_DELAY_MS);
                    out.write(",\"spoolTelemetryAtBundle\":"+snapshotJson()+"}");
                }
                if (!writePublic(bundlePath,temp)) throw new java.io.IOException("public burst bundle write failed");
            } finally { Files.deleteIfExists(temp); }
            for (Entry e : entries) {
                BUNDLE_PENDING.remove(e.publicPath.toString(), e);
            }
            lastBundlePath = bundlePath.toString();
            BUNDLE_WRITES.incrementAndGet();
            long elapsedNs = System.nanoTime() - startedNs;
            BUNDLE_LAST_NS.set(elapsedNs);
            BUNDLE_TOTAL_NS.addAndGet(elapsedNs);
            Log.d(TAG, "SIDECAR1B burst bundle exported entries=" + entries.size()
                    + "; elapsedMs=" + (elapsedNs / 1_000_000.0) + "; path=" + bundlePath);
        } catch (Throwable t) {
            BUNDLE_FAILED.incrementAndGet();
            Log.e(TAG, "SIDECAR1B burst bundle export failed; private staged files retained", t);
        } finally { if(appVisible && !BUNDLE_PENDING.isEmpty())scheduleBundle(); }
    }

    private static void exportIndividual(Entry entry) {
        if (!appVisible) return;
        String key = entry.publicPath.toString();
        if (INDIVIDUAL_PENDING.get(key) != entry) return;
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            if (!writePublic(entry.publicPath, entry.privatePath)) {
                throw new java.io.IOException("individual public export failed");
            }
            INDIVIDUAL_WRITES.incrementAndGet();
            INDIVIDUAL_PENDING.remove(key, entry);
            BUNDLE_PENDING.remove(key, entry);
            removePrivate(entry);
            Log.d(TAG, "SIDECAR1B individual compatibility export complete role=" + entry.role
                    + "; remaining=" + INDIVIDUAL_PENDING.size() + "; path=" + entry.publicPath);
        } catch (Throwable t) {
            INDIVIDUAL_FAILED.incrementAndGet();
            Log.e(TAG, "SIDECAR1B individual compatibility export failed; private stage retained: "
                    + entry.publicPath, t);
        }
    }

    private static boolean writePublic(Path path, Path source) {
        if (!appVisible) return false;
        try {
            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(path.toString());
            if (safOut != null) {
                try (OutputStream out = safOut) {
                    try (InputStream in = Files.newInputStream(source)) { copy(in,out); }
                    out.flush();
                }
                return true;
            }
        } catch (Throwable safError) {
            Log.w(TAG, "SIDECAR1B SAF public write failed, trying direct path: " + safError);
        }
        if (!appVisible) return false;
        try (OutputStream out = Files.newOutputStream(path)) {
            try (InputStream in = Files.newInputStream(source)) { copy(in,out); }
            out.flush();
            return true;
        } catch (Throwable directError) {
            Log.e(TAG, "SIDECAR1B all public write routes failed: " + path, directError);
            return false;
        }
    }

    private static void copy(InputStream in, OutputStream out) throws java.io.IOException {
        byte[] block=new byte[32768];int n;
        while((n=in.read(block))!=-1)out.write(block,0,n);
    }
    private static void scheduleIndividuals() {
        synchronized(BUNDLE_LOCK) {
            if(!appVisible || INDIVIDUAL_PENDING.isEmpty())return;
            if(scheduledIndividual!=null && !scheduledIndividual.isDone())return;
            scheduledIndividual=INDIVIDUAL_EXPORTER.schedule(M9DiagnosticBurstSpool::flushIndividuals,
                    INDIVIDUAL_DELAY_MS,TimeUnit.MILLISECONDS);
        }
    }
    private static void flushIndividuals() {
        synchronized(BUNDLE_LOCK) { scheduledIndividual=null; }
        if(!appVisible)return;
        try {
            long now=System.currentTimeMillis();int count=0;
            for(Entry entry:INDIVIDUAL_PENDING.values()) {
                if(now-entry.stagedEpochMs>=INDIVIDUAL_DELAY_MS)exportIndividual(entry);
                if(++count>=16)break;
            }
        } finally { scheduleIndividuals(); }
    }

    public static JSONObject snapshotJson() {
        JSONObject o = new JSONObject();
        try {
            long privateCount = PRIVATE_STAGED.get();
            long bundleCount = BUNDLE_WRITES.get();
            o.put("schema", SCHEMA);
            o.put("ioRevision", "M9HEAPREPAIR1A");
            long bytes=0;for(Entry e:INDIVIDUAL_PENDING.values())bytes+=e.payloadBytes;
            o.put("pendingPayloadBytesOnDisk",bytes);
            o.put("retainedPayloadBytes",0);
            o.put("individualQueueTasks",INDIVIDUAL_EXPORTER.getQueue().size());
            o.put("bundleStreaming",true);
            o.put("appVisible", appVisible);
            o.put("publicExportRequiresVisibleActivity", true);
            o.put("restartRecoveryForNewManifests", true);
            o.put("policy", "private_immediate_bundle_first_eventual_individual_public_export");
            o.put("bundleIdleMs", BUNDLE_IDLE_MS);
            o.put("individualExportDelayMs", INDIVIDUAL_DELAY_MS);
            o.put("privateStaged", privateCount);
            o.put("privateStageFailed", PRIVATE_FAILED.get());
            o.put("bundleWrites", bundleCount);
            o.put("bundleFailed", BUNDLE_FAILED.get());
            o.put("pendingBundleEntries", BUNDLE_PENDING.size());
            o.put("pendingIndividualEntries", INDIVIDUAL_PENDING.size());
            o.put("individualWrites", INDIVIDUAL_WRITES.get());
            o.put("individualFailed", INDIVIDUAL_FAILED.get());
            o.put("privateLastStageElapsedMs", PRIVATE_LAST_NS.get() / 1_000_000.0);
            if (privateCount > 0) {
                o.put("privateAverageStageElapsedMs", PRIVATE_TOTAL_NS.get() / 1_000_000.0 / privateCount);
            }
            o.put("bundleLastPersistElapsedMs", BUNDLE_LAST_NS.get() / 1_000_000.0);
            if (bundleCount > 0) {
                o.put("bundleAveragePersistElapsedMs", BUNDLE_TOTAL_NS.get() / 1_000_000.0 / bundleCount);
            }
            if (lastBundlePath != null) o.put("lastBundlePath", lastBundlePath);
        } catch (Exception ignored) {}
        return o;
    }

    private static String sanitize(String s) {
        if (s == null || s.isEmpty()) return "diagnostic.json";
        return s.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private static final class Entry {
        final Path publicPath;
        final Path privatePath;
        final long payloadBytes;
        final String role;
        final long stagedEpochMs;
        final long sequence;

        Entry(Path publicPath, Path privatePath, long payloadBytes, String role,
              long stagedEpochMs, long sequence) {
            this.publicPath = publicPath;
            this.privatePath = privatePath;
            this.payloadBytes = payloadBytes;
            this.role = role != null ? role : "unknown";
            this.stagedEpochMs = stagedEpochMs;
            this.sequence = sequence;
        }
    }
}
