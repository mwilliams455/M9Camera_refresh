package com.particlesdevs.photoncamera.m9.render;

import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.params.LensShadingMap;

import com.particlesdevs.photoncamera.processing.ImageFrame;

import org.json.JSONObject;

/**
 * SOURCESHADING2A: guarded application of the Camera2 RAW lens-shading map.
 *
 * This class is source-domain only. It operates on the black-subtracted,
 * white-normalized Bayer/CFA plane before demosaic and before any M9 target
 * transform. It deliberately knows nothing about M9 colour, SAT2, curve02,
 * BT.601, TG1 or tone policy.
 */
final class M9SourceShadingApply2A {
    static final String REVISION = "SOURCESHADING2A_ACQUISITIONPROOF_SAMERAW_GAINLOCK";

    static final class Result {
        boolean requested;
        boolean provenanceProven;
        boolean mapEligible;
        boolean applied;
        String reason = "not_evaluated";
        String mapSemantics = "unknown";
        int mapColumns;
        int mapRows;
        long clippedPixels;
        double minGain = Double.NaN;
        double maxGain = Double.NaN;
        double meanGain = Double.NaN;
        long elapsedNs;

        JSONObject toJson(ImageFrame frame, int width, int height, int cfa) throws Exception {
            JSONObject j = new JSONObject();
            j.put("schema", "m9cam.sourceshading.v2a.acquisitionproof.sameraw");
            j.put("revision", REVISION);
            j.put("requested", requested);
            j.put("provenanceProven", provenanceProven);
            j.put("mapEligible", mapEligible);
            j.put("applied", applied);
            j.put("reason", reason);
            j.put("mapSemantics", mapSemantics);
            j.put("stage", "black_subtracted_white_normalized_CFA_before_demosaic");
            j.put("mapInterpolation", "Camera2_exact_endpoint_grid_bilinear");
            j.put("mapChannelOrder", "R,Geven,Godd,B");
            j.put("mapColumns", mapColumns);
            j.put("mapRows", mapRows);
            j.put("cfa", cfa);
            j.put("rawWidth", width);
            j.put("rawHeight", height);
            j.put("clippedPixels", clippedPixels);
            j.put("clippedFraction", width > 0 && height > 0
                    ? clippedPixels / (double)((long)width * (long)height) : 0.0);
            if (Double.isFinite(minGain)) j.put("minGain", minGain); else j.put("minGain", JSONObject.NULL);
            if (Double.isFinite(maxGain)) j.put("maxGain", maxGain); else j.put("maxGain", JSONObject.NULL);
            if (Double.isFinite(meanGain)) j.put("meanGain", meanGain); else j.put("meanGain", JSONObject.NULL);
            j.put("elapsedMs", elapsedNs / 1_000_000.0);
            JSONObject p = new JSONObject();
            if (frame != null) {
                p.put("sourceFormat", frame.m9SourceImageFormat);
                p.put("sourceImageWidth", frame.m9SourceImageWidth);
                p.put("sourceImageHeight", frame.m9SourceImageHeight);
                p.put("sourceRowStrideBytes", frame.m9SourceRowStrideBytes);
                p.put("sourcePixelStrideBytes", frame.m9SourcePixelStrideBytes);
                p.put("sourceCopyOffsetBytes", frame.m9SourceCopyOffsetBytes);
                p.put("sourceCopyCapacityBytes", frame.m9SourceCopyCapacityBytes);
                p.put("sourcePlaneCapacityBytes", frame.m9SourcePlaneCapacityBytes);
                p.put("sourceAspect169Requested", frame.m9SourceAspect169Requested);
                p.put("sourceBinningRequested", frame.m9SourceBinningRequested);
                p.put("ownedBufferCapacityBytes", frame.buffer != null ? frame.buffer.capacity() : -1);
            }
            j.put("acquisitionProvenance", p);
            j.put("deviceSpecificAestheticLogic", false);
            j.put("m9TargetMutation", false);
            return j;
        }
    }

    private M9SourceShadingApply2A() {}

