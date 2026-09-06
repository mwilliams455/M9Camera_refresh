#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-edgeplacementbestfit2a-live1.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('BESTFIT2A LIVE1 missing expected file: ' + rel)
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
store_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java'
gradle_rel = 'app/build.gradle'
renderer = read(renderer_rel)
store = read(store_rel)
gradle = read(gradle_rel)

if 'M9EdgePlacementGate1ADiagnostic' not in read('app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderedLumaDiagnostic.java'):
    raise SystemExit('BESTFIT2A LIVE1 requires EDGEPLACEMENTGATE1A diagnostic baseline')
if '-metadatafix1a-edgeplacementgate1a' not in gradle:
    raise SystemExit('BESTFIT2A LIVE1 requires EDGEPLACEMENTGATE1A build identity')
if 'm9cam.sidecarspool.v1.privatebundle1b' not in read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'):
    raise SystemExit('BESTFIT2A LIVE1 requires SIDECAR1B immutable capture-sidecar baseline')

# The controller is intentionally JPEG-render-only. Freeze capture allocation, TC20 implementation,
# native colour math, DNG/JPEG persistence helpers and metadata finalization byte-for-byte.
frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

# -----------------------------------------------------------------------------
# 1) Capture-specific immutable snapshot bridge.
# SIDECAR1B persistence is unchanged; this adds a second bounded in-memory copy consumed only
# by the matching asynchronous renderer so selector decisions cannot read a later shutter.
# -----------------------------------------------------------------------------
if 'BESTFIT2A_RENDER_SNAPSHOT_BRIDGE' not in store:
    import_anchor = 'import java.nio.file.Path;\n'
    if import_anchor not in store:
        raise SystemExit('BESTFIT2A LIVE1 metadata-store import anchor missing')
    store = store.replace(import_anchor,
        import_anchor + 'import java.util.LinkedHashMap;\nimport java.util.Map;\n', 1)

    field_anchor = '    private static final ConcurrentHashMap<String, byte[]> STAGED = new ConcurrentHashMap<>();\n'
    fields = '''    private static final ConcurrentHashMap<String, byte[]> STAGED = new ConcurrentHashMap<>();
    // BESTFIT2A_RENDER_SNAPSHOT_BRIDGE
    // Independent bounded immutable copy for the asynchronous JPEG renderer. Public/private
    // sidecar persistence keeps its original STAGED ownership and timing.
    private static final Object RENDER_SNAPSHOT_LOCK = new Object();
    private static final int MAX_RENDER_SNAPSHOTS = 32;
    private static final LinkedHashMap<String, byte[]> RENDER_SNAPSHOTS = new LinkedHashMap<>();
'''
    if field_anchor not in store:
        raise SystemExit('BESTFIT2A LIVE1 metadata-store field anchor missing')
    store = store.replace(field_anchor, fields, 1)

    stage_old = '''    public static boolean stage(Path jsonPath, byte[] bytes) {
        if (jsonPath == null || bytes == null) return false;
        STAGED.put(jsonPath.toString(), bytes);
        return true;
    }
'''
    stage_new = '''    public static boolean stage(Path jsonPath, byte[] bytes) {
        if (jsonPath == null || bytes == null) return false;
        final String key = jsonPath.toString();
        final byte[] persistedCopy = bytes.clone();
        STAGED.put(key, persistedCopy);
        synchronized (RENDER_SNAPSHOT_LOCK) {
            RENDER_SNAPSHOTS.put(key, bytes.clone());
            while (RENDER_SNAPSHOTS.size() > MAX_RENDER_SNAPSHOTS) {
                java.util.Iterator<Map.Entry<String, byte[]>> it = RENDER_SNAPSHOTS.entrySet().iterator();
                if (!it.hasNext()) break;
                it.next();
                it.remove();
            }
        }
        return true;
    }
'''
    if stage_old not in store:
        raise SystemExit('BESTFIT2A LIVE1 metadata-store stage anchor missing')
    store = store.replace(stage_old, stage_new, 1)

    sidecar_anchor = '''    public static boolean persistAsyncForDng(Path dngPath) {
'''
    consume = '''    /** Consume the exact immutable capture snapshot matching this DNG render job. */
    public static byte[] consumeRenderSnapshotForDng(Path dngPath) {
        Path jsonPath = sidecarPath(dngPath);
        if (jsonPath == null) return null;
        synchronized (RENDER_SNAPSHOT_LOCK) {
            return RENDER_SNAPSHOTS.remove(jsonPath.toString());
        }
    }

'''
    if sidecar_anchor not in store:
        raise SystemExit('BESTFIT2A LIVE1 metadata-store consume anchor missing')
    store = store.replace(sidecar_anchor, consume + sidecar_anchor, 1)

    discard_old = '''    public static void discardForDng(Path dngPath) {
        Path jsonPath = sidecarPath(dngPath);
        if (jsonPath != null) STAGED.remove(jsonPath.toString());
    }
'''
    discard_new = '''    public static void discardForDng(Path dngPath) {
        Path jsonPath = sidecarPath(dngPath);
        if (jsonPath == null) return;
        final String key = jsonPath.toString();
        STAGED.remove(key);
        synchronized (RENDER_SNAPSHOT_LOCK) {
            RENDER_SNAPSHOTS.remove(key);
        }
    }
'''
    if discard_old not in store:
        raise SystemExit('BESTFIT2A LIVE1 metadata-store discard anchor missing')
    store = store.replace(discard_old, discard_new, 1)
    write(store_rel, store)
