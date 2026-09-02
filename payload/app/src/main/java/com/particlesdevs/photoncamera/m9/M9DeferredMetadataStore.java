package com.particlesdevs.photoncamera.m9;

import android.os.Process;

import com.particlesdevs.photoncamera.util.Log;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;

import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * METAFREEZE1A development-sidecar persistence.
 *
 * Capture-specific JSON is fully materialized to immutable UTF-8 bytes while
 * DefaultSaver still owns the current capture state. Only the potentially slow
 * SAF/filesystem persistence is deferred. This keeps the diagnostic snapshot
 * exact while removing sidecar I/O from the camera/saver critical section.
 */
public final class M9DeferredMetadataStore {
    private static final String TAG = "M9MetadataDeferred";
    private static final ConcurrentHashMap<String, byte[]> STAGED = new ConcurrentHashMap<>();
    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor(runnable -> {
        Thread t = new Thread(runnable, "M9MetadataPersist");
        t.setDaemon(true);
        return t;
    });

    private M9DeferredMetadataStore() {}

    public static boolean stage(Path jsonPath, byte[] bytes) {
        if (jsonPath == null || bytes == null) return false;
        STAGED.put(jsonPath.toString(), bytes);
        return true;
    }

    public static Path sidecarPath(Path dngPath) {
        if (dngPath == null) return null;
        String filename = dngPath.getFileName().toString();
        int dot = filename.lastIndexOf('.');
        String stem = dot > 0 ? filename.substring(0, dot) : filename;
        return dngPath.resolveSibling(stem + "_M9.json");
    }

    public static boolean persistAsyncForDng(Path dngPath) {
        final Path jsonPath = sidecarPath(dngPath);
        if (jsonPath == null) return false;
        final byte[] bytes = STAGED.remove(jsonPath.toString());
        if (bytes == null) {
            Log.w(TAG, "No staged metadata for " + jsonPath);
            return false;
        }
        EXECUTOR.execute(() -> persist(jsonPath, bytes));
        return true;
    }

    public static void discardForDng(Path dngPath) {
        Path jsonPath = sidecarPath(dngPath);
        if (jsonPath != null) STAGED.remove(jsonPath.toString());
    }

    private static void persist(Path jsonPath, byte[] bytes) {
        long startedNs = System.nanoTime();
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(jsonPath.toString());
            if (safOut != null) {
                try (OutputStream out = safOut) {
                    out.write(bytes);
                    out.flush();
                }
            } else {
                try (OutputStream out = Files.newOutputStream(jsonPath)) {
                    out.write(bytes);
                    out.flush();
                }
            }
            long elapsedMs = (System.nanoTime() - startedNs) / 1_000_000L;
            Log.d(TAG, "Deferred capture metadata persisted in " + elapsedMs + " ms: " + jsonPath);
        } catch (Throwable t) {
            Log.e(TAG, "Unable to persist deferred capture metadata: " + jsonPath, t);
        }
    }
}
