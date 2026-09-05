#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-edgeplacementgate1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('EDGEPLACEMENTGATE1A missing expected file: ' + rel)
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
luma_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderedLumaDiagnostic.java'
gradle_rel = 'app/build.gradle'
renderer = read(renderer_rel)
luma = read(luma_rel)
gradle = read(gradle_rel)

if 'METADATAFIX1A_PHYSICAL_ISO' not in renderer:
    raise SystemExit('EDGEPLACEMENTGATE1A requires METADATAFIX1A renderer baseline')
if 'm9cam.renderedluma.v1.grid64' not in luma or 'read_only_finished_bitmap_sampling' not in luma:
    raise SystemExit('EDGEPLACEMENTGATE1A requires CAPTURESPLIT1B finished-bitmap diagnostic seam')
if '-metadatafix1a' not in gradle:
    raise SystemExit('EDGEPLACEMENTGATE1A requires METADATAFIX1A build identity')

# Freeze the renderer itself and every live capture/photographic seam. This overlay may
# extend only the already-read-only finished-bitmap diagnostic class and build identity.
frozen_rels = [
    renderer_rel,
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

helper_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9EdgePlacementGate1ADiagnostic.java'
if (root / helper_rel).exists():
    raise SystemExit('EDGEPLACEMENTGATE1A helper already exists; refuse ambiguous reapply')

helper = r'''package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Bitmap;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Arrays;

/**
 * EDGEPLACEMENTGATE1A finished-placement evidence extractor.
 *
 * Diagnostic only. It reads the already-finished, already-oriented bitmap reached by
 * RENDERMETER1B. It cannot alter pixels, capture exposure, TC20, SAT3, curve02, TG1,
 * JPEG encoding or metadata. Full-pixel scanning is intentionally accepted in this
 * diagnostic build so the 16x22 / 4x6 values match the offline oracle geometry.
 */
public final class M9EdgePlacementGate1ADiagnostic {
    public static final String SCHEMA = "m9cam.edgeplacementgate.v1a.rendergrid";
    private static final int GRID_R = 16;
    private static final int GRID_C = 22;
    private static final int REG_R = 4;
    private static final int REG_C = 6;
    private static final int SCAN_ROWS = 64;

    // Exact recovered M10-R Integral quantity mask at 0x4001349c. Spatial geometry only.
    // Sum = 14160. This does not claim M10-R CA9 numerical parity.
    private static final int[] INTEGRAL_MASK = new int[] {
         0, 0, 0, 0,10,10,10,10,10,10,10,10,10,10,10,10,10,10, 0, 0, 0, 0,
         0, 0, 0,10,10,20,20,20,30,30,30,30,30,30,20,20,20,10,10, 0, 0, 0,
         0, 0,10,10,20,30,30,30,30,40,50,50,40,30,30,30,30,20,10,10, 0, 0,
         0,10,10,20,30,40,50,50,50,60,60,60,60,50,50,50,40,30,20,10,10, 0,
        10,10,20,30,40,50,60,80,80,80,80,80,80,80,80,60,50,40,30,20,10,10,
        10,20,30,40,50,60,80,80,100,100,100,100,100,100,80,80,60,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,80,100,100,100,100,100,100,100,100,100,100,80,50,40,30,20,10,
        10,20,30,40,50,60,80,80,100,100,100,100,100,100,80,80,60,50,40,30,20,10,
        10,10,20,30,40,50,60,80,80,80,80,80,80,80,80,60,50,40,30,20,10,10,
         0,10,10,20,30,40,50,50,50,60,60,60,60,50,50,50,40,30,20,10,10, 0,
         0, 0,10,10,20,30,30,30,30,40,50,50,40,30,30,30,30,20,10,10, 0, 0,
         0, 0, 0,10,10,20,20,20,30,30,30,30,30,30,20,20,20,10,10, 0, 0, 0,
         0, 0, 0, 0,10,10,10,10,10,10,10,10,10,10,10,10,10,10, 0, 0, 0, 0
    };

    private M9EdgePlacementGate1ADiagnostic() {}

    public static JSONObject measure(Bitmap bitmap) {
        final long startedNs = System.nanoTime();
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_finished_bitmap_no_pixel_mutation");
            out.put("liveLiftEnabled", false);
            out.put("usedToMutateRenderer", false);
            out.put("usedToMutateCapture", false);
            out.put("gateDecisionAvailableInRenderer", false);
            out.put("combinationPolicy", "combine_with_capture_M9_json_preview_grid_and_achieved_intent_offline");
            out.put("gridRows", GRID_R);
            out.put("gridColumns", GRID_C);
            out.put("regionRows", REG_R);
            out.put("regionColumns", REG_C);
            out.put("integralMaskSum", 14160);
            out.put("lumaFormula", "exact_bt601_q14_(4899R+9617G+1868B)>>14");
            out.put("sampling", "all_finished_bitmap_pixels_streamed_in_64_row_blocks");
            out.put("partitionPolicy", "integer_floor_cell_boundaries_match_offline_rendergrid");

            if (bitmap == null || bitmap.isRecycled() || bitmap.getWidth() <= 0 || bitmap.getHeight() <= 0) {
                out.put("valid", false);
                out.put("reason", "missing_or_recycled_finished_bitmap");
                return finish(out, startedNs);
            }
            final int width = bitmap.getWidth();
            final int height = bitmap.getHeight();
            final int[] gridX = partitionMap(width, GRID_C);
            final int[] gridY = partitionMap(height, GRID_R);
            final int[] regX = partitionMap(width, REG_C);
            final int[] regY = partitionMap(height, REG_R);

            final long[] gridSums = new long[GRID_R * GRID_C];
            final long[] gridCounts = new long[GRID_R * GRID_C];
            final long[] regionHist = new long[REG_R * REG_C * 256];
            final int rowsPerBlock = Math.min(SCAN_ROWS, height);
            final int[] pixels = new int[Math.multiplyExact(width, rowsPerBlock)];

            long pixelCount = 0L;
            for (int y0 = 0; y0 < height; y0 += rowsPerBlock) {
                final int rows = Math.min(rowsPerBlock, height - y0);
                bitmap.getPixels(pixels, 0, width, 0, y0, width, rows);
                for (int ly = 0; ly < rows; ly++) {
                    final int y = y0 + ly;
                    final int gy = gridY[y];
                    final int rr = regY[y];
                    final int rowBase = ly * width;
                    for (int x = 0; x < width; x++) {
                        final int p = pixels[rowBase + x];
                        final int r = (p >>> 16) & 0xff;
                        final int g = (p >>> 8) & 0xff;
                        final int b = p & 0xff;
                        final int yy = (4899 * r + 9617 * g + 1868 * b) >> 14;

                        final int gi = gy * GRID_C + gridX[x];
                        gridSums[gi] += yy;
                        gridCounts[gi]++;

                        final int ri = rr * REG_C + regX[x];
                        regionHist[(ri << 8) + yy]++;
                        pixelCount++;
                    }
                }
            }

            final double[] grid = new double[GRID_R * GRID_C];
            double gridMean = 0.0;
            for (int i = 0; i < grid.length; i++) {
                grid[i] = gridCounts[i] > 0 ? gridSums[i] / (double)gridCounts[i] : 0.0;
                gridMean += grid[i];
            }
            gridMean /= grid.length;

            long maskSum = 0L;
            double integralY = 0.0;
            for (int i = 0; i < grid.length; i++) {
                final int w = INTEGRAL_MASK[i];
                maskSum += w;
                integralY += grid[i] * w;
            }
            if (maskSum != 14160L) throw new IllegalStateException("bad Integral mask sum: " + maskSum);
            integralY /= maskSum;

            final double[] meanRegions = regions4x6(grid);
            final double center8 = rectMean(meanRegions, 1, 3, 1, 5);
            final double lower12 = rectMean(meanRegions, 2, 4, 0, 6);
            final double upper6 = rectMean(meanRegions, 0, 1, 0, 6);
            final double edge16 = edgeMean(meanRegions, true);
            final double inner8 = edgeMean(meanRegions, false);

            final double[] medians = new double[24];
            final double[] q95s = new double[24];
            final double[] dark64 = new double[24];
            for (int region = 0; region < 24; region++) {
                final int off = region << 8;
                long n = 0L;
                long darkN = 0L;
                for (int code = 0; code < 256; code++) {
                    final long c = regionHist[off + code];
                    n += c;
                    if (code <= 64) darkN += c;
                }
                medians[region] = histogramQuantile(regionHist, off, n, 0.50);
                q95s[region] = histogramQuantile(regionHist, off, n, 0.95);
                dark64[region] = n > 0 ? darkN / (double)n : 0.0;
            }

            out.put("valid", true);
            out.put("reason", "finished_render_geometry_recorded_no_live_gate_or_lift");
            out.put("bitmapWidth", width);
            out.put("bitmapHeight", height);
            out.put("pixelCount", pixelCount);
            out.put("renderGridMeanY", gridMean);
            out.put("renderIntegralY", integralY);
            out.put("renderIntegralVsMeanEv", log2Ratio(integralY, gridMean));
            out.put("renderRegionalMedianY", quantile(meanRegions, 0.50));
            out.put("renderCenter8Y", center8);
            out.put("renderLower12Y", lower12);
            out.put("renderUpper6Y", upper6);
            out.put("renderEdge16Y", edge16);
            out.put("renderInner8Y", inner8);
            out.put("renderUpperVsLowerEv", log2Ratio(upper6, lower12));
            out.put("renderCenterOverIntegralEv", log2Ratio(center8, integralY));
            out.put("renderInnerVsEdgeEv", log2Ratio(inner8, edge16));
            out.put("renderCellMedianP25", quantile(medians, 0.25));
            out.put("renderCellMedianP50", quantile(medians, 0.50));
            out.put("renderCellMedianP75", quantile(medians, 0.75));
            out.put("renderCellMedianMax", max(medians));
            out.put("renderCellQ95P50", quantile(q95s, 0.50));
            out.put("renderCellQ95P75", quantile(q95s, 0.75));
            out.put("renderCellQ95Max", max(q95s));
            out.put("renderCellDark64P50", quantile(dark64, 0.50));
            out.put("renderCellDark64P75", quantile(dark64, 0.75));
            out.put("renderGrid16x22", gridJson(grid));
            out.put("renderMeanRegions4x6", arrayJson(meanRegions));
            out.put("renderMedian4x6", arrayJson(medians));
            out.put("renderQ95_4x6", arrayJson(q95s));
            return finish(out, startedNs);
        } catch (Throwable t) {
            try {
                out.put("valid", false);
                out.put("reason", "edgeplacementgate1a_rendergrid_exception");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
            return finish(out, startedNs);
        }
    }

    private static JSONObject finish(JSONObject out, long startedNs) {
        try { out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0); }
        catch (Exception ignored) {}
        return out;
    }

    // Builds exactly the same integer-floor boundaries used by numpy slices:
    // [i*n/k, (i+1)*n/k). This avoids off-by-one differences from x*k/n labelling.
    private static int[] partitionMap(int n, int k) {
        int[] out = new int[n];
        for (int cell = 0; cell < k; cell++) {
            int a = cell * n / k;
            int b = (cell + 1) * n / k;
            for (int i = a; i < b; i++) out[i] = cell;
        }
        return out;
    }

    private static double[] regions4x6(double[] grid) {
        if (grid == null || grid.length != GRID_R * GRID_C) throw new IllegalArgumentException("bad render grid");
        double[] out = new double[REG_R * REG_C];
        for (int rr = 0; rr < REG_R; rr++) {
            int r0 = rr * GRID_R / REG_R;
            int r1 = (rr + 1) * GRID_R / REG_R;
            for (int cc = 0; cc < REG_C; cc++) {
                int c0 = cc * GRID_C / REG_C;
                int c1 = (cc + 1) * GRID_C / REG_C;
                double sum = 0.0;
                int n = 0;
                for (int r = r0; r < r1; r++) {
                    for (int c = c0; c < c1; c++) {
                        sum += grid[r * GRID_C + c];
                        n++;
                    }
                }
                out[rr * REG_C + cc] = n > 0 ? sum / n : 0.0;
            }
        }
        return out;
    }

    private static double rectMean(double[] regions, int r0, int r1, int c0, int c1) {
        double sum = 0.0;
        int n = 0;
        for (int r = r0; r < r1; r++) for (int c = c0; c < c1; c++) {
            sum += regions[r * REG_C + c];
            n++;
        }
        return n > 0 ? sum / n : 0.0;
    }

    private static double edgeMean(double[] regions, boolean edge) {
        double sum = 0.0;
        int n = 0;
        for (int r = 0; r < REG_R; r++) for (int c = 0; c < REG_C; c++) {
            boolean isEdge = r == 0 || r == REG_R - 1 || c == 0 || c == REG_C - 1;
            if (isEdge == edge) { sum += regions[r * REG_C + c]; n++; }
        }
        return n > 0 ? sum / n : 0.0;
    }

    // numpy default quantile interpolation: linear between adjacent ordered samples.
    private static double histogramQuantile(long[] hist, int off, long n, double q) {
        if (n <= 0) return 0.0;
        double pos = (n - 1) * q;
        long lo = (long)Math.floor(pos);
        long hi = (long)Math.ceil(pos);
        double a = histogramRank(hist, off, lo);
        double b = histogramRank(hist, off, hi);
        return a + (pos - lo) * (b - a);
    }

    private static int histogramRank(long[] hist, int off, long rank) {
        long acc = 0L;
        for (int code = 0; code < 256; code++) {
            acc += hist[off + code];
            if (rank < acc) return code;
        }
        return 255;
    }

    private static double quantile(double[] values, double q) {
        double[] s = values.clone();
        Arrays.sort(s);
        double pos = (s.length - 1) * q;
        int lo = (int)Math.floor(pos);
        int hi = (int)Math.ceil(pos);
        return s[lo] + (pos - lo) * (s[hi] - s[lo]);
    }

    private static double max(double[] values) {
        double m = Double.NEGATIVE_INFINITY;
        for (double v : values) if (v > m) m = v;
        return m;
    }

    private static double log2Ratio(double a, double b) {
        return Math.log(Math.max(a, 1.0e-6) / Math.max(b, 1.0e-6)) / Math.log(2.0);
    }

    private static JSONArray arrayJson(double[] values) {
        JSONArray out = new JSONArray();
        for (double v : values) out.put(v);
        return out;
    }

    private static JSONArray gridJson(double[] grid) {
        JSONArray rows = new JSONArray();
        for (int r = 0; r < GRID_R; r++) {
            JSONArray row = new JSONArray();
            for (int c = 0; c < GRID_C; c++) row.put(grid[r * GRID_C + c]);
            rows.put(row);
        }
        return rows;
    }
}
'''
write(helper_rel, helper)

# Attach to the existing read-only finished-bitmap diagnostic. Renderer call remains untouched.
anchor = '            out.put("middleCenter33", middleCenter33.toJson());\n'
insert = anchor + '            out.put("edgePlacementGate1A", M9EdgePlacementGate1ADiagnostic.measure(bitmap));\n'
if anchor not in luma:
    raise SystemExit('EDGEPLACEMENTGATE1A rendered-luma attachment anchor missing')
if 'edgePlacementGate1A' in luma:
    raise SystemExit('EDGEPLACEMENTGATE1A rendered-luma attachment already present')
luma = luma.replace(anchor, insert, 1)
write(luma_rel, luma)

# Distinguishable APK identity only.
if '-edgeplacementgate1a' not in gradle:
    version_re = re.compile(r"(versionName\s+['\"])([^'\"]+)(['\"])")
    m = version_re.search(gradle)
    if not m:
        raise SystemExit('EDGEPLACEMENTGATE1A versionName anchor missing')
    gradle = gradle[:m.start(2)] + m.group(2) + '-edgeplacementgate1a' + gradle[m.end(2):]
    write(gradle_rel, gradle)

for rel, before in frozen_before.items():
    if sha(rel) != before:
        raise SystemExit('EDGEPLACEMENTGATE1A frozen photographic/capture seam changed: ' + rel)

print('M9Cam EDGEPLACEMENTGATE1A diagnostic overlay applied')
print(' - existing CAPTURESPLIT1B finished-bitmap hook reused; renderer source frozen byte-for-byte')
print(' - exact BT.601 Q14 Y + exact integer-floor 16x22/4x6 geometry + direct medians recorded')
print(' - full-pixel diagnostic scan only; elapsedMs recorded for overhead audit')
print(' - liveLiftEnabled=false; no live gate or correction reaches pixels/capture')
print(' - capture AE, TC20, native color, SAT3, curve02, BT601/TG1, JPEG95 and metadata frozen')
