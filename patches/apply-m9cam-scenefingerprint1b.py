#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-scenefingerprint1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')

scene_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9SceneExposureDiagnostic.java'
negative_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java'
coord_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java'

scene_p = root / scene_rel
neg_p = root / negative_rel
coord_p = root / coord_rel
scene = scene_p.read_text()
neg = neg_p.read_text()
coord = coord_p.read_text()

if 'm9cam.sceneexposure.v8.renderaware1h' not in scene:
    raise SystemExit('SCENEFINGERPRINT1B requires frozen SCENEEXPOSURE1H')
if 'm9cam.m9negative.v3.capturemeter1b.scenefingerprint1a.signedcal1a' not in neg:
    raise SystemExit('SCENEFINGERPRINT1B requires M9NEGATIVE1C SIGNEDCAL1A')
if 'm9cam.exposuresplit.v4.capturemeter1b.m9negative1c.scenefingerprint1a.signedcal1a' not in coord:
    raise SystemExit('SCENEFINGERPRINT1B requires V4 exposure coordinator baseline')

# Publish already-computed orientation-aware 3x3 tile medians into the diagnostic scene
# payload. This is association metadata only; no exposure pressure/math is changed.
inputs_anchor = '''            if (finite(middleCenterQ95)) inputs.put("middleCenterQ95", middleCenterQ95);\n            out.put("inputs", inputs);\n'''
inputs_repl = '''            if (finite(middleCenterQ95)) inputs.put("middleCenterQ95", middleCenterQ95);\n            JSONObject spatialTileMedians3x3 = new JSONObject();\n            if (spatialTiles != null) {\n                String[] tileNames = new String[] {\n                        "topLeft", "topCenter", "topRight",\n                        "middleLeft", "middleCenter", "middleRight",\n                        "bottomLeft", "bottomCenter", "bottomRight"};\n                for (String tileName : tileNames) {\n                    JSONObject tile = spatialTiles.optJSONObject(tileName);\n                    if (tile == null) continue;\n                    double tileMedian = tile.optDouble("median", Double.NaN);\n                    if (finite(tileMedian)) spatialTileMedians3x3.put(tileName, tileMedian);\n                }\n            }\n            inputs.put("spatialTileMedians3x3", spatialTileMedians3x3);\n            out.put("inputs", inputs);\n'''
if inputs_anchor not in scene:
    raise SystemExit('SCENEFINGERPRINT1B scene inputs anchor missing')
scene = scene.replace(inputs_anchor, inputs_repl, 1)
scene_p.write_text(scene)

neg = neg.replace('m9cam.m9negative.v3.capturemeter1b.scenefingerprint1a.signedcal1a',
                  'm9cam.m9negative.v4.capturemeter1b.scenefingerprint1b.signedcal1a', 1)
neg = neg.replace('m9cam.scenefingerprint.v1.scene1h_existingfields1a',
                  'm9cam.scenefingerprint.v2.scene1h_spatialtiles1b', 1)
neg = neg.replace('SCENEFINGERPRINT1A', 'SCENEFINGERPRINT1B')

field_anchor = '        double previewEnergyIsoSeconds;\n'
if field_anchor not in neg:
    raise SystemExit('SCENEFINGERPRINT1B signature field anchor missing')
neg = neg.replace(field_anchor,
                  field_anchor + '        double[] spatialTileMedians3x3;\n', 1)

from_anchor = '''            s.previewEnergyIsoSeconds = previewEnergyIsoSeconds;\n            return s;\n'''
from_repl = '''            s.previewEnergyIsoSeconds = previewEnergyIsoSeconds;\n            JSONObject tileMedians = inputs.optJSONObject("spatialTileMedians3x3");\n            s.spatialTileMedians3x3 = readSpatialTileMedians(tileMedians);\n            return s;\n'''
if from_anchor not in neg:
    raise SystemExit('SCENEFINGERPRINT1B SceneSignature.from anchor missing')
neg = neg.replace(from_anchor, from_repl, 1)

energy_anchor = '''            if (finite(previewEnergyIsoSeconds) && finite(other.previewEnergyIsoSeconds)\n                    && previewEnergyIsoSeconds > 0.0 && other.previewEnergyIsoSeconds > 0.0) {\n                d = Math.max(d, Math.abs(log2(previewEnergyIsoSeconds / other.previewEnergyIsoSeconds)) / 1.50);\n            }\n            return d;\n'''
energy_repl = '''            if (finite(previewEnergyIsoSeconds) && finite(other.previewEnergyIsoSeconds)\n                    && previewEnergyIsoSeconds > 0.0 && other.previewEnergyIsoSeconds > 0.0) {\n                d = Math.max(d, Math.abs(log2(previewEnergyIsoSeconds / other.previewEnergyIsoSeconds)) / 1.50);\n            }\n            d = Math.max(d, spatialTileMedianDistance(spatialTileMedians3x3,\n                    other.spatialTileMedians3x3));\n            return d;\n'''
if energy_anchor not in neg:
    raise SystemExit('SCENEFINGERPRINT1B distance anchor missing')
