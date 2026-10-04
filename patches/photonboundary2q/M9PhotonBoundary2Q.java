package com.particlesdevs.photoncamera.m9.render;

import android.hardware.camera2.CaptureResult;
import android.media.Image;
import com.particlesdevs.photoncamera.processing.ImageFrame;
import org.json.JSONObject;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;

/** Per-owned-frame, read-only RAW handoff evidence. No global frame/result lookup. */
public final class M9PhotonBoundary2Q {
    public static final String ID = "M9PHOTONBOUNDARY2Q_READONLY";
    private M9PhotonBoundary2Q() {}

    public static final class Trace {
        final JSONObject acquisition = new JSONObject();
        final Map<String, JSONObject> stages = new LinkedHashMap<>();
        final Map<String, String> hashes = new LinkedHashMap<>();
        long imageTimestamp = -1;
        boolean raw16Copy;
        boolean failed;
        long elapsedNs;

        synchronized void error(Throwable error) {
            failed = true;
            put(acquisition, "error", error.getClass().getSimpleName() + ": " + error.getMessage());
        }
    }

    static void put(JSONObject out, String key, Object value) {
        try { out.put(key, value == null ? JSONObject.NULL : value); }
        catch (Exception ignored) { /* JSON failure must never change capture ownership. */ }
    }

    /** Hash the JNI base-address window, independent of caller position/limit/order/mark. */
    public static String hashWindow(ByteBuffer source, int offset, int length) throws Exception {
        if (source == null || offset < 0 || length <= 0
                || (long) offset + length > source.capacity()) {
            throw new IllegalArgumentException("invalid RAW byte window");
        }
        ByteBuffer view = source.asReadOnlyBuffer();
        view.clear();
        view.position(offset);
        view.limit(offset + length);
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        byte[] block = new byte[Math.min(length, 65536)];
        while (view.hasRemaining()) {
            int n = Math.min(block.length, view.remaining());
            view.get(block, 0, n);
            hash.update(block, 0, n);
        }
        char[] hex = new char[64];
        char[] digits = "0123456789abcdef".toCharArray();
        byte[] digest = hash.digest();
        for (int i = 0; i < digest.length; i++) {
            hex[2*i] = digits[(digest[i] >>> 4) & 15];
            hex[2*i+1] = digits[digest[i] & 15];
        }
        return new String(hex);
    }

    public static Trace beforeCopy(Image image, int width, int height,
                                   int offset, int capacity, boolean binning) {
        Trace trace = new Trace();
        long started = System.nanoTime();
        try {
            trace.imageTimestamp = image.getTimestamp();
            Image.Plane plane = image.getPlanes()[0];
            int rowStride = plane.getRowStride();
            int pixelStride = plane.getPixelStride();
            trace.raw16Copy = image.getFormat() == 32 && !binning && pixelStride == 2
                    && width > 0 && height > 0 && rowStride == (long) width * 2
                    && capacity == (long) rowStride * height;
            put(trace.acquisition, "imageTimestampNs", trace.imageTimestamp);
            put(trace.acquisition, "imageWidth", image.getWidth());
            put(trace.acquisition, "imageHeight", image.getHeight());
            put(trace.acquisition, "format", image.getFormat());
            put(trace.acquisition, "copyWidth", width);
            put(trace.acquisition, "copyHeight", height);
            put(trace.acquisition, "rowStrideBytes", rowStride);
            put(trace.acquisition, "pixelStrideBytes", pixelStride);
            put(trace.acquisition, "copyOffsetBytes", offset);
            put(trace.acquisition, "copyCapacityBytes", capacity);
            put(trace.acquisition, "binning", binning);
            put(trace.acquisition, "fullImageWidthEqualsCopyWidth", image.getWidth() == width);
            put(trace.acquisition, "raw16CopyComparable", trace.raw16Copy);
            snapshot(trace, "cameraPlaneBeforeCopy", plane.getBuffer(), offset, capacity,
                    trace.imageTimestamp, null, null);
        } catch (Throwable error) { trace.error(error); }
        finally { trace.elapsedNs += System.nanoTime() - started; }
        return trace;
    }

