#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourceboundaryprobe1a-multisensor.py <PhotonCamera-root>')
root = Path(sys.argv[1])
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not renderer.exists():
    raise SystemExit(f'missing renderer: {renderer}')
s = renderer.read_text()

# Correct the stale prose only; this does not alter executable behaviour.
s = s.replace(
'''    // BASISHSM1P-NATIVESOURCE1A production route.\n    // Photographic math is the validated 1O middle candidate exactly:\n    // native SOURCECAL2A + historical basis/H25 target role + self-meter TC20 + NORM030.\n    // The old Cobalt-source renderCore remains only as a dormant forensic reference.\n''',
'''    // COBALTROLEPURGE1A-NATIVEFIRMWARE1A production route.\n    // Physical-sensor SOURCECAL2A ends at common scene space; every supported camera\n    // then enters the same lens-independent M9 target renderer. Historical Cobalt\n    // basis/HSM paths are dormant forensic modes only.\n''', 1)

insert_anchor = '    // SKYCHROMA1A read-only audit. Counts signed/out-of-cube events before either\n'
if insert_anchor not in s:
    raise SystemExit('SOURCEBOUNDARYPROBE1A helper insertion anchor missing')

helper = r'''
    // SOURCEBOUNDARYPROBE1A: same-frame, read-only multi-sensor boundary audit.
    // No result from this probe feeds source calibration, TC20, SAT3, curve02,
    // BT.601, TG1 or the final bitmap. It samples native demosaic rows without
    // interpolation and mirrors the frozen scalar target arithmetic analytically.
    private static final int SOURCEBOUNDARY_MAX_PAIR_SAMPLES1A = 3072;
    private static final double SOURCEBOUNDARY_INV_SQRT2_1A = 0.7071067811865476;

    private static final class SourceBoundaryStageAccumulator1A {
        final String stage;
        final String domain;
        final String axisInterpretation;
        final double[] neutralAxisDistance;
        final double[] greenMagentaAbs;
        final double[] greenMagentaPairDeltaAbs;
        final double[] adjacentChromaVectorDelta;
        final double[] rValues;
        final double[] gValues;
        final double[] bValues;
        final double[] gridNeutralSum = new double[9];
        final double[] gridPairDeltaSum = new double[9];
        final long[] gridPixels = new long[9];
        final long[] gridPairs = new long[9];
        int pixelCount = 0;
        int pairCount = 0;
        long nonFiniteCount = 0L;
        long belowZeroChannels = 0L;
        long aboveOneChannels = 0L;
        double sumGreenMagenta = 0.0;
        double sumGreenMagentaSq = 0.0;

        SourceBoundaryStageAccumulator1A(String stage, String domain,
                                         String axisInterpretation, int maxPairs) {
            this.stage = stage;
            this.domain = domain;
            this.axisInterpretation = axisInterpretation;
            int maxPixels = Math.max(2, Math.multiplyExact(maxPairs, 2));
            neutralAxisDistance = new double[maxPixels];
            greenMagentaAbs = new double[maxPixels];
            greenMagentaPairDeltaAbs = new double[Math.max(1, maxPairs)];
            adjacentChromaVectorDelta = new double[Math.max(1, maxPairs)];
            rValues = new double[maxPixels];
            gValues = new double[maxPixels];
            bValues = new double[maxPixels];
        }

        private void addPixel1A(double[] v, int gridCell) {
            if (pixelCount >= neutralAxisDistance.length) return;
            double r = v[0], g = v[1], b = v[2];
            if (!Double.isFinite(r) || !Double.isFinite(g) || !Double.isFinite(b)) {
                nonFiniteCount++;
                r = Double.isFinite(r) ? r : 0.0;
                g = Double.isFinite(g) ? g : 0.0;
                b = Double.isFinite(b) ? b : 0.0;
            }
            rValues[pixelCount] = r;
            gValues[pixelCount] = g;
            bValues[pixelCount] = b;
            if (r < 0.0) belowZeroChannels++; if (g < 0.0) belowZeroChannels++; if (b < 0.0) belowZeroChannels++;
            if (r > 1.0) aboveOneChannels++; if (g > 1.0) aboveOneChannels++; if (b > 1.0) aboveOneChannels++;
            double rg = r - g, bg = b - g;
            double neutral = Math.sqrt(rg * rg + bg * bg) * SOURCEBOUNDARY_INV_SQRT2_1A;
            double gm = 0.5 * (r + b) - g;
            neutralAxisDistance[pixelCount] = neutral;
            greenMagentaAbs[pixelCount] = Math.abs(gm);
            sumGreenMagenta += gm;
            sumGreenMagentaSq += gm * gm;
            if (gridCell >= 0 && gridCell < 9) {
                gridNeutralSum[gridCell] += neutral;
                gridPixels[gridCell]++;
            }
            pixelCount++;
        }

        void addPair1A(double[] a, double[] b, int gridCell) {
            if (pairCount >= greenMagentaPairDeltaAbs.length) return;
            addPixel1A(a, gridCell);
            addPixel1A(b, gridCell);
            double gmA = 0.5 * (a[0] + a[2]) - a[1];
            double gmB = 0.5 * (b[0] + b[2]) - b[1];
            double rgDelta = (a[0] - a[1]) - (b[0] - b[1]);
            double bgDelta = (a[2] - a[1]) - (b[2] - b[1]);
            double pairGm = Math.abs(gmA - gmB);
            double pairChroma = Math.sqrt(rgDelta * rgDelta + bgDelta * bgDelta)
                    * SOURCEBOUNDARY_INV_SQRT2_1A;
            greenMagentaPairDeltaAbs[pairCount] = pairGm;
            adjacentChromaVectorDelta[pairCount] = pairChroma;
            if (gridCell >= 0 && gridCell < 9) {
                gridPairDeltaSum[gridCell] += pairChroma;
                gridPairs[gridCell]++;
            }
            pairCount++;
        }

        private static double mean1A(double[] v, int n) {
            if (n <= 0) return Double.NaN;
            double s = 0.0;
            for (int i = 0; i < n; i++) s += v[i];
            return s / n;
        }

        private static double quantile1A(double[] v, int n, double q) {
            if (n <= 0) return Double.NaN;
            double[] x = Arrays.copyOf(v, n);
            Arrays.sort(x);
            return skinLumaQuantile1A(x, q);
        }

        private static JSONObject distribution1A(double[] v, int n) throws Exception {
            JSONObject o = new JSONObject();
            o.put("count", n);
            if (n <= 0) return o;
            o.put("mean", mean1A(v, n));
            o.put("q50", quantile1A(v, n, 0.50));
            o.put("q90", quantile1A(v, n, 0.90));
            o.put("q95", quantile1A(v, n, 0.95));
            o.put("q99", quantile1A(v, n, 0.99));
            o.put("max", quantile1A(v, n, 1.00));
            return o;
        }

        JSONObject toJson1A() throws Exception {
            JSONObject o = new JSONObject();
            o.put("stage", stage);
            o.put("domain", domain);
            o.put("axisInterpretation", axisInterpretation);
            o.put("pixelSamples", pixelCount);
            o.put("pairSamples", pairCount);
            o.put("nonFinitePixelSamples", nonFiniteCount);
            o.put("belowZeroChannelFraction", pixelCount > 0
                    ? belowZeroChannels / (double)(pixelCount * 3L) : 0.0);
            o.put("aboveOneChannelFraction", pixelCount > 0
                    ? aboveOneChannels / (double)(pixelCount * 3L) : 0.0);
            JSONObject meanRgb = new JSONObject();
            meanRgb.put("r", mean1A(rValues, pixelCount));
            meanRgb.put("g", mean1A(gValues, pixelCount));
            meanRgb.put("b", mean1A(bValues, pixelCount));
            o.put("meanRgb", meanRgb);
            double gmMean = pixelCount > 0 ? sumGreenMagenta / pixelCount : Double.NaN;
            double gmVar = pixelCount > 0
                    ? Math.max(0.0, sumGreenMagentaSq / pixelCount - gmMean * gmMean)
                    : Double.NaN;
            o.put("greenMagentaAxisSignedMean", gmMean);
            o.put("greenMagentaAxisSignedStd", pixelCount > 0 ? Math.sqrt(gmVar) : Double.NaN);
            o.put("neutralAxisDistance", distribution1A(neutralAxisDistance, pixelCount));
            o.put("greenMagentaAxisAbs", distribution1A(greenMagentaAbs, pixelCount));
            o.put("adjacentPairGreenMagentaDeltaAbs", distribution1A(greenMagentaPairDeltaAbs, pairCount));
            o.put("adjacentPairChromaVectorDelta", distribution1A(adjacentChromaVectorDelta, pairCount));
            JSONArray grid = new JSONArray();
            for (int i = 0; i < 9; i++) {
                JSONObject cell = new JSONObject();
                cell.put("gridX", i % 3);
                cell.put("gridY", i / 3);
                cell.put("pixelSamples", gridPixels[i]);
                cell.put("pairSamples", gridPairs[i]);
                cell.put("meanNeutralAxisDistance", gridPixels[i] > 0
                        ? gridNeutralSum[i] / gridPixels[i] : JSONObject.NULL);
                cell.put("meanAdjacentPairChromaVectorDelta", gridPairs[i] > 0
                        ? gridPairDeltaSum[i] / gridPairs[i] : JSONObject.NULL);
                grid.put(cell);
            }
            o.put("grid3x3", grid);
            return o;
        }
    }

    private static double[] sourceBoundarySensorNeutralized1A(double[] cameraRgb, double[] neutral) {
        double nr = Math.max(Math.abs(neutral[0]), 1.0e-9);
        double ng = Math.max(Math.abs(neutral[1]), 1.0e-9);
        double nb = Math.max(Math.abs(neutral[2]), 1.0e-9);
        return new double[]{cameraRgb[0] / nr, cameraRgb[1] / ng, cameraRgb[2] / nb};
    }

    private static double[] sourceBoundarySourcecalUnclipped1A(double[] cameraRgb,
                                                               double[] nativeCamToPp,
                                                               double[] cw) {
        double cr = Math.min(cameraRgb[0], cw[0]);
        double cg = Math.min(cameraRgb[1], cw[1]);
        double cb = Math.min(cameraRgb[2], cw[2]);
        return new double[]{
                nativeCamToPp[0] * cr + nativeCamToPp[1] * cg + nativeCamToPp[2] * cb,
                nativeCamToPp[3] * cr + nativeCamToPp[4] * cg + nativeCamToPp[5] * cb,
                nativeCamToPp[6] * cr + nativeCamToPp[7] * cg + nativeCamToPp[8] * cb
        };
    }

    private static double[] sourceBoundaryClamp01_1A(double[] v) {
        return new double[]{clamp(v[0], 0.0, 1.0), clamp(v[1], 0.0, 1.0), clamp(v[2], 0.0, 1.0)};
    }

    private static double[] sourceBoundaryBridge1A(double[] commonScene, double[] ppToM9) {
        return new double[]{
                Math.max(ppToM9[0] * commonScene[0] + ppToM9[1] * commonScene[1] + ppToM9[2] * commonScene[2], 0.0),
                Math.max(ppToM9[3] * commonScene[0] + ppToM9[4] * commonScene[1] + ppToM9[5] * commonScene[2], 0.0),
                Math.max(ppToM9[6] * commonScene[0] + ppToM9[7] * commonScene[1] + ppToM9[8] * commonScene[2], 0.0)
        };
    }

    private static long[] sourceBoundaryGain14_1A(double[] m9, double gain) {
        return new long[]{
                clipLong((long)Math.rint(m9[0] * gain * RAW_MAX), 0, RAW_MAX),
                clipLong((long)Math.rint(m9[1] * gain * RAW_MAX), 0, RAW_MAX),
                clipLong((long)Math.rint(m9[2] * gain * RAW_MAX), 0, RAW_MAX)
        };
    }

    private static int[] sourceBoundarySat3_1A(long[] q14) {
        long r = q14[0], g = q14[1], b = q14[2];
        long[] q = r >= g ? QE : QO;
        long a0 = q[0] * r + q[1] * g + q[2] * b;
        long a1 = q[3] * r + q[4] * g + q[5] * b;
        long a2 = q[6] * r + q[7] * g + q[8] * b;
        return new int[]{
                (int)clipLong(a0 >> 16, 0, LUT_MAX),
                (int)clipLong(a1 >> 16, 0, LUT_MAX),
                (int)clipLong(a2 >> 16, 0, LUT_MAX)
        };
    }

    private static double[] sourceBoundaryNorm14_1A(long[] q14) {
        return new double[]{q14[0] / (double)RAW_MAX, q14[1] / (double)RAW_MAX, q14[2] / (double)RAW_MAX};
    }

    private static double[] sourceBoundaryNormSat3_1A(int[] sat) {
        return new double[]{sat[0] / (double)LUT_MAX, sat[1] / (double)LUT_MAX, sat[2] / (double)LUT_MAX};
    }

    private static int[] sourceBoundaryCurve1A(int[] sat, byte[] curve) {
        return new int[]{curve[sat[0]] & 0xff, curve[sat[1]] & 0xff, curve[sat[2]] & 0xff};
    }

    private static double[] sourceBoundaryNorm8_1A(int[] rgb8) {
        return new double[]{rgb8[0] / 255.0, rgb8[1] / 255.0, rgb8[2] / 255.0};
    }

    private static int[][] sourceBoundaryBt601Pair1A(int[] a, int[] b,
                                                      double cbGain, double crGain) {
        long r0 = a[0], g0 = a[1], b0 = a[2];
        long r1 = b[0], g1 = b[1], b1 = b[2];
        long y0 = (4899 * r0 + 9617 * g0 + 1868 * b0) >> 14;
        long y1 = (4899 * r1 + 9617 * g1 + 1868 * b1) >> 14;
        long rs = r0 + r1, gs = g0 + g1, bs = b0 + b1;
        long cbS = ((((-2765 * rs + 1) >> 1) - ((5427 * gs) >> 1) + ((8192 * bs) >> 1))) >> 14;
        long crS = ((((8192 * rs) >> 1) - ((6860 * gs) >> 1) - ((1332 * bs) >> 1))) >> 14;
        int cb = (int)((cbS + 128) & 0xff) - 128;
        int cr = (int)((crS + 128) & 0xff) - 128;
        double cbAdjusted = cb < 0 ? cb * cbGain : cb;
        double crAdjusted = cr < 0 ? cr * crGain : cr;
        return new int[][]{
                {roundU8(y0 + 1.402 * crAdjusted),
                        roundU8(y0 - .344136 * cbAdjusted - .714136 * crAdjusted),
                        roundU8(y0 + 1.772 * cbAdjusted)},
                {roundU8(y1 + 1.402 * crAdjusted),
                        roundU8(y1 - .344136 * cbAdjusted - .714136 * crAdjusted),
                        roundU8(y1 + 1.772 * cbAdjusted)}
        };
    }

    private static JSONObject sourceBoundaryProbe1A(Mat cam16,
                                                     double[] nativeCamToPp,
                                                     ColorContext ctx,
                                                     double[] sensorNeutral,
                                                     double effectiveRenderGain,
                                                     byte[] curve) throws Exception {
        JSONObject out = new JSONObject();
        out.put("schema", "m9cam.renderer.sourceboundaryprobe.v1a");
        out.put("diagnosticOnly", true);
        out.put("pixelMutation", false);
        out.put("gainMutation", false);
        out.put("matrixMutation", false);
        out.put("targetRendererMutation", false);
        out.put("cobaltRestored", false);
        out.put("purpose", "locate_green_magenta_contamination_relative_to_SOURCECAL2A_common_scene_boundary");
        out.put("sampleInput", "same_full_resolution_POST_DEMOSAIC_SENSORRGB_Mat_read_only_rows_no_resize_no_interpolation");
        out.put("sharedTargetMath", "identity_HSM_then_M9_bridge_TC20_gain_SAT3_curve02_exact_BT601_422_then_TG1");
        out.put("pairing", "source_horizontal_even_x_adjacent_pairs_matches_frozen_BT601_pairing_space");
        out.put("greenMagentaAxisDefinition", "((R+B)/2)-G");
        out.put("neutralAxisDistanceDefinition", "sqrt((R-G)^2+(B-G)^2)/sqrt(2)");
        out.put("adjacentPairChromaVectorDeltaDefinition",
                "sqrt(delta(R-G)^2+delta(B-G)^2)/sqrt(2)_between_adjacent_source_horizontal_pixels");

        final int width = cam16.cols();
        final int height = cam16.rows();
        if (width < 2 || height < 1 || cam16.channels() != 3) {
            out.put("valid", false);
            out.put("reason", "invalid_cam16_geometry_or_channels");
            return out;
        }
        final long totalPairs = (long)(width / 2) * (long)height;
        final int stride = Math.max(1, (int)Math.ceil(Math.sqrt(
                totalPairs / (double)SOURCEBOUNDARY_MAX_PAIR_SAMPLES1A)));
        final int pairOffset = stride / 2;
        final int yOffset = stride / 2;
        out.put("valid", true);
        out.put("inputWidth", width);
        out.put("inputHeight", height);
        out.put("maxPairSamples", SOURCEBOUNDARY_MAX_PAIR_SAMPLES1A);
        out.put("pairStride", stride);
        out.put("pairOffset", pairOffset);
        out.put("yOffset", yOffset);
        out.put("effectiveRenderGain", effectiveRenderGain);
        out.put("sensorNeutralR", sensorNeutral[0]);
        out.put("sensorNeutralG", sensorNeutral[1]);
        out.put("sensorNeutralB", sensorNeutral[2]);

        String[] names = {
                "POST_DEMOSAIC_SENSORRGB",
                "POST_DEMOSAIC_SENSORRGB_NEUTRALIZED_DIAGNOSTIC",
                "POST_SOURCECAL_LINEAR_UNCLIPPED",
                "POST_SOURCECAL_COMMONSCENE",
                "POST_M9_BRIDGE",
                "POST_TC20_GAIN",
                "POST_SAT3",
                "POST_CURVE02",
                "POST_BT601",
                "POST_TG1"
        };
        String[] domains = {
                "physical_camera_RGB_normalized_16bit",
                "diagnostic_camera_RGB_divided_by_AsShotNeutral_not_rendered",
                "linear_ProPhoto_D50_signed_before_common_scene_clamp",
                "linear_ProPhoto_D50_actual_0_1_common_scene_handoff",
                "linear_M9_bridge_RGB_nonnegative",
                "M9_RGB_14bit_after_TC20_gain_and_clip_normalized",
                "firmware_SAT3_M06_M07_indices_normalized_0_1",
                "curve02_RGB8_normalized_0_1",
                "exact_BT601_422_reconstructed_RGB8_without_TG1_normalized_0_1",
                "exact_BT601_422_plus_TG1_reconstructed_RGB8_normalized_0_1"
        };
        String[] interpretations = {
                "raw_sensor_channel_distance_only_not_a_scene_neutral_axis",
                "camera_space_neutralized_diagnostic_axis",
                "scene_referred_common_working_axis_before_renderer_clamp",
                "scene_referred_common_working_axis_actual_handoff",
                "shared_M9_target_domain_axis",
                "shared_M9_target_domain_after_meter_gain",
                "shared_M9_target_domain_after_firmware_saturation_matrix",
                "display_encoded_curve02_RGB_axis",
                "display_encoded_exact_BT601_pair_reconstruction_axis",
                "final_display_encoded_TG1_axis"
        };
        SourceBoundaryStageAccumulator1A[] acc = new SourceBoundaryStageAccumulator1A[names.length];
        for (int i = 0; i < names.length; i++) {
            acc[i] = new SourceBoundaryStageAccumulator1A(
                    names[i], domains[i], interpretations[i], SOURCEBOUNDARY_MAX_PAIR_SAMPLES1A);
        }

        final double tgWeight = tungstenGuardWeight(ctx.cct);
        final double tgCbGain = 1.0 - TG_NEG_CB_COMPRESSION * tgWeight;
        final double tgCrGain = 1.0 - TG_NEG_CR_COMPRESSION * tgWeight;
        out.put("tungstenGuardWeight", tgWeight);
        out.put("tungstenGuardCbGain", tgCbGain);
        out.put("tungstenGuardCrGain", tgCrGain);

        short[] row = new short[Math.multiplyExact(width, 3)];
        int sampledPairs = 0;
        outer:
        for (int y = Math.min(height - 1, yOffset); y < height; y += stride) {
            cam16.get(y, 0, row);
            int pairIndexStart = Math.min(Math.max(0, width / 2 - 1), pairOffset);
            for (int pairIndex = pairIndexStart; pairIndex < width / 2; pairIndex += stride) {
                if (sampledPairs >= SOURCEBOUNDARY_MAX_PAIR_SAMPLES1A) break outer;
                int x = pairIndex * 2;
                int c0 = x * 3, c1 = c0 + 3;
                double[] camA = {(row[c0] & 0xffff) / 65535.0,
                        (row[c0 + 1] & 0xffff) / 65535.0,
                        (row[c0 + 2] & 0xffff) / 65535.0};
                double[] camB = {(row[c1] & 0xffff) / 65535.0,
                        (row[c1 + 1] & 0xffff) / 65535.0,
                        (row[c1 + 2] & 0xffff) / 65535.0};
                int gx = Math.min(2, (x * 3) / Math.max(1, width));
                int gy = Math.min(2, (y * 3) / Math.max(1, height));
                int gridCell = gy * 3 + gx;
                acc[0].addPair1A(camA, camB, gridCell);
                acc[1].addPair1A(sourceBoundarySensorNeutralized1A(camA, sensorNeutral),
                        sourceBoundarySensorNeutralized1A(camB, sensorNeutral), gridCell);

                double[] sourceRawA = sourceBoundarySourcecalUnclipped1A(camA, nativeCamToPp, ctx.cw);
                double[] sourceRawB = sourceBoundarySourcecalUnclipped1A(camB, nativeCamToPp, ctx.cw);
                acc[2].addPair1A(sourceRawA, sourceRawB, gridCell);
                double[] commonA = sourceBoundaryClamp01_1A(sourceRawA);
                double[] commonB = sourceBoundaryClamp01_1A(sourceRawB);
                acc[3].addPair1A(commonA, commonB, gridCell);

                double[] bridgeA = sourceBoundaryBridge1A(commonA, ctx.ppToM9);
                double[] bridgeB = sourceBoundaryBridge1A(commonB, ctx.ppToM9);
                acc[4].addPair1A(bridgeA, bridgeB, gridCell);
                long[] gainA = sourceBoundaryGain14_1A(bridgeA, effectiveRenderGain);
                long[] gainB = sourceBoundaryGain14_1A(bridgeB, effectiveRenderGain);
                acc[5].addPair1A(sourceBoundaryNorm14_1A(gainA),
                        sourceBoundaryNorm14_1A(gainB), gridCell);
                int[] satA = sourceBoundarySat3_1A(gainA);
                int[] satB = sourceBoundarySat3_1A(gainB);
                acc[6].addPair1A(sourceBoundaryNormSat3_1A(satA),
                        sourceBoundaryNormSat3_1A(satB), gridCell);
                int[] curveA = sourceBoundaryCurve1A(satA, curve);
                int[] curveB = sourceBoundaryCurve1A(satB, curve);
                acc[7].addPair1A(sourceBoundaryNorm8_1A(curveA),
                        sourceBoundaryNorm8_1A(curveB), gridCell);
                int[][] bt = sourceBoundaryBt601Pair1A(curveA, curveB, 1.0, 1.0);
                acc[8].addPair1A(sourceBoundaryNorm8_1A(bt[0]),
                        sourceBoundaryNorm8_1A(bt[1]), gridCell);
                int[][] tg = sourceBoundaryBt601Pair1A(curveA, curveB, tgCbGain, tgCrGain);
                acc[9].addPair1A(sourceBoundaryNorm8_1A(tg[0]),
                        sourceBoundaryNorm8_1A(tg[1]), gridCell);
                sampledPairs++;
            }
        }
        out.put("sampledPairs", sampledPairs);
        out.put("sampledPixels", sampledPairs * 2L);
        JSONArray stages = new JSONArray();
        for (SourceBoundaryStageAccumulator1A a : acc) stages.put(a.toJson1A());
        out.put("stages", stages);
        out.put("decisionRule",
                "first_stage_with_material_3x_vs_main_jump_in_adjacentPairChromaVectorDelta_or_greenMagenta_axis_is_first_suspect_boundary");
        out.put("sourceSideStopStage", "POST_SOURCECAL_COMMONSCENE");
        out.put("targetSideStartStage", "POST_M9_BRIDGE");
        out.put("productionImageChanged", false);
        return out;
    }

'''
s = s.replace(insert_anchor, helper + insert_anchor, 1)