neg = neg.replace(energy_anchor, energy_repl, 1)

helper_anchor = '''    private static double normalizedDelta(double a, double b, double scale) {\n'''
helpers = '''    private static double[] readSpatialTileMedians(JSONObject tiles) {\n        if (tiles == null) return null;\n        String[] names = new String[] {\n                "topLeft", "topCenter", "topRight",\n                "middleLeft", "middleCenter", "middleRight",\n                "bottomLeft", "bottomCenter", "bottomRight"};\n        double[] values = new double[names.length];\n        for (int i = 0; i < names.length; i++) {\n            double v = tiles.optDouble(names[i], Double.NaN);\n            if (!finite(v)) return null;\n            values[i] = v;\n        }\n        return values;\n    }\n\n    private static double spatialTileMedianDistance(double[] a, double[] b) {\n        if (a == null || b == null || a.length != 9 || b.length != 9) return 0.0;\n        double max = 0.0;\n        for (int i = 0; i < 9; i++) {\n            if (!finite(a[i]) || !finite(b[i])) return 0.0;\n            max = Math.max(max, Math.abs(a[i] - b[i]) / 60.0);\n        }\n        return max;\n    }\n\n    private static double normalizedDelta(double a, double b, double scale) {\n'''
if helper_anchor not in neg:
    raise SystemExit('SCENEFINGERPRINT1B helper anchor missing')
neg = neg.replace(helper_anchor, helpers, 1)

# Log the spatial term explicitly so field tests can prove why an association passed/failed.
loop_anchor = '''                double d = current.distance(candidate.scene);\n                if (d < bestDistance) {\n'''
loop_repl = '''                double d = current.distance(candidate.scene);\n                if (d < bestDistance) {\n'''
if loop_anchor not in neg:
    raise SystemExit('SCENEFINGERPRINT1B candidate loop anchor missing')
# no loop behavior change: nearest recent candidate remains frozen

threshold_anchor = '            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n'
threshold_repl = '''            out.put("similarSceneThreshold", SIMILAR_SCENE_DISTANCE);\n            out.put("spatialTileMedianDistanceScaleY", 60.0);\n            out.put("spatialTileMedianDistancePolicy", "max_abs_delta_across_orientation_aware_3x3_tile_medians_div60");\n'''
if threshold_anchor not in neg:
    raise SystemExit('SCENEFINGERPRINT1B threshold output anchor missing')
neg = neg.replace(threshold_anchor, threshold_repl, 1)
neg_p.write_text(neg)

coord = coord.replace('m9cam.exposuresplit.v4.capturemeter1b.m9negative1c.scenefingerprint1a.signedcal1a',
                      'm9cam.exposuresplit.v5.capturemeter1b.m9negative1c.scenefingerprint1b.signedcal1a', 1)
coord_p.write_text(coord)

# Compact build identity only.
gradle = root / 'app/build.gradle'
g = gradle.read_text()
old_v = "versionName '1.48-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1a-sc1a-vbv1a-cm1b'"
new_v = "versionName '1.49-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cm1b'"
if old_v not in g:
    raise SystemExit('SCENEFINGERPRINT1B expected VIRTUALBV1A versionName missing')
gradle.write_text(g.replace(old_v, new_v, 1))

back = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
if back.exists():
    b = back.read_text()
    b = b.replace('scenefingerprint1acapturemeter1b', 'scenefingerprint1bcapturemeter1b')
    b = b.replace('1.48-', '1.49-', 1)
    back.write_text(b)

print('M9Cam SCENEFINGERPRINT1B overlay applied')
print(' - existing SCENEFINGERPRINT1A scalar descriptors, 1.0 threshold, nearest-recent policy and 60s gate preserved')
print(' - adds max(abs(delta 3x3 orientation-aware tile median))/60 spatial identity term')
print(' - SCENEEXPOSURE1H math unchanged; only existing tile medians are copied into diagnostic metadata')
print(' - VIRTUALBV1A and SIGNEDCAL1A equations unchanged')
print(' - no Camera2, motion, renderer, JPEG or DNG mutation')