else:
    raise SystemExit('BESTFIT2A LIVE1 snapshot bridge already present; refuse ambiguous reapply')

# -----------------------------------------------------------------------------
# 2) Exact research selector + bounded JPEG-only treatment helper.
# -----------------------------------------------------------------------------
helper_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9EdgePlacementBestFit2AController.java'
if (root / helper_rel).exists():
    raise SystemExit('BESTFIT2A LIVE1 helper already exists; refuse ambiguous reapply')

helper = r'''package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Bitmap;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Iterator;

/**
 * EDGEPLACEMENTBESTFIT2A LIVE1.
 *
 * Rare JPEG-render exception controller only. Capture exposure, Photon allocation, TC20's
 * baseline decision, DNG bytes, H25/HSM, SAT3, curve02 and native colour equations are not
 * changed. Missing/ambiguous evidence always resolves to HOLD.
 */
public final class M9EdgePlacementBestFit2AController {
    public static final String SCHEMA = "m9cam.edgeplacementbestfit.v2a.live1";

    private static final double A_INTENT_MIN_EV = 0.10;
    private static final double A_UL_SHIFT_MIN_EV = 1.50;
    private static final double A_P75_MAX_Y = 30.0;
    private static final double A_INTEGRAL_SHIFT_MAX_EV = 0.15;

    private static final double B_INTENT_MAX_EV = 0.10;
    private static final double B_SCENE_SPREAD_MIN_EV = 1.30;
    private static final double B_BRIGHT_REGION_MIN = 0.20;
    private static final double B_P75_MAX_Y = 15.0;
    private static final double B_GRID_MEAN_MAX_Y = 30.0;
    private static final double B_RETENTION_MAX_EV = -1.50;
    private static final int B_MIN_COLLAPSED = 3;

    private static final double C_UL_SHIFT_MIN_EV = 1.20;
    private static final double C_LOWER_MAX_Y = 18.0;
    private static final double C_UPPER_MIN_Y = 140.0;
    private static final double C_P75_MIN_Y = 120.0;
    private static final double C_CENTER_RETENTION_MIN_EV = -1.00;

    private static final double BRIGHT_SCORE_MIN = 0.60;
    private static final double BRIGHT_GAIN_MIN = 1.50;
    private static final double BRIGHT_FINISHED_MEDIAN_MIN_Y = 75.0;
    private static final double BRIGHT_INTENT_MAX_EV = 0.10;

    private static final double LOCAL_Q95_MIN_Y = 220.0;
    private static final double LOCAL_MINUS_GLOBAL_Q95_MIN_Y = 80.0;

    public static final double DARK_Q95_CEILING_Y = 242.0;
    public static final double DARK_BRIGHT224_DELTA_MAX = 0.040;
    public static final double BRIGHT_PIVOT = 0.85;
    public static final double BRIGHT_MILD_STRENGTH = 0.15;

    private M9EdgePlacementBestFit2AController() {}

    public static JSONObject evaluate(JSONObject capture, JSONObject renderer, JSONObject direct) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "jpeg_render_exception_controller_capture_tc20_dng_frozen");
            out.put("captureMutation", false);
            out.put("tc20BaselineMutation", false);
            out.put("dngMutation", false);
            out.put("thresholdStatus", "experimental_live_from_completed_bestfit1a_falsification");
            if (capture == null || renderer == null || direct == null || !direct.optBoolean("valid", false)) {
                out.put("selector", "HOLD");
                out.put("eligible", false);
                out.put("reason", "missing_capture_renderer_or_frozen_luma_fail_safe_hold");
                return out;
            }

            JSONObject audit = capture.optJSONObject("m9ExposureAudit");
            JSONObject derived = audit != null ? audit.optJSONObject("derived") : null;
            double intent = optDouble(derived, "captureEnergyVsPhotonOnlyEv");
            if (!finite(intent)) intent = optDouble(derived, "captureEnergyVsPreviewEv");

            JSONObject mfm = capture.optJSONObject("m9M10rMfmTest");
            JSONObject subject = capture.optJSONObject("subjectMotion");
            JSONObject previewLuma = subject != null ? subject.optJSONObject("previewLuma") : null;
            JSONObject previewGlobal = previewLuma != null ? previewLuma.optJSONObject("global") : null;
            JSONObject gate = direct.optJSONObject("edgePlacementGate1A");
            JSONObject finishedGlobal = direct.optJSONObject("global");

            double previewGridMean = previewGridMean(previewLuma);
            double previewIntegral = optDouble(mfm, "integralY");
            double previewIntegralVsMean = log2Ratio(previewIntegral, previewGridMean);
            double renderIntegralVsMean = optDouble(gate, "renderIntegralVsMeanEv");
            double integralShift = subtract(renderIntegralVsMean, previewIntegralVsMean);
            double previewUL = optDouble(mfm, "upperVsLowerEv");
            double renderUL = optDouble(gate, "renderUpperVsLowerEv");
            double ulShift = subtract(renderUL, previewUL);

            double centerRetention = log2Ratio(optDouble(gate, "renderCenter8Y"), optDouble(mfm, "center8Y"));
            double lowerRetention = log2Ratio(optDouble(gate, "renderLower12Y"), optDouble(mfm, "lower12Y"));
            double upperRetention = log2Ratio(optDouble(gate, "renderUpper6Y"), optDouble(mfm, "upper6Y"));
            double edgeRetention = log2Ratio(optDouble(gate, "renderEdge16Y"), optDouble(mfm, "edge16Y"));
            int collapsed = 0;
            if (finite(centerRetention) && centerRetention <= B_RETENTION_MAX_EV) collapsed++;
            if (finite(lowerRetention) && lowerRetention <= B_RETENTION_MAX_EV) collapsed++;
            if (finite(upperRetention) && upperRetention <= B_RETENTION_MAX_EV) collapsed++;
            if (finite(edgeRetention) && edgeRetention <= B_RETENTION_MAX_EV) collapsed++;

            double p75 = optDouble(gate, "renderCellMedianP75");
            double renderGridMean = optDouble(gate, "renderGridMeanY");
            double sceneSpread = optDouble(mfm, "sceneSpreadEv");
            double brightRegion = optDouble(mfm, "brightRegionFraction");

            boolean a = ge(intent, A_INTENT_MIN_EV)
                    && ge(ulShift, A_UL_SHIFT_MIN_EV)
                    && le(p75, A_P75_MAX_Y)
                    && le(integralShift, A_INTEGRAL_SHIFT_MAX_EV);
            boolean b = lt(intent, B_INTENT_MAX_EV)
                    && ge(sceneSpread, B_SCENE_SPREAD_MIN_EV)
                    && ge(brightRegion, B_BRIGHT_REGION_MIN)
                    && le(p75, B_P75_MAX_Y)
                    && le(renderGridMean, B_GRID_MEAN_MAX_Y)
                    && collapsed >= B_MIN_COLLAPSED;
            boolean c = ge(ulShift, C_UL_SHIFT_MIN_EV)
                    && le(optDouble(gate, "renderLower12Y"), C_LOWER_MAX_Y)
                    && ge(optDouble(gate, "renderUpper6Y"), C_UPPER_MIN_Y)
                    && ge(p75, C_P75_MIN_Y)
                    && ge(centerRetention, C_CENTER_RETENTION_MIN_EV);

            JSONObject center = direct.optJSONObject("center50");
            JSONObject middle = direct.optJSONObject("middleCenter33");
            double globalQ95 = optDouble(finishedGlobal, "q95");
            double centerQ95 = optDouble(center, "q95");
            double middleQ95 = optDouble(middle, "q95");
            double localQ95 = maxFinite(centerQ95, middleQ95);
            double localConcentration = subtract(localQ95, globalQ95);
            boolean subjectSurvival = ge(localQ95, LOCAL_Q95_MIN_Y)
                    && ge(localConcentration, LOCAL_MINUS_GLOBAL_Q95_MIN_Y);

            double structuralScore = findFirstNumber(capture, "structuralLowKeyScore");
            double appliedGain = optDouble(renderer, "gain");
            double finishedMedian = optDouble(finishedGlobal, "median");
            double previewMedian = optDouble(previewGlobal, "median");
            double previewQ95 = optDouble(previewGlobal, "q95");
            double medianShift = log2Ratio(finishedMedian, previewMedian);
            double q95Shift = log2Ratio(globalQ95, previewQ95);
            boolean lowkey = lt(intent, BRIGHT_INTENT_MAX_EV)
                    && ge(structuralScore, BRIGHT_SCORE_MIN)
                    && ge(appliedGain, BRIGHT_GAIN_MIN)
                    && ge(finishedMedian, BRIGHT_FINISHED_MEDIAN_MIN_Y);
            boolean broad = gt(medianShift, 0.0) && gt(q95Shift, 0.0);

            String selector = "HOLD";
            String reason = "no_edge_branch_matched";
            if (a) {
                selector = "DARK_INTENT";
                reason = "intent_collapse_conjunction";
            } else if (b) {
                if (subjectSurvival) {
                    selector = "HOLD";
                    reason = "zero_intent_collapse_vetoed_by_local_subject_survival";
                } else {
                    selector = "DARK_ZERO_INTENT";
                    reason = "zero_intent_collapse_conjunction";
                }
            } else if (c) {
                selector = "DARK_FOREGROUND";
                reason = "foreground_collapse_conjunction";
            } else if (lowkey && broad) {
                selector = "BRIGHT_LOWKEY_BROAD";
                reason = "coherent_lowkey_plus_actual_broad_opening";
            }

            out.put("selector", selector);
            out.put("eligible", !"HOLD".equals(selector));
            out.put("reason", reason);
            out.put("subjectSurvivalVeto", subjectSurvival);
            out.put("branchAIntentCollapse", a);
            out.put("branchBZeroIntentCollapse", b);
            out.put("branchCForegroundCollapse", c);
            out.put("brightLowkey", lowkey);
            out.put("brightBroadOpening", broad);
            putFinite(out, "achievedIntentEv", intent);
            putFinite(out, "structuralLowKeyScore", structuralScore);
            putFinite(out, "tc20AppliedGain", appliedGain);
            putFinite(out, "finishedGlobalMedianY", finishedMedian);
            putFinite(out, "finishedGlobalQ95Y", globalQ95);
            putFinite(out, "previewGlobalMedianY", previewMedian);
            putFinite(out, "previewGlobalQ95Y", previewQ95);
            putFinite(out, "medianShiftEv", medianShift);
            putFinite(out, "q95ShiftEv", q95Shift);
            putFinite(out, "upperLowerShiftEv", ulShift);
            putFinite(out, "integralRelativeShiftEv", integralShift);
            putFinite(out, "renderCellMedianP75", p75);
            putFinite(out, "renderGridMeanY", renderGridMean);
            putFinite(out, "centerRetentionEv", centerRetention);
            putFinite(out, "lowerRetentionEv", lowerRetention);
            putFinite(out, "upperRetentionEv", upperRetention);
            putFinite(out, "edgeRetentionEv", edgeRetention);
            out.put("collapsedRetentionRegions", collapsed);
            putFinite(out, "localQ95", localQ95);
            putFinite(out, "localMinusGlobalQ95", localConcentration);
        } catch (Throwable t) {
            try {
                out.put("selector", "HOLD");
                out.put("eligible", false);
                out.put("reason", "selector_exception_fail_safe_hold");
                out.put("error", t.toString());
            } catch (Exception ignored) {}
        }
        return out;
    }

    public static double[] darkLadder(String selector) {
        if ("DARK_INTENT".equals(selector) || "DARK_ZERO_INTENT".equals(selector)) {
            return new double[] {0.50, 0.35, 0.25, 0.15};
        }
        if ("DARK_FOREGROUND".equals(selector)) {
            return new double[] {0.25, 0.15};
        }
        return new double[0];
    }

    /** Sparse safety probe using the same finished-code luma formula as RENDERMETER1B. */
    public static JSONObject measureSparseLuma(Bitmap bitmap) {
        JSONObject out = new JSONObject();
        try {
            if (bitmap == null || bitmap.isRecycled() || bitmap.getWidth() <= 0 || bitmap.getHeight() <= 0) {
                out.put("valid", false);
                return out;
            }
            int w = bitmap.getWidth(), h = bitmap.getHeight();
            int sw = w >= h ? 64 : Math.max(1, (int)Math.round(64.0 * w / h));
            int sh = w >= h ? Math.max(1, (int)Math.round(64.0 * h / w)) : 64;
            int[] hist = new int[256];
            int count = 0;
            for (int sy = 0; sy < sh; sy++) {
                int py = Math.min(h - 1, (int)(((2L * sy + 1L) * h) / (2L * sh)));
                for (int sx = 0; sx < sw; sx++) {
                    int px = Math.min(w - 1, (int)(((2L * sx + 1L) * w) / (2L * sw)));
                    int p = bitmap.getPixel(px, py);
                    int r = (p >>> 16) & 255, g = (p >>> 8) & 255, b = p & 255;
                    int y = (77 * r + 150 * g + 29 * b + 128) >> 8;
                    hist[Math.max(0, Math.min(255, y))]++;
                    count++;
                }
            }
            int q95 = percentile(hist, count, 0.95);
            int bright224 = 0;
            for (int i = 224; i < 256; i++) bright224 += hist[i];
            out.put("valid", count > 0);
            out.put("sampleCount", count);
            out.put("q95", q95);
            out.put("brightFractionGE224", count > 0 ? bright224 / (double)count : 0.0);
        } catch (Throwable t) {
            try { out.put("valid", false); out.put("error", t.toString()); } catch (Exception ignored) {}
        }
        return out;
    }

    public static boolean acceptDarkCandidate(JSONObject frozenDirect, JSONObject candidateSparse) {
        if (frozenDirect == null || candidateSparse == null || !candidateSparse.optBoolean("valid", false)) return false;
        JSONObject g = frozenDirect.optJSONObject("global");
        if (g == null) return false;
        double baselineBright224 = optDouble(g, "brightFractionGE224");
        double q95 = optDouble(candidateSparse, "q95");
        double bright224 = optDouble(candidateSparse, "brightFractionGE224");
        return finite(baselineBright224) && finite(q95) && finite(bright224)
                && q95 <= DARK_Q95_CEILING_Y
                && (bright224 - baselineBright224) <= DARK_BRIGHT224_DELTA_MAX + 1e-12;
    }

    /** Exact prospective RGB-pivot operator. Returns a new mutable bitmap; source is untouched. */
    public static Bitmap applyBrightPivot(Bitmap source, double strength) {
        if (source == null || source.isRecycled()) return null;
        Bitmap out = source.copy(Bitmap.Config.ARGB_8888, true);
        if (out == null) return null;
        final int width = out.getWidth(), height = out.getHeight();
        final int rowsPerBlock = Math.min(64, height);
        final int[] pixels = new int[Math.multiplyExact(width, rowsPerBlock)];
        final double[] scale = new double[256];
        for (int y = 0; y < 256; y++) {
            double yn = y / 255.0;
            double weight = Math.max(0.0, Math.min(1.0, 1.0 - yn / BRIGHT_PIVOT));
            scale[y] = Math.pow(2.0, -strength * weight);
        }
        for (int y0 = 0; y0 < height; y0 += rowsPerBlock) {
            int rows = Math.min(rowsPerBlock, height - y0);
            out.getPixels(pixels, 0, width, 0, y0, width, rows);
            int n = width * rows;
            for (int i = 0; i < n; i++) {
                int p = pixels[i];
                int a = (p >>> 24) & 255;
                int r = (p >>> 16) & 255, g = (p >>> 8) & 255, b = p & 255;
                int y = (4899 * r + 9617 * g + 1868 * b) >> 14;
                double s = scale[Math.max(0, Math.min(255, y))];
                int rr = clamp8((int)Math.rint(r * s));
                int gg = clamp8((int)Math.rint(g * s));
                int bb = clamp8((int)Math.rint(b * s));
                pixels[i] = (a << 24) | (rr << 16) | (gg << 8) | bb;
            }
            out.setPixels(pixels, 0, width, 0, y0, width, rows);
        }
        return out;
    }

    private static int percentile(int[] hist, int count, double p) {
        if (count <= 0) return 0;
        int target = Math.max(1, (int)Math.ceil(p * count));
        int acc = 0;
        for (int i = 0; i < hist.length; i++) { acc += hist[i]; if (acc >= target) return i; }
        return 255;
    }

    private static int clamp8(int x) { return Math.max(0, Math.min(255, x)); }

    private static double previewGridMean(JSONObject previewLuma) {
        if (previewLuma == null) return Double.NaN;
        Object raw = previewLuma.opt("m10rAeGrid16x22");
        JSONArray rows = null;
        if (raw instanceof JSONObject) {
            JSONObject obj = (JSONObject)raw;
            rows = obj.optJSONArray("rows");
            if (rows == null) rows = obj.optJSONArray("grid");
        } else if (raw instanceof JSONArray) {
            rows = (JSONArray)raw;
        }
        if (rows == null) return Double.NaN;
        double sum = 0.0; int n = 0;
        for (int r = 0; r < rows.length(); r++) {
            JSONArray row = rows.optJSONArray(r);
            if (row == null) continue;
            for (int c = 0; c < row.length(); c++) {
                double v = row.optDouble(c, Double.NaN);
                if (finite(v)) { sum += v; n++; }
            }
        }
        return n > 0 ? sum / n : Double.NaN;
    }

    private static double findFirstNumber(Object root, String key) {
        if (root instanceof JSONObject) {
            JSONObject o = (JSONObject)root;
            if (o.has(key)) {
                double v = o.optDouble(key, Double.NaN);
                if (finite(v)) return v;
            }
            Iterator<String> it = o.keys();
            while (it.hasNext()) {
                Object child = o.opt(it.next());
                double v = findFirstNumber(child, key);
                if (finite(v)) return v;
            }
        } else if (root instanceof JSONArray) {
            JSONArray a = (JSONArray)root;
            for (int i = 0; i < a.length(); i++) {
                double v = findFirstNumber(a.opt(i), key);
                if (finite(v)) return v;
            }
        }
        return Double.NaN;
    }

    private static double optDouble(JSONObject o, String key) {
        return o != null ? o.optDouble(key, Double.NaN) : Double.NaN;
    }
    private static double subtract(double a, double b) {
        return finite(a) && finite(b) ? a - b : Double.NaN;
    }
    private static double log2Ratio(double a, double b) {
        return finite(a) && finite(b) && a > 0.0 && b > 0.0 ? Math.log(a / b) / Math.log(2.0) : Double.NaN;
    }
    private static double maxFinite(double a, double b) {
        if (finite(a) && finite(b)) return Math.max(a, b);
        if (finite(a)) return a;
        if (finite(b)) return b;
        return Double.NaN;
    }
    private static boolean finite(double x) { return !Double.isNaN(x) && !Double.isInfinite(x); }
    private static boolean ge(double x, double y) { return finite(x) && x >= y; }
    private static boolean gt(double x, double y) { return finite(x) && x > y; }
    private static boolean le(double x, double y) { return finite(x) && x <= y; }
    private static boolean lt(double x, double y) { return finite(x) && x < y; }
    private static void putFinite(JSONObject o, String key, double v) throws Exception { if (finite(v)) o.put(key, v); }
}
'''
write(helper_rel, helper)

