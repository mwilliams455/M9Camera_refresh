#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-capturesplit1c.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'CAPTURESPLIT1C missing expected file: {rel}')
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

if 'm9cam.rendermeter.v2.directluma1b' not in read(render_meter_rel):
    raise SystemExit('CAPTURESPLIT1C requires RENDERMETER1B')
if 'm9cam.sidecario.v1.directfirst1a' not in read('app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticSidecarIO.java'):
    raise SystemExit('CAPTURESPLIT1C requires SIDECAR1A')
if '1.43-m9modern7r38luma24fb1primary25perf3i' not in read('app/build.gradle'):
    raise SystemExit('CAPTURESPLIT1C requires 1.43 CAPTURESPLIT1B baseline')

# Photographic/capture seams are frozen. 1C changes only diagnostic model/storage plumbing.
frozen_rels = [
    scene_rel,
    coord_rel,
    renderer_rel,
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

# -----------------------------------------------------------------------------
# RENDERMETER1C: evidence model only. It consumes RENDERMETER1B direct luma but
# deliberately produces no signed EV and cannot mutate TC20/pixels.
# -----------------------------------------------------------------------------
model_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RenderMeterModel1C.java'
model = r'''package com.particlesdevs.photoncamera.m9.render;

import org.json.JSONObject;

/**
 * RENDERMETER1C evidence model.
 *
 * Converts direct finished-bitmap luminance into interpretable evidence terms.
 * It intentionally does NOT emit or apply EV. We need more hot-face / low-key / backlight
 * pairs before mapping these scores into a live tonal correction.
 */
public final class M9RenderMeterModel1C {
    public static final String SCHEMA = "m9cam.rendermetermodel.v1.evidence1c";

    private M9RenderMeterModel1C() {}

    public static JSONObject evaluate(JSONObject direct) {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "evidence_only_no_signed_ev");
            out.put("liveEligible", false);
            out.put("correctionCandidateEv", 0.0);
            if (direct == null || !direct.optBoolean("valid", false)) {
                out.put("valid", false);
                out.put("reason", "direct_render_luma_missing");
                return out;
            }

            JSONObject g = direct.optJSONObject("global");
            JSONObject c = direct.optJSONObject("center50");
            JSONObject m = direct.optJSONObject("middleCenter33");
            if (g == null || c == null || m == null) {
                out.put("valid", false);
                out.put("reason", "direct_render_regions_missing");
                return out;
            }

            double gm = g.optDouble("median", Double.NaN);
            double cm = c.optDouble("median", Double.NaN);
            double mm = m.optDouble("median", Double.NaN);
            double cq95 = c.optDouble("q95", Double.NaN);
            double mq95 = m.optDouble("q95", Double.NaN);
            double gDark64 = g.optDouble("darkFractionLE64", Double.NaN);
            double gBright224 = g.optDouble("brightFractionGE224", Double.NaN);
            if (!finite(gm) || !finite(cm) || !finite(mm) || !finite(cq95) || !finite(mq95)) {
                out.put("valid", false);
                out.put("reason", "non_finite_render_luma_input");
                return out;
            }

            double globalDarkness = 1.0 - smoothstep(gm, 35.0, 82.0);
            double centerAdequacy = smoothstep(cm, 68.0, 116.0);
            double middleAdequacy = smoothstep(mm, 76.0, 132.0);
            double localAdequacy = clamp01(Math.max(centerAdequacy, 0.82 * middleAdequacy));
            double centerVsGlobal = cm - gm;
            double separationEvidence = smoothstep(centerVsGlobal, 16.0, 55.0);
            double intentionalDarkSplitEvidence = clamp01(globalDarkness * localAdequacy * separationEvidence);
            double wholeFrameStarvationEvidence = clamp01(globalDarkness * (1.0 - localAdequacy));

            double centerUpperPlacement = smoothstep(cq95, 236.0, 250.0);
            double middleUpperPlacement = smoothstep(mq95, 238.0, 252.0);
            double localizedUpperPlacementEvidence = clamp01(localAdequacy
                    * Math.max(centerUpperPlacement, middleUpperPlacement));
            double globalBrightSupport = finite(gBright224) ? smoothstep(gBright224, 0.025, 0.18) : 0.0;
            double globalDarkOccupancy = finite(gDark64) ? smoothstep(gDark64, 0.35, 0.75) : globalDarkness;

            // These are evidence axes, not an EV equation. In particular, a bright q95 can
            // describe a white object/window just as easily as a hot face, so no negative EV
            // is inferred from upper-placement evidence alone.
            double renderLiftNeedEvidence = clamp01(wholeFrameStarvationEvidence
                    * (1.0 - 0.55 * localizedUpperPlacementEvidence));
            double renderHoldEvidence = clamp01(Math.max(intentionalDarkSplitEvidence,
                    localAdequacy * (0.35 + 0.65 * separationEvidence)));

            out.put("globalMedian", gm);
            out.put("centerMedian", cm);
            out.put("middleCenterMedian", mm);
            out.put("centerQ95", cq95);
            out.put("middleCenterQ95", mq95);
            out.put("centerMedianMinusGlobalMedian", centerVsGlobal);
            if (finite(gDark64)) out.put("globalDarkFractionLE64", gDark64);
            if (finite(gBright224)) out.put("globalBrightFractionGE224", gBright224);
            out.put("globalDarknessEvidence", globalDarkness);
            out.put("globalDarkOccupancyEvidence", globalDarkOccupancy);
            out.put("centerAdequacyEvidence", centerAdequacy);
            out.put("middleCenterAdequacyEvidence", middleAdequacy);
            out.put("localAdequacyEvidence", localAdequacy);
            out.put("centerVsGlobalSeparationEvidence", separationEvidence);
            out.put("intentionalDarkSplitEvidence", intentionalDarkSplitEvidence);
            out.put("wholeFrameStarvationEvidence", wholeFrameStarvationEvidence);
            out.put("localizedUpperPlacementEvidence", localizedUpperPlacementEvidence);
            out.put("globalBrightSupportEvidence", globalBrightSupport);
            out.put("renderLiftNeedEvidence", renderLiftNeedEvidence);
            out.put("renderHoldEvidence", renderHoldEvidence);
            out.put("calibrationState", "collect_more_direct_luma_scene_labels_before_signed_ev");
            out.put("valid", true);
            out.put("reason", "direct_render_tonal_evidence_scored_no_correction");
        } catch (Exception e) {
            try {
                out.put("valid", false);
                out.put("liveEligible", false);
                out.put("correctionCandidateEv", 0.0);
                out.put("reason", "rendermeter1c_exception");
            } catch (Exception ignored) {}
        }
        return out;
    }

    private static double smoothstep(double x, double lo, double hi) {
        if (!finite(x)) return 0.0;
        if (hi <= lo) return x >= hi ? 1.0 : 0.0;
        double t = clamp01((x - lo) / (hi - lo));
        return t * t * (3.0 - 2.0 * t);
    }

    private static double clamp01(double x) {
        return Math.max(0.0, Math.min(1.0, x));
    }

    private static boolean finite(double x) {
        return !Double.isNaN(x) && !Double.isInfinite(x);
    }
}
'''
write(model_rel, model)

render_meter = read(render_meter_rel)
render_meter = render_meter.replace('m9cam.rendermeter.v2.directluma1b',
                                    'm9cam.rendermeter.v3.evidence1c', 1)
render_meter = render_meter.replace('RENDERMETER1B: direct-render-luma observational diagnostics.',
                                    'RENDERMETER1C: direct-render-luma evidence diagnostics.', 1)
model_anchor = '''                out.put("tonalPlacement", placement);
                out.put("state", "direct_rendered_luma_measured_calibration_pending");
'''
model_insert = '''                out.put("tonalPlacement", placement);
                out.put("renderMeterModel1C", M9RenderMeterModel1C.evaluate(direct));
                out.put("state", "direct_rendered_luma_evidence_model_active_no_signed_ev");
'''
if model_anchor not in render_meter:
    raise SystemExit('RENDERMETER1C model insertion anchor missing')
render_meter = render_meter.replace(model_anchor, model_insert, 1)
render_meter = render_meter.replace('paired_scene_labels_for_render_tonal_target_calibration',
                                    'more_direct_luma_hot_subject_low_key_backlight_labels_for_signed_ev_calibration', 1)
write(render_meter_rel, render_meter)

# -----------------------------------------------------------------------------
# SIDECAR1B: immediate app-private immutable spool + debounced public burst bundle.
# Individual public files remain eventual compatibility exports, delayed so the one-bundle
# export has priority. JPEG/DNG paths are untouched.
# -----------------------------------------------------------------------------
spool_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
spool = r'''package com.particlesdevs.photoncamera.m9;

import android.content.Context;
import android.os.Process;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import com.particlesdevs.photoncamera.util.Log;
import com.particlesdevs.photoncamera.util.SimpleStorageHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * SIDECAR1B diagnostic-only storage spool.
 *
 * Each immutable JSON payload is written immediately to app-private storage. Public camera-folder
 * export is decoupled: one debounced burst bundle is written first, then legacy individual JSON
 * files are exported later for compatibility. No photographic JPEG/DNG storage is routed here.
 */
public final class M9DiagnosticBurstSpool {
    public static final String SCHEMA = "m9cam.sidecarspool.v1.privatebundle1b";
    private static final String TAG = "M9DiagSpool";
    private static final long BUNDLE_IDLE_MS = 1500L;
    private static final long INDIVIDUAL_DELAY_MS = 12000L;
    private static final Object BUNDLE_LOCK = new Object();

    private static final ConcurrentHashMap<String, Entry> INDIVIDUAL_PENDING = new ConcurrentHashMap<>();
    private static final ConcurrentHashMap<String, Entry> BUNDLE_PENDING = new ConcurrentHashMap<>();
    private static final AtomicLong SEQ = new AtomicLong();
    private static final AtomicLong PRIVATE_STAGED = new AtomicLong();
    private static final AtomicLong PRIVATE_FAILED = new AtomicLong();
    private static final AtomicLong BUNDLE_WRITES = new AtomicLong();
    private static final AtomicLong BUNDLE_FAILED = new AtomicLong();
    private static final AtomicLong INDIVIDUAL_WRITES = new AtomicLong();
    private static final AtomicLong INDIVIDUAL_FAILED = new AtomicLong();
    private static final AtomicLong PRIVATE_TOTAL_NS = new AtomicLong();
    private static final AtomicLong PRIVATE_LAST_NS = new AtomicLong();
    private static final AtomicLong BUNDLE_TOTAL_NS = new AtomicLong();
    private static final AtomicLong BUNDLE_LAST_NS = new AtomicLong();
    private static volatile String lastBundlePath = null;
    private static volatile ScheduledFuture<?> scheduledBundle = null;

    private static final ScheduledThreadPoolExecutor BUNDLE_EXECUTOR =
            new ScheduledThreadPoolExecutor(1, runnable -> {
                Thread t = new Thread(runnable, "M9DiagBundleIO");
                t.setDaemon(true);
                return t;
            });
    private static final ScheduledThreadPoolExecutor INDIVIDUAL_EXPORTER =
            new ScheduledThreadPoolExecutor(1, runnable -> {
                Thread t = new Thread(runnable, "M9DiagIndividualIO");
                t.setDaemon(true);
                return t;
            });

    static {
        BUNDLE_EXECUTOR.setRemoveOnCancelPolicy(true);
        INDIVIDUAL_EXPORTER.setRemoveOnCancelPolicy(true);
    }

    private M9DiagnosticBurstSpool() {}

    public static boolean stage(Path publicPath, byte[] bytes, String role) {
        if (publicPath == null || bytes == null) return false;
        final long startedNs = System.nanoTime();
        try {
            Context context = PhotonCamera.getAppContext();
            if (context == null) throw new IllegalStateException("PhotonCamera app context unavailable");
            Path dir = context.getFilesDir().toPath().resolve("m9diag_spool");
            Files.createDirectories(dir);
            long seq = SEQ.incrementAndGet();
            String base = sanitize(publicPath.getFileName().toString());
            Path privatePath = dir.resolve(String.format("%08d_%s.stage", seq, base));
            Files.write(privatePath, bytes);

            Entry entry = new Entry(publicPath, privatePath, bytes, role, System.currentTimeMillis(), seq);
            String key = publicPath.toString();
            INDIVIDUAL_PENDING.put(key, entry);
            BUNDLE_PENDING.put(key, entry);
            PRIVATE_STAGED.incrementAndGet();
            long elapsedNs = System.nanoTime() - startedNs;
            PRIVATE_LAST_NS.set(elapsedNs);
            PRIVATE_TOTAL_NS.addAndGet(elapsedNs);
            scheduleBundle();
            INDIVIDUAL_EXPORTER.schedule(() -> exportIndividual(entry),
                    INDIVIDUAL_DELAY_MS, TimeUnit.MILLISECONDS);
            Log.d(TAG, "SIDECAR1B private staged role=" + role + "; elapsedMs="
                    + (elapsedNs / 1_000_000.0) + "; pendingBundle=" + BUNDLE_PENDING.size()
                    + "; pendingIndividual=" + INDIVIDUAL_PENDING.size());
            return true;
        } catch (Throwable t) {
            PRIVATE_FAILED.incrementAndGet();
            Log.e(TAG, "SIDECAR1B private stage failed role=" + role + "; path=" + publicPath, t);
            return false;
        }
    }

    private static void scheduleBundle() {
        synchronized (BUNDLE_LOCK) {
            if (scheduledBundle != null) scheduledBundle.cancel(false);
            scheduledBundle = BUNDLE_EXECUTOR.schedule(M9DiagnosticBurstSpool::flushBundle,
                    BUNDLE_IDLE_MS, TimeUnit.MILLISECONDS);
        }
    }

    private static void flushBundle() {
        List<Entry> entries = new ArrayList<>(BUNDLE_PENDING.values());
        if (entries.isEmpty()) return;
        entries.sort(Comparator.comparingLong(e -> e.sequence));
        final long startedNs = System.nanoTime();
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            JSONObject root = new JSONObject();
            root.put("schema", "m9cam.diagnosticbundle.v1.sidecar1b");
            root.put("createdEpochMs", System.currentTimeMillis());
            root.put("entryCount", entries.size());
            root.put("bundleIdleMs", BUNDLE_IDLE_MS);
            root.put("individualExportDelayMs", INDIVIDUAL_DELAY_MS);
            JSONArray array = new JSONArray();
            for (Entry e : entries) {
                JSONObject item = new JSONObject();
                item.put("role", e.role);
                item.put("publicPath", e.publicPath.toString());
                item.put("publicFilename", e.publicPath.getFileName().toString());
                item.put("stagedEpochMs", e.stagedEpochMs);
                item.put("sequence", e.sequence);
                try {
                    item.put("payload", new JSONObject(new String(e.bytes, StandardCharsets.UTF_8)));
                } catch (Throwable parseError) {
                    item.put("payloadText", new String(e.bytes, StandardCharsets.UTF_8));
                }
                array.put(item);
            }
            root.put("entries", array);
            root.put("spoolTelemetryAtBundle", snapshotJson());
            byte[] bundleBytes = root.toString(2).getBytes(StandardCharsets.UTF_8);
            Path parent = entries.get(0).publicPath.getParent();
            if (parent == null) throw new IllegalStateException("public diagnostic parent missing");
            Path bundlePath = parent.resolve("M9_DIAGNOSTICS_BURST_"
                    + System.currentTimeMillis() + "_" + entries.size() + ".json");
            if (!writePublic(bundlePath, bundleBytes)) {
                throw new java.io.IOException("public burst bundle write failed: " + bundlePath);
            }
            for (Entry e : entries) {
                BUNDLE_PENDING.remove(e.publicPath.toString(), e);
            }
            lastBundlePath = bundlePath.toString();
            BUNDLE_WRITES.incrementAndGet();
            long elapsedNs = System.nanoTime() - startedNs;
            BUNDLE_LAST_NS.set(elapsedNs);
            BUNDLE_TOTAL_NS.addAndGet(elapsedNs);
            Log.d(TAG, "SIDECAR1B burst bundle exported entries=" + entries.size()
                    + "; elapsedMs=" + (elapsedNs / 1_000_000.0) + "; path=" + bundlePath);
        } catch (Throwable t) {
            BUNDLE_FAILED.incrementAndGet();
            Log.e(TAG, "SIDECAR1B burst bundle export failed; private staged files retained", t);
        }
    }

    private static void exportIndividual(Entry entry) {
        String key = entry.publicPath.toString();
        if (INDIVIDUAL_PENDING.get(key) != entry) return;
        try {
            Process.setThreadPriority(Process.THREAD_PRIORITY_BACKGROUND);
            if (!writePublic(entry.publicPath, entry.bytes)) {
                throw new java.io.IOException("individual public export failed");
            }
            INDIVIDUAL_WRITES.incrementAndGet();
            INDIVIDUAL_PENDING.remove(key, entry);
            try { Files.deleteIfExists(entry.privatePath); } catch (Throwable ignored) {}
            Log.d(TAG, "SIDECAR1B individual compatibility export complete role=" + entry.role
                    + "; remaining=" + INDIVIDUAL_PENDING.size() + "; path=" + entry.publicPath);
        } catch (Throwable t) {
            INDIVIDUAL_FAILED.incrementAndGet();
            Log.e(TAG, "SIDECAR1B individual compatibility export failed; private stage retained: "
                    + entry.publicPath, t);
        }
    }

    private static boolean writePublic(Path path, byte[] bytes) {
        try {
            OutputStream safOut = SimpleStorageHelper.openOutputStreamByAbsPath(path.toString());
            if (safOut != null) {
                try (OutputStream out = safOut) {
                    out.write(bytes);
                    out.flush();
                }
                return true;
            }
        } catch (Throwable safError) {
            Log.w(TAG, "SIDECAR1B SAF public write failed, trying direct path: " + safError);
        }
        try (OutputStream out = Files.newOutputStream(path)) {
            out.write(bytes);
            out.flush();
            return true;
        } catch (Throwable directError) {
            Log.e(TAG, "SIDECAR1B all public write routes failed: " + path, directError);
            return false;
        }
    }

    public static JSONObject snapshotJson() {
        JSONObject o = new JSONObject();
        try {
            long privateCount = PRIVATE_STAGED.get();
            long bundleCount = BUNDLE_WRITES.get();
            o.put("schema", SCHEMA);
            o.put("policy", "private_immediate_bundle_first_eventual_individual_public_export");
            o.put("bundleIdleMs", BUNDLE_IDLE_MS);
            o.put("individualExportDelayMs", INDIVIDUAL_DELAY_MS);
            o.put("privateStaged", privateCount);
            o.put("privateStageFailed", PRIVATE_FAILED.get());
            o.put("bundleWrites", bundleCount);
            o.put("bundleFailed", BUNDLE_FAILED.get());
            o.put("pendingBundleEntries", BUNDLE_PENDING.size());
            o.put("pendingIndividualEntries", INDIVIDUAL_PENDING.size());
            o.put("individualWrites", INDIVIDUAL_WRITES.get());
            o.put("individualFailed", INDIVIDUAL_FAILED.get());
            o.put("privateLastStageElapsedMs", PRIVATE_LAST_NS.get() / 1_000_000.0);
            if (privateCount > 0) {
                o.put("privateAverageStageElapsedMs", PRIVATE_TOTAL_NS.get() / 1_000_000.0 / privateCount);
            }
            o.put("bundleLastPersistElapsedMs", BUNDLE_LAST_NS.get() / 1_000_000.0);
            if (bundleCount > 0) {
                o.put("bundleAveragePersistElapsedMs", BUNDLE_TOTAL_NS.get() / 1_000_000.0 / bundleCount);
            }
            if (lastBundlePath != null) o.put("lastBundlePath", lastBundlePath);
        } catch (Exception ignored) {}
        return o;
    }

    private static String sanitize(String s) {
        if (s == null || s.isEmpty()) return "diagnostic.json";
        return s.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private static final class Entry {
        final Path publicPath;
        final Path privatePath;
        final byte[] bytes;
        final String role;
        final long stagedEpochMs;
        final long sequence;

        Entry(Path publicPath, Path privatePath, byte[] bytes, String role,
              long stagedEpochMs, long sequence) {
            this.publicPath = publicPath;
            this.privatePath = privatePath;
            this.bytes = bytes;
            this.role = role != null ? role : "unknown";
            this.stagedEpochMs = stagedEpochMs;
            this.sequence = sequence;
        }
    }
}
'''
write(spool_rel, spool)

meta_store = r'''package com.particlesdevs.photoncamera.m9;

import com.particlesdevs.photoncamera.util.Log;

import java.nio.file.Path;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * SIDECAR1B keeps METAFREEZE1A immutable capture bytes, stages them immediately in
 * app-private storage, and lets M9DiagnosticBurstSpool bundle/export them later.
 */
public final class M9DeferredMetadataStore {
    private static final String TAG = "M9MetadataDeferred";
    private static final ConcurrentHashMap<String, byte[]> STAGED = new ConcurrentHashMap<>();
    private static final ExecutorService FALLBACK = Executors.newSingleThreadExecutor(runnable -> {
        Thread t = new Thread(runnable, "M9MetadataFallbackIO");
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
        if (M9DiagnosticBurstSpool.stage(jsonPath, bytes, "capture_metadata")) {
            return true;
        }
        // Rare private-spool failure: preserve diagnostics through the old public writer,
        // but keep that slow path off the DNG owner thread.
        try {
            FALLBACK.execute(() -> M9DiagnosticSidecarIO.persist(jsonPath, bytes,
                    "capture_metadata_private_spool_fallback"));
            return true;
        } catch (RuntimeException rejected) {
            STAGED.put(key, bytes);
            Log.e(TAG, "Unable to schedule capture metadata fallback: " + jsonPath, rejected);
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

# PRIMARY timing now privately spools accepted timing bytes immediately after freeze.
timing = read(timing_rel)
if 'm9cam.primarytiming.v7.sidecar1a' not in timing:
    raise SystemExit('SIDECAR1B requires PRIMARY timing v7.sidecar1a')
if 'import com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;' not in timing:
    timing = timing.replace('import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\n',
                            'import com.particlesdevs.photoncamera.m9.M9DiagnosticSidecarIO;\nimport com.particlesdevs.photoncamera.m9.M9DiagnosticBurstSpool;\n', 1)
timing = timing.replace('m9cam.primarytiming.v7.sidecar1a', 'm9cam.primarytiming.v8.sidecar1b', 1)
timing = timing.replace('-SIDECAR1A";', '-SIDECAR1B";', 1)

accepted_old = '''            M9DiagnosticSidecarIO.noteScheduled("primary_timing");
            try {
                TIMING_WRITER.execute(() -> persistFrozen(frozen));
                return true;
            } catch (RuntimeException rejected) {
                M9DiagnosticSidecarIO.noteScheduleRejected("primary_timing", rejected);
                throw rejected;
            }
'''
accepted_new = '''            return persistFrozen(frozen);
'''
if accepted_old not in timing:
    raise SystemExit('SIDECAR1B accepted timing schedule anchor missing')
timing = timing.replace(accepted_old, accepted_new, 1)
timing = timing.replace('        M9DiagnosticSidecarIO.noteScheduled("primary_timing_rejected_capture");\n', '', 1)

timing = timing.replace('        root.put("diagnosticSidecarIo", M9DiagnosticSidecarIO.snapshotJson());\n',
                        '        root.put("diagnosticSidecarIoLegacyFallback", M9DiagnosticSidecarIO.snapshotJson());\n        root.put("diagnosticSidecarSpool", M9DiagnosticBurstSpool.snapshotJson());\n', 1)

persist_old = '''    private static void persistFrozen(FrozenTiming frozen) {
        if (frozen == null || frozen.timingPath == null || frozen.bytes == null) {
            M9DiagnosticSidecarIO.noteScheduleRejected("primary_timing", new IllegalArgumentException("missing frozen timing bytes"));
            return;
        }
        M9DiagnosticSidecarIO.persist(frozen.timingPath, frozen.bytes, "primary_timing");
    }
'''
persist_new = '''    private static boolean persistFrozen(FrozenTiming frozen) {
        if (frozen == null || frozen.timingPath == null || frozen.bytes == null) {
            return false;
        }
        if (M9DiagnosticBurstSpool.stage(frozen.timingPath, frozen.bytes, "primary_timing")) {
            return true;
        }
        return M9DiagnosticSidecarIO.persist(frozen.timingPath, frozen.bytes,
                "primary_timing_private_spool_fallback");
    }
'''
if persist_old not in timing:
    raise SystemExit('SIDECAR1B persistFrozen anchor missing')
timing = timing.replace(persist_old, persist_new, 1)
write(timing_rel, timing)

# Distinct diagnostic identity.
gradle_rel = 'app/build.gradle'
g = read(gradle_rel)
old_v = "versionName '1.43-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1brendermeter1bsidecar1a'"
new_v = "versionName '1.44-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1crendermeter1csidecar1b'"
if old_v not in g:
    raise SystemExit('CAPTURESPLIT1C expected 1.43 versionName missing')
g = g.replace(old_v, new_v, 1)
write(gradle_rel, g)

back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
b = read(back_rel)
old_b = '1.43-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1brendermeter1bsidecar1a'
new_b = '1.44-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1aexposureaudit1asceneexposure1hcapturesplit1crendermeter1csidecar1b'
if old_b not in b:
    raise SystemExit('CAPTURESPLIT1C build identity anchor missing')
b = b.replace(old_b, new_b, 1)
write(back_rel, b)

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'CAPTURESPLIT1C photographic/capture freeze violation: {rel} changed')

print('M9Cam CAPTURESPLIT1C applied: RENDERMETER1C evidence-only model + SIDECAR1B private immediate spool/bundle-first public export; capture/SceneExposure/TC20/renderer pixels/JPEG-DNG outputs unchanged')