    static void snapshot(Trace trace, String stage, ByteBuffer buffer, int offset, int length,
                         long timestamp, CaptureResult result, String requestedId) {
        synchronized (trace) {
            JSONObject item = new JSONObject();
            put(item, "frameTimestampNs", timestamp);
            put(item, "imageTimestampMatchesFrame", timestamp == trace.imageTimestamp);
            put(item, "bufferIdentity", buffer == null ? null : System.identityHashCode(buffer));
            put(item, "bufferCapacity", buffer == null ? null : buffer.capacity());
            put(item, "bufferPosition", buffer == null ? null : buffer.position());
            put(item, "bufferLimit", buffer == null ? null : buffer.limit());
            put(item, "byteOffset", offset);
            put(item, "byteCount", length);
            put(item, "thread", Thread.currentThread().getName());
            put(item, "captureResultPresent", result != null);
            try {
                String hash = hashWindow(buffer, offset, length);
                trace.hashes.put(stage, hash);
                put(item, "sha256", hash);
                put(item, "hashComplete", true);
                if (result != null) {
                    Long sensorTimestamp = result.get(CaptureResult.SENSOR_TIMESTAMP);
                    put(item, "sensorTimestampNs", sensorTimestamp);
                    put(item, "frameNumber", result.getFrameNumber());
                    put(item, "resultCameraId", M9PhysicalCaptureResult1A.resultCameraId(result));
                    put(item, "requestedCameraId", requestedId);
                    put(item, "imageTimestampMatchesResult", sensorTimestamp == null
                            ? null : trace.imageTimestamp == sensorTimestamp.longValue());
                }
            } catch (Throwable error) {
                trace.error(error);
                put(item, "hashComplete", false);
                put(item, "error", error.toString());
            }
            trace.stages.put(stage, item);
        }
    }

    public static void frame(ImageFrame frame, String stage, CaptureResult result, String requestedId) {
        if (frame == null || frame.m9PhotonBoundary2Q == null) return;
        Trace trace = frame.m9PhotonBoundary2Q;
        long started = System.nanoTime();
        try {
            int length = frame.buffer == null ? -1 : frame.buffer.capacity();
            snapshot(trace, stage, frame.buffer, 0, length, frame.timestamp, result, requestedId);
        } catch (Throwable error) { trace.error(error); }
        finally { synchronized (trace) { trace.elapsedNs += System.nanoTime() - started; } }
    }

    /** Final PRIMARY attachment, after the DNG call and before freeing the owned frame. */
    public static JSONObject finish(ImageFrame frame, boolean dngSaved) {
        JSONObject out = new JSONObject();
        put(out, "revision", ID);
        put(out, "dngSaved", dngSaved);
        Trace trace = frame == null ? null : frame.m9PhotonBoundary2Q;
        if (trace == null) {
            put(out, "status", "incomplete_no_acquisition_trace");
            return out;
        }
        synchronized (trace) {
            put(out, "acquisition", trace.acquisition);
            JSONObject stages = new JSONObject();
            for (Map.Entry<String, JSONObject> item : trace.stages.entrySet())
                put(stages, item.getKey(), item.getValue());
            put(out, "stages", stages);
            String[] required = {"cameraPlaneBeforeCopy", "photonOwnedAfterCopy", "rendererEntry",
                    "dngWriterInput", "dngWriterReturn"};
            String first = trace.hashes.get(required[0]);
            boolean complete = !trace.failed;
            boolean same = first != null;
            for (String name : required) {
                String hash = trace.hashes.get(name);
                complete &= hash != null;
                same &= first != null && first.equals(hash);
            }
            boolean identitiesComplete = true;
            boolean identitiesMatch = true;
            for (String name : new String[]{"rendererEntry", "dngWriterInput", "dngWriterReturn"}) {
                JSONObject item = trace.stages.get(name);
                identitiesComplete &= item != null && !item.isNull("sensorTimestampNs");
                identitiesMatch &= item != null && item.optBoolean("imageTimestampMatchesFrame", false)
                        && item.optBoolean("imageTimestampMatchesResult", false);
            }
            put(out, "allRequiredHashesPresent", complete);
            put(out, "allRawBytesEqual", complete && trace.raw16Copy ? same : null);
            put(out, "allResultTimestampsPresent", identitiesComplete);
            put(out, "allImageResultTimestampsEqual", identitiesComplete ? identitiesMatch : null);
            put(out, "diagnosticElapsedMs", trace.elapsedNs / 1_000_000.0);
            put(out, "savedDngDecodedPixelsCompared", false);
            put(out, "status", !complete || !identitiesComplete || !dngSaved ? "incomplete"
                    : !trace.raw16Copy ? "unsupported_copy_layout"
                    : !same ? "raw_bytes_changed"
                    : !identitiesMatch ? "frame_result_timestamp_mismatch"
                    : "buffer_handoffs_match_saved_DNG_decode_pending");
            put(out, "scope", "read_only_bytes_and_identity_no_pixel_correction; saved_DNG_decode_is_separate");
            return out;
        }
    }
}