# -----------------------------------------------------------------------------
# 3) Renderer: freeze baseline first, classify only after frozen JPEG bitmap exists.
# DARK candidates re-run the exact same renderer with a bounded gain offset; BRIGHT uses
# the exact prospective RGB-ratio-preserving 0.85-pivot transform. Frozen bitmap is held
# until a candidate is accepted. Any exception rolls back to Frozen.
# -----------------------------------------------------------------------------
renderer = read(renderer_rel)
if 'BESTFIT2A_LIVE1' in renderer:
    raise SystemExit('BESTFIT2A LIVE1 renderer already patched')

# imports
if 'import com.particlesdevs.photoncamera.m9.M9DeferredMetadataStore;' not in renderer:
    anchor = 'import com.particlesdevs.photoncamera.api.ParseExif;\n'
    if anchor not in renderer: raise SystemExit('BESTFIT2A renderer M9 import anchor missing')
    renderer = renderer.replace(anchor, anchor + 'import com.particlesdevs.photoncamera.m9.M9DeferredMetadataStore;\n', 1)
if 'import org.json.JSONArray;' not in renderer:
    renderer = renderer.replace('import org.json.JSONObject;\n', 'import org.json.JSONArray;\nimport org.json.JSONObject;\n', 1)
if 'import java.nio.charset.StandardCharsets;' not in renderer:
    renderer = renderer.replace('import java.nio.file.Files;\n', 'import java.nio.file.Files;\nimport java.nio.charset.StandardCharsets;\n', 1)

