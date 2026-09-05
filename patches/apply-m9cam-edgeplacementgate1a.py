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
    (root / rel).write_text(text)


def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_rel = 'app/build.gradle'
renderer = read(renderer_rel)
gradle = read(gradle_rel)

if 'METADATAFIX1A_PHYSICAL_ISO' not in renderer:
    raise SystemExit('EDGEPLACEMENTGATE1A requires METADATAFIX1A renderer baseline')
if '-metadatafix1a' not in gradle:
    raise SystemExit('EDGEPLACEMENTGATE1A requires METADATAFIX1A build identity')

# Every live photographic/capture seam except the Java finished-bitmap diagnostics target
# is frozen byte-for-byte during this overlay.
frozen_rels = [
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

marker = 'EDGEPLACEMENTGATE1A_RENDERGRID'
if marker in renderer:
    raise SystemExit('EDGEPLACEMENTGATE1A renderer marker already present; refuse ambiguous reapply')

call_anchor = '            bitmap = out.bitmap;\n\n            String dngName = dngPath.getFileName().toString();\n'
if call_anchor not in renderer:
    raise SystemExit('EDGEPLACEMENTGATE1A finished-bitmap call anchor missing')
call_repl = r'''            bitmap = out.bitmap;

            // EDGEPLACEMENTGATE1A_RENDERGRID
            // Diagnostic-only scan of the already-finished, already-oriented bitmap.
            // No value produced here is allowed to feed TC20, render gain, SAT3, curve02,
            // BT.601/TG1, JPEG pixels, Camera2 or capture allocation in this build.
            out.diagnostics.put("edgePlacementGate1A", edgePlacementGate1ARenderGrid(bitmap));

            String dngName = dngPath.getFileName().toString();
'''
renderer = renderer.replace(call_anchor, call_repl, 1)

method_anchor = '    private static synchronized void ensureOpenCv() {\n'
if method_anchor not in renderer:
    raise SystemExit('EDGEPLACEMENTGATE1A helper insertion anchor missing')
helper = r'''    // EDGEPLACEMENTGATE1A_RENDERGRID: exact recovered M10-R Integral geometry.
    // Used strictly as a spatial diagnostic against the already-finished M9 bitmap.
    // Mask sum is 14160, matching research/m9edgeplacement1a_rendergrid.py.
    private static final int[] EDGEPLACEMENT_INTEGRAL_MASK = new int[] {
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

    private static JSONObject edgePlacementGate1ARenderGrid(Bitmap bitmap) {
        final long startedNs = System.nanoTime();
        JSONObject out = new JSONObject();
        try {
            out.put("schema", "m9cam.edgeplacementgate.v1a.rendergrid");
            out.put("mode", "diagnostic_only_finished_bitmap_no_pixel_mutation");
            out.put("liveLiftEnabled", false);
            out.put("gateDecisionAvailableInRenderer", false);
            out.put("combinationPolicy", "combine_with_capture_M9_json_preview_grid_and_achieved_intent_offline");
            out.put("gridRows", 16);
            out.put("gridColumns", 22);
            out.put("regionRows", 4);
            out.put("regionColumns", 6);
            out.put("integralMaskSum", 14160);
            out.put("lumaFormula", "exact_bt601_q14_(4899R+9617G+1868B)>>14");
            out.put("sampling", "all_finished_bitmap_pixels_streamed_in_64_row_blocks");

            if (bitmap == null || bitmap.isRecycled()) {
                out.put("valid", false);
                out.put("reason", "finished_bitmap_missing");
                out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
                return out;
            }
            final int width = bitmap.getWidth();
            final int height = bitmap.getHeight();
            if (width <= 0 || height <= 0) {
                out.put("valid", false);
                out.put("reason", "finished_bitmap_dimensions_invalid");
                out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
                return out;
            }

            final int gridRows = 16;
            final int gridCols = 22;
            final int regionRows = 4;
            final int regionCols = 6;
            final long[] gridSums = new long[gridRows * gridCols];
            final long[] gridCounts = new long[gridRows * gridCols];
            final long[] regionHist = new long[regionRows * regionCols * 256];

            final int scanRows = Math.min(64, height);
            final int[] pixels = new int[Math.multiplyExact(width, scanRows)];
            for (int y0 = 0; y0 < height; y0 += scanRows) {
                final int rows = Math.min(scanRows, height - y0);
                bitmap.getPixels(pixels, 0, width, 0, y0, width, rows);
                for (int ly = 0; ly < rows; ly++) {
                    final int y = y0 + ly;
                    final int gy = Math.min(gridRows - 1, (y * gridRows) / height);
                    final int rr = Math.min(regionRows - 1, (y * regionRows) / height);
                    final int rowBase = ly * width;
                    for (int x = 0; x < width; x++) {
                        final int p = pixels[rowBase + x];
                        final int r = (p >>> 16) & 0xff;
                        final int g = (p >>> 8) & 0xff;
                        final int b = p & 0xff;
                        final int yy = (4899 * r + 9617 * g + 1868 * b) >> 14;

                        final int gx = Math.min(gridCols - 1, (x * gridCols) / width);
                        final int gi = gy * gridCols + gx;
                        gridSums[gi] += yy;
                        gridCounts[gi]++;

                        final int rc = Math.min(regionCols - 1, (x * regionCols) / width);
                        final int ri = rr * regionCols + rc;
                        regionHist[(ri << 8) + yy]++;
                    }
                }
            }

            final double[] grid = new double[gridRows * gridCols];
            double gridMean = 0.0;
            for (int i = 0; i < grid.length; i++) {
                grid[i] = gridCounts[i] > 0 ? gridSums[i] / (double)gridCounts[i] : 0.0;
                gridMean += grid[i];
            }
            gridMean /= grid.length;

            double integralWeighted = 0.0;
            long maskSum = 0L;
            for (int i = 0; i < grid.length; i++) {
                final int weight = EDGEPLACEMENT_INTEGRAL_MASK[i];
                integralWeighted += grid[i] * weight;
                maskSum += weight;
            }
            if (maskSum != 14160L) throw new IllegalStateException("bad EDGEPLACEMENT Integral mask sum " + maskSum);
            integralWeighted /= maskSum;

            final double[] meanRegions = edgePlacementRegions4x6(grid);
            final double center8 = edgePlacementRectMean(meanRegions, 1, 3, 1, 5);
            final double lower12 = edgePlacementRectMean(meanRegions, 2, 4, 0, 6);
            final double upper6 = edgePlacementRectMean(meanRegions, 0, 1, 0, 6);
            final double edge16 = edgePlacementEdgeMean(meanRegions, true);
            final double inner8 = edgePlacementEdgeMean(meanRegions, false);

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
                medians[region] = edgePlacementHistogramQuantile(regionHist, off, n, 0.50);
                q95s[region] = edgePlacementHistogramQuantile(regionHist, off, n, 0.95);
                dark64[region] = n > 0 ? darkN / (double)n : 0.0;
            }

            final double cellMedianP25 = edgePlacementQuantile(medians, 0.25);
            final double cellMedianP50 = edgePlacementQuantile(medians, 0.50);
            final double cellMedianP75 = edgePlacementQuantile(medians, 0.75);
            final double cellQ95P50 = edgePlacementQuantile(q95s, 0.50);
            final double cellQ95P75 = edgePlacementQuantile(q95s, 0.75);
            final double cellDark64P50 = edgePlacementQuantile(dark64, 0.50);
            final double cellDark64P75 = edgePlacementQuantile(dark64, 0.75);

            out.put("valid", true);
            out.put("reason", "finished_render_geometry_recorded_no_live_gate_or_lift");
            out.put("bitmapWidth", width);
            out.put("bitmapHeight", height);
            out.put("renderGridMeanY", gridMean);
            out.put("renderIntegralY", integralWeighted);
            out.put("renderIntegralVsMeanEv", edgePlacementLog2Ratio(integralWeighted, gridMean));
            out.put("renderRegionalMedianY", edgePlacementQuantile(meanRegions, 0.50));
            out.put("renderCenter8Y", center8);
            out.put("renderLower12Y", lower12);
            out.put("renderUpper6Y", upper6);
            out.put("renderEdge16Y", edge16);
            out.put("renderInner8Y", inner8);
            out.put("renderUpperVsLowerEv", edgePlacementLog2Ratio(upper6, lower12));
            out.put("renderCenterOverIntegralEv", edgePlacementLog2Ratio(center8, integralWeighted));
            out.put("renderInnerVsEdgeEv", edgePlacementLog2Ratio(inner8, edge16));
            out.put("renderCellMedianP25", cellMedianP25);
            out.put("renderCellMedianP50", cellMedianP50);
            out.put("renderCellMedianP75", cellMedianP75);
            out.put("renderCellQ95P50", cellQ95P50);
            out.put("renderCellQ95P75", cellQ95P75);
            out.put("renderCellDark64P50", cellDark64P50);
            out.put("renderCellDark64P75", cellDark64P75);
            out.put("renderGrid16x22", edgePlacementGridJson(grid));
            out.put("renderMeanRegions4x6", edgePlacementArrayJson(meanRegions));
            out.put("renderMedian4x6", edgePlacementArrayJson(medians));
            out.put("renderQ95_4x6", edgePlacementArrayJson(q95s));
            out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
        } catch (Throwable t) {
            try {
                out.put("valid", false);
                out.put("reason", "edgeplacementgate1a_rendergrid_exception");
                out.put("error", t.toString());
                out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static double[] edgePlacementRegions4x6(double[] grid) {
        if (grid == null || grid.length != 16 * 22) throw new IllegalArgumentException("bad EDGEPLACEMENT grid");
        final double[] out = new double[24];
        for (int rr = 0; rr < 4; rr++) {
            final int r0 = rr * 16 / 4;
            final int r1 = (rr + 1) * 16 / 4;
            for (int cc = 0; cc < 6; cc++) {
                final int c0 = cc * 22 / 6;
                final int c1 = (cc + 1) * 22 / 6;
                double sum = 0.0;
                int n = 0;
                for (int r = r0; r < r1; r++) {
                    for (int c = c0; c < c1; c++) {
                        sum += grid[r * 22 + c];
                        n++;
                    }
                }
                out[rr * 6 + cc] = n > 0 ? sum / n : 0.0;
            }
        }
        return out;
    }

    private static double edgePlacementRectMean(double[] regions, int r0, int r1, int c0, int c1) {
        double sum = 0.0;
        int n = 0;
        for (int r = r0; r < r1; r++) {
            for (int c = c0; c < c1; c++) {
                sum += regions[r * 6 + c];
                n++;
            }
        }
        return n > 0 ? sum / n : 0.0;
    }

    private static double edgePlacementEdgeMean(double[] regions, boolean edge) {
        double sum = 0.0;
        int n = 0;
        for (int r = 0; r < 4; r++) {
            for (int c = 0; c < 6; c++) {
                boolean isEdge = r == 0 || r == 3 || c == 0 || c == 5;
                if (isEdge == edge) {
                    sum += regions[r * 6 + c];
                    n++;
                }
            }
        }
        return n > 0 ? sum / n : 0.0;
    }

    private static double edgePlacementHistogramQuantile(long[] hist, int off, long n, double q) {
        if (n <= 0) return 0.0;
        final double pos = (n - 1) * q;
        final long lo = (long)Math.floor(pos);
        final long hi = (long)Math.ceil(pos);
        final double vlo = edgePlacementHistogramRank(hist, off, lo);
        final double vhi = edgePlacementHistogramRank(hist, off, hi);
        return vlo + (pos - lo) * (vhi - vlo);
    }

    private static int edgePlacementHistogramRank(long[] hist, int off, long rank) {
        long acc = 0L;
        for (int code = 0; code < 256; code++) {
            acc += hist[off + code];
            if (rank < acc) return code;
        }
        return 255;
    }

    private static double edgePlacementQuantile(double[] values, double q) {
        if (values == null || values.length == 0) return 0.0;
        double[] sorted = values.clone();
        Arrays.sort(sorted);
        final double pos = (sorted.length - 1) * q;
        final int lo = (int)Math.floor(pos);
        final int hi = (int)Math.ceil(pos);
        return sorted[lo] + (pos - lo) * (sorted[hi] - sorted[lo]);
    }

    private static double edgePlacementLog2Ratio(double a, double b) {
        final double aa = Math.max(a, 1.0e-6);
        final double bb = Math.max(b, 1.0e-6);
        return Math.log(aa / bb) / Math.log(2.0);
    }

    private static org.json.JSONArray edgePlacementArrayJson(double[] values) {
        org.json.JSONArray out = new org.json.JSONArray();
        if (values != null) for (double v : values) out.put(v);
        return out;
    }

    private static org.json.JSONArray edgePlacementGridJson(double[] grid) {
        org.json.JSONArray rows = new org.json.JSONArray();
        if (grid == null || grid.length != 16 * 22) return rows;
        for (int r = 0; r < 16; r++) {
            org.json.JSONArray row = new org.json.JSONArray();
            for (int c = 0; c < 22; c++) row.put(grid[r * 22 + c]);
            rows.put(row);
        }
        return rows;
    }

'''
renderer = renderer.replace(method_anchor, helper + method_anchor, 1)
write(renderer_rel, renderer)

# Distinguishable APK identity only. Photographic/capture constants are untouched.
if '-edgeplacementgate1a' not in gradle:
    version_re = re.compile(r"(versionName\s+['\"])([^'\"]+)(['\"])")
    m = version_re.search(gradle)
    if not m:
        raise SystemExit('EDGEPLACEMENTGATE1A versionName anchor missing')
    value = m.group(2)
    gradle = gradle[:m.start(2)] + value + '-edgeplacementgate1a' + gradle[m.end(2):]
    write(gradle_rel, gradle)

for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit('EDGEPLACEMENTGATE1A frozen photographic/capture seam changed: ' + rel)

print('M9Cam EDGEPLACEMENTGATE1A diagnostic overlay applied')
print(' - finished oriented bitmap scanned only after frozen renderCore returns')
print(' - exact BT.601 Q14 Y + 16x22 Integral geometry + 4x6 direct medians recorded')
print(' - no gate output feeds pixels; liveLiftEnabled=false')
print(' - capture AE, TC20, native color, SAT3, curve02, BT601/TG1, JPEG95 and metadata frozen')
