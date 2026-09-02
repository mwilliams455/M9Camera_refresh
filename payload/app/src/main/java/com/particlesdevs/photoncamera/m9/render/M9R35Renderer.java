package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Bitmap;
import android.graphics.Point;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.CaptureResult;

import com.particlesdevs.photoncamera.api.ParseExif;
import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.processing.ImageFrame;
import com.particlesdevs.photoncamera.processing.ImageSaver;
import com.particlesdevs.photoncamera.processing.render.Parameters;
import com.particlesdevs.photoncamera.util.FileManager;
import com.particlesdevs.photoncamera.util.Log;

import org.json.JSONObject;
import org.opencv.android.OpenCVLoader;
import org.opencv.core.Core;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;

import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.ShortBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * Android renderer derived directly from the parity-proven R3.5 port.
 * R3.6-CCTFIX corrected the McCamy CCT denominator sign.
 * R3.8-H25 retains TG1 and reduces only the Xiaomi Cobalt HSM hue-shift channel after the exact M9/BT.601
 * stage; all earlier frozen photographic stages and calibration data remain unchanged.
 * Class name retained for working-branch / stale-workflow compatibility.
 *
 * v0.7 deliberately uses the official OpenCV 4.13 Android AAR for the two
 * operations the frozen Python reference also delegates to OpenCV:
 *   - COLOR_BayerRG2BGR_EA
 *   - a dedicated INTER_AREA meter reference at long side 1600
 *
 * FULL12-2 keeps that frozen 1600-side TC20 meter reference, but the final
 * photographic render is streamed at the native 4096x3072 main-camera size.
 * This avoids the several-hundred-MB full-resolution double[] intermediates a
 * naive LONG_SIDE=4096 promotion would create.
 *
 * All Leica/Cobalt colour, TC20, SAT3/ColorMatrix, curve02 and exact
 * horizontal BT.601 4:2:2 arithmetic is isolated here rather than routed
 * through Photon's PostPipeline.
 *
 * FULL12-2 disables the temporary parity PNG. ASYNC1 detaches a private RAW copy before Photon releases its capture buffer. The user-facing photographic
 * outputs are the untouched DNG and the full-resolution *_M9.jpg; the existing
 * JSON sidecar remains available for exposure/render diagnostics.
 */
public final class M9R35Renderer {
    private static final String TAG = "M9R35Renderer";

    public static final int LONG_SIDE = 4096;
    public static final int METER_LONG_SIDE = 1600;
    // COLORNATIVE2A: collapse the promoted 24-row/128-call Java scheduling boundary into
    // eight 384-row blocks at 12 MP. Each block crosses JNI once; four native threads then
    // execute disjoint row ranges through the exact frozen scalar renderStripScalar kernel.
    // 384 rows bounds Java/native scratch growth while removing 120 JNI crossings/frame.
    private static final int NATIVE_COLOR_BLOCK_ROWS = 384;
    private static final int NATIVE_COLOR_WORKERS = Math.max(2, Math.min(8, Runtime.getRuntime().availableProcessors()));
    // PRIMARY2.2 parallelizes only the RAW normalization/histogram pass in addition
    // to PRIMARY2's already-validated colour stage. Each worker reads through its
    // own ShortBuffer duplicate and writes a disjoint row range into norm16.
    private static final int PARALLEL_NORMALIZE_WORKERS = Math.max(2, Math.min(4, Runtime.getRuntime().availableProcessors()));
    public static final int SATURATION_BANK = 3;
    public static final int JPEG_QUALITY = 95;
    public static final boolean SAVE_PARITY_PNG = false;

    private static final double METER_TARGET = 0.107 * (8192.0 / 10000.0);
    private static final double METER_CW = 0.75;
    private static final double TC_HEADROOM_TARGET = 0.95;
    private static final double TC_ALPHA = 0.20;
    private static final double TC_TAIL_CURVATURE_THRESHOLD = 0.25;
    private static final double HSM_H = 0.25;
    private static final double HSM_S = 0.85;
    private static final double HSM_V = 1.00;
    private static final int RAW_MAX = 16383;
    private static final int LUT_MAX = 2047;

    // Inherited exact lookup is retained only for Java-side meter/HSM helper compatibility.
    // PRIMARY2.4 TC20NATIVE1B-ORIENT1A retains FIX7 full-resolution colour using PRIMARY2.2's literal q / 65535.0
    // operation in scalar C++; no UNIT16LUT1 full-colour optimization is promoted.
    private static final double[] UNIT16 = buildUnit16();

    // M9Modern Tungsten Guard TG1.  This is intentionally outside the exact
    // M9 core: it preserves BT.601 Y and gently compresses only the negative
    // Cb (yellow) and negative Cr (green) axes under genuinely warm light.
    // It is fully off at/above 4500 K and reaches full strength at/below 3200 K.
    private static final double TG_START_K = 4500.0;
    private static final double TG_FULL_K = 3200.0;
    private static final double TG_NEG_CB_COMPRESSION = 0.25;
    private static final double TG_NEG_CR_COMPRESSION = 0.16;

    // SAT3: firmware ColorMatrix M06/M07 piecewise pair, selected by R >= G.
    private static final long[] QE = {
            16754, -7632, -922,
            -3124, 14774, -3458,
            -567, -9579, 18330
    };
    private static final long[] QO = {
            18160, -9034, -922,
            -3422, 15080, -3458,
            137, -10264, 18330
    };

    private static final double[] M9_CM_A = {
            .8560, -.2034, -.0066,
            -.4240, 1.3600, .2920,
            -.0740, .2470, .8980
    };
    private static final double[] M9_CM_D65 = {
            .6260, -.1019, -.0470,
            -.3730, 1.1450, .1930,
            -.1409, .2950, .6210
    };
    private static final double[] D50_XY = {.34567, .35850};
    private static final double[] D65_XY = {.31271, .32902};
    private static final double[] BRADFORD = {
            .8951, .2664, -.1614,
            -.7502, 1.7135, .0367,
            .0389, -.0685, 1.0296
    };
    private static final double[] BRADFORD_INV = inverse3(BRADFORD);
    private static final double[] XYZ2SRGB = {
            3.2404542, -1.5371385, -.4985314,
            -.9692660, 1.8760108, .0415560,
            .0556434, -.2040259, 1.0572252
    };
    private static final double[] PP_TO_XYZ_RAW = {
            .7977, .1352, .0313,
            .2880, .7119, .0001,
            0.0, 0.0, .8249
    };
    private static final double[] PP_TO_XYZ = normalizedPpToXyz();
    private static final double[] XYZ_TO_PP = inverse3(PP_TO_XYZ);

    private static volatile JSONObject lastDiagnostics = new JSONObject();
    private static volatile boolean openCvReady = false;

    private M9R35Renderer() {}

    public static final class Result {
        // success means the photographic JPEG payload was encoded/written successfully.
        // PERF3F EXIFASYNC1A final metadata success is tracked by M9JpegFinalizeQueue.Ticket.
        public final boolean success;
        public final Path jpegPath;
        public final Path parityPngPath;
        public final String error;
        public final JSONObject diagnostics;
        public final ParseExif.ExifData jpegExifData;

        Result(boolean success, Path jpegPath, Path parityPngPath, String error, JSONObject diagnostics,
               ParseExif.ExifData jpegExifData) {
            this.success = success;
            this.jpegPath = jpegPath;
            this.parityPngPath = parityPngPath;
            this.error = error;
            this.diagnostics = diagnostics;
            this.jpegExifData = jpegExifData;
        }
    }

    public static synchronized JSONObject snapshotJson() {
        try {
            return new JSONObject(lastDiagnostics.toString());
        } catch (Exception e) {
            return lastDiagnostics;
        }
    }

    /**
     * Copy the tightly-packed Photon RAW into independently-owned native memory.
     * The returned frame no longer depends on IMAGE_BUFFER ownership and may be
     * rendered after DefaultSaver releases bufferLock and closes the camera frame.
     */
    public static ImageFrame detachForBackground(ImageFrame frame) {
        if (frame == null || frame.buffer == null) {
            throw new IllegalArgumentException("missing RAW frame for background handoff");
        }
        ByteBuffer src = frame.buffer.duplicate();
        src.clear();
        ImageFrame detached = new ImageFrame(src);
        detached.width = frame.width;
        detached.height = frame.height;
        detached.timestamp = frame.timestamp;
        detached.number = frame.number;
        return detached;
    }

