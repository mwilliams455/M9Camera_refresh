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
 * M9SPOOLSTREAM1A.
 *
 * Diagnostic payloads are durable files, not heap-resident objects. Recovery records
 * only path/size metadata. Burst bundles are bounded manifests; complete payloads are
 * streamed one at a time during compatibility export.
 */
public final class M9DiagnosticBurstSpool {
    public static final String SCHEMA = "m9cam.sidecarspool.v1.privatebundle1b";
    public static final String MEMORY_REVISION = "M9SPOOLSTREAM1A";
    private static final String TAG = "M9DiagSpool";
    private static volatile boolean appVisible;
    private static final AtomicBoolean recovered = new AtomicBoolean();
    private static final long BUNDLE_IDLE_MS = 3000L;
    private static final long INDIVIDUAL_DELAY_MS = 12000L;
    // PRIMARYEXPORT1A: PRIMARY is the compact final renderer authority needed to
    // validate noise/exposure. Keep private-first durability, but do not place it
    // behind multi-megabyte shutter traces on the normal individual exporter.
    private static final long PRIMARY_TIMING_EXPORT_DELAY_MS = 250L;
    private static final String PRIORITY_ROLE = "primary_timing";
    private static final int COPY_BUFFER_BYTES = 64 * 1024;
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
    private static final AtomicLong RECOVERED_ENTRIES = new AtomicLong();
    private static final AtomicLong RECOVERED_BYTES_REFERENCED = new AtomicLong();
    private static volatile String lastBundlePath = null;
    private static volatile ScheduledFuture<?> scheduledBundle = null;

    private static final ScheduledThreadPoolExecutor BUNDLE_EXECUTOR =
            new ScheduledThreadPoolExecutor(1, runnable -> {
                Thread t = new Thread(runnable, "M9DiagBundleIO");
                t.setDaemon(true);
                return t;
            });
    private static final ScheduledThreadPoolExecutor INDIVIDUAL_EXPORTER =
            new ScheduledThreadPoolExecutor(1, runnable -> {
                Thread t = new Thread(runnable, "M9DiagIndividualIO");
                t.setDaemon(true);
                return t;
            });
    private static final ScheduledThreadPoolExecutor PRIORITY_EXPORTER =
            new ScheduledThreadPoolExecutor(1, runnable -> {
                Thread t = new Thread(runnable, "M9DiagPrimaryIO");
                t.setDaemon(true);
                return t;
            });