call_anchor = '''            final JSONObject skyChromaSignedAudit1AJson = skinLumaStageAuditEnabled1A
                    ? skyChromaSignedAudit1A(cam16, ctx, skyChromaMode1A)
                    : null;
'''
if call_anchor not in s:
    raise SystemExit('SOURCEBOUNDARYPROBE1A call anchor missing')
call_insert = call_anchor + r'''

            // SOURCEBOUNDARYPROBE1A is diagnostic-only and cannot fail the photographic render.
            JSONObject sourceBoundaryProbe1AJson;
            long sourceBoundaryProbeElapsedMs1A;
            long sourceBoundaryProbeStartedNs1A = System.nanoTime();
            try {
                sourceBoundaryProbe1AJson = sourceBoundaryProbe1A(
                        cam16, nativeCamToPpBeforeProbe, ctx, nativeSource.neutral,
                        effectiveRenderGain, firmwareCurve02);
            } catch (Throwable probeError1A) {
                sourceBoundaryProbe1AJson = new JSONObject();
                sourceBoundaryProbe1AJson.put("schema", "m9cam.renderer.sourceboundaryprobe.v1a");
                sourceBoundaryProbe1AJson.put("diagnosticOnly", true);
                sourceBoundaryProbe1AJson.put("valid", false);
                sourceBoundaryProbe1AJson.put("error", probeError1A.toString());
                sourceBoundaryProbe1AJson.put("productionImageChanged", false);
            }
            sourceBoundaryProbeElapsedMs1A =
                    (System.nanoTime() - sourceBoundaryProbeStartedNs1A) / 1_000_000L;
'''
s = s.replace(call_anchor, call_insert, 1)

