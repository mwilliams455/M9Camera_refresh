package com.particlesdevs.photoncamera.m9.render;

import android.os.Process;

import com.particlesdevs.photoncamera.util.Log;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;

import org.json.JSONObject;

import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;

/** Capture-specific PRIMARY2.4 QUEUE1B + TIMINGFREEZE1A + DNGASYNC1A timing sidecar. */
public final class M9PrimaryTimingWriter {
    private static final String TAG = "M9PrimaryTiming";
    private static final String ROUTE = "M9-PRIMARY2.5-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A-COLORNATIVE2A-FIX1-NAME1A-QUEUE1B-TIMINGFREEZE1A-DNGASYNC1A-EXIFASYNC1A";

    private static final ThreadFactory TIMING_THREAD_FACTORY = runnable -> {
        Thread t = new Thread(runnable, "M9PrimaryTimingIO");
        t.setDaemon(true);
        return t;
    };

    // TIMINGFREEZE1A remains intact: the complete PRIMARY timing JSON is serialized
    // to immutable UTF-8 bytes before RAW release, then only bytes/path cross onto
    // this storage executor. DNGASYNC1A changes the thread that reaches that freeze:
    // normally M9PrimaryDngIO after final DNG status is known; bounded fallback may
    // freeze on M9PrimaryRenderer. SAF persistence is never performed on either owner.
    private static final ExecutorService TIMING_WRITER =
            Executors.newSingleThreadExecutor(TIMING_THREAD_FACTORY);

    private M9PrimaryTimingWriter() {}

    private static final class FrozenTiming {
        final Path timingPath;
        final byte[] bytes;

        FrozenTiming(Path timingPath, byte[] bytes) {
            this.timingPath = timingPath;
            this.bytes = bytes;
        }
    }

    /**
     * Freeze the completed accepted timing sidecar to immutable bytes now, then persist only
     * those bytes asynchronously. Returns true once persistence has been scheduled.
     */
    public static boolean freezeAndWriteAsync(Path dngPath,
                                              Path jpegPath,
                                              boolean jpegSaved,
                                              boolean dngSaved,
                                              long ownershipTransferMs,
                                              long captureMetadataMs,
                                              long queueWaitMs,
                                              long renderElapsedMs,
                                              long dngSaveElapsedMs,
                                              long workerElapsedMs,
                                              long dngWorkerElapsedMs,
                                              String dngPersistMode,
                                              boolean dngAsyncAccepted,
                                              boolean dngAsyncFallbackSync,
                                              int dngQueueDepthAtHandoff,
                                              int dngActiveCountAtHandoff,
                                              int dngQueueCapacity,
                                              long dngHandoffElapsedMs,
                                              long dngQueueWaitElapsedMs,
                                              long dngFallbackCountSnapshot,
                                              boolean captureMetadataPersistScheduled,
                                              int queueDepthAtEnqueue,
                                              int activeRenderCountAtEnqueue,
                                              int queueCapacity,
                                              long queueFullCountAtEnqueue,
                                              long enqueueWaitElapsedMs,
                                              JSONObject rendererDiagnostics,
                                              String error,
                                              String primaryTimingFreezeThread) {
        if (dngPath == null) return false;
        try {
            FrozenTiming frozen = freezeInternal(
                    dngPath,
                    jpegPath,
                    jpegSaved,
                    dngSaved,
                    ownershipTransferMs,
                    captureMetadataMs,
                    queueWaitMs,
                    renderElapsedMs,
                    dngSaveElapsedMs,
                    workerElapsedMs,
                    dngWorkerElapsedMs,
                    dngPersistMode,
                    dngAsyncAccepted,
                    dngAsyncFallbackSync,
                    dngQueueDepthAtHandoff,
                    dngActiveCountAtHandoff,
                    dngQueueCapacity,
                    dngHandoffElapsedMs,
                    dngQueueWaitElapsedMs,
                    dngFallbackCountSnapshot,
                    captureMetadataPersistScheduled,
                    queueDepthAtEnqueue,
                    activeRenderCountAtEnqueue,
                    queueCapacity,
                    queueFullCountAtEnqueue,
                    enqueueWaitElapsedMs,
                    true,
                    "accepted",
                    rendererDiagnostics,
                    error,
                    true,
                    primaryTimingFreezeThread);
            TIMING_WRITER.execute(() -> persistFrozen(frozen));
            return true;
        } catch (Throwable t) {
            Log.e(TAG, "Unable to freeze/schedule PRIMARY2.4 DNGASYNC1A timing sidecar", t);
            return false;
        }
    }

