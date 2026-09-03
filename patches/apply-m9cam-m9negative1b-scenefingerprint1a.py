#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9negative1b-scenefingerprint1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
p = root / rel
if not p.exists():
    raise SystemExit('SCENEFINGERPRINT1A requires M9NEGATIVE1A generated source')
s = p.read_text()
if 'm9cam.m9negative.v1.capturemeter1b.completedraw1a' not in s:
    raise SystemExit('SCENEFINGERPRINT1A requires M9NEGATIVE1A schema')

# Schema/version marker only; recommendation math below remains byte-for-byte structurally unchanged.
s = s.replace('m9cam.m9negative.v1.capturemeter1b.completedraw1a',
              'm9cam.m9negative.v2.capturemeter1b.scenefingerprint1a', 1)

# Strengthen association: richer preview fingerprint + recency gate. Keep the existing 1.0
# distance threshold so the experiment isolates descriptor quality rather than threshold tuning.
s = s.replace('private static final double SIMILAR_SCENE_DISTANCE = 1.0;\n',
              'private static final double SIMILAR_SCENE_DISTANCE = 1.0;\n'
              '    private static final long MAX_FEEDBACK_AGE_MS = 60_000L;\n', 1)

old_fields = '''        double median;\n        double center;\n        double q99;\n        double starvation;\n'''
new_fields = '''        double median;\n        double center;\n        double q95;\n        double q99;\n        double dark64;\n        double bright192;\n        double bright224;\n        double starvation;\n        double axisSpread;\n        double lowRegionMedianRatio;\n        double topBrightShare;\n        double topRowHeterogeneity;\n        double previewEnergyIsoSeconds;\n'''
if old_fields not in s:
    raise SystemExit('SCENEFINGERPRINT1A SceneSignature fields anchor missing')
s = s.replace(old_fields, new_fields, 1)

old_from = '''            double median = inputs.optDouble("globalMedian", Double.NaN);\n            double center = inputs.optDouble("centerMedian", Double.NaN);\n            double q99 = inputs.optDouble("globalQ99", Double.NaN);\n            double starvation = positive.optDouble("spatialQualificationStarvationPressure",\n                    positive.optDouble("luma24BacklightPressure", Double.NaN));\n            if (!finite(median) || !finite(center) || !finite(q99) || !finite(starvation)) return null;\n            SceneSignature s = new SceneSignature();\n            s.sequence = sequence;\n            s.median = median;\n            s.center = center;\n            s.q99 = q99;\n            s.starvation = starvation;\n            return s;\n'''
new_from = '''            double median = inputs.optDouble("globalMedian", Double.NaN);\n            double center = inputs.optDouble("centerMedian", Double.NaN);\n            double q95 = inputs.optDouble("globalQ95", Double.NaN);\n            double q99 = inputs.optDouble("globalQ99", Double.NaN);\n            double dark64 = inputs.optDouble("darkFractionLe64",\n                    inputs.optDouble("fractionLe64", Double.NaN));\n            double bright192 = inputs.optDouble("brightFractionGe192",\n                    inputs.optDouble("fractionGe192", Double.NaN));\n            double bright224 = inputs.optDouble("brightFractionGe224",\n                    inputs.optDouble("fractionGe224", Double.NaN));\n            double starvation = positive.optDouble("spatialQualificationStarvationPressure",\n                    positive.optDouble("luma24BacklightPressure", Double.NaN));\n\n            JSONObject spatial = firstObject(scene, "spatial", "spatialDiagnostics", "orientationAwareSpatial",\n                    "luma24Spatial", "spatialEvidence");\n            JSONObject exposure = firstObject(scene, "captureExposure", "previewExposure", "exposure",\n                    "cameraExposure");\n            double axisSpread = optAny(spatial, Double.NaN, "axisSpread", "orientationAxisSpread",\n                    "spatialAxisSpread");\n            double lowRegionMedianRatio = optAny(spatial, Double.NaN, "lowRegionMedianRatio",\n                    "spatialLowRegionMedianRatio");\n            double topBrightShare = optAny(spatial, Double.NaN, "topBrightShare",\n                    "spatialTopBrightShare");\n            double topRowHeterogeneity = optAny(spatial, Double.NaN, "topRowHeterogeneity",\n                    "spatialTopRowHeterogeneity");\n            double previewEnergyIsoSeconds = optAny(exposure, Double.NaN,\n                    "previewExposureEnergyIsoSeconds", "captureExposureEnergyIsoSeconds",\n                    "exposureEnergyIsoSeconds");\n\n            // Core fields are mandatory. Additional descriptors are optional so older/partial\n            // SCENEEXPOSURE1H JSON remains diagnostic instead of failing closed at construction.\n            if (!finite(median) || !finite(center) || !finite(q99) || !finite(starvation)) return null;\n            SceneSignature s = new SceneSignature();\n            s.sequence = sequence;\n            s.median = median;\n            s.center = center;\n            s.q95 = q95;\n            s.q99 = q99;\n            s.dark64 = dark64;\n            s.bright192 = bright192;\n            s.bright224 = bright224;\n            s.starvation = starvation;\n            s.axisSpread = axisSpread;\n            s.lowRegionMedianRatio = lowRegionMedianRatio;\n            s.topBrightShare = topBrightShare;\n            s.topRowHeterogeneity = topRowHeterogeneity;\n            s.previewEnergyIsoSeconds = previewEnergyIsoSeconds;\n            return s;\n'''
if old_from not in s:
    raise SystemExit('SCENEFINGERPRINT1A SceneSignature.from anchor missing')