# Consume the capture-specific immutable snapshot before any deferred persistence can evict its other copy.
frame_anchor = '            if (frame == null || frame.buffer == null) throw new IllegalArgumentException("missing RAW frame");\n'
frame_insert = frame_anchor + '''            // BESTFIT2A_LIVE1 capture-specific immutable evidence bridge.
            final byte[] edgePlacementCaptureBytes = M9DeferredMetadataStore.consumeRenderSnapshotForDng(dngPath);
'''
if frame_anchor not in renderer:
    raise SystemExit('BESTFIT2A renderer frame anchor missing')
renderer = renderer.replace(frame_anchor, frame_insert, 1)

# First render is always the frozen baseline.
call_old = '''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation);
'''
call_new = '''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,
                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0);
'''
if call_old not in renderer:
    raise SystemExit('BESTFIT2A renderer baseline renderCore call anchor missing')
renderer = renderer.replace(call_old, call_new, 1)

# Replace the existing CAPTURESPLIT1B hook with classify/treat/rollback logic.
hook = '            out.diagnostics.put("directRenderedLuma", M9RenderedLumaDiagnostic.measure(bitmap));\n'
if hook not in renderer:
    raise SystemExit('BESTFIT2A renderer directRenderedLuma hook missing')
live_block = r'''            JSONObject frozenDirectLuma = M9RenderedLumaDiagnostic.measure(bitmap);
            out.diagnostics.put("directRenderedLuma", frozenDirectLuma);
            JSONObject edgeDecision;
            try {
                JSONObject captureEvidence = edgePlacementCaptureBytes != null
                        ? new JSONObject(new String(edgePlacementCaptureBytes, StandardCharsets.UTF_8)) : null;
                edgeDecision = M9EdgePlacementBestFit2AController.evaluate(captureEvidence, out.diagnostics, frozenDirectLuma);
            } catch (Throwable evidenceError) {
                edgeDecision = new JSONObject();
                edgeDecision.put("schema", M9EdgePlacementBestFit2AController.SCHEMA);
                edgeDecision.put("selector", "HOLD");
                edgeDecision.put("eligible", false);
                edgeDecision.put("reason", "capture_snapshot_parse_exception_fail_safe_hold");
                edgeDecision.put("error", evidenceError.toString());
            }
            edgeDecision.put("captureSnapshotAvailable", edgePlacementCaptureBytes != null);
            edgeDecision.put("applied", false);
            edgeDecision.put("treatment", "FROZEN");
            edgeDecision.put("appliedEv", 0.0);
            JSONArray edgeAttempts = new JSONArray();
            String edgeSelector = edgeDecision.optString("selector", "HOLD");

            if (edgeSelector.startsWith("DARK_")) {
                double[] ladder = M9EdgePlacementBestFit2AController.darkLadder(edgeSelector);
                for (double candidateEv : ladder) {
                    JSONObject attempt = new JSONObject();
                    attempt.put("candidateEv", candidateEv);
                    RenderCore candidateCore = null;
                    Bitmap candidateBitmap = null;
                    try {
                        long candidateStartedNs = System.nanoTime();
                        candidateCore = renderCore(frame.buffer, frame.width, frame.height,
                                encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, candidateEv);
                        candidateBitmap = candidateCore.bitmap;
                        JSONObject candidateSparse = M9EdgePlacementBestFit2AController.measureSparseLuma(candidateBitmap);
                        boolean safe = M9EdgePlacementBestFit2AController.acceptDarkCandidate(frozenDirectLuma, candidateSparse);
                        attempt.put("renderElapsedMs", (System.nanoTime() - candidateStartedNs) / 1_000_000.0);
                        attempt.put("q95Y", candidateSparse.optDouble("q95", Double.NaN));
                        attempt.put("brightFractionGE224", candidateSparse.optDouble("brightFractionGE224", Double.NaN));
                        attempt.put("accepted", safe);
                        edgeAttempts.put(attempt);
                        if (safe) {
                            if (bitmap != null && bitmap != candidateBitmap && !bitmap.isRecycled()) bitmap.recycle();
                            bitmap = candidateBitmap;
                            candidateBitmap = null;
                            edgeDecision.put("applied", true);
                            edgeDecision.put("treatment", "DARK_EXACT_RERENDER_GAIN_OFFSET");
                            edgeDecision.put("appliedEv", candidateEv);
                            break;
                        }
                    } catch (Throwable candidateError) {
                        attempt.put("accepted", false);
                        attempt.put("error", candidateError.toString());
                        edgeAttempts.put(attempt);
                        // A renderer exception is not a signal to try another photographic strength.
                        edgeDecision.put("rollbackReason", "candidate_render_exception_frozen_preserved");
                        break;
                    } finally {
                        if (candidateBitmap != null && !candidateBitmap.isRecycled()) candidateBitmap.recycle();
                    }
                }
                if (!edgeDecision.optBoolean("applied", false) && !edgeDecision.has("rollbackReason")) {
                    edgeDecision.put("rollbackReason", "no_dark_candidate_inside_highlight_budget");
                }
            } else if ("BRIGHT_LOWKEY_BROAD".equals(edgeSelector)) {
                Bitmap candidateBitmap = null;
                try {
                    candidateBitmap = M9EdgePlacementBestFit2AController.applyBrightPivot(
                            bitmap, M9EdgePlacementBestFit2AController.BRIGHT_MILD_STRENGTH);
                    if (candidateBitmap != null) {
                        if (bitmap != null && bitmap != candidateBitmap && !bitmap.isRecycled()) bitmap.recycle();
                        bitmap = candidateBitmap;
                        candidateBitmap = null;
                        edgeDecision.put("applied", true);
                        edgeDecision.put("treatment", "BRIGHT_RGB_PIVOT");
                        edgeDecision.put("appliedEv", -M9EdgePlacementBestFit2AController.BRIGHT_MILD_STRENGTH);
                        edgeDecision.put("strengthEv", M9EdgePlacementBestFit2AController.BRIGHT_MILD_STRENGTH);
                        edgeDecision.put("pivotYNormalized", M9EdgePlacementBestFit2AController.BRIGHT_PIVOT);
                    } else {
                        edgeDecision.put("rollbackReason", "bright_candidate_copy_failed_frozen_preserved");
                    }
                } catch (Throwable brightError) {
                    edgeDecision.put("rollbackReason", "bright_transform_exception_frozen_preserved");
                    edgeDecision.put("treatmentError", brightError.toString());
                } finally {
                    if (candidateBitmap != null && !candidateBitmap.isRecycled()) candidateBitmap.recycle();
                }
            }

            edgeDecision.put("attempts", edgeAttempts);
            if (edgeDecision.optBoolean("applied", false)) {
                // Keep exported renderer diagnostics truthful to the actual JPEG pixels.
                out.diagnostics.put("directRenderedLumaFrozen", frozenDirectLuma);
                JSONObject finalDirectLuma = M9RenderedLumaDiagnostic.measure(bitmap);
                out.diagnostics.put("directRenderedLuma", finalDirectLuma);
                JSONObject finalGlobal = finalDirectLuma.optJSONObject("global");
                if (finalGlobal != null) {
                    edgeDecision.put("finalGlobalMedianY", finalGlobal.optDouble("median", Double.NaN));
                    edgeDecision.put("finalGlobalQ95Y", finalGlobal.optDouble("q95", Double.NaN));
                    edgeDecision.put("finalBrightFractionGE224", finalGlobal.optDouble("brightFractionGE224", Double.NaN));
                }
            }
            out.diagnostics.put("edgePlacementBestFit2A", edgeDecision);
'''
renderer = renderer.replace(hook, live_block, 1)