    /** Queue-full fallback diagnostics contain only immutable paths/primitives and remain async. */
    public static void writeRejectedAsync(Path dngPath,
                                          long ownershipTransferMs,
                                          long captureMetadataMs,
                                          boolean captureMetadataPersistScheduled,
                                          int queueDepthAtEnqueue,
                                          int activeRenderCountAtEnqueue,
                                          int queueCapacity,
                                          long queueFullCountAtEnqueue,
                                          long enqueueWaitElapsedMs,
                                          String error) {
        TIMING_WRITER.execute(() -> {
            try {
                FrozenTiming frozen = freezeInternal(
                        dngPath,
                        null,
                        false,
                        false,
                        ownershipTransferMs,
                        captureMetadataMs,
                        0L,
                        -1L,
                        -1L,
                        0L,
                        -1L,
                        "not_started_queue_rejected",
                        false,
                        false,
                        0,
                        0,
                        1,
                        -1L,
                        -1L,
                        M9PrimaryRenderQueue.dngHandoffFallbackCount(),
                        captureMetadataPersistScheduled,
                        queueDepthAtEnqueue,
                        activeRenderCountAtEnqueue,
                        queueCapacity,
                        queueFullCountAtEnqueue,
                        enqueueWaitElapsedMs,
                        false,
                        "rejected_queue_full",
                        null,
                        error,
                        false,
                        "M9PrimaryTimingIO");
                persistFrozen(frozen);
            } catch (Throwable t) {
                Log.e(TAG, "Unable to write PRIMARY2.4 QUEUE1B rejected timing sidecar", t);
            }
        });
    }