s = s.replace(old_from, new_from, 1)

old_distance = '''        double distance(SceneSignature other) {\n            if (other == null) return Double.POSITIVE_INFINITY;\n            return Math.max(Math.abs(median - other.median) / 40.0,\n                    Math.max(Math.abs(center - other.center) / 40.0,\n                    Math.max(Math.abs(q99 - other.q99) / 50.0,\n                            Math.abs(starvation - other.starvation) / 0.50)));\n        }\n'''
new_distance = '''        double distance(SceneSignature other) {\n            if (other == null) return Double.POSITIVE_INFINITY;\n            double d = 0.0;\n            d = Math.max(d, normalizedDelta(median, other.median, 40.0));\n            d = Math.max(d, normalizedDelta(center, other.center, 40.0));\n            d = Math.max(d, normalizedDelta(q95, other.q95, 48.0));\n            d = Math.max(d, normalizedDelta(q99, other.q99, 50.0));\n            d = Math.max(d, normalizedDelta(dark64, other.dark64, 0.22));\n            d = Math.max(d, normalizedDelta(bright192, other.bright192, 0.18));\n            d = Math.max(d, normalizedDelta(bright224, other.bright224, 0.10));\n            d = Math.max(d, normalizedDelta(starvation, other.starvation, 0.50));\n            d = Math.max(d, normalizedDelta(axisSpread, other.axisSpread, 0.22));\n            d = Math.max(d, normalizedDelta(lowRegionMedianRatio, other.lowRegionMedianRatio, 0.28));\n            d = Math.max(d, normalizedDelta(topBrightShare, other.topBrightShare, 0.20));\n            d = Math.max(d, normalizedDelta(topRowHeterogeneity, other.topRowHeterogeneity, 0.22));\n            if (finite(previewEnergyIsoSeconds) && finite(other.previewEnergyIsoSeconds)\n                    && previewEnergyIsoSeconds > 0.0 && other.previewEnergyIsoSeconds > 0.0) {\n                // Exposure energy is useful as a moderator but deliberately loose: we do not want\n                // ordinary AE movement within one composition to break scene identity.\n                d = Math.max(d, Math.abs(log2(previewEnergyIsoSeconds / other.previewEnergyIsoSeconds)) / 1.50);\n            }\n            return d;\n        }\n'''
if old_distance not in s:
    raise SystemExit('SCENEFINGERPRINT1A distance anchor missing')
s = s.replace(old_distance, new_distance, 1)

# Add reusable optional-field helpers immediately before CompletedRaw.
anchor = '''    private static final class CompletedRaw {\n'''
helpers = '''    private static double normalizedDelta(double a, double b, double scale) {\n        if (!finite(a) || !finite(b)) return 0.0;\n        return Math.abs(a - b) / Math.max(scale, 1e-9);\n    }\n\n    private static JSONObject firstObject(JSONObject root, String... keys) {\n        if (root == null) return null;\n        for (String key : keys) {\n            JSONObject v = root.optJSONObject(key);\n            if (v != null) return v;\n        }\n        JSONObject inputs = root.optJSONObject("inputs");\n        if (inputs != null) {\n            for (String key : keys) {\n                JSONObject v = inputs.optJSONObject(key);\n                if (v != null) return v;\n            }\n        }\n        return null;\n    }\n\n    private static double optAny(JSONObject o, double fallback, String... keys) {\n        if (o == null) return fallback;\n        for (String key : keys) {\n            double v = o.optDouble(key, Double.NaN);\n            if (finite(v)) return v;\n        }\n        return fallback;\n    }\n\n    private static final class CompletedRaw {\n'''
if anchor not in s:
    raise SystemExit('SCENEFINGERPRINT1A helper insertion anchor missing')
s = s.replace(anchor, helpers, 1)

