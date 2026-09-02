package com.particlesdevs.photoncamera.m9.render;

import com.particlesdevs.photoncamera.app.PhotonCamera;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * Frozen calibration payload used by the Android R3.5 parity renderer.
 *
 * The binary asset is generated from:
 *  - Xiaomi 15 Ultra Rear Wide Camera Cobalt Modular.dcp
 *  - Leica M9 firmware curve_02.bin
 *
 * Forward matrices are normalized exactly as the frozen Python R3.5 renderer
 * does before being stored in the asset.  HSM data remains the original DCP
 * float32 values; the renderer promotes them to double during interpolation.
 */
public final class M9R35Calibration {
    private static final String ASSET = "m9/m9_r35_calibration.bin";
    private static volatile M9R35Calibration INSTANCE;

    public final int hueDivisions;
    public final int satDivisions;
    public final int valueDivisions;
    public final double[] colorMatrixA;
    public final double[] colorMatrixD65;
    public final double[] forwardMatrixA;
    public final double[] forwardMatrixD65;
    public final float[] hsmA;
    public final float[] hsmD65;
    public final byte[] curve02;

    private M9R35Calibration(int hd, int sd, int vd,
                             double[] cmA, double[] cmD,
                             double[] fmA, double[] fmD,
                             float[] hA, float[] hD,
                             byte[] curve) {
        hueDivisions = hd;
        satDivisions = sd;
        valueDivisions = vd;
        colorMatrixA = cmA;
        colorMatrixD65 = cmD;
        forwardMatrixA = fmA;
        forwardMatrixD65 = fmD;
        hsmA = hA;
        hsmD65 = hD;
        curve02 = curve;
    }

    public static M9R35Calibration get() throws Exception {
        M9R35Calibration c = INSTANCE;
        if (c != null) return c;
        synchronized (M9R35Calibration.class) {
            if (INSTANCE == null) INSTANCE = load();
            return INSTANCE;
        }
    }

    private static M9R35Calibration load() throws Exception {
        byte[] bytes;
        try (InputStream in = PhotonCamera.getResourcesStatic().getAssets().open(ASSET);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] tmp = new byte[16384];
            int n;
            while ((n = in.read(tmp)) >= 0) out.write(tmp, 0, n);
            bytes = out.toByteArray();
        }
        ByteBuffer b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);
        byte[] magicBytes = new byte[8];
        b.get(magicBytes);
        String magic = new String(magicBytes, StandardCharsets.US_ASCII);
        if (!"M9R35CAL".equals(magic)) throw new IllegalStateException("bad R3.5 calibration magic: " + magic);
        int version = b.getInt();
        if (version != 1) throw new IllegalStateException("unsupported R3.5 calibration version: " + version);
        int hd = b.getInt();
        int sd = b.getInt();
        int vd = b.getInt();
        if (hd != 90 || sd != 30 || vd != 1) {
            throw new IllegalStateException("unexpected Cobalt HSM dimensions: " + hd + "x" + sd + "x" + vd);
        }
        double[] cmA = readDoubles(b, 9);
        double[] cmD = readDoubles(b, 9);
        double[] fmA = readDoubles(b, 9);
        double[] fmD = readDoubles(b, 9);
        int hsmLen = hd * sd * vd * 3;
        float[] hA = readFloats(b, hsmLen);
        float[] hD = readFloats(b, hsmLen);
        byte[] curve = new byte[2048];
        b.get(curve);
        if (b.hasRemaining()) throw new IllegalStateException("unexpected trailing R3.5 calibration bytes: " + b.remaining());
        return new M9R35Calibration(hd, sd, vd, cmA, cmD, fmA, fmD, hA, hD, curve);
    }

    private static double[] readDoubles(ByteBuffer b, int n) {
        double[] out = new double[n];
        for (int i = 0; i < n; i++) out[i] = b.getDouble();
        return out;
    }

    private static float[] readFloats(ByteBuffer b, int n) {
        float[] out = new float[n];
        for (int i = 0; i < n; i++) out[i] = b.getFloat();
        return out;
    }

    @Override
    public String toString() {
        return "M9R35Calibration{" + hueDivisions + "x" + satDivisions + "x" + valueDivisions +
                ", curve=" + curve02.length + ", cmA=" + Arrays.toString(colorMatrixA) + "}";
    }
}
