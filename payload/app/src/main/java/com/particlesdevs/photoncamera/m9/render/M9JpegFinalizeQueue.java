package com.particlesdevs.photoncamera.m9.render;

import android.os.Process;

import androidx.exifinterface.media.ExifInterface;

import com.particlesdevs.photoncamera.api.ParseExif;
import com.particlesdevs.photoncamera.processing.ProcessingEventsListener;
import com.particlesdevs.photoncamera.util.Log;

import org.json.JSONObject;

import java.nio.file.Path;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * PERF3F EXIFASYNC1A: bounded JPEG metadata finalization off the single M9 render worker.
 *
 * The photographic JPEG payload has already been written by the exact PERF3E path before a
 * Ticket is submitted here. This worker performs the same Photon EXIF operations as before:
 * ParseExif.setAllAttributes(path, data) -> ExifInterface.saveAttributes(). Only after those
 * operations succeed is notifyImageSavedStatus(true, path) invoked, which preserves the existing
 * media-scanner/gallery publication boundary.
 *
 * Queue saturation never drops metadata. A rejected submit runs the exact finalization
 * synchronously on the render worker as a preservation fallback.
 */
public final class M9JpegFinalizeQueue {
    private static final String TAG = "M9JpegFinalize";
    private static final int MAX_PENDING = 2;
    private static final AtomicLong FALLBACK_COUNT = new AtomicLong(0L);

    private static final ThreadFactory THREAD_FACTORY = runnable -> {
        Thread t = new Thread(runnable, "M9JpegExifIO");
        t.setDaemon(true);
        return t;
    };

    private static final ThreadPoolExecutor EXECUTOR = new ThreadPoolExecutor(
            1, 1, 0L, TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(MAX_PENDING), THREAD_FACTORY);

    private M9JpegFinalizeQueue() {}

    public static final class Ticket {
        private final CountDownLatch done = new CountDownLatch(1);
        private final long queuedAtNs = System.nanoTime();
        private final int queueDepthAtSubmit;
        private final int activeCountAtSubmit;
        private final int queueCapacity;
        private volatile boolean asyncAccepted;
        private volatile boolean syncFallback;
        private volatile boolean success;
        private volatile long queueWaitElapsedMs = -1L;
        private volatile long exifSetupElapsedNs = -1L;
        private volatile long exifSaveElapsedNs = -1L;
        private volatile long finalizeElapsedNs = -1L;
        private volatile long publishElapsedNs = -1L;
        private volatile long fallbackCountSnapshot;
        private volatile String error;

        Ticket(int queueDepthAtSubmit, int activeCountAtSubmit, int queueCapacity) {
            this.queueDepthAtSubmit = queueDepthAtSubmit;
            this.activeCountAtSubmit = activeCountAtSubmit;
            this.queueCapacity = queueCapacity;
        }

        public void awaitCompletion() {
            boolean interrupted = false;
            for (;;) {
                try {
                    done.await();
                    break;
                } catch (InterruptedException e) {
                    interrupted = true;
                }
            }
            if (interrupted) Thread.currentThread().interrupt();
        }

        public boolean isSuccess() {
            return success;
        }

        public String error() {
            return error;
        }

        public void appendDiagnostics(JSONObject diag) {
            if (diag == null) return;
            try {
                diag.put("jpegExifAsyncAccepted", asyncAccepted);
                diag.put("jpegExifSyncFallback", syncFallback);
                diag.put("jpegExifFinalizeSuccess", success);
                diag.put("jpegExifQueueDepthAtSubmit", queueDepthAtSubmit);
                diag.put("jpegExifActiveCountAtSubmit", activeCountAtSubmit);
                diag.put("jpegExifQueueCapacity", queueCapacity);
                diag.put("jpegExifQueueWaitElapsedMs", queueWaitElapsedMs);
                diag.put("jpegExifSetupElapsedMs", exifSetupElapsedNs >= 0 ? exifSetupElapsedNs / 1_000_000.0 : -1.0);
                diag.put("jpegExifSaveElapsedMs", exifSaveElapsedNs >= 0 ? exifSaveElapsedNs / 1_000_000.0 : -1.0);
                diag.put("jpegExifFinalizeElapsedMs", finalizeElapsedNs >= 0 ? finalizeElapsedNs / 1_000_000.0 : -1.0);
                diag.put("jpegPublicationElapsedMs", publishElapsedNs >= 0 ? publishElapsedNs / 1_000_000.0 : -1.0);
                diag.put("jpegExifFallbackCountSnapshot", fallbackCountSnapshot);
                diag.put("jpegPublicationAfterExif", true);
                diag.put("jpegExifFinalizerThread", asyncAccepted ? "M9JpegExifIO" : "M9PrimaryRenderer");
                if (error != null && !error.isEmpty()) diag.put("jpegExifFinalizeError", error);
            } catch (Throwable ignored) {
            }
        }
    }