# Recency must participate in candidate selection, not just be reported after selection.
old_loop = '''            for (int i = history.size() - 1; i >= 0; i--) {\n                CompletedRaw candidate = history.get(i);\n                if (candidate.scene == null) continue;\n                double d = current.distance(candidate.scene);\n                if (d < bestDistance) {\n                    bestDistance = d;\n                    best = candidate;\n                }\n            }\n            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);\n            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n            if (best == null || !finite(bestDistance) || bestDistance > SIMILAR_SCENE_DISTANCE) {\n'''
new_loop = '''            long nowMs = System.currentTimeMillis();\n            int recentCandidateCount = 0;\n            int expiredCandidateCount = 0;\n            for (int i = history.size() - 1; i >= 0; i--) {\n                CompletedRaw candidate = history.get(i);\n                if (candidate.scene == null) continue;\n                long ageMs = Math.max(0L, nowMs - candidate.completedEpochMs);\n                if (ageMs > MAX_FEEDBACK_AGE_MS) {\n                    expiredCandidateCount++;\n                    continue;\n                }\n                recentCandidateCount++;\n                double d = current.distance(candidate.scene);\n                if (d < bestDistance) {\n                    bestDistance = d;\n                    best = candidate;\n                }\n            }\n            out.put("sceneFingerprintSchema", "m9cam.scenefingerprint.v1.previewexistingfields1a");\n            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);\n            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n            out.put("maxFeedbackAgeMs", MAX_FEEDBACK_AGE_MS);\n            out.put("recentCandidateCount", recentCandidateCount);\n            out.put("expiredCandidateCount", expiredCandidateCount);\n            if (best == null || !finite(bestDistance) || bestDistance > SIMILAR_SCENE_DISTANCE) {\n'''
if old_loop not in s:
    raise SystemExit('SCENEFINGERPRINT1A candidate loop anchor missing')
s = s.replace(old_loop, new_loop, 1)

old_reason = '''                out.put("reason", best == null\n                        ? "no_completed_raw_with_scene_signature_yet"\n                        : "completed_raw_not_scene_similar_enough");\n'''
new_reason = '''                out.put("reason", best == null\n                        ? (history.isEmpty()\n                            ? "no_completed_raw_with_scene_signature_yet"\n                            : recentCandidateCount == 0\n                            ? "completed_raw_feedback_expired"\n                            : "no_recent_completed_raw_with_scene_signature")\n                        : "completed_raw_not_scene_similar_enough");\n'''
if old_reason not in s:
    raise SystemExit('SCENEFINGERPRINT1A rejection reason anchor missing')
s = s.replace(old_reason, new_reason, 1)

# More precise source age and explicit association policy marker.
s = s.replace('out.put("sourceAgeMs", Math.max(0L, System.currentTimeMillis() - best.completedEpochMs));',
              'out.put("sourceAgeMs", Math.max(0L, nowMs - best.completedEpochMs));\n'
              '            out.put("associationPolicy", "recent_full_preview_fingerprint_then_completed_raw");', 1)

p.write_text(s)

# Keep coordinator schema clear that only association advanced; CAPTUREMETER live candidate remains preserved.
coord_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
cp = root / coord_rel
c = cp.read_text()
if 'm9cam.exposuresplit.v2.capturemeter1b.m9negative1a' not in c:
    raise SystemExit('SCENEFINGERPRINT1A requires CAPTUREMETER1B/M9NEGATIVE1A coordinator')
c = c.replace('m9cam.exposuresplit.v2.capturemeter1b.m9negative1a',
              'm9cam.exposuresplit.v3.capturemeter1b.m9negative1b.scenefingerprint1a', 1)
cp.write_text(c)

# Bump build identity without altering photographic paths.
gradle = root / 'app/build.gradle'
g = gradle.read_text()
needle = 'm9negative1acapturemeter1b'
if needle not in g:
    raise SystemExit('SCENEFINGERPRINT1A versionName M9NEGATIVE1A marker missing')
g = g.replace(needle, 'm9negative1bscenefingerprint1acapturemeter1b', 1)
g = g.replace("versionName '1.45-", "versionName '1.46-", 1)
gradle.write_text(g)

# Backlight diagnostic carries the frozen-build identity; update only that string marker if present.
back = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
if back.exists():
    b = back.read_text()
    if 'm9negative1acapturemeter1b' in b:
        b = b.replace('m9negative1acapturemeter1b', 'm9negative1bscenefingerprint1acapturemeter1b')
    if '1.45-' in b:
        b = b.replace('1.45-', '1.46-', 1)
    back.write_text(b)

print('M9Cam M9NEGATIVE1B / SCENEFINGERPRINT1A overlay applied')
print(' - completed RAW recommendation thresholds/math preserved from M9NEGATIVE1A')
print(' - scene association upgraded with existing preview distribution/spatial/exposure descriptors')
print(' - 60s completed-RAW recency gate; no unrelated fallback when no match passes')
print(' - live capture mutation remains disabled')
