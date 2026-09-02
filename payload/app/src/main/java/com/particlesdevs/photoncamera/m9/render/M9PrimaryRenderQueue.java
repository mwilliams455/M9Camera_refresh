package com.particlesdevs.photoncamera.m9.render;

import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;
import android.os.Process;

import com.particlesdevs.photoncamera.processing.ImageFrame;
import com.particlesdevs.photoncamera.processing.ImageSaver;
import com.particlesdevs.photoncamera.m9.M9DeferredMetadataStore;
import com.particlesdevs.photoncamera.processing.ProcessingEventsListener;
import com.particlesdevs.photoncamera.util.Log;

import org.json.JSONObject;

import java.nio.file.Path;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * PRIMARY2.5 QUEUE1B + TIMINGFREEZE1A + DNGASYNC1A + EXIFASYNC1A finished-image processor.
 *
 * Ownership contract:
 *   DefaultSaver removes the already Allocator-owned Photon ImageFrame from
 *   IMAGE_BUFFER and releases bufferLock. No second RAW copy is made. If this
 *   method returns true, this queue owns that ImageFrame. The M9 render worker
 *   uses it through finished-JPEG rendering, then DNGASYNC1A transfers ownership
 *   to a bounded single DNG worker. The DNG worker closes the frame only after
 *   the untouched development DNG is complete and final PRIMARY timing has been
 *   frozen to immutable bytes. If the DNG handoff queue is saturated, DNG save
 *   falls back synchronously on M9PrimaryRenderer so a DNG is never silently lost
 *   and RAW ownership cannot grow without bound.
 *
 * QUEUE1B contract:
 *   the UI shutter path performs a nonblocking capacity preflight before
 *   CaptureController.takePicture(), so a known-saturated renderer does not acquire
 *   a RAW that would be discarded. This executor-level rejection remains as a
 *   mandatory race/failure safety net: saturation MUST NEVER block Photon. Frozen
 *   capture metadata and a fallback rejection timing sidecar are persisted
 *   asynchronously if that safety net is reached.
 */
public final class M9PrimaryRenderQueue {
    private static final String TAG = "M9PrimaryRender";
    private static final String DNG_TAG = "M9PrimaryDng";
    private static final String OWNERSHIP_MODEL = "direct_Photon_ImageFrame_transfer";

    private static final int MAX_PENDING = 2;
    private static final int MAX_IN_FLIGHT = 1 + MAX_PENDING;
    private static final AtomicLong IN_FLIGHT_COUNT = new AtomicLong(0L);
    private static final AtomicLong QUEUE_FULL_COUNT = new AtomicLong(0L);
    private static final AtomicLong ADMISSION_REJECT_COUNT = new AtomicLong(0L);

    // DNGASYNC1A is deliberately smaller than the render queue. One DNG may be
    // active and only one may wait. A third attempted handoff falls back to the
    // render worker rather than retaining another full RAW frame in memory.
    private static final int DNG_MAX_PENDING = 1;
    private static final AtomicLong DNG_HANDOFF_FALLBACK_COUNT = new AtomicLong(0L);

    private static final ThreadFactory THREAD_FACTORY = runnable -> {
        Thread t = new Thread(runnable, "M9PrimaryRenderer");
        t.setDaemon(true);
        return t;
    };

    private static final ThreadPoolExecutor EXECUTOR = new ThreadPoolExecutor(
            1, 1, 0L, TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(MAX_PENDING), THREAD_FACTORY);

    private static final ThreadFactory DNG_THREAD_FACTORY = runnable -> {
        Thread t = new Thread(runnable, "M9PrimaryDngIO");
        t.setDaemon(true);
        return t;
    };

    private static final ThreadPoolExecutor DNG_EXECUTOR = new ThreadPoolExecutor(
            1, 1, 0L, TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(DNG_MAX_PENDING), DNG_THREAD_FACTORY);

    private M9PrimaryRenderQueue() {}