    private static FrozenTiming freezeInternal(Path dngPath,
                                               Path jpegPath,
                                               boolean jpegSaved,
                                               boolean dngSaved,
                                               long ownershipTransferMs,
                                               long captureMetadataMs,
                                               long queueWaitMs,
                                               long renderElapsedMs,
                                               long dngSaveElapsedMs,
                                               long workerElapsedMs,
                                               long dngWorkerElapsedMs,
                                               String dngPersistMode,
                                               boolean dngAsyncAccepted,
                                               boolean dngAsyncFallbackSync,
                                               int dngQueueDepthAtHandoff,
                                               int dngActiveCountAtHandoff,
                                               int dngQueueCapacity,
                                               long dngHandoffElapsedMs,
                                               long dngQueueWaitElapsedMs,
                                               long dngFallbackCountSnapshot,
                                               boolean captureMetadataPersistScheduled,
                                               int queueDepthAtEnqueue,
                                               int activeRenderCountAtEnqueue,
                                               int queueCapacity,
                                               long queueFullCountAtEnqueue,
                                               long enqueueWaitElapsedMs,
                                               boolean queueAccepted,
                                               String queueOutcome,
                                               JSONObject rendererDiagnostics,
                                               String error,
                                               boolean frozenBeforeFrameRelease,
                                               String primaryTimingFreezeThread) throws Exception {
        if (dngPath == null) throw new IllegalArgumentException("missing DNG path");
        final long freezeStartedNs = System.nanoTime();

        String name = dngPath.getFileName().toString();
        int dot = name.lastIndexOf('.');
        String stem = dot > 0 ? name.substring(0, dot) : name;
        Path timingPath = dngPath.resolveSibling(stem + "_M9_PRIMARY.json");

        JSONObject root = new JSONObject();
        root.put("schema", "m9cam.primarytiming.v6.exifasync1a.dngasync1a");
        root.put("route", ROUTE);
        root.put("primaryPhotonFinishedImage", true);
        root.put("rawHandoffCopy", "none");
        root.put("ownershipModel", "direct_Photon_ImageFrame_transfer_with_optional_bounded_DNG_worker_transfer");
        root.put("captureReleasedBeforeRender", true);
        root.put("shutterAdmissionPolicy", "queue1b_preflight_before_takePicture_nonreserving");
        root.put("fallbackQueueRejectEnabled", true);
        root.put("admissionRejectCountSnapshot", M9PrimaryRenderQueue.admissionRejectCount());
        root.put("captureStemPolicy", "name1a_epoch_millis_plus_same_millis_sequence");

        root.put("primaryTimingMode", "frozen_bytes_deferred_persist_after_dng_stage");
        root.put("jpegExifFinalizationOffRenderWorker", true);
        root.put("jpegPublicationAfterExif", true);
        root.put("jpegExifFinalizationPolicy", "bounded_single_worker_with_sync_preservation_fallback");
        root.put("primaryTimingFrozenBeforeFrameRelease", frozenBeforeFrameRelease);
        root.put("primaryTimingIoOffRenderWorker", true);
        root.put("primaryTimingFreezeThread",
                primaryTimingFreezeThread != null ? primaryTimingFreezeThread : "unknown");

        root.put("dngPersistMode", dngPersistMode != null ? dngPersistMode : "unknown");
        root.put("dngAsyncAccepted", dngAsyncAccepted);
        root.put("dngAsyncFallbackSync", dngAsyncFallbackSync);
        root.put("dngQueueDepthAtHandoff", dngQueueDepthAtHandoff);
        root.put("dngActiveCountAtHandoff", dngActiveCountAtHandoff);
        root.put("dngQueueCapacity", dngQueueCapacity);
        root.put("dngHandoffElapsedMs", dngHandoffElapsedMs);
        root.put("dngQueueWaitElapsedMs", dngQueueWaitElapsedMs);
        root.put("dngFallbackCountSnapshot", dngFallbackCountSnapshot);
        root.put("dngWorkerElapsedMs", dngWorkerElapsedMs);
        root.put("rawFrameCloseOwner", dngAsyncAccepted
                ? "M9PrimaryDngIO"
                : (queueAccepted ? "M9PrimaryRenderer" : "caller"));

        root.put("dngPath", dngPath.toString());
        if (jpegPath != null) root.put("jpegPath", jpegPath.toString());
        root.put("jpegSaved", jpegSaved);
        root.put("dngSaved", dngSaved);
        root.put("ownershipTransferElapsedMs", ownershipTransferMs);
        root.put("captureMetadataElapsedMs", captureMetadataMs);
        root.put("captureMetadataMode", "frozen_bytes_deferred_persist_after_dng_or_queue_reject");
        root.put("captureMetadataPersistScheduled", captureMetadataPersistScheduled);
        root.put("queueDepthAtEnqueue", queueDepthAtEnqueue);
        root.put("activeRenderCountAtEnqueue", activeRenderCountAtEnqueue);
        root.put("queueCapacity", queueCapacity);
        root.put("queueFullCountAtEnqueue", queueFullCountAtEnqueue);
        root.put("enqueueWaitElapsedMs", enqueueWaitElapsedMs);
        root.put("queueAccepted", queueAccepted);
        root.put("queueOutcome", queueOutcome != null ? queueOutcome : "unknown");
        root.put("queueWaitElapsedMs", queueWaitMs);
        root.put("renderElapsedMs", renderElapsedMs);
        root.put("dngSaveElapsedMs", dngSaveElapsedMs);
        root.put("workerElapsedMs", workerElapsedMs);
        root.put("workerElapsedBoundary", "render_worker_elapsed_to_dng_handoff_or_sync_completion");
        if (rendererDiagnostics != null) {
            root.put("renderer", new JSONObject(rendererDiagnostics.toString()));
        }
        if (error != null && !error.isEmpty()) root.put("error", error);

        byte[] provisional = root.toString(2).getBytes(StandardCharsets.UTF_8);
        long freezeElapsedMs = (System.nanoTime() - freezeStartedNs) / 1_000_000L;
        root.put("primaryTimingFreezeElapsedMs", freezeElapsedMs);
        root.put("primaryTimingProvisionalBytes", provisional.length);
        byte[] bytes = root.toString(2).getBytes(StandardCharsets.UTF_8);
        root = null;

        Log.d(TAG, "PRIMARY2.4 TIMINGFREEZE1A+DNGASYNC1A frozen in memory: " + timingPath
                + "; bytes=" + bytes.length + "; freezeElapsedMs=" + freezeElapsedMs
                + "; freezeThread=" + primaryTimingFreezeThread);
        return new FrozenTiming(timingPath, bytes);
    }

    private static void persistFrozen(FrozenTiming frozen) {
        if (frozen == null || frozen.timingPath == null || frozen.bytes == null) return;
        final long persistStartedNs = System.nanoTime();
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(frozen.timingPath.toString());
            if (safOut == null) {
                throw new java.io.IOException("Unable to open PRIMARY2.4 DNGASYNC1A timing sidecar via Photon storage helper: " + frozen.timingPath);
            }
            try (OutputStream out = safOut) {
                out.write(frozen.bytes);
                out.flush();
            }
            long persistElapsedMs = (System.nanoTime() - persistStartedNs) / 1_000_000L;
            Log.d(TAG, "PRIMARY2.4 TIMINGFREEZE1A+DNGASYNC1A timing persisted async in "
                    + persistElapsedMs + " ms: " + frozen.timingPath);
        } catch (Throwable t) {
            Log.e(TAG, "Unable to persist PRIMARY2.4 DNGASYNC1A timing sidecar", t);
        }
    }
}