    static {
        BUNDLE_EXECUTOR.setRemoveOnCancelPolicy(true);
        INDIVIDUAL_EXPORTER.setRemoveOnCancelPolicy(true);
        PRIORITY_EXPORTER.setRemoveOnCancelPolicy(true);
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

            // Do not retain caller bytes. The private file is the payload authority.
            Entry entry = new Entry(publicPath, privatePath, bytes.length, role,
                    System.currentTimeMillis(), seq);
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
                if (isPriorityRole(entry.role)) {
                    PRIORITY_EXPORTER.schedule(() -> exportIndividual(entry),
                            PRIMARY_TIMING_EXPORT_DELAY_MS, TimeUnit.MILLISECONDS);
                } else {
                    INDIVIDUAL_EXPORTER.schedule(() -> exportIndividual(entry),
                            INDIVIDUAL_DELAY_MS, TimeUnit.MILLISECONDS);
                }
            }
            Log.d(TAG, "M9SPOOLSTREAM1A private staged role=" + role
                    + "; payloadBytes=" + entry.byteCount
                    + "; elapsedMs=" + (elapsedNs / 1_000_000.0)
                    + "; pendingBundle=" + BUNDLE_PENDING.size()
                    + "; pendingIndividual=" + INDIVIDUAL_PENDING.size());
            return true;
        } catch (Throwable t) {
            PRIVATE_FAILED.incrementAndGet();
            Log.e(TAG, "M9SPOOLSTREAM1A private stage failed role=" + role + "; path=" + publicPath, t);
            return false;
        }
    }

    public static void setAppVisible(boolean visible) {
        appVisible = visible;
        if (!visible) {
            synchronized (BUNDLE_LOCK) {
                if (scheduledBundle != null) scheduledBundle.cancel(false);
            }
            INDIVIDUAL_EXPORTER.getQueue().clear();
            PRIORITY_EXPORTER.getQueue().clear();
            return;
        }
        BUNDLE_EXECUTOR.execute(() -> {
            if (recovered.compareAndSet(false, true)) recoverPrivate();
            if (!appVisible) return;
            scheduleBundle();
            int normalIndex = 0;
            int priorityIndex = 0;
            INDIVIDUAL_EXPORTER.getQueue().clear();
            PRIORITY_EXPORTER.getQueue().clear();
            List<Entry> pending = new ArrayList<>(INDIVIDUAL_PENDING.values());
            pending.sort(Comparator.comparingLong(e -> e.sequence));
            for (Entry e : pending) {
                if (isPriorityRole(e.role)) {
                    PRIORITY_EXPORTER.schedule(() -> exportIndividual(e),
                            PRIMARY_TIMING_EXPORT_DELAY_MS + 50L * priorityIndex++,
                            TimeUnit.MILLISECONDS);
                } else {
                    INDIVIDUAL_EXPORTER.schedule(() -> exportIndividual(e),
                            INDIVIDUAL_DELAY_MS + 250L * normalIndex++,
                            TimeUnit.MILLISECONDS);
                }
            }
        });
    }

    private static boolean isPriorityRole(String role) {
        return PRIORITY_ROLE.equals(role);
    }

    private static int priorityPendingCount() {
        int n = 0;
        for (Entry e : INDIVIDUAL_PENDING.values()) if (isPriorityRole(e.role)) n++;
        return n;
    }

    private static Path manifest(Entry e) {
        return e.privatePath.resolveSibling(e.privatePath.getFileName() + ".meta");
    }

    private static void persistManifest(Entry e) throws Exception {
        Properties p = new Properties();
        p.setProperty("publicPath", e.publicPath.toString());
        p.setProperty("role", e.role == null ? "diagnostic" : e.role);
        p.setProperty("stagedEpochMs", Long.toString(e.stagedEpochMs));
        p.setProperty("payloadBytes", Long.toString(e.byteCount));
        p.setProperty("memoryRevision", MEMORY_REVISION);
        Path m = manifest(e), tmp = m.resolveSibling(m.getFileName() + ".tmp");
        try (java.io.FileOutputStream out = new java.io.FileOutputStream(tmp.toFile())) {
            p.store(out, MEMORY_REVISION);
            out.getFD().sync();
        }
        Files.move(tmp, m, StandardCopyOption.REPLACE_EXISTING);
    }

    private static void removePrivate(Entry e) {
        try {
            Files.deleteIfExists(manifest(e));
            Files.deleteIfExists(e.privatePath);
        } catch (Exception ignored) {}
    }

    /**
     * Restart recovery is metadata-only. The old implementation read every payload
     * into a byte[] here and retained it in two maps, which could refill a 512 MB heap
     * before the camera was usable.
     */
    private static void recoverPrivate() {
        try {
            Context c = PhotonCamera.getAppContext();
            if (c == null) return;
            Path dir = c.getFilesDir().toPath().resolve("m9diag_spool");
            if (!Files.isDirectory(dir)) return;
            try (java.nio.file.DirectoryStream<Path> files = Files.newDirectoryStream(dir, "*.stage.meta")) {
                for (Path m : files) {
                    try {
                        Properties p = new Properties();
                        try (InputStream in = Files.newInputStream(m)) { p.load(in); }
                        String name = m.getFileName().toString();
                        Path source = m.resolveSibling(name.substring(0, name.length() - 5));
                        if (!Files.isRegularFile(source)) continue;
                        long size = Files.size(source);
                        Entry e = new Entry(
                                java.nio.file.Paths.get(p.getProperty("publicPath")),
                                source,
                                size,
                                p.getProperty("role", "recovered"),
                                Long.parseLong(p.getProperty("stagedEpochMs")),
                                SEQ.incrementAndGet());
                        String key = e.publicPath.toString();
                        INDIVIDUAL_PENDING.compute(key, (k, old) -> {
                            if (old != null && old.privatePath.equals(e.privatePath)) return old;
                            if (old != null && old.stagedEpochMs >= e.stagedEpochMs) {
                                removePrivate(e);
                                return old;
                            }
                            if (old != null) removePrivate(old);
                            BUNDLE_PENDING.put(key, e);
                            return e;
                        });
                        RECOVERED_ENTRIES.incrementAndGet();
                        RECOVERED_BYTES_REFERENCED.addAndGet(size);
                    } catch (Exception error) {
                        Log.w(TAG, "M9SPOOLSTREAM1A manifest retained after recovery error: " + error);
                    }
                }
            }
            Log.d(TAG, "M9SPOOLSTREAM1A recovery metadataOnly=true entries="
                    + RECOVERED_ENTRIES.get() + " referencedBytes="
                    + RECOVERED_BYTES_REFERENCED.get());
        } catch (Exception error) {
            Log.w(TAG, "M9SPOOLSTREAM1A recovery failed: " + error);
        }
    }

    private static void scheduleBundle() {
        if (!appVisible) return;
        synchronized (BUNDLE_LOCK) {
            if (scheduledBundle != null) scheduledBundle.cancel(false);
            scheduledBundle = BUNDLE_EXECUTOR.schedule(
                    M9DiagnosticBurstSpool::flushBundle, BUNDLE_IDLE_MS, TimeUnit.MILLISECONDS);
        }
    }

    /**
     * The burst is now a bounded manifest only. Complete JSON remains in each private
     * stage and is streamed later as the normal individual sidecar.
     */
    private static void flushBundle() {
        if (!appVisible) return;
        List<Entry> entries = new ArrayList<>(BUNDLE_PENDING.values());
        if (entries.isEmpty()) return;
        entries.sort(Comparator.comparingLong(e -> e.sequence));
        final long startedNs = System.nanoTime();
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            JSONObject root = new JSONObject();
            root.put("schema", "m9cam.diagnosticbundle.v1.sidecar1b");
            root.put("memoryRevision", MEMORY_REVISION);
            root.put("bundleMode", "bounded_manifest_payloads_streamed_individually");
            root.put("createdEpochMs", System.currentTimeMillis());
            root.put("entryCount", entries.size());
            root.put("bundleIdleMs", BUNDLE_IDLE_MS);
            root.put("individualExportDelayMs", INDIVIDUAL_DELAY_MS);
            root.put("primaryTimingExportDelayMs", PRIMARY_TIMING_EXPORT_DELAY_MS);
            root.put("primaryTimingPriorityExporter", true);
            JSONArray array = new JSONArray();
            long referencedBytes = 0L;
            for (Entry e : entries) {
                referencedBytes += e.byteCount;
                JSONObject item = new JSONObject();
                item.put("role", e.role);
                item.put("publicPath", e.publicPath.toString());
                item.put("publicFilename", e.publicPath.getFileName().toString());
                item.put("stagedEpochMs", e.stagedEpochMs);
                item.put("sequence", e.sequence);
                item.put("payloadBytes", e.byteCount);
                item.put("payloadInline", false);
                item.put("payloadDelivery", "individual_stream_export");
                array.put(item);
            }
            root.put("entries", array);
            root.put("referencedPayloadBytes", referencedBytes);
            root.put("payloadBytesMaterializedForBundle", 0);
            root.put("spoolTelemetryAtBundle", snapshotJson());
            byte[] bundleBytes = root.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8);
            Path parent = entries.get(0).publicPath.getParent();
            if (parent == null) throw new IllegalStateException("public diagnostic parent missing");
            Path bundlePath = parent.resolve("M9_DIAGNOSTICS_BURST_"
                    + System.currentTimeMillis() + "_" + entries.size() + ".json");
            if (!writePublicBytes(bundlePath, bundleBytes)) {
                throw new java.io.IOException("public burst manifest write failed: " + bundlePath);
            }
            for (Entry e : entries) {
                BUNDLE_PENDING.remove(e.publicPath.toString(), e);
            }
            lastBundlePath = bundlePath.toString();
            BUNDLE_WRITES.incrementAndGet();
            long elapsedNs = System.nanoTime() - startedNs;
            BUNDLE_LAST_NS.set(elapsedNs);
            BUNDLE_TOTAL_NS.addAndGet(elapsedNs);
            Log.d(TAG, "M9SPOOLSTREAM1A burst manifest exported entries=" + entries.size()
                    + "; referencedBytes=" + referencedBytes
                    + "; manifestBytes=" + bundleBytes.length
                    + "; elapsedMs=" + (elapsedNs / 1_000_000.0));
        } catch (Throwable t) {
            BUNDLE_FAILED.incrementAndGet();
            Log.e(TAG, "M9SPOOLSTREAM1A burst manifest export failed; private staged files retained", t);
        }
    }

    private static void exportIndividual(Entry entry) {
        if (!appVisible) return;
        String key = entry.publicPath.toString();
        if (INDIVIDUAL_PENDING.get(key) != entry) return;
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            if (!streamPublic(entry.publicPath, entry.privatePath)) {
                throw new java.io.IOException("individual public stream export failed");
            }
            INDIVIDUAL_WRITES.incrementAndGet();
            INDIVIDUAL_PENDING.remove(key, entry);
            removePrivate(entry);
            Log.d(TAG, "M9SPOOLSTREAM1A individual stream export complete role="
                    + entry.role + "; bytes=" + entry.byteCount
                    + "; remaining=" + INDIVIDUAL_PENDING.size());
        } catch (Throwable t) {
            INDIVIDUAL_FAILED.incrementAndGet();
            Log.e(TAG, "M9SPOOLSTREAM1A individual stream export failed; private stage retained: "
                    + entry.publicPath, t);
        }
    }

    private static boolean writePublicBytes(Path path, byte[] bytes) {
        if (!appVisible) return false;
        try {
            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(path.toString());
            if (safOut != null) {
                try (OutputStream out = safOut) {
                    out.write(bytes);
                    out.flush();
                }
                return true;
            }
        } catch (Throwable safError) {
            Log.w(TAG, "M9SPOOLSTREAM1A SAF manifest write failed, trying direct path: " + safError);
        }
        if (!appVisible) return false;
        try (OutputStream out = Files.newOutputStream(path)) {
            out.write(bytes);
            out.flush();
            return true;
        } catch (Throwable directError) {
            Log.e(TAG, "M9SPOOLSTREAM1A all manifest write routes failed: " + path, directError);
            return false;
        }
    }

    private static boolean streamPublic(Path publicPath, Path privatePath) {
        if (!appVisible || !Files.isRegularFile(privatePath)) return false;
        try {
            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(publicPath.toString());
            if (safOut != null) {
                try (InputStream in = Files.newInputStream(privatePath);
                     OutputStream out = safOut) {
                    copy(in, out);
                    out.flush();
                }
                return true;
            }
        } catch (Throwable safError) {
            Log.w(TAG, "M9SPOOLSTREAM1A SAF stream failed, trying direct path: " + safError);
        }
        if (!appVisible) return false;
        try (InputStream in = Files.newInputStream(privatePath);
             OutputStream out = Files.newOutputStream(publicPath)) {
            copy(in, out);
            out.flush();
            return true;
        } catch (Throwable directError) {
            Log.e(TAG, "M9SPOOLSTREAM1A all stream routes failed: " + publicPath, directError);
            return false;
        }
    }

    private static void copy(InputStream in, OutputStream out) throws java.io.IOException {
        byte[] buffer = new byte[COPY_BUFFER_BYTES];
        int n;
        while ((n = in.read(buffer)) >= 0) {
            if (n > 0) out.write(buffer, 0, n);
        }
    }

    public static JSONObject snapshotJson() {
        JSONObject o = new JSONObject();
        try {
            long privateCount = PRIVATE_STAGED.get();
            long bundleCount = BUNDLE_WRITES.get();
            o.put("schema", SCHEMA);
            o.put("ioRevision", "M9DIAGIO1E");
            o.put("memoryRevision", MEMORY_REVISION);
            o.put("appVisible", appVisible);
            o.put("publicExportRequiresVisibleActivity", true);
            o.put("restartRecoveryForNewManifests", true);
            o.put("recoveryPayloadMaterialized", false);
            o.put("bundlePayloadMaterialized", false);
            o.put("individualExportMode", "64KiB_stream");
            o.put("policy", "private_immediate_manifest_bundle_eventual_individual_stream");
            o.put("bundleIdleMs", BUNDLE_IDLE_MS);
            o.put("individualExportDelayMs", INDIVIDUAL_DELAY_MS);
            o.put("primaryTimingExportDelayMs", PRIMARY_TIMING_EXPORT_DELAY_MS);
            o.put("primaryTimingPriorityRole", PRIORITY_ROLE);
            o.put("primaryTimingPriorityExporter", true);
            o.put("priorityPendingEntries", priorityPendingCount());
            o.put("privateStaged", privateCount);
            o.put("privateStageFailed", PRIVATE_FAILED.get());
            o.put("bundleWrites", bundleCount);
            o.put("bundleFailed", BUNDLE_FAILED.get());
            o.put("pendingBundleEntries", BUNDLE_PENDING.size());
            o.put("pendingIndividualEntries", INDIVIDUAL_PENDING.size());
            o.put("individualWrites", INDIVIDUAL_WRITES.get());
            o.put("individualFailed", INDIVIDUAL_FAILED.get());
            o.put("recoveredEntries", RECOVERED_ENTRIES.get());
            o.put("recoveredPayloadBytesReferenced", RECOVERED_BYTES_REFERENCED.get());
            o.put("recoveredPayloadBytesHeldInJavaHeap", 0);
            o.put("privateLastStageElapsedMs", PRIVATE_LAST_NS.get() / 1_000_000.0);
            if (privateCount > 0) {
                o.put("privateAverageStageElapsedMs",
                        PRIVATE_TOTAL_NS.get() / 1_000_000.0 / privateCount);
            }
            o.put("bundleLastPersistElapsedMs", BUNDLE_LAST_NS.get() / 1_000_000.0);
            if (bundleCount > 0) {
                o.put("bundleAveragePersistElapsedMs",
                        BUNDLE_TOTAL_NS.get() / 1_000_000.0 / bundleCount);
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
        final long byteCount;
        final String role;
        final long stagedEpochMs;
        final long sequence;

        Entry(Path publicPath, Path privatePath, long byteCount, String role,
              long stagedEpochMs, long sequence) {
            this.publicPath = publicPath;
            this.privatePath = privatePath;
            this.byteCount = Math.max(0L, byteCount);
            this.role = role != null ? role : "unknown";
            this.stagedEpochMs = stagedEpochMs;
            this.sequence = sequence;
        }
    }
}