    /**
     * QUEUE1B shutter-side preflight. This remains non-reserving. DNGASYNC1A
     * does not enlarge the renderer queue; it only lets a completed render hand
     * its already-owned RAW to a separately bounded DNG stage.
     */
    public static boolean preflightCaptureAdmission() {
        final int active = EXECUTOR.getActiveCount();
        final int pending = EXECUTOR.getQueue().size();
        final long inFlight = IN_FLIGHT_COUNT.get();
        final boolean accepted = inFlight < MAX_IN_FLIGHT;
        if (!accepted) {
            final long rejected = ADMISSION_REJECT_COUNT.incrementAndGet();
            Log.d(TAG, "PRIMARY2.4 QUEUE1B shutter admission rejected before RAW capture; "
                    + "pending=" + pending + "; active=" + active
                    + "; inFlight=" + inFlight + "; maxInFlight=" + MAX_IN_FLIGHT
                    + "; admissionRejectCount=" + rejected);
        }
        return accepted;
    }

    public static long admissionRejectCount() {
        return ADMISSION_REJECT_COUNT.get();
    }

    private static final class QueueTelemetry {
        final int queueDepthAtEnqueue;
        final int activeRenderCountAtEnqueue;
        final int queueCapacity;
        volatile long queueFullCountAtEnqueue;
        volatile long enqueueWaitElapsedMs;

        QueueTelemetry(int queueDepthAtEnqueue,
                       int activeRenderCountAtEnqueue,
                       int queueCapacity,
                       long queueFullCountAtEnqueue) {
            this.queueDepthAtEnqueue = queueDepthAtEnqueue;
            this.activeRenderCountAtEnqueue = activeRenderCountAtEnqueue;
            this.queueCapacity = queueCapacity;
            this.queueFullCountAtEnqueue = queueFullCountAtEnqueue;
            this.enqueueWaitElapsedMs = -1L;
        }
    }

    /** Immutable except for the render-worker release metric, which is written immediately
     * after the async handoff. The DNG worker only reads it after DNG persistence completes. */
    private static final class DngJob {
        final Path dngPath;
        final ImageFrame ownedFrame;
        final CameraCharacteristics characteristics;
        final CaptureResult captureResult;
        final int cameraRotation;
        final ProcessingEventsListener processingEventsListener;
        final Path jpegPath;
        final boolean jpegPayloadSaved;
        final M9JpegFinalizeQueue.Ticket jpegFinalizeTicket;
        final String rendererDiagnosticsJson;
        final String renderError;
        final long ownershipTransferMs;
        final long captureMetadataMs;
        final long queueWaitMs;
        final long renderElapsedMs;
        final long renderWorkerStartedNs;
        final long renderWorkerElapsedAtHandoffMs;
        final QueueTelemetry queueTelemetry;
        final long dngQueuedAtNs;
        final int dngQueueDepthAtHandoff;
        final int dngActiveCountAtHandoff;
        final int dngQueueCapacity;
        volatile long dngHandoffElapsedMs;
        volatile long renderWorkerReleaseElapsedMs;

