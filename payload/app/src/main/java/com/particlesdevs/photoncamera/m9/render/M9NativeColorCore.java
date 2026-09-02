package com.particlesdevs.photoncamera.m9.render;

/**
 * PRIMARY2.4 COLORNATIVE2A bridge: FIX7 scalar colour plus native weighted-selection TC20 meter.
 *
 * Native loading is deliberately lazy: class initialization must never make PhotonCamera
 * unlaunchable if m9color has an ABI/packaging/linker problem. The renderer calls
 * ensureLoaded() only when an M9 frame actually enters the native colour path.
 */
final class M9NativeColorCore {
    private static volatile boolean loadAttempted;
    private static volatile boolean loaded;
    private static volatile Throwable loadFailure;

    private M9NativeColorCore() {}

    static boolean ensureLoaded() {
        if (loaded) return true;
        if (loadAttempted) return false;
        synchronized (M9NativeColorCore.class) {
            if (loaded) return true;
            if (loadAttempted) return false;
            loadAttempted = true;
            try {
                System.loadLibrary("m9color");
                loaded = true;
                return true;
            } catch (Throwable t) {
                loadFailure = t;
                return false;
            }
        }
    }

    static String loadError() {
        Throwable t = loadFailure;
        if (t == null) return "unknown native-load failure";
        String message = t.getMessage();
        return t.getClass().getName() + (message == null || message.isEmpty() ? "" : ": " + message);
    }

    static native long createContext(double[] cw,
                                     double[] camToPp,
                                     double[] hsm,
                                     double[] ppToM9,
                                     double[] adapt50To65,
                                     double[] ppToXyz,
                                     double[] xyz2Srgb,
                                     byte[] curve02,
                                     int hueDivisions,
                                     int satDivisions);

    static native void destroyContext(long handle);

    /**
     * NORMNATIVE1A: exact PRIMARY2 RAW normalization arithmetic + per-CFA histograms.
     * Reads the direct RAW ByteBuffer from offset zero and writes the normalized 16-bit plane
     * plus a flattened [4][whiteLevel] histogram. stats = {computeNs, outputCopyNs, workers}.
     */
    static native long normalizeRawDirect(java.nio.ByteBuffer rawBuffer,
                                          int pixelCount,
                                          int width,
                                          int height,
                                          float[] black,
                                          int whiteLevel,
                                          int workers,
                                          short[] norm16,
                                          long[] rawCountsFlat,
                                          long[] stats);


    /** Native TC20NATIVE1B-ORIENT1A: frozen scalar H25/HSM+luma, weighted-selection median and P98. */
    static native void meterTc20WeightedSelect(long handle,
                                         short[] cam,
                                         int pixelCount,
                                         int width,
                                         int height,
                                         double[] rowWeights,
                                         double[] colWeights,
                                         double[] stats);

    /** PERF3H CVDIRECT1A: exact TC20 input read directly from a packed OpenCV CV_16UC3 Mat. */
    static native void meterTc20WeightedSelectDirect(long handle,
                                                     long camAddress,
                                                     int pixelCount,
                                                     int width,
                                                     int height,
                                                     double[] rowWeights,
                                                     double[] colWeights,
                                                     double[] stats);

    static native void renderStrip(long handle,
                                   short[] camStrip,
                                   int pixelCount,
                                   int width,
                                   int[] argbStrip,
                                   double gain,
                                   double tgCbGain,
                                   double tgCrGain,
                                   int cameraRotation,
                                   long[] stats);

    /**
     * COLORNATIVE2A: one JNI call per bounded colour block. Native code partitions
     * the block into disjoint row ranges and runs the frozen scalar kernel concurrently.
     * PERF3A stats = {even, edge, nearWhite, summedWorkerNs, workersUsed, scratchPrepNs,
     * inputCopyNs, workerWallNs, maxWorkerNs, orientationNs, outputCopyNs, nativeTotalNs}.
     */
    static native void renderBlockParallel(long handle,
                                           short[] camBlock,
                                           int pixelCount,
                                           int width,
                                           int[] argbBlock,
                                           double gain,
                                           double tgCbGain,
                                           double tgCrGain,
                                           int cameraRotation,
                                           int workers,
                                           long[] stats);


    /** PERF3H CVDIRECT1A: exact full-color input read directly from packed OpenCV Mat storage. */
    static native void renderBlockParallelDirect(long handle,
                                                 long camAddress,
                                                 int pixelCount,
                                                 int width,
                                                 int[] argbBlock,
                                                 double gain,
                                                 double tgCbGain,
                                                 double tgCrGain,
                                                 int cameraRotation,
                                                 int workers,
                                                 long[] stats);

    /**
     * PERF3I BITMAPDIRECT1A: same frozen scalar render, but writes completed oriented pixels
     * directly into a mutable ARGB_8888 Bitmap through AndroidBitmap_lockPixels().
     * Returns false before modifying pixels if native Bitmap layout validation/locking fails,
     * allowing the exact PERF3H int[] -> Bitmap.setPixels fallback.
     */
    static native boolean renderBlockParallelDirectBitmap(long handle,
                                                          long camAddress,
                                                          int pixelCount,
                                                          int width,
                                                          android.graphics.Bitmap bitmap,
                                                          int blockY0,
                                                          int sourceHeight,
                                                          double gain,
                                                          double tgCbGain,
                                                          double tgCrGain,
                                                          int cameraRotation,
                                                          int workers,
                                                          long[] stats);
}