# renderCore gains an explicit bounded render-only offset. TC20 meter computation and its logged
# baseline gain remain unchanged; only the native colour call receives effectiveRenderGain.
sig_old = '''    private static RenderCore renderCore(ByteBuffer rawBuffer,
                                         int width,
                                         int height,
                                         float[] black,
                                         int whiteLevel,
                                         float[] neutralF,
                                         int cameraRotation) throws Exception {
'''
sig_new = '''    private static RenderCore renderCore(ByteBuffer rawBuffer,
                                         int width,
                                         int height,
                                         float[] black,
                                         int whiteLevel,
                                         float[] neutralF,
                                         int cameraRotation,
                                         double edgePlacementGainEv) throws Exception {
'''
if sig_old not in renderer:
    raise SystemExit('BESTFIT2A renderer renderCore signature anchor missing')
renderer = renderer.replace(sig_old, sig_new, 1)

meter_anchor = '''            meterTc20ElapsedMs = (System.nanoTime() - meterStartedNs) / 1_000_000L;

            long fullRenderStartedNs = System.nanoTime();
'''
meter_insert = '''            meterTc20ElapsedMs = (System.nanoTime() - meterStartedNs) / 1_000_000L;
            // BESTFIT2A_LIVE1: bounded JPEG-render-only pre-curve gain offset. The TC20
            // decision itself is untouched and remains available as meter.gain.
            final double effectiveRenderGain = meter.gain * Math.pow(2.0, edgePlacementGainEv);

            long fullRenderStartedNs = System.nanoTime();
'''
if meter_anchor not in renderer:
    raise SystemExit('BESTFIT2A renderer meter/effective-gain anchor missing')
