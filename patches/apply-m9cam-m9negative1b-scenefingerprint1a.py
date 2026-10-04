#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9negative1b-scenefingerprint1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
p = root / negative_rel
if not p.exists():
    raise SystemExit('SCENEFINGERPRINT1A requires M9NEGATIVE1A generated source')
s = p.read_text()
if 'm9cam.m9negative.v1.capturemeter1b.completedraw1a' not in s:
    raise SystemExit('SCENEFINGERPRINT1A requires M9NEGATIVE1A schema')

# Association-only revision. The completed-RAW recommendation equations are intentionally untouched.
s = s.replace('m9cam.m9negative.v1.capturemeter1b.completedraw1a',
              'm9cam.m9negative.v2.capturemeter1b.scenefingerprint1a', 1)
s = s.replace('private static final double SIMILAR_SCENE_DISTANCE = 1.0;\n',
              'private static final double SIMILAR_SCENE_DISTANCE = 1.0;\n'
              '    private static final long MAX_FEEDBACK_AGE_MS = 60_000L;\n', 1)

old_fields = '''        double median;\n        double center;\n        double q99;\n        double starvation;\n'''
new_fields = '''        double median;\n        double center;\n        double q95;\n        double q99;\n        double dark64;\n        double bright192;\n        double bright224;\n        double centerDelta;\n        double middleCenterQ95;\n        double starvation;\n        double previewEnergyIsoSeconds;\n'''
if old_fields not in s:
    raise SystemExit('SCENEFINGERPRINT1A SceneSignature fields anchor missing')
s = s.replace(old_fields, new_fields, 1)

old_from = '''            double median = inputs.optDouble("globalMedian", Double.NaN);\n            double center = inputs.optDouble("centerMedian", Double.NaN);\n            double q99 = inputs.optDouble("globalQ99", Double.NaN);\n            double starvation = positive.optDouble("spatialQualificationStarvationPressure",\n                    positive.optDouble("luma24BacklightPressure", Double.NaN));\n            if (!finite(median) || !finite(center) || !finite(q99) || !finite(starvation)) return null;\n            SceneSignature s = new SceneSignature();\n            s.sequence = sequence;\n            s.median = median;\n            s.center = center;\n            s.q99 = q99;\n            s.starvation = starvation;\n            return s;\n'''
new_from = '''            double median = inputs.optDouble("globalMedian", Double.NaN);\n            double center = inputs.optDouble("centerMedian", Double.NaN);\n            double q95 = inputs.optDouble("globalQ95", Double.NaN);\n            double q99 = inputs.optDouble("globalQ99", Double.NaN);\n            double dark64 = inputs.optDouble("darkFractionLE64", Double.NaN);\n            double bright192 = inputs.optDouble("brightFractionGE192", Double.NaN);\n            double bright224 = inputs.optDouble("brightFractionGE224", Double.NaN);\n            double centerDelta = inputs.optDouble("centerMedianMinusGlobalMedian", Double.NaN);\n            double middleCenterQ95 = inputs.optDouble("middleCenterQ95", Double.NaN);\n            double starvation = positive.optDouble("spatialQualificationStarvationPressure",\n                    positive.optDouble("luma24BacklightPressure", Double.NaN));\n            double previewEnergyIsoSeconds = scene.optDouble("previewExposureEnergyIsoSeconds", Double.NaN);\n\n            if (!finite(median) || !finite(center) || !finite(q99) || !finite(starvation)) return null;\n            SceneSignature s = new SceneSignature();\n            s.sequence = sequence;\n            s.median = median;\n            s.center = center;\n            s.q95 = q95;\n            s.q99 = q99;\n            s.dark64 = dark64;\n            s.bright192 = bright192;\n            s.bright224 = bright224;\n            s.centerDelta = centerDelta;\n            s.middleCenterQ95 = middleCenterQ95;\n            s.starvation = starvation;\n            s.previewEnergyIsoSeconds = previewEnergyIsoSeconds;\n            return s;\n'''
if old_from not in s:
    raise SystemExit('SCENEFINGERPRINT1A SceneSignature.from anchor missing')
s = s.replace(old_from, new_from, 1)

old_distance = '''        double distance(SceneSignature other) {\n            if (other == null) return Double.POSITIVE_INFINITY;\n            return Math.max(Math.abs(median - other.median) / 40.0,\n                    Math.max(Math.abs(center - other.center) / 40.0,\n                    Math.max(Math.abs(q99 - other.q99) / 50.0,\n                            Math.abs(starvation - other.starvation) / 0.50)));\n        }\n'''
new_distance = '''        double distance(SceneSignature other) {\n            if (other == null) return Double.POSITIVE_INFINITY;\n            double d = 0.0;\n            d = Math.max(d, normalizedDelta(median, other.median, 40.0));\n            d = Math.max(d, normalizedDelta(center, other.center, 40.0));\n            d = Math.max(d, normalizedDelta(q95, other.q95, 48.0));\n            d = Math.max(d, normalizedDelta(q99, other.q99, 50.0));\n            d = Math.max(d, normalizedDelta(dark64, other.dark64, 0.22));\n            d = Math.max(d, normalizedDelta(bright192, other.bright192, 0.18));\n            d = Math.max(d, normalizedDelta(bright224, other.bright224, 0.10));\n            d = Math.max(d, normalizedDelta(centerDelta, other.centerDelta, 50.0));\n            d = Math.max(d, normalizedDelta(middleCenterQ95, other.middleCenterQ95, 50.0));\n            d = Math.max(d, normalizedDelta(starvation, other.starvation, 0.50));\n            if (finite(previewEnergyIsoSeconds) && finite(other.previewEnergyIsoSeconds)\n                    && previewEnergyIsoSeconds > 0.0 && other.previewEnergyIsoSeconds > 0.0) {\n                d = Math.max(d, Math.abs(log2(previewEnergyIsoSeconds / other.previewEnergyIsoSeconds)) / 1.50);\n            }\n            return d;\n        }\n'''
if old_distance not in s:
    raise SystemExit('SCENEFINGERPRINT1A distance anchor missing')