telemetry_anchor = '''            d.put("skyChromaProductionBehaviorChanged",
                    skyDiagnosticEncodedAny1A && skyChromaMode1A != 0);
'''
if telemetry_anchor not in s:
    raise SystemExit('SOURCEBOUNDARYPROBE1A telemetry anchor missing')
telemetry = telemetry_anchor + r'''
            d.put("sourceBoundaryProbe1AEnabled", true);
            d.put("sourceBoundaryProbe1ADiagnosticOnly", true);
            d.put("sourceBoundaryProbe1APixelMutation", false);
            d.put("sourceBoundaryProbe1AGainMutation", false);
            d.put("sourceBoundaryProbe1ATargetRendererMutation", false);
            d.put("sourceBoundaryProbe1AElapsedMs", sourceBoundaryProbeElapsedMs1A);
            d.put("sourceBoundaryProbe1A", sourceBoundaryProbe1AJson);
'''
s = s.replace(telemetry_anchor, telemetry, 1)

# Promote the wrapper schema/architecture label for unambiguous device sidecars.
wrapper_anchor = '        d.put("architectureRevision", "COBALTROLEPURGE1A_NATIVEFIRMWARE1A");\n'
if wrapper_anchor not in s:
    raise SystemExit('production architecture telemetry anchor missing')
s = s.replace(wrapper_anchor,
'''        d.put("architectureRevision", "COBALTROLEPURGE1A_NATIVEFIRMWARE1A_SOURCEBOUNDARYPROBE1A");
        d.put("sourceBoundaryProbeBranch", "research/sourceboundaryprobe1a-multisensor");
''', 1)

renderer.write_text(s)
print('SOURCEBOUNDARYPROBE1A_MULTISENSOR applied')
