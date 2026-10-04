#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-capturesplit1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CAPTURESPLIT1B missing expected file: {rel}')
    return p.read_text()

def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
coord_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
render_meter_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterDiagnostic.java'
meta_store_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java'
timing_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java'

if 'm9cam.sceneexposure.v8.renderaware1h' not in read(scene_rel):
    raise SystemExit('CAPTURESPLIT1B requires SCENEEXPOSURE1H')
if 'm9cam.exposuresplit.v1.capturemeter1a.temporal1a' not in read(coord_rel):
    raise SystemExit('CAPTURESPLIT1B requires CAPTURESPLIT1A')
if 'm9cam.rendermeter.v1.observational1a' not in read(render_meter_rel):
    raise SystemExit('CAPTURESPLIT1B requires RENDERMETER1A')

# Freeze all photographic/capture seams. 1B may read the finished bitmap and may alter
# development-sidecar persistence only; it must not mutate capture allocation, scene math,
# TC20/native colour, or the bitmap's pixels.
frozen_rels = [
    scene_rel,
    coord_rel,
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

# -----------------------------------------------------------------------------
# RENDERMETER1B: direct finished-bitmap luma sampling, observational only.
# -----------------------------------------------------------------------------
rendered_luma_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderedLumaDiagnostic.java'
rendered_luma = r'''package com.particlesdevs.photoncamera.m9.render;

import android.graphics.Bitmap;

import org.json.JSONObject;

/**
 * RENDERMETER1B direct display-bitmap luminance measurement.
 *
 * Reads a sparse nearest-neighbour grid from the already-finished ARGB_8888 bitmap.
 * It never writes pixels, never rescales/replaces the bitmap and never changes TC20.
 * The grid is capped at 64 samples on the long side to keep diagnostic overhead tiny.
 */
public final class M9RenderedLumaDiagnostic {
    public static final String SCHEMA = "m9cam.renderedluma.v1.grid64";
    private static final int SAMPLE_LONG_SIDE = 64;

    private M9RenderedLumaDiagnostic() {}

    public static JSONObject measure(Bitmap bitmap) {
        JSONObject out = new JSONObject();
        long startedNs = System.nanoTime();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "read_only_finished_bitmap_sampling");
            if (bitmap == null || bitmap.isRecycled() || bitmap.getWidth() <= 0 || bitmap.getHeight() <= 0) {
                out.put("valid", false);
                out.put("reason", "missing_or_recycled_bitmap");
                return out;
            }

            final int width = bitmap.getWidth();
            final int height = bitmap.getHeight();
            final boolean landscape = width >= height;
            final int sampleW = landscape ? SAMPLE_LONG_SIDE
                    : Math.max(1, (int)Math.round(SAMPLE_LONG_SIDE * (width / (double)height)));
            final int sampleH = landscape
                    ? Math.max(1, (int)Math.round(SAMPLE_LONG_SIDE * (height / (double)width)))
                    : SAMPLE_LONG_SIDE;

            Stats global = new Stats();
            Stats center50 = new Stats();
            Stats middleCenter33 = new Stats();

            for (int sy = 0; sy < sampleH; sy++) {
                int py = Math.min(height - 1,
                        (int)(((2L * sy + 1L) * height) / (2L * sampleH)));
                for (int sx = 0; sx < sampleW; sx++) {
                    int px = Math.min(width - 1,
                            (int)(((2L * sx + 1L) * width) / (2L * sampleW)));
                    int argb = bitmap.getPixel(px, py);
                    int r = (argb >>> 16) & 0xff;
                    int g = (argb >>> 8) & 0xff;
                    int b = argb & 0xff;
                    // Integer BT.601-style display luma proxy in finished sRGB code space.
                    int y = (77 * r + 150 * g + 29 * b + 128) >> 8;
                    global.add(y);

                    if (sx * 4 >= sampleW && sx * 4 < sampleW * 3
                            && sy * 4 >= sampleH && sy * 4 < sampleH * 3) {
                        center50.add(y);
                    }
                    if (sx * 3 >= sampleW && sx * 3 < sampleW * 2
                            && sy * 3 >= sampleH && sy * 3 < sampleH * 2) {
                        middleCenter33.add(y);
                    }
                }
            }

            out.put("bitmapWidth", width);
            out.put("bitmapHeight", height);
            out.put("orientationSpace", "finished_display_bitmap");
            out.put("sampleLongSide", SAMPLE_LONG_SIDE);
            out.put("sampleWidth", sampleW);
            out.put("sampleHeight", sampleH);
            out.put("sampleCount", global.count);
            out.put("global", global.toJson());
            out.put("center50", center50.toJson());
            out.put("middleCenter33", middleCenter33.toJson());
            out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
            out.put("valid", global.count > 0 && center50.count > 0 && middleCenter33.count > 0);
            out.put("reason", "direct_finished_bitmap_luma_measured");
        } catch (Throwable t) {
            try {
                out.put("valid", false);
                out.put("reason", "rendered_luma_measurement_exception");
                out.put("error", t.toString());
                out.put("elapsedMs", (System.nanoTime() - startedNs) / 1_000_000.0);
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static final class Stats {
        final int[] hist = new int[256];
        long sum = 0L;
        int count = 0;

        void add(int y) {
            int v = Math.max(0, Math.min(255, y));
            hist[v]++;
            sum += v;
            count++;
        }

        JSONObject toJson() throws Exception {
            JSONObject o = new JSONObject();
            o.put("sampleCount", count);
            if (count <= 0) return o;
            o.put("mean", sum / (double)count);
            o.put("median", percentile(0.50));
            o.put("q90", percentile(0.90));
            o.put("q95", percentile(0.95));
            o.put("q99", percentile(0.99));
            o.put("darkFractionLE48", fractionLE(48));
            o.put("darkFractionLE64", fractionLE(64));
            o.put("brightFractionGE192", fractionGE(192));
            o.put("brightFractionGE224", fractionGE(224));
            o.put("brightFractionGE240", fractionGE(240));
            return o;
        }

        int percentile(double p) {
            int target = Math.max(1, (int)Math.ceil(p * count));
            int acc = 0;
            for (int i = 0; i < hist.length; i++) {
                acc += hist[i];
                if (acc >= target) return i;
            }
            return 255;
        }

        double fractionLE(int threshold) {
            int acc = 0;
            for (int i = 0; i <= Math.min(255, threshold); i++) acc += hist[i];
            return acc / (double)count;
        }

        double fractionGE(int threshold) {
            int acc = 0;
            for (int i = Math.max(0, threshold); i < hist.length; i++) acc += hist[i];
            return acc / (double)count;
        }
    }
}
'''
write(rendered_luma_rel, rendered_luma)

render_meter = r'''package com.particlesdevs.photoncamera.m9.render;

import org.json.JSONObject;

/**
 * RENDERMETER1B: direct-render-luma observational diagnostics.
 *
 * Capture exposure remains decoupled from JPEG tonal placement. This build measures
 * the finished bitmap directly but deliberately keeps render correction disabled until
 * paired DNG/JPEG examples establish stable target ranges.
 */
public final class M9RenderMeterDiagnostic {
    public static final String SCHEMA = "m9cam.rendermeter.v2.directluma1b";

    private M9RenderMeterDiagnostic() {}

    public static JSONObject evaluate(JSONObject renderer) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_renderer_mutation");
            out.put("liveEligible", false);
            out.put("correctionAppliedEv", 0.0);
            out.put("correctionCandidateEv", 0.0);
            out.put("candidatePolicy", "disabled_pending_paired_direct_luma_calibration");

            double gain = renderer != null ? renderer.optDouble("gain", Double.NaN) : Double.NaN;
            double baseGain = renderer != null ? renderer.optDouble("baseMedianGain", Double.NaN) : Double.NaN;
            double guardGain = renderer != null ? renderer.optDouble("tc20GuardGain", Double.NaN) : Double.NaN;
            double rawQ99 = renderer != null ? renderer.optDouble("rawUq99", Double.NaN) : Double.NaN;
            double rawClip = renderer != null ? renderer.optDouble("rawHardClipFraction", Double.NaN) : Double.NaN;
            double rgbClip = renderer != null ? renderer.optDouble("rgb8ClipFraction", Double.NaN) : Double.NaN;
            double nearWhite = renderer != null ? renderer.optDouble("renderNearWhiteFraction", Double.NaN) : Double.NaN;
            JSONObject direct = renderer != null ? renderer.optJSONObject("directRenderedLuma") : null;
            boolean directValid = direct != null && direct.optBoolean("valid", false);

            JSONObject observations = new JSONObject();
            if (finite(gain)) {
                observations.put("tc20Gain", gain);
                observations.put("tc20GainEv", log2(Math.max(gain, 1e-12)));
            }
            if (finite(baseGain)) observations.put("baseMedianGain", baseGain);
            if (finite(guardGain)) observations.put("tc20GuardGain", guardGain);
            if (finite(rawQ99)) observations.put("rawUq99", rawQ99);
            if (finite(rawClip)) observations.put("rawHardClipFraction", rawClip);
            if (finite(rgbClip)) observations.put("renderRgbChannelClipFraction", rgbClip);
            if (finite(nearWhite)) observations.put("renderNearWhiteFraction", nearWhite);
            out.put("observations", observations);

            if (directValid) {
                JSONObject copy = new JSONObject(direct.toString());
                out.put("directRenderedLuma", copy);
                JSONObject global = direct.optJSONObject("global");
                JSONObject center = direct.optJSONObject("center50");
                JSONObject middle = direct.optJSONObject("middleCenter33");
                JSONObject placement = new JSONObject();
                if (global != null) {
                    placement.put("globalMedian", global.optDouble("median", Double.NaN));
                    placement.put("globalQ95", global.optDouble("q95", Double.NaN));
                    placement.put("globalQ99", global.optDouble("q99", Double.NaN));
                    placement.put("globalDarkFractionLE64", global.optDouble("darkFractionLE64", Double.NaN));
                    placement.put("globalBrightFractionGE224", global.optDouble("brightFractionGE224", Double.NaN));
                }
                if (center != null) {
                    double cm = center.optDouble("median", Double.NaN);
                    placement.put("centerMedian", cm);
                    placement.put("centerQ95", center.optDouble("q95", Double.NaN));
                    if (global != null) {
                        double gm = global.optDouble("median", Double.NaN);
                        if (finite(cm) && finite(gm)) placement.put("centerMedianMinusGlobalMedian", cm - gm);
                    }
                }
                if (middle != null) {
                    placement.put("middleCenterMedian", middle.optDouble("median", Double.NaN));
                    placement.put("middleCenterQ95", middle.optDouble("q95", Double.NaN));
                }
                out.put("tonalPlacement", placement);
                out.put("state", "direct_rendered_luma_measured_calibration_pending");
                out.put("nextRequiredSignal", "paired_scene_labels_for_render_tonal_target_calibration");
                out.put("valid", true);
                out.put("reason", "direct_render_luma_available_no_correction_applied");
            } else {
                out.put("state", "direct_rendered_luma_missing");
                out.put("nextRequiredSignal", "direct_render_global_center_luma_statistics");
                out.put("valid", finite(gain) || finite(rawQ99) || finite(nearWhite));
                out.put("reason", "renderer_observations_available_direct_luma_missing");
            }

            out.put("captureRenderDecouplingEvidence",
                    "direct_finished_bitmap_luma_logged_beside_tc20_gain_and_raw_placement_without_using_it_for_capture_ev");
        } catch (Exception ignored) {
            try {
                out.put("valid", false);
                out.put("liveEligible", false);
                out.put("correctionAppliedEv", 0.0);
                out.put("correctionCandidateEv", 0.0);
                out.put("reason", "render_meter_diagnostic_exception");
            } catch (Exception ignoredAgain) {}
        }
        return out;
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }

    private static double log2(double x) {
        return Math.log(x) / Math.log(2.0);
    }
}
'''
write(render_meter_rel, render_meter)

renderer = read(renderer_rel)
renderer_before = renderer
renderer_anchor = '''            bitmap = out.bitmap;

            String dngName = dngPath.getFileName().toString();
'''
renderer_insert = '''            bitmap = out.bitmap;
            // RENDERMETER1B read-only sparse sampling of the already-final bitmap.
            // No pixel, TC20, colour or JPEG state is mutated by this diagnostic.
            out.diagnostics.put("directRenderedLuma", M9RenderedLumaDiagnostic.measure(bitmap));

            String dngName = dngPath.getFileName().toString();
'''
if renderer_anchor not in renderer:
    raise SystemExit('CAPTURESPLIT1B renderer bitmap anchor missing')
renderer = renderer.replace(renderer_anchor, renderer_insert, 1)
added_renderer = '''            // RENDERMETER1B read-only sparse sampling of the already-final bitmap.
            // No pixel, TC20, colour or JPEG state is mutated by this diagnostic.
            out.diagnostics.put("directRenderedLuma", M9RenderedLumaDiagnostic.measure(bitmap));
'''
if renderer.replace(added_renderer, '', 1) != renderer_before:
    raise SystemExit('CAPTURESPLIT1B renderer structural guard failed')
write(renderer_rel, renderer)

# -----------------------------------------------------------------------------
# SIDECAR1A: diagnostic sidecars direct-filesystem-first, SAF fallback, telemetry.
# JPEG/DNG persistence is untouched.
# -----------------------------------------------------------------------------
sidecar_io_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticSidecarIO.java'
sidecar_io = r'''package com.particlesdevs.photoncamera.m9;

import android.os.Process;

import com.particlesdevs.photoncamera.util.Log;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;

import org.json.JSONObject;

import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.atomic.AtomicLong;

/** Development JSON sidecar transport only. Finished JPEG/DNG storage is untouched. */
public final class M9DiagnosticSidecarIO {
    public static final String SCHEMA = "m9cam.sidecario.v1.directfirst1a";
    private static final String TAG = "M9SidecarIO";

    private static final AtomicLong SCHEDULED = new AtomicLong();
    private static final AtomicLong COMPLETED = new AtomicLong();
    private static final AtomicLong FAILED = new AtomicLong();
    private static final AtomicLong PENDING = new AtomicLong();
    private static final AtomicLong MAX_PENDING = new AtomicLong();
    private static final AtomicLong DIRECT_WRITES = new AtomicLong();
    private static final AtomicLong SAF_FALLBACK_WRITES = new AtomicLong();
    private static final AtomicLong TOTAL_PERSIST_NS = new AtomicLong();
    private static final AtomicLong LAST_PERSIST_NS = new AtomicLong();

    private M9DiagnosticSidecarIO() {}

    public static void noteScheduled(String role) {
        SCHEDULED.incrementAndGet();
        long p = PENDING.incrementAndGet();
        long old;
        while (p > (old = MAX_PENDING.get()) && !MAX_PENDING.compareAndSet(old, p)) {}
        Log.d(TAG, "SIDECAR1A scheduled role=" + role + "; pending=" + p);
    }

    public static void noteScheduleRejected(String role, Throwable t) {
        long p = Math.max(0L, PENDING.decrementAndGet());
        FAILED.incrementAndGet();
        Log.e(TAG, "SIDECAR1A schedule rejected role=" + role + "; pending=" + p, t);
    }

    public static boolean persist(Path path, byte[] bytes, String role) {
        final long startedNs = System.nanoTime();
        boolean success = false;
        String mode = "none";
        Throwable directError = null;
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            try {
                try (OutputStream out = Files.newOutputStream(path)) {
                    out.write(bytes);
                    out.flush();
                }
                mode = "direct_filesystem";
                DIRECT_WRITES.incrementAndGet();
                success = true;
            } catch (Throwable direct) {
                directError = direct;
                OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(path.toString());
                if (safOut == null) throw direct;
                try (OutputStream out = safOut) {
                    out.write(bytes);
                    out.flush();
                }
                mode = "saf_fallback";
                SAF_FALLBACK_WRITES.incrementAndGet();
                success = true;
            }
            return true;
        } catch (Throwable t) {
            FAILED.incrementAndGet();
            if (directError != null) {
                Log.e(TAG, "SIDECAR1A direct and SAF persistence failed role=" + role
                        + "; path=" + path + "; directError=" + directError, t);
            } else {
                Log.e(TAG, "SIDECAR1A persistence failed role=" + role + "; path=" + path, t);
            }
            return false;
        } finally {
            long elapsedNs = System.nanoTime() - startedNs;
            LAST_PERSIST_NS.set(elapsedNs);
            TOTAL_PERSIST_NS.addAndGet(elapsedNs);
            if (success) COMPLETED.incrementAndGet();
            long p = Math.max(0L, PENDING.decrementAndGet());
            Log.d(TAG, "SIDECAR1A persisted role=" + role + "; success=" + success
                    + "; mode=" + mode + "; elapsedMs=" + (elapsedNs / 1_000_000.0)
                    + "; pending=" + p + "; path=" + path);
        }
    }

    public static JSONObject snapshotJson() {
        JSONObject o = new JSONObject();
        try {
            long completed = COMPLETED.get();
            o.put("schema", SCHEMA);
            o.put("writePolicy", "direct_filesystem_first_then_saf_fallback");
            o.put("scheduled", SCHEDULED.get());
            o.put("completed", completed);
            o.put("failed", FAILED.get());
            o.put("pending", PENDING.get());
            o.put("maxPending", MAX_PENDING.get());
            o.put("directWrites", DIRECT_WRITES.get());
            o.put("safFallbackWrites", SAF_FALLBACK_WRITES.get());
            o.put("lastPersistElapsedMs", LAST_PERSIST_NS.get() / 1_000_000.0);
            if (completed > 0) {
                o.put("averagePersistElapsedMs", TOTAL_PERSIST_NS.get() / 1_000_000.0 / completed);
            }
        } catch (Exception ignored) {}
        return o;
    }
}
'''
write(sidecar_io_rel, sidecar_io)

meta_store = r'''package com.particlesdevs.photoncamera.m9;

import com.particlesdevs.photoncamera.util.Log;

import java.nio.file.Path;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * SIDECAR1A keeps METAFREEZE1A immutable capture bytes but routes only development
 * JSON persistence through direct-filesystem-first transport with SAF fallback.
 */
public final class M9DeferredMetadataStore {
    private static final String TAG = "M9MetadataDeferred";
    private static final ConcurrentHashMap<String, byte[]> STAGED = new ConcurrentHashMap<>();
    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor(runnable -> {
        Thread t = new Thread(runnable, "M9MetadataPersist");
        t.setDaemon(true);
        return t;
    });

    private M9DeferredMetadataStore() {}

    public static boolean stage(Path jsonPath, byte[] bytes) {
        if (jsonPath == null || bytes == null) return false;
        STAGED.put(jsonPath.toString(), bytes);
        return true;
    }

    public static Path sidecarPath(Path dngPath) {
        if (dngPath == null) return null;
        String filename = dngPath.getFileName().toString();
        int dot = filename.lastIndexOf('.');
        String stem = dot > 0 ? filename.substring(0, dot) : filename;
        return dngPath.resolveSibling(stem + "_M9.json");
    }

    public static boolean persistAsyncForDng(Path dngPath) {
        final Path jsonPath = sidecarPath(dngPath);
        if (jsonPath == null) return false;
        final String key = jsonPath.toString();
        final byte[] bytes = STAGED.remove(key);
        if (bytes == null) {
            Log.w(TAG, "No staged metadata for " + jsonPath);
            return false;
        }
        M9DiagnosticSidecarIO.noteScheduled("capture_metadata");
        try {
            EXECUTOR.execute(() -> M9DiagnosticSidecarIO.persist(jsonPath, bytes, "capture_metadata"));
            return true;
        } catch (RuntimeException rejected) {
            M9DiagnosticSidecarIO.noteScheduleRejected("capture_metadata", rejected);
            STAGED.put(key, bytes);
            return false;
        }
    }

    public static void discardForDng(Path dngPath) {
        Path jsonPath = sidecarPath(dngPath);
        if (jsonPath != null) STAGED.remove(jsonPath.toString());
    }
}
'''
write(meta_store_rel, meta_store)

# PRIMARY timing: preserve immutable freeze semantics, change only sidecar transport and
# append a queue/counter snapshot so burst tests prove whether persistence is keeping up.
timing = read(timing_rel)
if 'm9cam.primarytiming.v6.exifasync1a.dngasync1a' not in timing:
    raise SystemExit('SIDECAR1A PRIMARY timing schema anchor missing')
if 'import com.particlesdevs.photoncamera.util.SimpleStorageHelper;' in timing:
    timing = timing.replace('import com.particlesdevs.photoncamera.util.SimpleStorageHelper;\n', '', 1)
if 'import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;' not in timing:
    timing = timing.replace('import com.particlesdevs.photoncamera.util.Log;\n',
                            'import com.particlesdevs.photoncamera.util.Log;\nimport com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\n', 1)
timing = timing.replace('m9cam.primarytiming.v6.exifasync1a.dngasync1a',
                        'm9cam.primarytiming.v7.sidecar1a', 1)
timing = timing.replace('M9-PRIMARY2.5-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A-COLORNATIVE2A-FIX1-NAME1A-QUEUE1B-TIMINGFREEZE1A-DNGASYNC1A-EXIFASYNC1A',
                        'M9-PRIMARY2.5-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A-COLORNATIVE2A-FIX1-NAME1A-QUEUE1B-TIMINGFREEZE1A-DNGASYNC1A-EXIFASYNC1A-SIDECAR1A', 1)

schedule_anchor = '''            TIMING_WRITER.execute(() -> persistFrozen(frozen));
            return true;
'''
schedule_insert = '''            M9DiagnosticSidecarIO.noteScheduled("primary_timing");
            try {
                TIMING_WRITER.execute(() -> persistFrozen(frozen));
                return true;
            } catch (RuntimeException rejected) {
                M9DiagnosticSidecarIO.noteScheduleRejected("primary_timing", rejected);
                throw rejected;
            }
'''
if schedule_anchor not in timing:
    raise SystemExit('SIDECAR1A accepted timing schedule anchor missing')
timing = timing.replace(schedule_anchor, schedule_insert, 1)

rejected_anchor = '''        TIMING_WRITER.execute(() -> {
            try {
                FrozenTiming frozen = freezeInternal(
'''
rejected_insert = '''        M9DiagnosticSidecarIO.noteScheduled("primary_timing_rejected_capture");
        TIMING_WRITER.execute(() -> {
            try {
                FrozenTiming frozen = freezeInternal(
'''
if rejected_anchor not in timing:
    raise SystemExit('SIDECAR1A rejected timing schedule anchor missing')
timing = timing.replace(rejected_anchor, rejected_insert, 1)

snapshot_anchor = '''        if (error != null && !error.isEmpty()) root.put("error", error);

        byte[] provisional = root.toString(2).getBytes(StandardCharsets.UTF_8);
'''
snapshot_insert = '''        if (error != null && !error.isEmpty()) root.put("error", error);
        root.put("diagnosticSidecarIo", M9DiagnosticSidecarIO.snapshotJson());

        byte[] provisional = root.toString(2).getBytes(StandardCharsets.UTF_8);
'''
if snapshot_anchor not in timing:
    raise SystemExit('SIDECAR1A timing freeze snapshot anchor missing')
timing = timing.replace(snapshot_anchor, snapshot_insert, 1)

persist_start = timing.find('    private static void persistFrozen(FrozenTiming frozen) {')
if persist_start < 0:
    raise SystemExit('SIDECAR1A persistFrozen start missing')
class_end = timing.rfind('\n}')
if class_end < persist_start:
    raise SystemExit('SIDECAR1A timing class end missing')
old_persist = timing[persist_start:class_end]
new_persist = '''    private static void persistFrozen(FrozenTiming frozen) {
        if (frozen == null || frozen.timingPath == null || frozen.bytes == null) {
            M9DiagnosticSidecarIO.noteScheduleRejected("primary_timing", new IllegalArgumentException("missing frozen timing bytes"));
            return;
        }
        M9DiagnosticSidecarIO.persist(frozen.timingPath, frozen.bytes, "primary_timing");
    }
'''
timing = timing[:persist_start] + new_persist + timing[class_end:]
write(timing_rel, timing)

# Distinct diagnostic build identity.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.42-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1a'"
new_v = "versionName '1.43-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1brendermeter1bsidecar1a'"
if old_v not in g:
    raise SystemExit('CAPTURESPLIT1B expected CAPTURESPLIT1A versionName missing')
g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.42-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1a'
new_b = '1.43-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1brendermeter1bsidecar1a'
if old_b not in b:
    raise SystemExit('CAPTURESPLIT1B build identity anchor missing')
b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'CAPTURESPLIT1B photographic/capture freeze violation: {rel} changed')

print('M9Cam CAPTURESPLIT1B applied: direct finished-bitmap RENDERMETER1B + SIDECAR1A direct-first diagnostic persistence; capture/SCENEEXPOSURE/TC20/native colour/JPEG-DNG photographic outputs unchanged')