s = s.replace(old_distance, new_distance, 1)

anchor = '''    private static final class CompletedRaw {\n'''
helper = '''    private static double normalizedDelta(double a, double b, double scale) {\n        if (!finite(a) || !finite(b)) return 0.0;\n        return Math.abs(a - b) / Math.max(scale, 1e-9);\n    }\n\n    private static final class CompletedRaw {\n'''
if anchor not in s:
    raise SystemExit('SCENEFINGERPRINT1A normalizedDelta insertion anchor missing')
s = s.replace(anchor, helper, 1)

old_loop = '''            for (int i = history.size() - 1; i >= 0; i--) {\n                CompletedRaw candidate = history.get(i);\n                if (candidate.scene == null) continue;\n                double d = current.distance(candidate.scene);\n                if (d < bestDistance) {\n                    bestDistance = d;\n                    best = candidate;\n                }\n            }\n            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);\n            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n            if (best == null || !finite(bestDistance) || bestDistance > SIMILAR_SCENE_DISTANCE) {\n'''
new_loop = '''            long nowMs = System.currentTimeMillis();\n            int recentCandidateCount = 0;\n            int expiredCandidateCount = 0;\n            for (int i = history.size() - 1; i >= 0; i--) {\n                CompletedRaw candidate = history.get(i);\n                if (candidate.scene == null) continue;\n                long ageMs = Math.max(0L, nowMs - candidate.completedEpochMs);\n                if (ageMs > MAX_FEEDBACK_AGE_MS) {\n                    expiredCandidateCount++;\n                    continue;\n                }\n                recentCandidateCount++;\n                double d = current.distance(candidate.scene);\n                if (d < bestDistance) {\n                    bestDistance = d;\n                    best = candidate;\n                }\n            }\n            out.put("sceneFingerprintSchema", "m9cam.scenefingerprint.v1.scene1h_existingfields1a");\n            out.put("nearestCompletedSceneDistance", finite(bestDistance) ? bestDistance : JSONObject.NULL);\n            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n            out.put("maxFeedbackAgeMs", MAX_FEEDBACK_AGE_MS);\n            out.put("recentCandidateCount", recentCandidateCount);\n            out.put("expiredCandidateCount", expiredCandidateCount);\n            if (best == null || !finite(bestDistance) || bestDistance > SIMILAR_SCENE_DISTANCE) {\n'''
if old_loop not in s:
    raise SystemExit('SCENEFINGERPRINT1A candidate loop anchor missing')
s = s.replace(old_loop, new_loop, 1)

old_reason = '''                out.put("reason", best == null\n                        ? "no_completed_raw_with_scene_signature_yet"\n                        : "completed_raw_not_scene_similar_enough");\n'''
new_reason = '''                out.put("reason", best == null\n                        ? (history.isEmpty()\n                            ? "no_completed_raw_with_scene_signature_yet"\n                            : recentCandidateCount == 0\n                            ? "completed_raw_feedback_expired"\n                            : "no_recent_completed_raw_with_scene_signature")\n                        : "completed_raw_not_scene_similar_enough");\n'''
if old_reason not in s:
    raise SystemExit('SCENEFINGERPRINT1A rejection reason anchor missing')
s = s.replace(old_reason, new_reason, 1)

age_anchor = 'out.put("sourceAgeMs", Math.max(0L, System.currentTimeMillis() - best.completedEpochMs));'
if age_anchor not in s:
    raise SystemExit('SCENEFINGERPRINT1A source-age anchor missing')
s = s.replace(age_anchor,
              'out.put("sourceAgeMs", Math.max(0L, nowMs - best.completedEpochMs));\n'
              '            out.put("associationPolicy", "recent_scene1h_fingerprint_then_completed_raw");', 1)

p.write_text(s)

coord_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'
cp = root / coord_rel
c = cp.read_text()
if 'm9cam.exposuresplit.v2.capturemeter1b.m9negative1a' not in c:
    raise SystemExit('SCENEFINGERPRINT1A requires CAPTUREMETER1B/M9NEGATIVE1A coordinator')
c = c.replace('m9cam.exposuresplit.v2.capturemeter1b.m9negative1a',
              'm9cam.exposuresplit.v3.capturemeter1b.m9negative1b.scenefingerprint1a', 1)
cp.write_text(c)

# Keep Android's versionName compact because AGP embeds it in the APK filename. The full
# forensic identity remains in the diagnostic schemas and M9BacklightDiagnostic build marker.
gradle = root / 'app/build.gradle'
g = gradle.read_text()
lines = g.splitlines()
version_index = -1
for i, line in enumerate(lines):
    if "versionName '1.45-" in line and 'm9negative1acapturemeter1b' in line:
        version_index = i
        break
if version_index < 0:
    raise SystemExit('SCENEFINGERPRINT1A expected long 1.45 M9NEGATIVE1A versionName missing')
indent = lines[version_index][:len(lines[version_index]) - len(lines[version_index].lstrip())]
lines[version_index] = indent + "versionName '1.46-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1b-fp1a-cm1b'"
gradle.write_text('\n'.join(lines) + ('\n' if g.endswith('\n') else ''))

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
print(' - association uses existing SCENEEXPOSURE1H distribution/center/preview-energy fields')
print(' - 60s completed-RAW recency gate; no unrelated fallback when no match passes')
print(' - compact Android versionName prevents AGP/Linux APK filename overflow')
print(' - live capture mutation remains disabled')