    static Result applyInPlace(short[] normalizedCfa,
                               int width,
                               int height,
                               ImageFrame frame,
                               CameraCharacteristics characteristics,
                               CaptureResult captureResult,
                               int cfa,
                               boolean requested) {
        long started = System.nanoTime();
        Result out = new Result();
        out.requested = requested;
        try {
            if (normalizedCfa == null || normalizedCfa.length != Math.multiplyExact(width, height)) {
                out.reason = "normalized_CFA_size_mismatch";
                return finish(out, started);
            }
            if (frame == null || frame.buffer == null) {
                out.reason = "missing_ImageFrame_provenance";
                return finish(out, started);
            }
            final long expectedBytes = Math.multiplyExact((long)width * (long)height, 2L);
            final boolean provenance =
                    frame.m9SourceImageFormat == ImageFormat.RAW_SENSOR
                    && !frame.m9SourceAspect169Requested
                    && !frame.m9SourceBinningRequested
                    && frame.m9SourceCopyOffsetBytes == 0
                    && frame.m9SourceImageWidth == width
                    && frame.m9SourceImageHeight == height
                    && frame.m9SourcePixelStrideBytes == 2
                    && frame.m9SourceRowStrideBytes == Math.multiplyExact(width, 2)
                    && frame.m9SourceCopyCapacityBytes == expectedBytes
                    && frame.m9SourcePlaneCapacityBytes == expectedBytes
                    && frame.buffer.capacity() == expectedBytes;
            out.provenanceProven = provenance;
            if (!provenance) {
                out.reason = "RAW_acquisition_provenance_gate_failed";
                return finish(out, started);
            }
            if (characteristics == null || captureResult == null) {
                out.reason = "missing_Camera2_metadata";
                return finish(out, started);
            }
            Rect pre = characteristics.get(CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE);
            if (pre == null) pre = characteristics.get(CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE);
            if (pre == null || pre.width() != width || pre.height() != height) {
                out.reason = "RAW_dimensions_do_not_match_preCorrection_active_region";
                return finish(out, started);
            }
            if (cfa < 0 || cfa > 3) {
                out.reason = "unsupported_nonconventional_Bayer_CFA";
                return finish(out, started);
            }
            Boolean rawShadingApplied = characteristics.get(
                    CameraCharacteristics.SENSOR_INFO_LENS_SHADING_APPLIED);
            if (rawShadingApplied == null) {
                out.reason = "SENSOR_INFO_LENS_SHADING_APPLIED_missing";
                return finish(out, started);
            }
            out.mapSemantics = rawShadingApplied
                    ? "remaining_correction_after_RAW_partial_or_full_shading"
                    : "complete_correction_for_uncorrected_RAW";

            LensShadingMap map = captureResult.get(
                    CaptureResult.STATISTICS_LENS_SHADING_CORRECTION_MAP);
            if (map == null || map.getColumnCount() < 2 || map.getRowCount() < 2) {
                out.reason = "live_Camera2_lens_shading_map_missing_or_degenerate";
                return finish(out, started);
            }
            out.mapColumns = map.getColumnCount();
            out.mapRows = map.getRowCount();
            float[] factors = new float[map.getGainFactorCount()];
            map.copyGainFactors(factors, 0);
            if (factors.length != Math.multiplyExact(Math.multiplyExact(out.mapColumns, out.mapRows), 4)) {
                out.reason = "lens_shading_map_factor_count_mismatch";
                return finish(out, started);
            }
            for (float f : factors) {
                if (!Float.isFinite(f) || f < LensShadingMap.MINIMUM_GAIN_FACTOR) {
                    out.reason = "invalid_lens_shading_gain";
                    return finish(out, started);
                }
            }
            out.mapEligible = true;
            if (!requested) {
                out.reason = "control_path_no_pixel_mutation";
                return finish(out, started);
            }

            int[] x0 = new int[width];
            int[] x1 = new int[width];
            double[] xw = new double[width];
            final double xScale = (out.mapColumns - 1) / (double)Math.max(1, width - 1);
            for (int x = 0; x < width; x++) {
                double gx = x * xScale;
                int lo = Math.min(out.mapColumns - 1, (int)Math.floor(gx));
                int hi = Math.min(out.mapColumns - 1, lo + 1);
                x0[x] = lo;
                x1[x] = hi;
                xw[x] = gx - lo;
            }
            final double yScale = (out.mapRows - 1) / (double)Math.max(1, height - 1);
            double minGain = Double.POSITIVE_INFINITY;
            double maxGain = Double.NEGATIVE_INFINITY;
            double sumGain = 0.0;
            long clipped = 0L;

            for (int y = 0; y < height; y++) {
                double gy = y * yScale;
                int y0 = Math.min(out.mapRows - 1, (int)Math.floor(gy));
                int y1 = Math.min(out.mapRows - 1, y0 + 1);
                double wy = gy - y0;
                int rowBase = y * width;
                for (int x = 0; x < width; x++) {
                    int ch = channelFor(cfa, x, y);
                    int a = ((y0 * out.mapColumns + x0[x]) * 4) + ch;
                    int b = ((y0 * out.mapColumns + x1[x]) * 4) + ch;
                    int c = ((y1 * out.mapColumns + x0[x]) * 4) + ch;
                    int d = ((y1 * out.mapColumns + x1[x]) * 4) + ch;
                    double top = factors[a] + (factors[b] - factors[a]) * xw[x];
                    double bot = factors[c] + (factors[d] - factors[c]) * xw[x];
                    double gain = top + (bot - top) * wy;
                    minGain = Math.min(minGain, gain);
                    maxGain = Math.max(maxGain, gain);
                    sumGain += gain;
                    int i = rowBase + x;
                    long q = Math.round((normalizedCfa[i] & 0xffff) * gain);
                    if (q > 65535L) {
                        q = 65535L;
                        clipped++;
                    }
                    normalizedCfa[i] = (short)(q & 0xffffL);
                }
            }
            out.applied = true;
            out.reason = "applied_live_Camera2_map_exactly_once";
            out.clippedPixels = clipped;
            out.minGain = minGain;
            out.maxGain = maxGain;
            out.meanGain = sumGain / Math.max(1.0, (double)normalizedCfa.length);
            return finish(out, started);
        } catch (Throwable t) {
            out.applied = false;
            out.reason = "fail_closed_exception:" + t.getClass().getSimpleName();
            return finish(out, started);
        }
    }

    private static Result finish(Result out, long started) {
        out.elapsedNs = System.nanoTime() - started;
        return out;
    }

    private static int channelFor(int cfa, int x, int y) {
        boolean xe = (x & 1) == 0;
        boolean ye = (y & 1) == 0;
        switch (cfa) {
            case 0: // RGGB
                if (ye && xe) return 0;
                if (!ye && !xe) return 3;
                return ye ? 1 : 2;
            case 1: // GRBG
                if (ye && !xe) return 0;
                if (!ye && xe) return 3;
                return ye ? 1 : 2;
            case 2: // GBRG
                if (!ye && xe) return 0;
                if (ye && !xe) return 3;
                return ye ? 1 : 2;
            case 3: // BGGR
                if (!ye && !xe) return 0;
                if (ye && xe) return 3;
                return ye ? 1 : 2;
            default:
                throw new IllegalArgumentException("unsupported CFA " + cfa);
        }
    }
}