        DngJob(Path dngPath,
               ImageFrame ownedFrame,
               CameraCharacteristics characteristics,
               CaptureResult captureResult,
               int cameraRotation,
               ProcessingEventsListener processingEventsListener,
               Path jpegPath,
               boolean jpegPayloadSaved,
               M9JpegFinalizeQueue.Ticket jpegFinalizeTicket,
               String rendererDiagnosticsJson,
               String renderError,
               long ownershipTransferMs,
               long captureMetadataMs,
               long queueWaitMs,
               long renderElapsedMs,
               long renderWorkerStartedNs,
               long renderWorkerElapsedAtHandoffMs,
               QueueTelemetry queueTelemetry,
               int dngQueueDepthAtHandoff,
               int dngActiveCountAtHandoff,
               int dngQueueCapacity) {
            this.dngPath = dngPath;
            this.ownedFrame = ownedFrame;
            this.characteristics = characteristics;
            this.captureResult = captureResult;
            this.cameraRotation = cameraRotation;
            this.processingEventsListener = processingEventsListener;
            this.jpegPath = jpegPath;
            this.jpegPayloadSaved = jpegPayloadSaved;
            this.jpegFinalizeTicket = jpegFinalizeTicket;
            this.rendererDiagnosticsJson = rendererDiagnosticsJson;
            this.renderError = renderError;
            this.ownershipTransferMs = ownershipTransferMs;
            this.captureMetadataMs = captureMetadataMs;
            this.queueWaitMs = queueWaitMs;
            this.renderElapsedMs = renderElapsedMs;
            this.renderWorkerStartedNs = renderWorkerStartedNs;
            this.renderWorkerElapsedAtHandoffMs = renderWorkerElapsedAtHandoffMs;
            this.queueTelemetry = queueTelemetry;
            this.dngQueuedAtNs = System.nanoTime();
            this.dngQueueDepthAtHandoff = dngQueueDepthAtHandoff;
            this.dngActiveCountAtHandoff = dngActiveCountAtHandoff;
            this.dngQueueCapacity = dngQueueCapacity;
            this.dngHandoffElapsedMs = -1L;
            this.renderWorkerReleaseElapsedMs = -1L;
        }
    }