renderer = renderer.replace(meter_anchor, meter_insert, 1)

count_gain_calls = renderer.count('meter.gain, tgCbGain')
if count_gain_calls != 3:
    raise SystemExit(f'BESTFIT2A expected 3 native colour gain call sites, found {count_gain_calls}')
renderer = renderer.replace('meter.gain, tgCbGain', 'effectiveRenderGain, tgCbGain')

# Keep the legacy gain field as the untouched TC20 baseline; add explicit actual render gain fields.
diag_gain_anchor = '            d.put("gain", meter.gain);\n'
if diag_gain_anchor not in renderer:
    raise SystemExit('BESTFIT2A renderer gain diagnostic anchor missing')
renderer = renderer.replace(diag_gain_anchor,
    diag_gain_anchor + '            d.put("edgePlacementRenderGainEv", edgePlacementGainEv);\n'
                       '            d.put("edgePlacementEffectiveGain", effectiveRenderGain);\n', 1)
write(renderer_rel, renderer)

# Distinct APK identity only.
if '-bestfit2alive1' not in gradle:
    version_re = re.compile(r"(versionName\s+['\"])([^'\"]+)(['\"])")
    m = version_re.search(gradle)
    if not m:
        raise SystemExit('BESTFIT2A versionName anchor missing')
    gradle = gradle[:m.start(2)] + m.group(2) + '-bestfit2alive1' + gradle[m.end(2):]
    write(gradle_rel, gradle)

for rel, before in frozen_before.items():
    if sha(rel) != before:
        raise SystemExit('BESTFIT2A LIVE1 frozen non-render seam changed: ' + rel)

print('M9Cam EDGEPLACEMENTBESTFIT2A LIVE1 applied')
print(' - capture exposure / Photon allocator / TC20 baseline / native colour equations / DNG frozen')
print(' - capture-specific immutable sidecar snapshot bridge added for asynchronous renderer')
print(' - DARK_INTENT + DARK_ZERO_INTENT exact rerender ladders max +0.50 EV with highlight rollback')
print(' - DARK_FOREGROUND exact rerender ladder max +0.25 EV')
print(' - ZERO_INTENT local-subject-survival veto retained')
print(' - BRIGHT_LOWKEY_BROAD applies exact RGB-pivot strength 0.15 only')
print(' - HOLD or any exception preserves frozen JPEG pixels')