    /**
     * Capture-time renderer record written to _M9.json before the camera buffer is
     * released. Final render timing is logged by the background worker rather than
     * rewriting capture diagnostics after later captures may update analyzer state.
     */
    public static synchronized void prepareBackgroundDiagnostics(Path dngPath,
                                                                 int width,
                                                                 int height,
                                                                 int cameraRotation,
                                                                 long handoffElapsedMs) {
        try {
            int rot = ((cameraRotation % 360) + 360) % 360;
            boolean swap = rot == 90 || rot == 270;
            JSONObject d = new JSONObject();
            d.put("schema", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1");
            d.put("reference", "v0.7ZD-FIX1-COLORNATIVE2A R3.8-H25/TG1 PRIMARY2.4 TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A exact scalar kernel with native block threading");
            d.put("pipeline", "Cobalt main DCP H25/S85/V100 -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
            d.put("resolutionMode", "M9-PRIMARY2.4-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-COLORNATIVE2A");
            d.put("meterReferenceLongSide", METER_LONG_SIDE);
            d.put("nativeColorBlockRows", NATIVE_COLOR_BLOCK_ROWS);
            d.put("parallelColorWorkers", NATIVE_COLOR_WORKERS);
            d.put("parallelColorMode", "native_block_internal_threads_scalar_math");
            d.put("orientationMode", "native_strip_destination_layout_orient1a");
            d.put("orientationFusedIntoColorOutput", true);
            d.put("orientationPairingSpace", "source_horizontal_pre_orientation");
            d.put("nativeOrientationLayout", "post_pair_strip_transpose_copy");
            d.put("colorHotLoopMode", "primary22_scalar_cpp_jni_parity1");
            d.put("nativeColorCore", true);
            d.put("nativeColorMode", "scalar_cpp_jni_blockthreads2a");
            d.put("nativeColorLibrary", "m9color");
            d.put("nativeColorVectorization", "disabled_scalar_baseline");
            d.put("tc20MeterMode", "native_parallel_luma8_weightedselect_parity1b");
            d.put("tc20NativeLibrary", "m9color");
            d.put("tc20Algorithm", "parallel_luma8_ordered_index_scan_then_weighted_selection_partition_p98_select");
            d.put("tc20JavaGainMath", true);
            d.put("bridgeParityReference", "9frame_1600_precurve14bit_zero_diff");
            d.put("parallelNormalizeWorkers", PARALLEL_NORMALIZE_WORKERS);
            d.put("parallelNormalizeMode", "native_directbuffer_disjoint_row_ranges_histogram_reduce");
            d.put("nativeNormalizeCore", true);
            d.put("nativeNormalizeMode", "directbuffer_scalar4_histogram_parity1a");
            d.put("nativeNormalizeLibrary", "m9color");
            d.put("inputWidth", width);
            d.put("inputHeight", height);
            d.put("renderWidthPreOrientation", width);
            d.put("renderHeightPreOrientation", height);
            d.put("outputWidth", swap ? height : width);
            d.put("outputHeight", swap ? width : height);
            d.put("cameraRotation", cameraRotation);
            d.put("longSide", LONG_SIDE);
            d.put("jpegQuality", JPEG_QUALITY);
            d.put("parityPngEnabled", SAVE_PARITY_PNG);
            d.put("backgroundRender", true);
            d.put("captureReleasedBeforeRender", true);
            d.put("rawHandoffCopy", "detached_ImageFrame_native_buffer");
            d.put("rawHandoffElapsedMs", handoffElapsedMs);
            d.put("status", "queued");
            if (dngPath != null) d.put("dngPath", dngPath.toString());
            d.put("diagnosticsTiming", "capture JSON frozen before asynchronous JPEG render");
            lastDiagnostics = d;
        } catch (Exception ignored) {
        }
    }

    /** PRIMARY1 capture-time record. Photon already owns an Allocator-backed ImageFrame,
     * so ownership is transferred directly out of IMAGE_BUFFER without a second RAW copy. */
    public static synchronized void preparePrimaryDiagnostics(Path dngPath,
                                                              int width,
                                                              int height,
                                                              int cameraRotation,
                                                              long ownershipTransferMs,
                                                              int bufferedFrameCount) {
        try {
            int rot = ((cameraRotation % 360) + 360) % 360;
            boolean swap = rot == 90 || rot == 270;
            JSONObject d = new JSONObject();
            d.put("schema", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1");
            d.put("reference", "v0.7ZD-FIX1-COLORNATIVE2A R3.8-H25/TG1 PRIMARY2.4 TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A exact scalar kernel with native block threading");
            d.put("pipeline", "Cobalt main DCP H25/S85/V100 -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
            d.put("resolutionMode", "M9-PRIMARY2.4-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-COLORNATIVE2A");
            d.put("meterReferenceLongSide", METER_LONG_SIDE);
            d.put("nativeColorBlockRows", NATIVE_COLOR_BLOCK_ROWS);
            d.put("parallelColorWorkers", NATIVE_COLOR_WORKERS);
            d.put("parallelColorMode", "native_block_internal_threads_scalar_math");
            d.put("orientationMode", "native_strip_destination_layout_orient1a");
            d.put("orientationFusedIntoColorOutput", true);
            d.put("orientationPairingSpace", "source_horizontal_pre_orientation");
            d.put("nativeOrientationLayout", "post_pair_strip_transpose_copy");
            d.put("colorHotLoopMode", "primary22_scalar_cpp_jni_parity1");
            d.put("nativeColorCore", true);
            d.put("nativeColorMode", "scalar_cpp_jni_blockthreads2a");
            d.put("nativeColorLibrary", "m9color");
            d.put("nativeColorVectorization", "disabled_scalar_baseline");
            d.put("tc20MeterMode", "native_parallel_luma8_weightedselect_parity1b");
            d.put("tc20NativeLibrary", "m9color");
            d.put("tc20Algorithm", "parallel_luma8_ordered_index_scan_then_weighted_selection_partition_p98_select");
            d.put("tc20JavaGainMath", true);
            d.put("bridgeParityReference", "9frame_1600_precurve14bit_zero_diff");
            d.put("parallelNormalizeWorkers", PARALLEL_NORMALIZE_WORKERS);
            d.put("parallelNormalizeMode", "native_directbuffer_disjoint_row_ranges_histogram_reduce");
            d.put("nativeNormalizeCore", true);
            d.put("nativeNormalizeMode", "directbuffer_scalar4_histogram_parity1a");
            d.put("nativeNormalizeLibrary", "m9color");
            d.put("inputWidth", width);
            d.put("inputHeight", height);
            d.put("renderWidthPreOrientation", width);
            d.put("renderHeightPreOrientation", height);
            d.put("outputWidth", swap ? height : width);
            d.put("outputHeight", swap ? width : height);
            d.put("cameraRotation", cameraRotation);
            d.put("longSide", LONG_SIDE);
            d.put("jpegQuality", JPEG_QUALITY);
            d.put("parityPngEnabled", SAVE_PARITY_PNG);
            d.put("primaryPhotonFinishedImage", true);
            d.put("backgroundRender", true);
            d.put("captureReleasedBeforeRender", true);
            d.put("rawHandoffCopy", "none");
            d.put("ownershipModel", "direct_Photon_ImageFrame_transfer");
            d.put("ownershipTransferElapsedMs", ownershipTransferMs);
            d.put("bufferedFrameCountAtTransfer", bufferedFrameCount);
            d.put("developmentDngPersistence", "bounded_async_single_worker_after_jpeg_with_sync_fallback");
            d.put("status", "queued");
            if (dngPath != null) d.put("dngPath", dngPath.toString());
            d.put("diagnosticsTiming", "capture JSON frozen before primary worker; final timings in *_M9_PRIMARY.json");
            lastDiagnostics = d;
        } catch (Exception ignored) {
        }
    }

    public static synchronized void recordBackgroundHandoffFailure(Throwable t) {
        try {
            JSONObject d = new JSONObject(lastDiagnostics.toString());
            d.put("status", "handoff_failed");
            d.put("error", t != null ? t.toString() : "unknown background handoff failure");
            lastDiagnostics = d;
        } catch (Exception ignored) {
        }
    }

    public static Result renderAndSave(Path dngPath,
                                       ImageFrame frame,
                                       CameraCharacteristics characteristics,
                                       CaptureResult captureResult,
                                       CaptureRequest captureRequest,
                                       int cameraRotation) {
        return renderAndSaveInternal(dngPath, frame, characteristics, captureResult, captureRequest, cameraRotation, false);
    }

    public static Result renderAndSavePrimary(Path dngPath,
                                              ImageFrame frame,
                                              CameraCharacteristics characteristics,
                                              CaptureResult captureResult,
                                              CaptureRequest captureRequest,
                                              int cameraRotation) {
        return renderAndSaveInternal(dngPath, frame, characteristics, captureResult, captureRequest, cameraRotation, true);
    }

    private static Result renderAndSaveInternal(Path dngPath,
                                                ImageFrame frame,
                                                CameraCharacteristics characteristics,
                                                CaptureResult captureResult,
                                                CaptureRequest captureRequest,
                                                int cameraRotation,
                                                boolean primaryRoute) {
        long started = System.nanoTime();
        Path jpgPath = null;
        Path pngPath = null;
        Bitmap bitmap = null;
        try {
            long setupStartedNs = System.nanoTime();
            ensureOpenCv();
            if (frame == null || frame.buffer == null) throw new IllegalArgumentException("missing RAW frame");

            Parameters params = new Parameters();
            params.FillConstParameters(characteristics, new Point(frame.width, frame.height));
            Integer isoObj = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);
            int iso = isoObj != null ? isoObj : 100;
            params.FillDynamicParameters(captureResult, captureRequest, iso);
            params.cameraRotation = cameraRotation;

            // Frozen main-camera R3.5 reference is RGGB.  Fail loudly rather than
            // silently applying the wrong Bayer interpretation to another lens.
            if (params.cfaPattern != 0) {
                throw new IllegalStateException("R3.5 v0.7 main-camera parity build expects RGGB CFA=0, got " + params.cfaPattern);
            }
            if (params.whitePoint == null || params.whitePoint.length < 3 ||
                    params.whitePoint[0] <= 0 || params.whitePoint[1] <= 0 || params.whitePoint[2] <= 0) {
                throw new IllegalStateException("missing SENSOR_NEUTRAL_COLOR_POINT / AsShotNeutral");
            }

            // Photon DngCreator writes BlackLevel by casting Parameters.blackLevel
            // to short. Mirror the encoded DNG values here because the offline
            // parity oracle reads those tags back from the saved DNG.
            float[] encodedBlack = new float[4];
            for (int i = 0; i < 4; i++) {
                int q = ((short)params.blackLevel[i]) & 0xffff;
                encodedBlack[i] = q;
            }
            long setupElapsedMs = (System.nanoTime() - setupStartedNs) / 1_000_000L;
            long renderCoreStartedNs = System.nanoTime();
            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation);
            long renderCoreElapsedMs = (System.nanoTime() - renderCoreStartedNs) / 1_000_000L;
            bitmap = out.bitmap;

            String dngName = dngPath.getFileName().toString();
            int dot = dngName.lastIndexOf('.');
            String stem = dot > 0 ? dngName.substring(0, dot) : dngName;
            jpgPath = Paths.get(FileManager.sDCIM_CAMERA.getAbsolutePath(),
                    stem + (primaryRoute ? ".jpg" : "_M9.jpg"));
            pngPath = dngPath.resolveSibling(stem + "_M9_PARITY.png");

            boolean pngSaved = true;
            if (SAVE_PARITY_PNG) pngSaved = savePng(pngPath, bitmap);

            // PERF3F EXIFASYNC1A keeps the exact quality-95 Bitmap.compress + 64 KiB
            // transport path on the render worker, but stops before EXIF rewrite/publication.
            // The bounded M9JpegFinalizeQueue performs the same ParseExif.setAllAttributes() +
            // saveAttributes() sequence and only then publishes the completed JPEG to Photon.
            ParseExif.ExifData exif = ParseExif.parse(captureResult, captureRequest);
            long jpegStartedNs = System.nanoTime();
            boolean jpgSaved = ImageSaver.Util.saveBitmapAsJPGPayloadM9(jpgPath, bitmap, JPEG_QUALITY, exif);
            long jpegEncodeWriteElapsedMs = (System.nanoTime() - jpegStartedNs) / 1_000_000L;
            ImageSaver.Util.M9JpegSaveTiming jpegTiming = ImageSaver.Util.consumeM9JpegSaveTiming();
            bitmap = null;
            if (!jpgSaved) throw new IllegalStateException("M9 JPEG payload save failed");
            if (SAVE_PARITY_PNG && !pngSaved) throw new IllegalStateException("M9 parity PNG save failed");

            long elapsedMs = (System.nanoTime() - started) / 1_000_000L;
            JSONObject diag = out.diagnostics;
            diag.put("status", "success");
            diag.put("opencvVersion", Core.VERSION);
            diag.put("jpegQuality", JPEG_QUALITY);
            diag.put("jpegPath", jpgPath.toString());
            diag.put("parityPngEnabled", SAVE_PARITY_PNG);
            if (SAVE_PARITY_PNG) diag.put("parityPngPath", pngPath.toString());
            diag.put("renderElapsedMs", elapsedMs);
            diag.put("setupParametersElapsedMs", setupElapsedMs);
            diag.put("renderCoreElapsedMs", renderCoreElapsedMs);
            diag.put("jpegEncodeWriteElapsedMs", jpegEncodeWriteElapsedMs);
            if (jpegTiming != null) {
                diag.put("jpegFileOpenElapsedMs", jpegTiming.fileOpenNs / 1_000_000.0);
                diag.put("jpegCompressElapsedMs", jpegTiming.compressNs / 1_000_000.0);
                diag.put("jpegStreamWriteElapsedMs", jpegTiming.streamWriteNs / 1_000_000.0);
                diag.put("jpegCompressCpuApproxElapsedMs", Math.max(0L, jpegTiming.compressNs - jpegTiming.streamWriteNs) / 1_000_000.0);
                diag.put("jpegFlushElapsedMs", jpegTiming.flushNs / 1_000_000.0);
                diag.put("jpegCloseElapsedMs", jpegTiming.closeNs / 1_000_000.0);
                diag.put("jpegRecycleElapsedMs", jpegTiming.recycleNs / 1_000_000.0);
                diag.put("jpegPayloadSaveHelperElapsedMs", jpegTiming.totalNs / 1_000_000.0);
                diag.put("jpegSaveHelperElapsedMs", jpegTiming.totalNs / 1_000_000.0);
                diag.put("jpegSaveHelperBoundary", "payload_before_exifasync1a");
                diag.put("jpegStreamWriteCalls", jpegTiming.writeCalls);
            }
            diag.put("jpegForensics", "PERF3F_EXIFASYNC1A_JPEGBUF64K1A_EXACT_PAYLOAD");
            diag.put("jpegExifFinalizationMode", "bounded_single_worker_async_with_sync_preservation_fallback");
            diag.put("jpegPublicationAfterExif", true);
            diag.put("primaryPhotonFinishedImage", primaryRoute);
            diag.put("outputRole", primaryRoute ? "primary_photon_jpeg" : "legacy_m9_sidecar");
            // Do not overwrite capture-time lastDiagnostics here: a later shutter may already
            // have frozen its own _M9.json queued record while this background job was running.
            Log.d(TAG, "R3.8-H25/TG1 PRIMARY2.4 COLORNATIVE2A render complete in " + elapsedMs + " ms: " + jpgPath);
            return new Result(true, jpgPath, SAVE_PARITY_PNG ? pngPath : null, null, diag, exif);
        } catch (Throwable t) {
            if (bitmap != null && !bitmap.isRecycled()) bitmap.recycle();
            Log.e(TAG, "R3.8-H25/TG1 render failed", t);
            JSONObject failureDiag = new JSONObject();
            try {
                failureDiag.put("schema", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1");
                failureDiag.put("status", "failed");
                failureDiag.put("error", t.toString());
                failureDiag.put("renderElapsedMs", (System.nanoTime() - started) / 1_000_000L);
                failureDiag.put("primaryPhotonFinishedImage", primaryRoute);
                // Capture JSON remains the synchronous queued snapshot; failure is logged here.
            } catch (Exception ignored) {}
            return new Result(false, jpgPath, pngPath, t.toString(), failureDiag, null);
        }
    }

    private static synchronized void ensureOpenCv() {
        if (openCvReady) return;
        if (!OpenCVLoader.initLocal()) throw new IllegalStateException("OpenCV 4.13 initLocal() failed");
        openCvReady = true;
        Log.d(TAG, "OpenCV ready: " + Core.VERSION);
    }

    private static final class RenderCore {
        final Bitmap bitmap;
        final JSONObject diagnostics;
        RenderCore(Bitmap bitmap, JSONObject diagnostics) {
            this.bitmap = bitmap;
            this.diagnostics = diagnostics;
        }
    }

    private static RenderCore renderCore(ByteBuffer rawBuffer,
                                         int width,
                                         int height,
                                         float[] black,
                                         int whiteLevel,
                                         float[] neutralF,
                                         int cameraRotation) throws Exception {
        final int pixels = Math.multiplyExact(width, height);
        if (pixels <= 0) throw new IllegalArgumentException("bad RAW dimensions " + width + "x" + height);
        long normalizeRawElapsedMs = -1L;
        long nativeNormalizeRawElapsedMs = -1L;
        long nativeNormalizeComputeElapsedMs = -1L;
        long nativeNormalizeOutputCopyElapsedMs = -1L;
        long nativeNormalizeWorkersUsed = -1L;
        long nativeLibraryLoadElapsedMs = -1L;
        long demosaicElapsedMs = -1L;
        long colorContextElapsedMs = -1L;
        long nativeColorContextSetupElapsedMs = -1L;
        long meterTc20ElapsedMs = -1L;
        long meterResizeElapsedMs = -1L;
        long meterTransferElapsedMs = -1L;
        long meterWeightElapsedMs = -1L;
        long nativeTc20ElapsedMs = -1L;
        long fullColorRenderElapsedMs = -1L;
        long orientationElapsedMs = -1L;
        long nativeColorContext = 0L;
        if (Math.max(width, height) > LONG_SIDE) {
            throw new IllegalArgumentException("PRIMARY2.4 TC20NATIVE1B-ORIENT1A-NORMNATIVE1A expects main-camera RAW <= " + LONG_SIDE
                    + " long side; got " + width + "x" + height);
        }
        final int expectedBytes = Math.multiplyExact(pixels, 2);
        ByteBuffer dup = rawBuffer.duplicate().order(ByteOrder.LITTLE_ENDIAN);
        dup.position(0);
        if (dup.remaining() < expectedBytes) {
            throw new IllegalArgumentException("RAW buffer too small: " + dup.remaining() + " < " + expectedBytes);
        }

        // NORMNATIVE1A moves PRIMARY2's exact per-pixel normalization + CFA histograms
        // into the already-required m9color library. The direct RAW ByteBuffer is read
        // without a Java ShortBuffer walk; the normalized 16-bit plane is copied back
        // once for the unchanged OpenCV EA demosaic. rawTail() remains Java and unchanged.
        long nativeLoadStartedNs = System.nanoTime();
        Log.d(TAG, "PRIMARY2.4 NORMNATIVE1A native load begin");
        if (!M9NativeColorCore.ensureLoaded()) {
            throw new IllegalStateException("M9 scalar JNI library load failed: "
                    + M9NativeColorCore.loadError());
        }
        nativeLibraryLoadElapsedMs = (System.nanoTime() - nativeLoadStartedNs) / 1_000_000L;

        long normalizeRawStartedNs = System.nanoTime();
        final int wl = Math.max(2, whiteLevel);
        short[] norm16 = new short[pixels];
        long[] rawCountsFlat = new long[Math.multiplyExact(4, wl)];
        long[] normalizeStats = new long[3];
        final int normalizeWorkers = Math.min(PARALLEL_NORMALIZE_WORKERS, Math.max(1, height));
        long nativeNormalizeStartedNs = System.nanoTime();
        long clipped = M9NativeColorCore.normalizeRawDirect(dup, pixels, width, height,
                black, wl, normalizeWorkers, norm16, rawCountsFlat, normalizeStats);
        nativeNormalizeRawElapsedMs = (System.nanoTime() - nativeNormalizeStartedNs) / 1_000_000L;
        nativeNormalizeComputeElapsedMs = normalizeStats[0] / 1_000_000L;
        nativeNormalizeOutputCopyElapsedMs = normalizeStats[1] / 1_000_000L;
        nativeNormalizeWorkersUsed = normalizeStats[2];

        long[][] rawCounts = new long[4][wl];
        for (int plane = 0; plane < 4; plane++) {
            System.arraycopy(rawCountsFlat, plane * wl, rawCounts[plane], 0, wl);
        }
        rawCountsFlat = null;
        RawTail tail = rawTail(rawCounts, black, wl, pixels, clipped);
        rawCounts = null;
        normalizeRawElapsedMs = (System.nanoTime() - normalizeRawStartedNs) / 1_000_000L;

        Mat rawMat = new Mat(height, width, CvType.CV_16UC1);
        Mat cam16 = new Mat();
        Mat meterCam16 = new Mat();
        try {
            long demosaicStartedNs = System.nanoTime();
            rawMat.put(0, 0, norm16);
            norm16 = null;
            Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);
            rawMat.release();
            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;

            long colorContextStartedNs = System.nanoTime();
            M9R35Calibration cal = M9R35Calibration.get();
            ColorContext ctx = buildColorContext(neutralF, cal);
            colorContextElapsedMs = (System.nanoTime() - colorContextStartedNs) / 1_000_000L;

            // PRIMARY2.4 TC20NATIVE1B-ORIENT1A creates one frame-native context before metering and
            // reuses it for the already-validated FIX7 full-colour strips. This is one .so,
            // one context and one coarse JNI meter call; no per-pixel JNI crossings.
            long nativeContextStartedNs = System.nanoTime();
            Log.d(TAG, "PRIMARY2.4 TC20NATIVE1B-ORIENT1A-NORMNATIVE1A context create begin");
            nativeColorContext = M9NativeColorCore.createContext(
                    ctx.cw, ctx.camToPp, ctx.hsm, ctx.ppToM9, ctx.adapt50To65,
                    PP_TO_XYZ, XYZ2SRGB, cal.curve02, ctx.hueDivisions, ctx.satDivisions);
            nativeColorContextSetupElapsedMs =
                    (System.nanoTime() - nativeContextStartedNs) / 1_000_000L;
            if (nativeColorContext == 0L) {
                throw new IllegalStateException("M9 scalar JNI context creation failed");
            }
            final long nativeContextForFrame = nativeColorContext;
            Log.d(TAG, "PRIMARY2.4 TC20NATIVE1B-ORIENT1A native context created");

            long meterStartedNs = System.nanoTime();
            // Preserve N/FIX7's exact tone/exposure reference: the same 1600-long-side
            // INTER_AREA camera-space image. Only H25/HSM+luma and the weighted-selection median/P98 implementation move from Java into scalar C++.
            int meterW = width;
            int meterH = height;
            long meterResizeStartedNs = System.nanoTime();
            if (Math.max(width, height) > METER_LONG_SIDE) {
                double sc = METER_LONG_SIDE / (double)Math.max(width, height);
                meterW = pyRoundPositive(width * sc);
                meterH = pyRoundPositive(height * sc);
                Imgproc.resize(cam16, meterCam16, new Size(meterW, meterH), 0.0, 0.0, Imgproc.INTER_AREA);
            } else {
                cam16.copyTo(meterCam16);
            }
            meterResizeElapsedMs = (System.nanoTime() - meterResizeStartedNs) / 1_000_000L;
            int meterPixels = Math.multiplyExact(meterW, meterH);
            final boolean meterCvDirectEligible = meterCam16.isContinuous()
                    && meterCam16.channels() == 3
                    && meterCam16.elemSize1() == 2L
                    && meterCam16.step1() == (long)meterW * 3L
                    && meterCam16.dataAddr() != 0L;
            short[] meterCam = null;
            long meterCamAddress = 0L;
            long meterTransferStartedNs = System.nanoTime();
            if (meterCvDirectEligible) {
                meterCamAddress = meterCam16.dataAddr();
            } else {
                meterCam = new short[Math.multiplyExact(meterPixels, 3)];
                meterCam16.get(0, 0, meterCam);
            }
            meterTransferElapsedMs = (System.nanoTime() - meterTransferStartedNs) / 1_000_000L;

            long meterWeightStartedNs = System.nanoTime();
            double[] rowW = new double[meterH];
            double[] colW = new double[meterW];
            double h2 = meterH / 2.0, w2 = meterW / 2.0;
            double den = 2.0 * METER_CW * METER_CW;
            for (int yy = 0; yy < meterH; yy++) {
                double ry = (yy - h2) / h2;
                rowW[yy] = Math.exp(-(ry * ry) / den);
            }
            for (int xx = 0; xx < meterW; xx++) {
                double rx = (xx - w2) / w2;
                colW[xx] = Math.exp(-(rx * rx) / den);
            }
            meterWeightElapsedMs = (System.nanoTime() - meterWeightStartedNs) / 1_000_000L;

            long nativeTc20StartedNs = System.nanoTime();
            Meter meter;
            if (meterCvDirectEligible) {
                meter = tc20MeterNativeDirect(meterCamAddress, meterW, meterH, tail, nativeContextForFrame, rowW, colW);
            } else {
                meter = tc20MeterNative(meterCam, meterW, meterH, tail, nativeContextForFrame, rowW, colW);
            }
            nativeTc20ElapsedMs = (System.nanoTime() - nativeTc20StartedNs) / 1_000_000L;
            meterCam16.release();
            meterCam = null;
            meterTc20ElapsedMs = (System.nanoTime() - meterStartedNs) / 1_000_000L;

            long fullRenderStartedNs = System.nanoTime();
            // COLORNATIVE2A keeps ORIENT1A's source-horizontal BT.601 4:2:2 pairing and
            // uses bounded 384-row native blocks. PERF3H CVDIRECT1A reads the packed OpenCV
            // camera Mat in-place when its layout is explicitly validated; otherwise it falls
            // back to the promoted copied-input path. The scalar pixel/pair kernel itself is
            // unchanged and is not vectorized or reordered.
            final int rotation = ((cameraRotation % 360) + 360) % 360;
            final int orientedWidth = (rotation == 90 || rotation == 270) ? height : width;
            final int orientedHeight = (rotation == 90 || rotation == 270) ? width : height;
            long bitmapCreateStartedNs = System.nanoTime();
            Bitmap oriented = Bitmap.createBitmap(orientedWidth, orientedHeight, Bitmap.Config.ARGB_8888);
            long nativeColorBitmapCreateElapsedNs = System.nanoTime() - bitmapCreateStartedNs;
            final int maxBlockPixels = Math.multiplyExact(width, NATIVE_COLOR_BLOCK_ROWS);
            // PERF3H CVDIRECT1A: cvtColor produces a packed CV_16UC3 Mat on the normal path.
            // When that exact layout is present, read it synchronously in native code and avoid
            // Mat.get(short[]) + JNI GetShortArrayRegion. Any unexpected layout falls back to
            // the promoted copied-input path rather than guessing about stride/type semantics.
            final boolean nativeColorCvDirectEligible = cam16.isContinuous()
                    && cam16.channels() == 3
                    && cam16.elemSize1() == 2L
                    && cam16.step1() == (long)width * 3L
                    && cam16.dataAddr() != 0L;
            final long nativeColorCvBaseAddress = nativeColorCvDirectEligible ? cam16.dataAddr() : 0L;
            final long nativeColorCvStepShorts = cam16.step1();
            final long nativeColorCvRowBytes = nativeColorCvDirectEligible ? nativeColorCvStepShorts * cam16.elemSize1() : 0L;
            final short[] camBlock = nativeColorCvDirectEligible ? null : new short[Math.multiplyExact(maxBlockPixels, 3)];
            // PERF3I BITMAPDIRECT1A keeps this promoted PERF3H block output only as a
            // preservation fallback. The normal path writes completed oriented pixels
            // directly into the mutable ARGB_8888 destination Bitmap.
            final int[] argbBlock = new int[maxBlockPixels];
            final boolean nativeColorBitmapDirectEligible = nativeColorCvDirectEligible
                    && oriented.isMutable()
                    && oriented.getConfig() == Bitmap.Config.ARGB_8888
                    && oriented.getWidth() == orientedWidth
                    && oriented.getHeight() == orientedHeight
                    && oriented.getRowBytes() >= Math.multiplyExact(orientedWidth, 4);
            boolean nativeColorBitmapDirectActive = nativeColorBitmapDirectEligible;
            final long[] nativeStats = new long[12];
            long even = 0;
            long edge = 0;
            long nearWhite = 0;
            long nativeColorTaskElapsedNsSum = 0;
            long nativeColorJniElapsedNsSum = 0;
            long nativeColorCalls = 0;
            long nativeColorOpenCvTransferElapsedNs = 0;
            long nativeColorScratchPrepElapsedNs = 0;
            long nativeColorInputCopyElapsedNs = 0;
            long nativeColorWorkerWallElapsedNs = 0;
            long nativeColorWorkerMaxElapsedNsSum = 0;
            long nativeColorOrientationElapsedNs = 0;
            long nativeColorOutputCopyElapsedNs = 0;
            long nativeColorNativeTotalElapsedNs = 0;
            long directOrientedCommitElapsedNs = 0;
            long nativeColorWorkersUsed = 0;
            long nativeColorCvDirectBlocks = 0;
            long nativeColorCvFallbackBlocks = 0;
            long nativeColorBitmapDirectBlocks = 0;
            long nativeColorBitmapFallbackBlocks = 0;
            final double tgWeight = tungstenGuardWeight(ctx.cct);
            final double tgCbGain = 1.0 - TG_NEG_CB_COMPRESSION * tgWeight;
            final double tgCrGain = 1.0 - TG_NEG_CR_COMPRESSION * tgWeight;

            for (int y0 = 0; y0 < height; y0 += NATIVE_COLOR_BLOCK_ROWS) {
                final int rows = Math.min(NATIVE_COLOR_BLOCK_ROWS, height - y0);
                final int blockPixels = Math.multiplyExact(rows, width);
                long openCvTransferStartedNs = System.nanoTime();
                long nativeStartedNs;
                boolean bitmapDirectForBlock = false;
                if (nativeColorCvDirectEligible) {
                    long blockAddress = nativeColorCvBaseAddress + (long)y0 * nativeColorCvRowBytes;
                    nativeColorOpenCvTransferElapsedNs += System.nanoTime() - openCvTransferStartedNs;
                    nativeStartedNs = System.nanoTime();
                    if (nativeColorBitmapDirectActive) {
                        bitmapDirectForBlock = M9NativeColorCore.renderBlockParallelDirectBitmap(
                                nativeContextForFrame, blockAddress, blockPixels, width,
                                oriented, y0, height,
                                meter.gain, tgCbGain, tgCrGain, rotation, NATIVE_COLOR_WORKERS, nativeStats);
                        if (!bitmapDirectForBlock) {
                            // Native layout/lock rejection is guaranteed to occur before pixel writes.
                            // Permanently use the exact PERF3H int[] + setPixels fallback for this frame.
                            nativeColorBitmapDirectActive = false;
                            M9NativeColorCore.renderBlockParallelDirect(nativeContextForFrame, blockAddress, blockPixels, width,
                                    argbBlock, meter.gain, tgCbGain, tgCrGain, rotation, NATIVE_COLOR_WORKERS, nativeStats);
                        }
                    } else {
                        M9NativeColorCore.renderBlockParallelDirect(nativeContextForFrame, blockAddress, blockPixels, width,
                                argbBlock, meter.gain, tgCbGain, tgCrGain, rotation, NATIVE_COLOR_WORKERS, nativeStats);
                    }
                    nativeColorCvDirectBlocks++;
                } else {
                    cam16.get(y0, 0, camBlock);
                    nativeColorOpenCvTransferElapsedNs += System.nanoTime() - openCvTransferStartedNs;
                    nativeStartedNs = System.nanoTime();
                    M9NativeColorCore.renderBlockParallel(nativeContextForFrame, camBlock, blockPixels, width,
                            argbBlock, meter.gain, tgCbGain, tgCrGain, rotation, NATIVE_COLOR_WORKERS, nativeStats);
                    nativeColorCvFallbackBlocks++;
                }
                nativeColorJniElapsedNsSum += System.nanoTime() - nativeStartedNs;
                nativeColorCalls++;
                even += nativeStats[0];
                edge += nativeStats[1];
                nearWhite += nativeStats[2];
                nativeColorTaskElapsedNsSum += nativeStats[3];
                nativeColorWorkersUsed = Math.max(nativeColorWorkersUsed, nativeStats[4]);
                nativeColorScratchPrepElapsedNs += nativeStats[5];
                nativeColorInputCopyElapsedNs += nativeStats[6];
                nativeColorWorkerWallElapsedNs += nativeStats[7];
                nativeColorWorkerMaxElapsedNsSum += nativeStats[8];
                nativeColorOrientationElapsedNs += nativeStats[9];
                nativeColorOutputCopyElapsedNs += nativeStats[10];
                nativeColorNativeTotalElapsedNs += nativeStats[11];

                if (bitmapDirectForBlock) {
                    nativeColorBitmapDirectBlocks++;
                } else {
                    nativeColorBitmapFallbackBlocks++;
                    long commitStartedNs = System.nanoTime();
                    if (rotation == 90) {
                        int destX = height - (y0 + rows);
                        oriented.setPixels(argbBlock, 0, rows, destX, 0, rows, width);
                    } else if (rotation == 270) {
                        oriented.setPixels(argbBlock, 0, rows, y0, 0, rows, width);
                    } else if (rotation == 180) {
                        int destY = height - (y0 + rows);
                        oriented.setPixels(argbBlock, 0, width, 0, destY, width, rows);
                    } else {
                        oriented.setPixels(argbBlock, 0, width, 0, y0, width, rows);
                    }
                    directOrientedCommitElapsedNs += System.nanoTime() - commitStartedNs;
                }
            }
            cam16.release();
            fullColorRenderElapsedMs = (System.nanoTime() - fullRenderStartedNs) / 1_000_000L;

            // ORIENT1A has no standalone full-frame orientation pass. Pair math remains
            // source-horizontal inside native; only completed RGB pixels are rearranged into
            // strip-local destination order before the direct final-Bitmap commit above.
            orientationElapsedMs = 0L;

            JSONObject d = new JSONObject();
            d.put("schema", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1");
            d.put("reference", "v0.7ZD-FIX1-COLORNATIVE2A R3.8-H25/TG1 PRIMARY2.4 TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A exact scalar kernel with native block threading");
            d.put("pipeline", "Cobalt main DCP H25/S85/V100 -> M9 bridge -> TC20 -> SAT3 M06/M07 -> curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
            d.put("resolutionMode", "M9-PRIMARY2.4-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-COLORNATIVE2A");
            d.put("backgroundRender", true);
            d.put("captureReleasedBeforeRender", true);
            d.put("meterReferenceLongSide", METER_LONG_SIDE);
            d.put("nativeColorBlockRows", NATIVE_COLOR_BLOCK_ROWS);
            d.put("parallelColorWorkers", NATIVE_COLOR_WORKERS);
            d.put("parallelColorMode", "native_block_internal_threads_scalar_math");
            d.put("orientationMode", "native_strip_destination_layout_orient1a");
            d.put("orientationFusedIntoColorOutput", true);
            d.put("orientationPairingSpace", "source_horizontal_pre_orientation");
            d.put("nativeOrientationLayout", "post_pair_strip_transpose_copy");
            d.put("directOrientedCommitElapsedMs", directOrientedCommitElapsedNs / 1_000_000L);
            d.put("colorHotLoopMode", "primary22_scalar_cpp_jni_parity1");
            d.put("nativeColorCore", true);
            d.put("nativeColorMode", "scalar_cpp_jni_blockthreads2a");
            d.put("nativeColorLibrary", "m9color");
            d.put("nativeColorVectorization", "disabled_scalar_baseline");
            d.put("tc20MeterMode", "native_parallel_luma8_weightedselect_parity1b");
            d.put("tc20NativeLibrary", "m9color");
            d.put("tc20Algorithm", "parallel_luma8_ordered_index_scan_then_weighted_selection_partition_p98_select");
            d.put("tc20JavaGainMath", true);
            d.put("bridgeParityReference", "9frame_1600_precurve14bit_zero_diff");
            d.put("parallelNormalizeWorkers", PARALLEL_NORMALIZE_WORKERS);
            d.put("parallelNormalizeMode", "native_directbuffer_disjoint_row_ranges_histogram_reduce");
            d.put("nativeNormalizeCore", true);
            d.put("nativeNormalizeMode", "directbuffer_scalar4_histogram_parity1a");
            d.put("nativeNormalizeLibrary", "m9color");
            d.put("inputWidth", width);
            d.put("inputHeight", height);
            d.put("whiteLevel", wl);
            d.put("blackLevelR", black != null && black.length >= 4 ? black[0] : 64.0);
            d.put("blackLevelG0", black != null && black.length >= 4 ? black[1] : 64.0);
            d.put("blackLevelG1", black != null && black.length >= 4 ? black[2] : 64.0);
            d.put("blackLevelB", black != null && black.length >= 4 ? black[3] : 64.0);
            d.put("neutralR", neutralF[0]);
            d.put("neutralG", neutralF[1]);
            d.put("neutralB", neutralF[2]);
            d.put("renderWidthPreOrientation", width);
            d.put("renderHeightPreOrientation", height);
            d.put("outputWidth", oriented.getWidth());
            d.put("outputHeight", oriented.getHeight());
            d.put("cameraRotation", cameraRotation);
            d.put("longSide", LONG_SIDE);
            d.put("cct", ctx.cct);
            d.put("AWeight", ctx.wA);
            d.put("tungstenGuard", "TG1");
            d.put("tungstenGuardWeight", tgWeight);
            d.put("tungstenGuardStartK", TG_START_K);
            d.put("tungstenGuardFullK", TG_FULL_K);
            d.put("tungstenGuardNegativeCbCompression", TG_NEG_CB_COMPRESSION);
            d.put("tungstenGuardNegativeCrCompression", TG_NEG_CR_COMPRESSION);
            d.put("gain", meter.gain);
            d.put("baseMedianGain", meter.baseGain);
            d.put("legacyR31Gain", meter.legacyGain);
            d.put("legacyP98Proxy", meter.p98);
            d.put("tc20GuardGain", meter.guardGain);
            d.put("rawHardClipFraction", tail.clipFraction);
            d.put("rawUq99", tail.uq99);
            d.put("rawUq99_5", tail.uq995);
            d.put("rawUq99_8", tail.uq998);
            d.put("tc20Q", tail.q);
            d.put("tc20AdaptiveUq", tail.adaptiveUq);
            d.put("tc20TailCurvature", tail.curvature);
            d.put("tc20TailIsolated", tail.isolated);
            d.put("tc20TailValue", tail.tailValue);
            d.put("satBank", SATURATION_BANK);
            d.put("contrastCurve", "curve02 normal-ISO sRGB Standard");
            d.put("branchEvenOccurrence", even / (double)pixels);
            d.put("rgb8ClipFraction", edge / (double)(pixels * 3L));
            d.put("renderNearWhiteFraction", nearWhite / (double)pixels);
            d.put("baselineExposureEv", 0.0);
            d.put("hsmHueStrength", HSM_H);
            d.put("hsmSaturationStrength", HSM_S);
            d.put("hsmValueStrength", HSM_V);
            d.put("normalizeRawElapsedMs", normalizeRawElapsedMs);
            d.put("nativeNormalizeRawElapsedMs", nativeNormalizeRawElapsedMs);
            d.put("nativeNormalizeComputeElapsedMs", nativeNormalizeComputeElapsedMs);
            d.put("nativeNormalizeOutputCopyElapsedMs", nativeNormalizeOutputCopyElapsedMs);
            d.put("nativeNormalizeWorkersUsed", nativeNormalizeWorkersUsed);
            d.put("nativeLibraryLoadElapsedMs", nativeLibraryLoadElapsedMs);
            d.put("demosaicElapsedMs", demosaicElapsedMs);
            d.put("colorContextElapsedMs", colorContextElapsedMs);
            d.put("meterTc20ElapsedMs", meterTc20ElapsedMs);
            d.put("meterResizeElapsedMs", meterResizeElapsedMs);
            d.put("meterTransferElapsedMs", meterTransferElapsedMs);
            d.put("meterInputMode", meterCvDirectEligible ? "opencv_mat_dataaddr_direct1a" : "java_short_array_fallback");
            d.put("meterCvDirectEligible", meterCvDirectEligible);
            d.put("meterCvDirectFallback", !meterCvDirectEligible);
            d.put("meterWeightElapsedMs", meterWeightElapsedMs);
            d.put("nativeTc20ElapsedMs", nativeTc20ElapsedMs);
            d.put("tc20NativeScratchPrepElapsedMs", meter.nativeScratchPrepMs);
            d.put("tc20NativeInputCopyElapsedMs", meter.nativeInputCopyMs);
            d.put("tc20NativeLumaPopulationElapsedMs", meter.nativeLumaPopulationMs);
            d.put("tc20NativeTotalWeightElapsedMs", meter.nativeTotalWeightMs);
            d.put("tc20NativeWeightedMedianElapsedMs", meter.nativeWeightedMedianMs);
            d.put("tc20NativeP98ElapsedMs", meter.nativeP98Ms);
            d.put("tc20NativeScalarTotalElapsedMs", meter.nativeScalarTotalMs);
            d.put("tc20NativeLumaComputeElapsedMs", meter.nativeLumaComputeMs);
            d.put("tc20NativeOrderBuildElapsedMs", meter.nativeOrderBuildMs);
            d.put("tc20NativeLumaWorkersUsed", meter.nativeLumaWorkers);
            d.put("fullColorRenderElapsedMs", fullColorRenderElapsedMs);
            d.put("nativeColorContextSetupElapsedMs", nativeColorContextSetupElapsedMs);
            d.put("nativeColorCalls", nativeColorCalls);
            d.put("nativeColorTaskElapsedMsSum", nativeColorTaskElapsedNsSum / 1_000_000.0);
            d.put("nativeColorJniElapsedMsSum", nativeColorJniElapsedNsSum / 1_000_000.0);
            d.put("nativeColorBitmapCreateElapsedMs", nativeColorBitmapCreateElapsedNs / 1_000_000.0);
            d.put("nativeColorOpenCvTransferElapsedMsSum", nativeColorOpenCvTransferElapsedNs / 1_000_000.0);
            d.put("nativeColorScratchPrepElapsedMsSum", nativeColorScratchPrepElapsedNs / 1_000_000.0);
            d.put("nativeColorInputCopyElapsedMsSum", nativeColorInputCopyElapsedNs / 1_000_000.0);
            d.put("nativeColorWorkerWallElapsedMsSum", nativeColorWorkerWallElapsedNs / 1_000_000.0);
            d.put("nativeColorWorkerMaxElapsedMsSum", nativeColorWorkerMaxElapsedNsSum / 1_000_000.0);
            d.put("nativeColorThreadOverheadApproxMsSum", Math.max(0L, nativeColorWorkerWallElapsedNs - nativeColorWorkerMaxElapsedNsSum) / 1_000_000.0);
            d.put("nativeColorOrientationElapsedMsSum", nativeColorOrientationElapsedNs / 1_000_000.0);
            d.put("nativeColorOutputCopyElapsedMsSum", nativeColorOutputCopyElapsedNs / 1_000_000.0);
            d.put("nativeColorNativeTotalElapsedMsSum", nativeColorNativeTotalElapsedNs / 1_000_000.0);
            d.put("nativeColorWorkersUsed", nativeColorWorkersUsed);
            d.put("nativeColorInputMode", nativeColorCvDirectEligible ? "opencv_mat_dataaddr_direct1a" : "java_short_array_fallback");
            d.put("nativeColorCvDirectEligible", nativeColorCvDirectEligible);
            d.put("nativeColorCvDirectBlocks", nativeColorCvDirectBlocks);
            d.put("nativeColorCvFallbackBlocks", nativeColorCvFallbackBlocks);
            d.put("nativeColorCvStepShorts", nativeColorCvStepShorts);
            d.put("nativeColorBitmapOutputMode", nativeColorBitmapDirectEligible ? "androidbitmap_rgba8888_direct1a" : "java_setpixels_fallback");
            d.put("nativeColorBitmapDirectEligible", nativeColorBitmapDirectEligible);
            d.put("nativeColorBitmapDirectBlocks", nativeColorBitmapDirectBlocks);
            d.put("nativeColorBitmapFallbackBlocks", nativeColorBitmapFallbackBlocks);
            d.put("nativeColorBitmapRowBytes", oriented.getRowBytes());
            d.put("performanceForensics", "PERF3I_BITMAPDIRECT1A_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A");
            d.put("nativeColorOrientationMode", "orientfuse8a_worker_subranges_exact");
            d.put("nativeColorOrientationTimingMode", "sum_worker_local_fused_copy_ns");
            d.put("nativeColorSerialOrientationPass", false);
            d.put("performanceExperiment", "retained_color8a_tc20luma8a_jpegbuf64k1a_exifasync1a_orientfuse8a_cvdirect1a_plus_exact_androidbitmap_rgba8888_direct_output_with_fallback");
            d.put("fullColorRenderStages", "COLORNATIVE2A native-block threaded scalar H25/HSM + M9 bridge + SAT3 + curve02 + BT601/TG1");
            d.put("orientationElapsedMs", orientationElapsedMs);
            return new RenderCore(oriented, d);
        } finally {
            if (nativeColorContext != 0L) M9NativeColorCore.destroyContext(nativeColorContext);
            if (!rawMat.empty()) rawMat.release();
            if (!cam16.empty()) cam16.release();
            if (!meterCam16.empty()) meterCam16.release();
        }
    }

    private static final class NormalizeResult {
        final long[][] rawCounts;
        final long clipped;

        NormalizeResult(long[][] rawCounts, long clipped) {
            this.rawCounts = rawCounts;
            this.clipped = clipped;
        }
    }

    /** PRIMARY2.2 scheduling extraction of PRIMARY2's exact RAW normalization loop. */
    private static NormalizeResult normalizeRange(ShortBuffer shorts,
                                                  short[] norm16,
                                                  int width,
                                                  int y0,
                                                  int y1,
                                                  float[] black,
                                                  int wl) {
        long[][] localCounts = new long[4][wl];
        long localClipped = 0;
        shorts.position(Math.multiplyExact(y0, width));
        for (int y = y0; y < y1; y++) {
            int row = y * width;
            int py = y & 1;
            for (int x = 0; x < width; x++) {
                int i = row + x;
                int plane = py * 2 + (x & 1);
                int rv = shorts.get() & 0xffff;
                if (rv >= wl) localClipped++; else localCounts[plane][rv]++;
                float bl = black != null && black.length >= 4 ? black[plane] : 64.0f;
                float v = (rv - bl) / Math.max(1.0f, wl - bl);
                if (v < 0.0f) v = 0.0f;
                if (v > 1.0f) v = 1.0f;
                int nv = (int)Math.floor(v * 65535.0f + 0.5f);
                norm16[i] = (short)(nv & 0xffff);
            }
        }
        return new NormalizeResult(localCounts, localClipped);
    }

    private static final class ColorContext {
        double[] cw;
        double[] camToPp;
        double[] hsm;
        double[] adapt50ToScene;
        double[] adapt50To65;
        double[] m9cm;
        double[] mwhite;
        double[] ppToM9;
        double cct;
        double wA;
        int hueDivisions;
        int satDivisions;
    }

    private static ColorContext buildColorContext(float[] neutralF, M9R35Calibration cal) {
        ColorContext ctx = new ColorContext();
        double[] neutral = {neutralF[0], neutralF[1], neutralF[2]};
        double[] xy = neutralToXy(neutral, cal);
        ctx.cct = cctFromXy(xy);
        ctx.wA = weightA(ctx.cct);

        double[] cm = interp9(cal.colorMatrixA, cal.colorMatrixD65, ctx.wA);
        double[] fm = interp9(cal.forwardMatrixA, cal.forwardMatrixD65, ctx.wA);
        double[] whiteXyz = xyToXyz(xy);
        ctx.cw = matVec3(cm, whiteXyz);
        double cwMax = Math.max(ctx.cw[0], Math.max(ctx.cw[1], ctx.cw[2]));
        for (int k = 0; k < 3; k++) ctx.cw[k] = clamp(ctx.cw[k] / Math.max(cwMax, 1e-12), .001, 1.0);
        double[] diagInvCw = {
                1.0 / ctx.cw[0], 0, 0,
                0, 1.0 / ctx.cw[1], 0,
                0, 0, 1.0 / ctx.cw[2]
        };
        ctx.camToPp = matMul3(matMul3(XYZ_TO_PP, fm), diagInvCw);
        ctx.hsm = new double[cal.hsmA.length];
        for (int i = 0; i < ctx.hsm.length; i++) {
            ctx.hsm[i] = ctx.wA * cal.hsmA[i] + (1.0 - ctx.wA) * cal.hsmD65[i];
        }
        ctx.adapt50ToScene = bradford(D50_XY, xy);
        ctx.adapt50To65 = bradford(D50_XY, D65_XY);
        ctx.hueDivisions = cal.hueDivisions;
        ctx.satDivisions = cal.satDivisions;
        ctx.m9cm = interp9(M9_CM_A, M9_CM_D65, ctx.wA);
        ctx.mwhite = matVec3(ctx.m9cm, whiteXyz);
        for (int k = 0; k < 3; k++) ctx.mwhite[k] = Math.max(ctx.mwhite[k], 1e-8);

        // PRIMARY2.2 BRIDGE1: PP->XYZ50, Bradford scene adaptation, M9 matrix and
        // per-channel M9 white normalization are all invariant for the frame. Compose
        // them once here instead of executing two extra 3x3 transforms plus three
        // divides for every full-resolution pixel. Nine-frame regression at 1600-side
        // showed zero differences after the frozen 14-bit pre-SAT3 quantization.
        double[] ppToM9Unnormalized = matMul3(ctx.m9cm, matMul3(ctx.adapt50ToScene, PP_TO_XYZ));
        ctx.ppToM9 = new double[9];
        for (int row = 0; row < 3; row++) {
            double den = ctx.mwhite[row];
            int base = row * 3;
            ctx.ppToM9[base] = ppToM9Unnormalized[base] / den;
            ctx.ppToM9[base + 1] = ppToM9Unnormalized[base + 1] / den;
            ctx.ppToM9[base + 2] = ppToM9Unnormalized[base + 2] / den;
        }
        return ctx;
    }

    private static void cameraToHsmXyz50(short[] cam, int c, ColorContext ctx, double[] hsmOut) {
        double r = UNIT16[cam[c] & 0xffff];
        double g = UNIT16[cam[c + 1] & 0xffff];
        double b = UNIT16[cam[c + 2] & 0xffff];
        r = Math.min(r, ctx.cw[0]);
        g = Math.min(g, ctx.cw[1]);
        b = Math.min(b, ctx.cw[2]);
        double pr = clamp(ctx.camToPp[0] * r + ctx.camToPp[1] * g + ctx.camToPp[2] * b, 0, 1);
        double pg = clamp(ctx.camToPp[3] * r + ctx.camToPp[4] * g + ctx.camToPp[5] * b, 0, 1);
        double pb = clamp(ctx.camToPp[6] * r + ctx.camToPp[7] * g + ctx.camToPp[8] * b, 0, 1);
        applyHsm(pr, pg, pb, ctx.hsm, hsmOut);
    }

    private static double cameraToSrgbLuma(short[] cam, int c, ColorContext ctx, double[] hsmOut) {
        cameraToHsmXyz50(cam, c, ctx, hsmOut);
        double x50 = PP_TO_XYZ[0] * hsmOut[0] + PP_TO_XYZ[1] * hsmOut[1] + PP_TO_XYZ[2] * hsmOut[2];
        double y50 = PP_TO_XYZ[3] * hsmOut[0] + PP_TO_XYZ[4] * hsmOut[1] + PP_TO_XYZ[5] * hsmOut[2];
        double z50 = PP_TO_XYZ[6] * hsmOut[0] + PP_TO_XYZ[7] * hsmOut[1] + PP_TO_XYZ[8] * hsmOut[2];
        double x65 = ctx.adapt50To65[0] * x50 + ctx.adapt50To65[1] * y50 + ctx.adapt50To65[2] * z50;
        double y65 = ctx.adapt50To65[3] * x50 + ctx.adapt50To65[4] * y50 + ctx.adapt50To65[5] * z50;
        double z65 = ctx.adapt50To65[6] * x50 + ctx.adapt50To65[7] * y50 + ctx.adapt50To65[8] * z50;
        double sr = XYZ2SRGB[0] * x65 + XYZ2SRGB[1] * y65 + XYZ2SRGB[2] * z65;
        double sg = XYZ2SRGB[3] * x65 + XYZ2SRGB[4] * y65 + XYZ2SRGB[5] * z65;
        double sb = XYZ2SRGB[6] * x65 + XYZ2SRGB[7] * y65 + XYZ2SRGB[8] * z65;
        return Math.max(.2126 * sr + .7152 * sg + .0722 * sb, 0.0);
    }

    /**
     * PRIMARY2.2C retained Java helper (meter/parity support only): preserve PRIMARY2.2's precomposed bridge and frozen
     * SAT3/curve02 arithmetic, but keep the three M9 bridge values as scalars instead
     * of round-tripping through worker-owned m90/m91 arrays. The arithmetic order of
     * each bridge dot product and each Math.rint input is unchanged.
     */
    private static int cameraToM9CurvePacked(short[] cam, int c, ColorContext ctx,
                                              double[] hsmOut, double gain, byte[] curve) {
        cameraToHsmXyz50(cam, c, ctx, hsmOut);
        double[] m = ctx.ppToM9;
        double pr = hsmOut[0], pg = hsmOut[1], pb = hsmOut[2];
        double m9r = Math.max(m[0] * pr + m[1] * pg + m[2] * pb, 0.0);
        double m9g = Math.max(m[3] * pr + m[4] * pg + m[5] * pb, 0.0);
        double m9b = Math.max(m[6] * pr + m[7] * pg + m[8] * pb, 0.0);

        long r = clipLong((long)Math.rint(m9r * gain * RAW_MAX), 0, RAW_MAX);
        long g = clipLong((long)Math.rint(m9g * gain * RAW_MAX), 0, RAW_MAX);
        long b = clipLong((long)Math.rint(m9b * gain * RAW_MAX), 0, RAW_MAX);
        final boolean evenBranch = r >= g;
        final long a0;
        final long a1;
        final long a2;
        if (evenBranch) {
            a0 = 16754 * r - 7632 * g - 922 * b;
            a1 = -3124 * r + 14774 * g - 3458 * b;
            a2 = -567 * r - 9579 * g + 18330 * b;
        } else {
            a0 = 18160 * r - 9034 * g - 922 * b;
            a1 = -3422 * r + 15080 * g - 3458 * b;
            a2 = 137 * r - 10264 * g + 18330 * b;
        }
        int i0 = (int)clipLong(a0 >> 16, 0, LUT_MAX);
        int i1 = (int)clipLong(a1 >> 16, 0, LUT_MAX);
        int i2 = (int)clipLong(a2 >> 16, 0, LUT_MAX);
        int rr = curve[i0] & 0xff;
        int gg = curve[i1] & 0xff;
        int bb = curve[i2] & 0xff;
        int edge = 0;
        if (rr == 0 || rr == 255) edge++;
        if (gg == 0 || gg == 255) edge++;
        if (bb == 0 || bb == 255) edge++;
        return (evenBranch ? (1 << 26) : 0) | (edge << 24) | (rr << 16) | (gg << 8) | bb;
    }

    private static final class TailBin {
        final double value;
        final long count;
        TailBin(double value, long count) { this.value = value; this.count = count; }
    }

    private static final class RawTail {
        double clipFraction, uq99, uq995, uq998, q, adaptiveUq, curvature, tailValue;
        boolean isolated;
    }

    private static RawTail rawTail(long[][] counts, float[] black, int wl, long totalPixels, long clipped) {
        List<TailBin> bins = new ArrayList<>();
        long total = 0;
        for (int plane = 0; plane < 4; plane++) {
            double bl = black != null && black.length >= 4 ? black[plane] : 64.0;
            double den = Math.max(1.0, wl - bl);
            for (int rv = 0; rv < wl; rv++) {
                long n = counts[plane][rv];
                if (n == 0) continue;
                double v = clamp((rv - bl) / den, 0.0, 1.0);
                bins.add(new TailBin(v, n));
                total += n;
            }
        }
        bins.sort(Comparator.comparingDouble(a -> a.value));
        RawTail o = new RawTail();
        o.clipFraction = totalPixels > 0 ? clipped / (double)totalPixels : 0.0;
        if (total <= 0) {
            o.uq99 = o.uq995 = o.uq998 = o.adaptiveUq = o.tailValue = 1.0;
            o.q = .95;
            o.curvature = 0.0;
            o.isolated = false;
            return o;
        }
        o.uq99 = quantileBins(bins, total, .99);
        o.uq995 = quantileBins(bins, total, .995);
        o.uq998 = quantileBins(bins, total, .998);
        o.q = clamp(.999 - TC_ALPHA * o.clipFraction, .95, .999);
        o.adaptiveUq = quantileBins(bins, total, o.q);
        double d1 = Math.log(Math.max(o.uq995, 1e-9) / Math.max(o.uq99, 1e-9));
        double d2 = Math.log(Math.max(o.uq998, 1e-9) / Math.max(o.uq995, 1e-9));
        o.curvature = d2 - .6 * d1;
        o.isolated = o.curvature > TC_TAIL_CURVATURE_THRESHOLD;
        o.tailValue = o.isolated ? o.uq995 : o.adaptiveUq;
        return o;
    }

    private static double quantileBins(List<TailBin> bins, long total, double q) {
        if (bins.isEmpty() || total <= 0) return 1.0;
        double pos = (total - 1) * q;
        long lo = (long)Math.floor(pos);
        long hi = (long)Math.ceil(pos);
        double frac = pos - lo;
        double vlo = valueAtRank(bins, lo);
        double vhi = hi == lo ? vlo : valueAtRank(bins, hi);
        return vlo + frac * (vhi - vlo);
    }

    private static double valueAtRank(List<TailBin> bins, long rank) {
        long c = 0;
        for (TailBin b : bins) {
            long next = c + b.count;
            if (rank < next) return b.value;
            c = next;
        }
        return bins.get(bins.size() - 1).value;
    }

    private static final class Meter {
        double gain, baseGain, legacyGain, p98, guardGain;
        double nativeScratchPrepMs, nativeInputCopyMs, nativeLumaPopulationMs;
        double nativeTotalWeightMs, nativeWeightedMedianMs, nativeP98Ms, nativeScalarTotalMs;
        double nativeLumaComputeMs, nativeOrderBuildMs; int nativeLumaWorkers;
    }

    /**
     * PRIMARY2.4 TC20NATIVE1B-ORIENT1A parity gate. Native code computes only the expensive frozen
     * H25/HSM -> sRGB-linear luma population, full sort, centre-weighted median and P98.
     * Gain/headroom decisions remain Java-side in the exact FIX7 operation order.
     */
    private static Meter tc20MeterNative(short[] cam, int w, int h, RawTail rawTail, long nativeContext,
                                           double[] rowW, double[] colW) {
        double[] nativeStats = new double[13]; // median, p98, validCount + PERF3C native timing ns
        M9NativeColorCore.meterTc20WeightedSelect(nativeContext, cam, Math.multiplyExact(w, h),
                w, h, rowW, colW, nativeStats);
        return tc20MeterFromNativeStats(nativeStats, rawTail);
    }

    // PERF3H CVDIRECT1A: same native TC20 scalar routine and Java gain math, but the
    // packed CV_16UC3 meter Mat is read in-place during this synchronous JNI call.
    private static Meter tc20MeterNativeDirect(long camAddress, int w, int h, RawTail rawTail, long nativeContext,
                                                 double[] rowW, double[] colW) {
        double[] nativeStats = new double[13];
        M9NativeColorCore.meterTc20WeightedSelectDirect(nativeContext, camAddress, Math.multiplyExact(w, h),
                w, h, rowW, colW, nativeStats);
        return tc20MeterFromNativeStats(nativeStats, rawTail);
    }

    private static Meter tc20MeterFromNativeStats(double[] nativeStats, RawTail rawTail) {
        int validCount = (int)Math.rint(nativeStats[2]);
        Meter out = new Meter();
        out.nativeScratchPrepMs = nativeStats[3] / 1_000_000.0;
        out.nativeInputCopyMs = nativeStats[4] / 1_000_000.0;
        out.nativeLumaPopulationMs = nativeStats[5] / 1_000_000.0;
        out.nativeTotalWeightMs = nativeStats[6] / 1_000_000.0;
        out.nativeWeightedMedianMs = nativeStats[7] / 1_000_000.0;
        out.nativeP98Ms = nativeStats[8] / 1_000_000.0;
        out.nativeScalarTotalMs = nativeStats[9] / 1_000_000.0;
        out.nativeLumaComputeMs = nativeStats[10] / 1_000_000.0;
        out.nativeOrderBuildMs = nativeStats[11] / 1_000_000.0;
        out.nativeLumaWorkers = (int)Math.rint(nativeStats[12]);
        if (validCount == 0) {
            out.baseGain = out.legacyGain = out.gain = 1.0;
            out.p98 = 0.0;
            out.guardGain = Math.max(1.0, TC_HEADROOM_TARGET / Math.max(rawTail.tailValue, 1e-9));
            return out;
        }
        double median = nativeStats[0];
        out.p98 = nativeStats[1];
        out.baseGain = clamp(METER_TARGET / Math.max(median, 1e-6), .5, 16.0);
        double legacy = out.p98 <= 1e-6 ? out.baseGain : Math.min(out.baseGain, 1.0 / out.p98);
        out.legacyGain = clamp(legacy, .5, 16.0);
        out.guardGain = Math.max(1.0, TC_HEADROOM_TARGET / Math.max(rawTail.tailValue, 1e-9));
        out.gain = Math.min(out.baseGain, out.guardGain);
        return out;
    }

    // Frozen FIX7 Java oracle retained only for source/host parity auditing; never called at runtime.
    private static Meter tc20MeterJavaReference(double[] y, int w, int h, RawTail rawTail) {
        int validCount = 0;
        for (double v : y) if (v > 1e-5) validCount++;
        Meter out = new Meter();
        if (validCount == 0) {
            out.baseGain = out.legacyGain = out.gain = 1.0;
            out.p98 = 0.0;
            out.guardGain = Math.max(1.0, TC_HEADROOM_TARGET / Math.max(rawTail.tailValue, 1e-9));
            return out;
        }
        int[] order = new int[validCount];
        int k = 0;
        for (int i = 0; i < y.length; i++) if (y[i] > 1e-5) order[k++] = i;
        sortIndicesByValue(order, y, 0, order.length - 1);

        double[] rowW = new double[h];
        double[] colW = new double[w];
        double h2 = h / 2.0, w2 = w / 2.0;
        double den = 2.0 * METER_CW * METER_CW;
        for (int yy = 0; yy < h; yy++) {
            double ry = (yy - h2) / h2;
            rowW[yy] = Math.exp(-(ry * ry) / den);
        }
        for (int xx = 0; xx < w; xx++) {
            double rx = (xx - w2) / w2;
            colW[xx] = Math.exp(-(rx * rx) / den);
        }
        double totalWeight = 0.0;
        for (int idx : order) totalWeight += rowW[idx / w] * colW[idx % w];
        double half = totalWeight * .5;
        double cum = 0.0;
        double median = y[order[order.length - 1]];
        for (int idx : order) {
            cum += rowW[idx / w] * colW[idx % w];
            if (cum >= half) { median = y[idx]; break; }
        }
        out.baseGain = clamp(METER_TARGET / Math.max(median, 1e-6), .5, 16.0);

        // Python's legacy P98 is diagnostic only in R3.5.  Derive it from the
        // already-sorted >1e-5 population; for ordinary photographs the 98th
        // percentile is far above that mask floor.
        long lowCount = y.length - order.length;
        double p = (y.length - 1) * .98;
        if (p < lowCount) {
            out.p98 = 0.0;
        } else {
            double pos = p - lowCount;
            int lo = Math.min(order.length - 1, Math.max(0, (int)Math.floor(pos)));
            int hi = Math.min(order.length - 1, Math.max(0, (int)Math.ceil(pos)));
            double frac = pos - Math.floor(pos);
            out.p98 = y[order[lo]] + frac * (y[order[hi]] - y[order[lo]]);
        }
        double legacy = out.p98 <= 1e-6 ? out.baseGain : Math.min(out.baseGain, 1.0 / out.p98);
        out.legacyGain = clamp(legacy, .5, 16.0);
        out.guardGain = Math.max(1.0, TC_HEADROOM_TARGET / Math.max(rawTail.tailValue, 1e-9));
        // Xiaomi main-camera DNGs used to freeze R3.5 contain no BaselineExposure;
        // therefore parity v0.7 deliberately uses baseline EV 0.0.
        out.gain = Math.min(out.baseGain, out.guardGain);
        return out;
    }

    // In-place primitive index sort, avoiding millions of boxed Integer objects.
    private static void sortIndicesByValue(int[] a, double[] v, int lo, int hi) {
        while (lo < hi) {
            int i = lo, j = hi;
            double pivot = v[a[lo + ((hi - lo) >>> 1)]];
            while (i <= j) {
                while (v[a[i]] < pivot) i++;
                while (v[a[j]] > pivot) j--;
                if (i <= j) {
                    int t = a[i]; a[i] = a[j]; a[j] = t;
                    i++; j--;
                }
            }
            // Recurse into smaller half first; continue on larger half to cap stack depth.
            if (j - lo < hi - i) {
                if (lo < j) sortIndicesByValue(a, v, lo, j);
                lo = i;
            } else {
                if (i < hi) sortIndicesByValue(a, v, i, hi);
                hi = j;
            }
        }
    }

    private static final class Stage {
        int[] argb;
        double branchEvenOccurrence;
        double rgb8ClipFraction;
        double nearWhiteFraction;
    }

    private static Stage m9Stage(double[] m9, int w, int h, double gain, byte[] curve, double cct) {
        int n = w * h;
        byte[] rgb8 = new byte[n * 3];
        long even = 0;
        long edge = 0;
        for (int p = 0, c = 0; p < n; p++, c += 3) {
            long r = clipLong((long)Math.rint(m9[c] * gain * RAW_MAX), 0, RAW_MAX);
            long g = clipLong((long)Math.rint(m9[c + 1] * gain * RAW_MAX), 0, RAW_MAX);
            long b = clipLong((long)Math.rint(m9[c + 2] * gain * RAW_MAX), 0, RAW_MAX);
            long[] q = r >= g ? QE : QO;
            if (r >= g) even++;
            long a0 = q[0] * r + q[1] * g + q[2] * b;
            long a1 = q[3] * r + q[4] * g + q[5] * b;
            long a2 = q[6] * r + q[7] * g + q[8] * b;
            int i0 = (int)clipLong(a0 >> 16, 0, LUT_MAX);
            int i1 = (int)clipLong(a1 >> 16, 0, LUT_MAX);
            int i2 = (int)clipLong(a2 >> 16, 0, LUT_MAX);
            int rr = curve[i0] & 0xff;
            int gg = curve[i1] & 0xff;
            int bb = curve[i2] & 0xff;
            rgb8[c] = (byte)rr; rgb8[c + 1] = (byte)gg; rgb8[c + 2] = (byte)bb;
            if (rr == 0 || rr == 255) edge++;
            if (gg == 0 || gg == 255) edge++;
            if (bb == 0 || bb == 255) edge++;
        }
        int[] argb = new int[n];
        long nearWhite = 0;
        final double tgWeight = tungstenGuardWeight(cct);
        final double tgCbGain = 1.0 - TG_NEG_CB_COMPRESSION * tgWeight;
        final double tgCrGain = 1.0 - TG_NEG_CR_COMPRESSION * tgWeight;
        int w2 = w - (w & 1);
        for (int y = 0; y < h; y++) {
            int row = y * w;
            for (int x = 0; x < w2; x += 2) {
                int p0 = row + x;
                int p1 = p0 + 1;
                int c0 = p0 * 3;
                int c1 = p1 * 3;
                long r0 = rgb8[c0] & 0xff, g0 = rgb8[c0 + 1] & 0xff, b0 = rgb8[c0 + 2] & 0xff;
                long r1 = rgb8[c1] & 0xff, g1 = rgb8[c1 + 1] & 0xff, b1 = rgb8[c1 + 2] & 0xff;
                long y0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;
                long y1 = (4899 * r1 + 9617 * g1 + 1868 * b1) >> 14;
                long rs = r0 + r1, gs = g0 + g1, bs = b0 + b1;
                long cbS = ((((-2765 * rs + 1) >> 1) - ((5427 * gs) >> 1) + ((8192 * bs) >> 1))) >> 14;
                long crS = ((((8192 * rs) >> 1) - ((6860 * gs) >> 1) - ((1332 * bs) >> 1))) >> 14;
                int cb = (int)((cbS + 128) & 0xff) - 128;
                int cr = (int)((crS + 128) & 0xff) - 128;

                // M9Modern TG1: preserve exact BT.601 Y and the 4:2:2 shared
                // chroma structure, but pull the historically troublesome
                // yellow/green sides gently toward neutral under tungsten.
                double cbModern = cb < 0 ? cb * tgCbGain : cb;
                double crModern = cr < 0 ? cr * tgCrGain : cr;
                int rr0 = roundU8(y0 + 1.402 * crModern);
                int gg0 = roundU8(y0 - .344136 * cbModern - .714136 * crModern);
                int bb0 = roundU8(y0 + 1.772 * cbModern);
                int rr1 = roundU8(y1 + 1.402 * crModern);
                int gg1 = roundU8(y1 - .344136 * cbModern - .714136 * crModern);
                int bb1 = roundU8(y1 + 1.772 * cbModern);
                argb[p0] = 0xff000000 | (rr0 << 16) | (gg0 << 8) | bb0;
                argb[p1] = 0xff000000 | (rr1 << 16) | (gg1 << 8) | bb1;
                if (Math.max(rr0, Math.max(gg0, bb0)) >= 250) nearWhite++;
                if (Math.max(rr1, Math.max(gg1, bb1)) >= 250) nearWhite++;
            }
            if (w2 != w) {
                int p = row + w2;
                int c = p * 3;
                int rr = rgb8[c] & 0xff, gg = rgb8[c + 1] & 0xff, bb = rgb8[c + 2] & 0xff;
                argb[p] = 0xff000000 | (rr << 16) | (gg << 8) | bb;
                if (Math.max(rr, Math.max(gg, bb)) >= 250) nearWhite++;
            }
        }
        Stage s = new Stage();
        s.argb = argb;
        s.branchEvenOccurrence = even / (double)n;
        s.rgb8ClipFraction = edge / (double)(n * 3L);
        s.nearWhiteFraction = nearWhite / (double)n;
        return s;
    }

    private static double tungstenGuardWeight(double cct) {
        double x = clamp((TG_START_K - cct) / (TG_START_K - TG_FULL_K), 0.0, 1.0);
        // Smoothstep avoids a visible regime edge in mixed light.
        return x * x * (3.0 - 2.0 * x);
    }

    private static int roundU8(double v) {
        // Mirror Python R3.5 literally: out = clip(v / 255, 0, 1), then
        // (out * 255 + .5).astype(uint8). Keeping the divide/multiply makes
        // boundary behavior match the NumPy oracle as closely as possible.
        double unit = clamp(v / 255.0, 0.0, 1.0);
        return (int)(unit * 255.0 + 0.5);
    }

    private static boolean savePng(Path path, Bitmap bitmap) {
        try (OutputStream out = Files.newOutputStream(path)) {
            boolean ok = bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
            out.flush();
            return ok;
        } catch (Exception e) {
            Log.e(TAG, "Unable to save parity PNG: " + Log.getStackTraceString(e));
            return false;
        }
    }

    private static double[] neutralToXy(double[] neutral, M9R35Calibration cal) {
        double[] xy = D50_XY.clone();
        for (int iter = 0; iter < 30; iter++) {
            double wA = weightA(cctFromXy(xy));
            double[] cm = interp9(cal.colorMatrixA, cal.colorMatrixD65, wA);
            double[] xyz = solve3(cm, neutral);
            double sum = xyz[0] + xyz[1] + xyz[2];
            if (Math.abs(sum) < 1e-15) throw new IllegalStateException("neutral_to_xy singular white point");
            double[] q = {xyz[0] / sum, xyz[1] / sum};
            if (Math.abs(q[0] - xy[0]) + Math.abs(q[1] - xy[1]) < 1e-8) return q;
            xy = q;
        }
        return xy;
    }

    private static void applyHsm(double r, double g, double b,
                                 double[] hsm, double[] out) {
        double v = Math.max(r, Math.max(g, b));
        double mn = Math.min(r, Math.min(g, b));
        double gap = v - mn;
        double h = 0.0, s = 0.0;
        if (gap > 1e-12) {
            if (r == v) {
                h = (g - b) / gap;
                if (h < 0) h += 6.0;
            } else if (g == v) {
                h = 2.0 + (b - r) / gap;
            } else {
                h = 4.0 + (r - g) / gap;
            }
            // gap > 1e-12 and RGB is clamped non-negative, therefore v > 1e-12.
            // Removing Math.max(v, 1e-12) is bit-identical for every reachable input.
            s = gap / v;
        }
        // Calibration loading rejects anything except 90x30x1, so these constants
        // are the exact former hd/6 and sd-1 values without per-pixel dimension math.
        double hp = h * 15.0;
        double sp = s * 29.0;
        // hp/sp are non-negative; Java's integer cast is therefore identical to floor.
        int h0 = (int)hp;
        int s0 = (int)sp;
        if (s0 > 28) s0 = 28;
        int h1 = h0 + 1;
        boolean wrap = h0 >= 89;
        if (wrap) { h0 = 89; h1 = 0; }
        double hf = hp - h0;
        double sf = sp - s0;
        double oneMinusHf = 1.0 - hf;
        double oneMinusSf = 1.0 - sf;
        int e00 = (h0 * 30 + s0) * 3;
        int e01 = (h1 * 30 + s0) * 3;
        int e10 = e00 + 3;
        int e11 = e01 + 3;
        double a0 = oneMinusHf * hsm[e00] + hf * hsm[e01];
        double c0 = oneMinusHf * hsm[e10] + hf * hsm[e11];
        double d0 = oneMinusSf * a0 + sf * c0;
        double a1 = oneMinusHf * hsm[e00 + 1] + hf * hsm[e01 + 1];
        double c1 = oneMinusHf * hsm[e10 + 1] + hf * hsm[e11 + 1];
        double d1 = oneMinusSf * a1 + sf * c1;
        double a2 = oneMinusHf * hsm[e00 + 2] + hf * hsm[e01 + 2];
        double c2 = oneMinusHf * hsm[e10 + 2] + hf * hsm[e11 + 2];
        double d2 = oneMinusSf * a2 + sf * c2;

        // Frozen Cobalt asset hue deltas are bounded to [-25.21723, +10.633671]
        // degrees. H25 therefore moves h by at most ~0.106 of a six-sector hue
        // coordinate, so a single branch wrap is exactly sufficient and avoids a
        // floating-point remainder in the 12.6 MP hot loop.
        double hue = h + HSM_H * d0 * (6.0 / 360.0);
        if (hue < 0.0) hue += 6.0;
        else if (hue >= 6.0) hue -= 6.0;
        double sat = Math.min(s * (1.0 + HSM_S * (d1 - 1.0)), 1.0);
        double val = clamp(v * (1.0 + HSM_V * (d2 - 1.0)), 0.0, 1.0);
        hsv6ToRgbWrapped(hue, sat, val, out);
    }

    /** Input hue is already guaranteed in [0,6) by applyHsm's one-step wrap. */
    private static void hsv6ToRgbWrapped(double h, double s, double v, double[] out) {
        int i = (int)h;
        double f = h - i;
        double p = v * (1.0 - s);
        double q = v * (1.0 - s * f);
        double t = v * (1.0 - s * (1.0 - f));
        switch (i) {
            case 0: out[0] = v; out[1] = t; out[2] = p; break;
            case 1: out[0] = q; out[1] = v; out[2] = p; break;
            case 2: out[0] = p; out[1] = v; out[2] = t; break;
            case 3: out[0] = p; out[1] = q; out[2] = v; break;
            case 4: out[0] = t; out[1] = p; out[2] = v; break;
            default: out[0] = v; out[1] = p; out[2] = q; break;
        }
    }

    private static double[] buildUnit16() {
        double[] out = new double[65536];
        for (int i = 0; i < out.length; i++) out[i] = i / 65535.0;
        return out;
    }

    private static double[] normalizedPpToXyz() {
        double[] pcs = xyToXyz(D50_XY);
        double[] row = matVec3(PP_TO_XYZ_RAW, new double[]{1, 1, 1});
        double[] m = PP_TO_XYZ_RAW.clone();
        for (int r = 0; r < 3; r++) {
            double scale = pcs[r] / row[r];
            for (int c = 0; c < 3; c++) m[r * 3 + c] *= scale;
        }
        return m;
    }

    private static double cctFromXy(double[] xy) {
        double x = xy[0], y = xy[1];
        double n = (x - .3320) / (y - .1858);
        return clamp(-449 * n * n * n + 3525 * n * n - 6823.3 * n + 5520.33, 2000, 12000);
    }

    private static double weightA(double t) {
        double m = 1e6 / t;
        return clamp((m - 1e6 / 6500.0) / (1e6 / 2850.0 - 1e6 / 6500.0), 0, 1);
    }

    private static double[] xyToXyz(double[] xy) {
        double x = xy[0], y = xy[1];
        return new double[]{x / y, 1.0, (1.0 - x - y) / y};
    }

    private static double[] bradford(double[] srcXy, double[] dstXy) {
        double[] s = matVec3(BRADFORD, xyToXyz(srcXy));
        double[] d = matVec3(BRADFORD, xyToXyz(dstXy));
        double[] diag = {d[0] / s[0], 0, 0, 0, d[1] / s[1], 0, 0, 0, d[2] / s[2]};
        return matMul3(matMul3(BRADFORD_INV, diag), BRADFORD);
    }

    private static double[] interp9(double[] a, double[] d, double wA) {
        double[] o = new double[9];
        for (int i = 0; i < 9; i++) o[i] = wA * a[i] + (1.0 - wA) * d[i];
        return o;
    }

    private static double[] matMul3(double[] a, double[] b) {
        double[] o = new double[9];
        for (int r = 0; r < 3; r++) {
            for (int c = 0; c < 3; c++) {
                o[r * 3 + c] = a[r * 3] * b[c] + a[r * 3 + 1] * b[3 + c] + a[r * 3 + 2] * b[6 + c];
            }
        }
        return o;
    }

    private static double[] matVec3(double[] m, double[] v) {
        return new double[]{
                m[0] * v[0] + m[1] * v[1] + m[2] * v[2],
                m[3] * v[0] + m[4] * v[1] + m[5] * v[2],
                m[6] * v[0] + m[7] * v[1] + m[8] * v[2]
        };
    }

    private static double[] inverse3(double[] m) {
        double a = m[0], b = m[1], c = m[2], d = m[3], e = m[4], f = m[5], g = m[6], h = m[7], i = m[8];
        double A = e * i - f * h;
        double B = -(d * i - f * g);
        double C = d * h - e * g;
        double D = -(b * i - c * h);
        double E = a * i - c * g;
        double F = -(a * h - b * g);
        double G = b * f - c * e;
        double H = -(a * f - c * d);
        double I = a * e - b * d;
        double det = a * A + b * B + c * C;
        if (Math.abs(det) < 1e-15) throw new IllegalArgumentException("singular 3x3 matrix");
        return new double[]{A / det, D / det, G / det, B / det, E / det, H / det, C / det, F / det, I / det};
    }

    private static double[] solve3(double[] a, double[] b) {
        return matVec3(inverse3(a), b);
    }

    private static int pyRoundPositive(double x) {
        long fl = (long)Math.floor(x);
        double f = x - fl;
        if (f < .5) return (int)fl;
        if (f > .5) return (int)(fl + 1);
        return (int)((fl & 1L) == 0L ? fl : fl + 1);
    }

    private static double clamp(double v, double lo, double hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    private static long clipLong(long v, long lo, long hi) {
        return Math.max(lo, Math.min(hi, v));
    }
}