    public static boolean enqueue(Path dngPath,
                                  ImageFrame ownedFrame,
                                  CameraCharacteristics characteristics,
                                  CaptureResult captureResult,
                                  CaptureRequest captureRequest,
                                  int cameraRotation,
                                  long ownershipTransferMs,
                                  long captureMetadataMs,
                                  ProcessingEventsListener processingEventsListener) {
        if (ownedFrame == null || ownedFrame.buffer == null) {
            throw new IllegalArgumentException("missing Photon-owned RAW frame");
        }

        final long enqueueStartedNs = System.nanoTime();
        final QueueTelemetry queueTelemetry = new QueueTelemetry(
                EXECUTOR.getQueue().size(),
                EXECUTOR.getActiveCount(),
                MAX_PENDING,
                QUEUE_FULL_COUNT.get());
        final long queuedAtNs = System.nanoTime();

        Runnable job = () -> {
            final long workerStartedNs = System.nanoTime();
            final long queueWaitMs = (workerStartedNs - queuedAtNs) / 1_000_000L;
            M9R35Renderer.Result renderResult = null;
            DngJob dngJob = null;
            boolean frameTransferredToDngWorker = false;
            long renderElapsedMs = -1L;
            String error = null;
            try {
                Process.setThreadPriority(Process.THREAD_PRIORITY_DEFAULT);
                Log.d(TAG, "starting PRIMARY2.5 QUEUE1B-NAME1A-TIMINGFREEZE1A-DNGASYNC1A-EXIFASYNC1A TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A-COLORNATIVE2A-FIX1 M9 render after "
                        + queueWaitMs + " ms queue wait; pending=" + EXECUTOR.getQueue().size()
                        + "; depthAtEnqueue=" + queueTelemetry.queueDepthAtEnqueue
                        + "; activeAtEnqueue=" + queueTelemetry.activeRenderCountAtEnqueue);

                // Finished image remains first and photographically unchanged.
                long renderStartedNs = System.nanoTime();
                renderResult = M9R35Renderer.renderAndSavePrimary(
                        dngPath, ownedFrame, characteristics, captureResult, captureRequest, cameraRotation);
                renderElapsedMs = (System.nanoTime() - renderStartedNs) / 1_000_000L;

                final Path jpegPath = renderResult != null ? renderResult.jpegPath : null;
                final boolean jpegPayloadSaved = renderResult != null && renderResult.success && jpegPath != null;
                M9JpegFinalizeQueue.Ticket jpegFinalizeTicket = null;
                if (jpegPayloadSaved) {
                    // PERF3F EXIFASYNC1A: publication moves with EXIF finalization. The renderer
                    // has already written the exact PERF3E JPEG payload; do not media-scan it here.
                    jpegFinalizeTicket = M9JpegFinalizeQueue.submit(
                            jpegPath, renderResult.jpegExifData, processingEventsListener);
                } else {
                    error = renderResult != null ? renderResult.error : "null renderer result";
                    Log.e(TAG, "PRIMARY2.5 EXIFASYNC1A M9 JPEG payload failed: " + error);
                }

                // Freeze renderer diagnostics to text before ownership leaves M9PrimaryRenderer.
                // No mutable renderer Result/JSONObject is retained by the DNG worker.
                String rendererDiagnosticsJson = null;
                if (renderResult != null && renderResult.diagnostics != null) {
                    rendererDiagnosticsJson = renderResult.diagnostics.toString();
                }

                final long renderWorkerElapsedAtHandoffMs =
                        (System.nanoTime() - workerStartedNs) / 1_000_000L;
                dngJob = new DngJob(
                        dngPath,
                        ownedFrame,
                        characteristics,
                        captureResult,
                        cameraRotation,
                        processingEventsListener,
                        jpegPath,
                        jpegPayloadSaved,
                        jpegFinalizeTicket,
                        rendererDiagnosticsJson,
                        error,
                        ownershipTransferMs,
                        captureMetadataMs,
                        queueWaitMs,
                        renderElapsedMs,
                        workerStartedNs,
                        renderWorkerElapsedAtHandoffMs,
                        queueTelemetry,
                        DNG_EXECUTOR.getQueue().size(),
                        DNG_EXECUTOR.getActiveCount(),
                        DNG_MAX_PENDING);

                final long dngHandoffStartedNs = System.nanoTime();
                try {
                    final DngJob acceptedDngJob = dngJob;
                    DNG_EXECUTOR.execute(() -> runAsyncDng(acceptedDngJob));
                    dngJob.dngHandoffElapsedMs =
                            (System.nanoTime() - dngHandoffStartedNs) / 1_000_000L;
                    frameTransferredToDngWorker = true;
                    Log.d(TAG, "PRIMARY2.4 DNGASYNC1A RAW ownership handoff accepted in "
                            + dngJob.dngHandoffElapsedMs + " ms; dngPending="
                            + DNG_EXECUTOR.getQueue().size() + "; dngActive="
                            + DNG_EXECUTOR.getActiveCount());
                } catch (RejectedExecutionException dngFull) {
                    dngJob.dngHandoffElapsedMs =
                            (System.nanoTime() - dngHandoffStartedNs) / 1_000_000L;
                    final long fallbackCount = DNG_HANDOFF_FALLBACK_COUNT.incrementAndGet();
                    Log.d(TAG, "PRIMARY2.4 DNGASYNC1A bounded DNG queue saturated; saving DNG synchronously to preserve output; "
                            + "fallbackCount=" + fallbackCount + "; dngPending="
                            + DNG_EXECUTOR.getQueue().size() + "; dngActive="
                            + DNG_EXECUTOR.getActiveCount());
                    runDngAndFinalize(dngJob, false, true, fallbackCount, 0L);
                }
            } catch (Throwable t) {
                error = t.toString();
                Log.e(TAG, "PRIMARY2.4 QUEUE1B DNGASYNC1A render worker failed", t);
                // Preserve the pre-DNG failure behavior: do not invent a development DNG if
                // rendering itself threw before the handoff point. Still flush frozen diagnostics.
                boolean captureMetadataPersistScheduled = M9DeferredMetadataStore.persistAsyncForDng(dngPath);
                long workerElapsedMs = (System.nanoTime() - workerStartedNs) / 1_000_000L;
                Path jpegPath = renderResult != null ? renderResult.jpegPath : null;
                boolean jpegSaved = false; // EXIF/publication completion is not proven on this failure path.
                JSONObject diagnostics = renderResult != null ? renderResult.diagnostics : null;
                M9PrimaryTimingWriter.freezeAndWriteAsync(
                        dngPath,
                        jpegPath,
                        jpegSaved,
                        false,
                        ownershipTransferMs,
                        captureMetadataMs,
                        queueWaitMs,
                        renderElapsedMs,
                        -1L,
                        workerElapsedMs,
                        workerElapsedMs,
                        "not_started_render_failure",
                        false,
                        false,
                        0,
                        0,
                        DNG_MAX_PENDING,
                        -1L,
                        -1L,
                        DNG_HANDOFF_FALLBACK_COUNT.get(),
                        captureMetadataPersistScheduled,
                        queueTelemetry.queueDepthAtEnqueue,
                        queueTelemetry.activeRenderCountAtEnqueue,
                        queueTelemetry.queueCapacity,
                        queueTelemetry.queueFullCountAtEnqueue,
                        queueTelemetry.enqueueWaitElapsedMs,
                        diagnostics,
                        error,
                        "M9PrimaryRenderer");
            } finally {
                // DNGASYNC1A releases renderer capacity independently of RAW lifetime. If the
                // async handoff succeeded, M9PrimaryDngIO now owns/ultimately closes the frame.
                // Otherwise the render worker still owns it and closes it here.
                try {
                    if (!frameTransferredToDngWorker) {
                        ownedFrame.close();
                    }
                } finally {
                    IN_FLIGHT_COUNT.decrementAndGet();
                }
                final long workerReleaseElapsedMs =
                        (System.nanoTime() - workerStartedNs) / 1_000_000L;
                if (frameTransferredToDngWorker && dngJob != null) {
                    dngJob.renderWorkerReleaseElapsedMs = workerReleaseElapsedMs;
                    Log.d(TAG, "PRIMARY2.4 QUEUE1B DNGASYNC1A render worker released in "
                            + workerReleaseElapsedMs + " ms; RAW owned by M9PrimaryDngIO; next render may start now");
                } else {
                    Log.d(TAG, "PRIMARY2.4 QUEUE1B DNGASYNC1A render worker released in "
                            + workerReleaseElapsedMs + " ms; RAW closed on render worker");
                }
            }
        };

        IN_FLIGHT_COUNT.incrementAndGet();
        try {
            EXECUTOR.execute(job);
            queueTelemetry.enqueueWaitElapsedMs =
                    (System.nanoTime() - enqueueStartedNs) / 1_000_000L;
            Log.d(TAG, "PRIMARY2.4 QUEUE1B enqueue accepted without blocking in "
                    + queueTelemetry.enqueueWaitElapsedMs + " ms; depthAtEnqueue="
                    + queueTelemetry.queueDepthAtEnqueue + "; activeAtEnqueue="
                    + queueTelemetry.activeRenderCountAtEnqueue);
            return true;
        } catch (RejectedExecutionException full) {
            IN_FLIGHT_COUNT.decrementAndGet();
            final long fullCount = QUEUE_FULL_COUNT.incrementAndGet();
            queueTelemetry.queueFullCountAtEnqueue = fullCount;
            queueTelemetry.enqueueWaitElapsedMs =
                    (System.nanoTime() - enqueueStartedNs) / 1_000_000L;

            boolean captureMetadataPersistScheduled =
                    M9DeferredMetadataStore.persistAsyncForDng(dngPath);
            M9PrimaryTimingWriter.writeRejectedAsync(
                    dngPath,
                    ownershipTransferMs,
                    captureMetadataMs,
                    captureMetadataPersistScheduled,
                    queueTelemetry.queueDepthAtEnqueue,
                    queueTelemetry.activeRenderCountAtEnqueue,
                    queueTelemetry.queueCapacity,
                    fullCount,
                    queueTelemetry.enqueueWaitElapsedMs,
                    "primary_queue_full_nonblocking_reject");

            Log.d(TAG, "PRIMARY2.4 QUEUE1B fallback queue full; rejected immediately without BlockingQueue.put; "
                    + "depthAtEnqueue=" + queueTelemetry.queueDepthAtEnqueue
                    + "; activeAtEnqueue=" + queueTelemetry.activeRenderCountAtEnqueue
                    + "; queueFullCount=" + fullCount
                    + "; enqueueWaitElapsedMs=" + queueTelemetry.enqueueWaitElapsedMs);
            return false;
        } catch (RuntimeException unexpected) {
            IN_FLIGHT_COUNT.decrementAndGet();
            throw unexpected;
        }
    }