    public static Ticket submit(Path jpegPath,
                                ParseExif.ExifData exifData,
                                ProcessingEventsListener processingEventsListener) {
        if (jpegPath == null) throw new IllegalArgumentException("missing JPEG path");
        if (exifData == null) throw new IllegalArgumentException("missing JPEG EXIF data");

        final Ticket ticket = new Ticket(
                EXECUTOR.getQueue().size(),
                EXECUTOR.getActiveCount(),
                MAX_PENDING);
        Runnable task = () -> runFinalize(ticket, jpegPath, exifData, processingEventsListener, true);
        try {
            ticket.asyncAccepted = true;
            EXECUTOR.execute(task);
            ticket.fallbackCountSnapshot = FALLBACK_COUNT.get();
            Log.d(TAG, "EXIFASYNC1A accepted; pending=" + EXECUTOR.getQueue().size()
                    + "; active=" + EXECUTOR.getActiveCount());
        } catch (RejectedExecutionException full) {
            ticket.asyncAccepted = false;
            ticket.syncFallback = true;
            ticket.fallbackCountSnapshot = FALLBACK_COUNT.incrementAndGet();
            Log.d(TAG, "EXIFASYNC1A bounded metadata queue saturated; finalizing synchronously; fallbackCount="
                    + ticket.fallbackCountSnapshot);
            runFinalize(ticket, jpegPath, exifData, processingEventsListener, false);
        }
        return ticket;
    }

    private static void runFinalize(Ticket ticket,
                                    Path jpegPath,
                                    ParseExif.ExifData exifData,
                                    ProcessingEventsListener processingEventsListener,
                                    boolean backgroundThread) {
        final long startedNs = System.nanoTime();
        ticket.queueWaitElapsedMs = (startedNs - ticket.queuedAtNs) / 1_000_000L;
        try {
            if (backgroundThread) Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);

            long stageStartedNs = System.nanoTime();
            ExifInterface inter = ParseExif.setAllAttributes(jpegPath.toFile(), exifData);
            ticket.exifSetupElapsedNs = System.nanoTime() - stageStartedNs;
            if (inter == null) throw new IllegalStateException("ParseExif.setAllAttributes returned null");

            stageStartedNs = System.nanoTime();
            inter.saveAttributes();
            ticket.exifSaveElapsedNs = System.nanoTime() - stageStartedNs;
            ticket.success = true;

            // Photon publication remains strictly after EXIF saveAttributes(), exactly as before.
            if (processingEventsListener != null) {
                stageStartedNs = System.nanoTime();
                processingEventsListener.notifyImageSavedStatus(true, jpegPath);
                ticket.publishElapsedNs = System.nanoTime() - stageStartedNs;
            }
        } catch (Throwable t) {
            ticket.success = false;
            ticket.error = t.toString();
            Log.e(TAG, "EXIFASYNC1A JPEG finalization failed: " + jpegPath, t);
        } finally {
            ticket.finalizeElapsedNs = System.nanoTime() - startedNs;
            ticket.done.countDown();
            Log.d(TAG, "EXIFASYNC1A complete; success=" + ticket.success
                    + "; async=" + ticket.asyncAccepted
                    + "; fallback=" + ticket.syncFallback
                    + "; queueWaitMs=" + ticket.queueWaitElapsedMs
                    + "; finalizeMs=" + (ticket.finalizeElapsedNs / 1_000_000.0));
        }
    }
}