    private static void runAsyncDng(DngJob job) {
        final long dngWorkerStartedNs = System.nanoTime();
        final long dngQueueWaitMs = (dngWorkerStartedNs - job.dngQueuedAtNs) / 1_000_000L;
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            Log.d(DNG_TAG, "DNGASYNC1A starting untouched DNG after " + dngQueueWaitMs
                    + " ms DNG queue wait; dngPending=" + DNG_EXECUTOR.getQueue().size());
            runDngAndFinalize(job, true, false, DNG_HANDOFF_FALLBACK_COUNT.get(), dngQueueWaitMs);
        } catch (Throwable t) {
            // runDngAndFinalize owns its own failure/timing/close path; this is a final guard.
            Log.e(DNG_TAG, "DNGASYNC1A unexpected DNG worker failure", t);
            try {
                job.ownedFrame.close();
            } catch (Throwable closeError) {
                Log.e(DNG_TAG, "DNGASYNC1A final-guard RAW close failed", closeError);
            }
        }
    }

    /** Runs on either M9PrimaryDngIO or the render worker's bounded fallback path. */
    private static void runDngAndFinalize(DngJob job,
                                          boolean dngAsyncAccepted,
                                          boolean dngAsyncFallbackSync,
                                          long dngFallbackCountSnapshot,
                                          long dngQueueWaitMs) {
        final long dngWorkerStartedNs = System.nanoTime();
        boolean dngSaved = false;
        long dngSaveElapsedMs = -1L;
        String error = job.renderError;
        try {
            long dngStartedNs = System.nanoTime();
            dngSaved = ImageSaver.Util.saveSingleRaw(
                    job.dngPath,
                    job.ownedFrame,
                    job.characteristics,
                    job.captureResult,
                    job.cameraRotation);
            dngSaveElapsedMs = (System.nanoTime() - dngStartedNs) / 1_000_000L;
            if (!dngSaved) {
                error = appendError(error, "development DNG save returned false");
            }
        } catch (Throwable t) {
            error = appendError(error, t.toString());
            Log.e(DNG_TAG, "DNGASYNC1A development DNG save failed", t);
        } finally {
            // Preserve parent publication order even though JPEG EXIF now runs asynchronously:
            // the JPEG finalizer performs its media-scan notification before this latch releases,
            // so the DNG cannot be announced before the finalized JPEG. This wait is on the DNG
            // stage (normally hidden under its much longer save), never on the render worker.
            boolean jpegSaved = false;
            if (job.jpegPayloadSaved && job.jpegFinalizeTicket != null) {
                job.jpegFinalizeTicket.awaitCompletion();
                jpegSaved = job.jpegFinalizeTicket.isSuccess();
                if (!jpegSaved) {
                    error = appendError(error, "JPEG EXIF finalization failed: " + job.jpegFinalizeTicket.error());
                }
            } else if (job.jpegPayloadSaved) {
                error = appendError(error, "JPEG payload saved but EXIF finalizer ticket missing");
            }

            if (dngSaved && job.processingEventsListener != null) {
                try {
                    job.processingEventsListener.notifyImageSavedStatus(true, job.dngPath);
                } catch (Throwable publishError) {
                    error = appendError(error, "DNG publication failed: " + publishError);
                }
            }

            // Preserve METAFREEZE1A storage ordering: DNG gets the storage path first; only
            // after it completes do capture metadata and PRIMARY timing persistence get queued.
            boolean captureMetadataPersistScheduled =
                    M9DeferredMetadataStore.persistAsyncForDng(job.dngPath);
            final long dngWorkerElapsedMs =
                    (System.nanoTime() - dngWorkerStartedNs) / 1_000_000L;
            long renderWorkerElapsedMs;
            if (dngAsyncAccepted) {
                renderWorkerElapsedMs = job.renderWorkerReleaseElapsedMs >= 0L
                        ? job.renderWorkerReleaseElapsedMs
                        : job.renderWorkerElapsedAtHandoffMs;
            } else {
                renderWorkerElapsedMs =
                        (System.nanoTime() - job.renderWorkerStartedNs) / 1_000_000L;
            }

            JSONObject rendererDiagnostics = null;
            if (job.rendererDiagnosticsJson != null) {
                try {
                    rendererDiagnostics = new JSONObject(job.rendererDiagnosticsJson);
                    if (job.jpegFinalizeTicket != null) {
                        job.jpegFinalizeTicket.appendDiagnostics(rendererDiagnostics);
                    }
                } catch (Throwable t) {
                    error = appendError(error, "renderer diagnostics rehydrate failed: " + t);
                }
            }

            boolean primaryTimingPersistScheduled = M9PrimaryTimingWriter.freezeAndWriteAsync(
                    job.dngPath,
                    job.jpegPath,
                    jpegSaved,
                    dngSaved,
                    job.ownershipTransferMs,
                    job.captureMetadataMs,
                    job.queueWaitMs,
                    job.renderElapsedMs,
                    dngSaveElapsedMs,
                    renderWorkerElapsedMs,
                    dngWorkerElapsedMs,
                    dngAsyncAccepted ? "async_single_worker_bounded" : "sync_fallback_dng_queue_full",
                    dngAsyncAccepted,
                    dngAsyncFallbackSync,
                    job.dngQueueDepthAtHandoff,
                    job.dngActiveCountAtHandoff,
                    job.dngQueueCapacity,
                    job.dngHandoffElapsedMs,
                    dngQueueWaitMs,
                    dngFallbackCountSnapshot,
                    captureMetadataPersistScheduled,
                    job.queueTelemetry.queueDepthAtEnqueue,
                    job.queueTelemetry.activeRenderCountAtEnqueue,
                    job.queueTelemetry.queueCapacity,
                    job.queueTelemetry.queueFullCountAtEnqueue,
                    job.queueTelemetry.enqueueWaitElapsedMs,
                    rendererDiagnostics,
                    error,
                    dngAsyncAccepted ? "M9PrimaryDngIO" : "M9PrimaryRenderer");

            Log.d(DNG_TAG, "DNGASYNC1A complete; saved=" + dngSaved
                    + "; dngSaveElapsedMs=" + dngSaveElapsedMs
                    + "; dngQueueWaitMs=" + dngQueueWaitMs
                    + "; primaryTimingScheduled=" + primaryTimingPersistScheduled
                    + "; async=" + dngAsyncAccepted);

            if (dngAsyncAccepted) {
                // The final timing object is frozen before the RAW is closed. Only immutable
                // timing bytes/path remain after this point.
                try {
                    job.ownedFrame.close();
                } catch (Throwable closeError) {
                    Log.e(DNG_TAG, "DNGASYNC1A RAW close failed", closeError);
                }
            }
        }
    }

    private static String appendError(String existing, String addition) {
        if (addition == null || addition.isEmpty()) return existing;
        if (existing == null || existing.isEmpty()) return addition;
        return existing + " | " + addition;
    }

    public static int pendingCount() {
        return EXECUTOR.getQueue().size();
    }

    public static long queueFullCount() {
        return QUEUE_FULL_COUNT.get();
    }

    public static int dngPendingCount() {
        return DNG_EXECUTOR.getQueue().size();
    }

    public static long dngHandoffFallbackCount() {
        return DNG_HANDOFF_FALLBACK_COUNT.get();
    }
}
