#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-virtualbv-spatial1b.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'VIRTUALBVSPATIAL1B missing expected file: {rel}')
    return p.read_text()


def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
virtual_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'
constraint_ref_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
gradle_rel = 'app/build.gradle'

if 'm9cam.virtualbv.v1' not in read(virtual_rel):
    raise SystemExit('VIRTUALBVSPATIAL1B requires frozen VIRTUALBV1A')
if 'm9cam.constraintref.v1' not in read(constraint_ref_rel):
    raise SystemExit('VIRTUALBVSPATIAL1B requires CONSTRAINTREF1A')
if "versionName '1.53-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b-cr1a'" not in read(gradle_rel):
    raise SystemExit('VIRTUALBVSPATIAL1B expected CONSTRAINTREF1A 1.53 versionName missing')

# Research-only geometry probe. Freeze all live exposure, RAW-teacher, constraint,
# rendering and photographic seams. Only a new class, capture metadata publication,
# diagnostic build identity and CI are allowed to change.
frozen_rels = [
    virtual_rel,
    constraint_ref_rel,
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

candidate_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBvSpatial1B.java'
candidate_p = root / candidate_rel
if candidate_p.exists():
    raise SystemExit('VIRTUALBVSPATIAL1B target class already exists; refuse ambiguous reapply')

candidate = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * VIRTUALBVSPATIAL1B: diagnostic-only geometry probes beside frozen VIRTUALBV1A.
 *
 * Test 20 showed that the broad centerMedian can be much brighter than the
 * orientation-aware middle-center tile when a bright window/background occupies
 * a large part of the center region.  This class does NOT choose a new meter.
 * It logs three fixed spatial alternatives using the same Y=120 reference and
 * Photon/pre-FB1 EV zero point so only meter geometry changes.
 *
 * None of these weights are recovered Leica firmware constants.
 */
public final class M9VirtualBvSpatial1B {
    public static final String SCHEMA = "m9cam.virtualbv.spatial.v1b";
    private static final double REFERENCE_Y = 120.0;
    private static final double DIRECTION_DEADBAND_EV = 0.08;

    // Candidate A: moderate broad-center / middle-center / global blend.
    private static final double MODERATE_CENTER = 0.50;
    private static final double MODERATE_MIDDLE_CENTER = 0.30;
    private static final double MODERATE_GLOBAL = 0.20;

    // Candidate B: static 3x3 center-concentrated kernel, normalized by 9.0.
    // corners=.25, axial neighbors=.50, center=6.0. Research probe only.
    private static final double K_CORNER = 0.25;
    private static final double K_AXIS = 0.50;
    private static final double K_CENTER = 6.00;
    private static final double K_SUM = 9.00;

    // Candidate C: aggressive middle-center/global probe to bracket geometry.
    private static final double AGGRESSIVE_MIDDLE_CENTER = 0.80;
    private static final double AGGRESSIVE_GLOBAL = 0.20;

    private M9VirtualBvSpatial1B() {}

    public static JSONObject evaluate(JSONObject root) {
        JSONObject out = contract();
        try {
            if (root == null) return invalid(out, "metadata_root_missing");
            JSONObject scene = root.optJSONObject("m9SceneExposureDiagnostic");
            JSONObject inputs = scene != null ? scene.optJSONObject("inputs") : null;
            JSONObject tiles = inputs != null ? inputs.optJSONObject("spatialTileMedians3x3") : null;
            JSONObject base = root.optJSONObject("m9VirtualBv");
            if (scene == null || !scene.optBoolean("valid", false) || inputs == null || tiles == null
                    || base == null || !base.optBoolean("valid", false)) {
                return invalid(out, "scene_tiles_or_virtualbv1a_missing");
            }

            double global = inputs.optDouble("globalMedian", Double.NaN);
            double center = inputs.optDouble("centerMedian", Double.NaN);
            double tl = tiles.optDouble("topLeft", Double.NaN);
            double tc = tiles.optDouble("topCenter", Double.NaN);
            double tr = tiles.optDouble("topRight", Double.NaN);
            double ml = tiles.optDouble("middleLeft", Double.NaN);
            double mc = tiles.optDouble("middleCenter", Double.NaN);
            double mr = tiles.optDouble("middleRight", Double.NaN);
            double bl = tiles.optDouble("bottomLeft", Double.NaN);
            double bc = tiles.optDouble("bottomCenter", Double.NaN);
            double br = tiles.optDouble("bottomRight", Double.NaN);
            if (!finite(global) || !finite(center) || !finite(tl) || !finite(tc) || !finite(tr)
                    || !finite(ml) || !finite(mc) || !finite(mr) || !finite(bl)
                    || !finite(bc) || !finite(br)) {
                return invalid(out, "spatial_meter_inputs_non_finite");
            }

            double baseRequest = base.optDouble("signedMeterDeltaEv", Double.NaN);
            double photonBv = base.optDouble("photonEquivalentBvEv", Double.NaN);
            double fb1Applied = base.optDouble("luma24AppliedEv", 0.0);
            if (!finite(baseRequest) || !finite(photonBv) || !finite(fb1Applied)) {
                return invalid(out, "virtualbv1a_reference_coordinates_missing");
            }

            double moderateProxy = MODERATE_CENTER * center
                    + MODERATE_MIDDLE_CENTER * mc + MODERATE_GLOBAL * global;
            double kernelProxy = (K_CORNER * (tl + tr + bl + br)
                    + K_AXIS * (tc + ml + mr + bc) + K_CENTER * mc) / K_SUM;
            double aggressiveProxy = AGGRESSIVE_MIDDLE_CENTER * mc
                    + AGGRESSIVE_GLOBAL * global;

            JSONObject moderate = candidate("moderate_center_middle_global_50_30_20",
                    moderateProxy, photonBv, baseRequest, fb1Applied);
            JSONObject kernel = candidate("static_center_concentrated_3x3_kernel",
                    kernelProxy, photonBv, baseRequest, fb1Applied);
            JSONObject aggressive = candidate("middle_center_global_80_20_bracketing_probe",
                    aggressiveProxy, photonBv, baseRequest, fb1Applied);

            out.put("valid", true);
            out.put("reason", "spatial_meter_candidates_recorded_no_live_exposure_change");
            out.put("referenceY", REFERENCE_Y);
            out.put("referenceFrame", "photon_pre_fb1_exposure_baseline_same_as_virtualbv1a");
            out.put("baselineVirtualBv1ARequestEv", baseRequest);
            out.put("legacyFb1AppliedEv", fb1Applied);
            out.put("photonEquivalentBvEv", photonBv);
            out.put("globalMedian", global);
            out.put("broadCenterMedian", center);
            out.put("middleCenterTileMedian", mc);
            out.put("broadCenterMinusMiddleCenterTileY", center - mc);
            out.put("moderateBlend", moderate);
            out.put("centerConcentratedKernel", kernel);
            out.put("aggressiveMiddleCenterProbe", aggressive);
            out.put("kernelWeights",
                    "corners_0.25_axis_0.50_center_6.00_sum_9.00_not_leica_firmware_constants");
            out.put("calibrationState",
                    "geometry_candidates_only_keep_virtualbv1a_y120_and_all_live_exposure_frozen");
        } catch (Throwable t) {
            try { invalid(out, "virtualbv_spatial1b_exception"); out.put("error", t.toString()); }
            catch (Exception ignored) {}
        }
        return out;
    }

    private static JSONObject candidate(String name, double proxyY, double photonBv,
                                        double baseRequest, double fb1Applied) {
        JSONObject out = new JSONObject();
        try {
            double requestEv = log2(REFERENCE_Y / Math.max(proxyY, 1e-6));
            out.put("name", name);
            out.put("proxyY", proxyY);
            out.put("signedMeterDeltaFromPhotonEv", requestEv);
            out.put("virtualBvEv", photonBv - requestEv);
            out.put("deltaVsVirtualBv1AEv", requestEv - baseRequest);
            out.put("residualAfterLegacyFb1Ev", requestEv - fb1Applied);
            out.put("direction", direction(requestEv));
        } catch (Exception ignored) {}
        return out;
    }

    private static JSONObject contract() {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("jpegBrightnessUsedForCapture", false);
            out.put("rawFeedbackUsedForMeter", false);
            out.put("renderedLumaUsedForMeter", false);
            out.put("baselineMeterFrozen", "VIRTUALBV1A_70pct_center_30pct_global_Y120");
            out.put("purpose", "test_spatial_meter_geometry_without_promoting_a_winner");
        } catch (Exception ignored) {}
        return out;
    }

    private static JSONObject invalid(JSONObject out, String reason) {
        try {
            out.put("valid", false);
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("reason", reason);
        } catch (Exception ignored) {}
        return out;
    }

    private static String direction(double ev) {
        if (!finite(ev)) return "invalid";
        if (Math.abs(ev) < DIRECTION_DEADBAND_EV) return "neutral";
        return ev > 0.0 ? "increase" : "decrease";
    }
    private static boolean finite(double x) { return !Double.isNaN(x) && !Double.isInfinite(x); }
    private static double log2(double x) { return Math.log(Math.max(x, 1e-12)) / Math.log(2.0); }
}
'''
candidate_p.parent.mkdir(parents=True, exist_ok=True)
candidate_p.write_text(candidate)

metadata_p = root / meta_rel
metadata = metadata_p.read_text()
metadata_anchor = '''            root.put("m9ConstraintRef", M9ConstraintRef1A.evaluateCapture(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
metadata_repl = '''            root.put("m9ConstraintRef", M9ConstraintRef1A.evaluateCapture(root));\n            root.put("m9VirtualBvSpatialCandidate", M9VirtualBvSpatial1B.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
if metadata_anchor not in metadata:
    raise SystemExit('VIRTUALBVSPATIAL1B metadata anchor missing')
metadata_p.write_text(metadata.replace(metadata_anchor, metadata_repl, 1))

gradle_p = root / gradle_rel
gradle = gradle_p.read_text()
old_version = "versionName '1.53-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cm1b-cr1a'"
new_version = "versionName '1.54-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b'"
if old_version not in gradle:
    raise SystemExit('VIRTUALBVSPATIAL1B 1.53 versionName anchor missing')
gradle_p.write_text(gradle.replace(old_version, new_version, 1))

back_p = root / back_rel
back = back_p.read_text()
marker_anchor = 'constraintref1ascenefingerprint1b'
marker_repl = 'constraintref1avirtualbvspatial1bscenefingerprint1b'
if marker_anchor not in back:
    raise SystemExit('VIRTUALBVSPATIAL1B forensic marker anchor missing')
back = back.replace(marker_anchor, marker_repl, 1)
if '1.53-' not in back:
    raise SystemExit('VIRTUALBVSPATIAL1B backlight version anchor missing')
back_p.write_text(back.replace('1.53-', '1.54-', 1))

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'VIRTUALBVSPATIAL1B froze seam changed unexpectedly: {rel}')

print('M9Cam VIRTUALBVSPATIAL1B diagnostic geometry probes applied')
print(' - frozen VIRTUALBV1A 70/30 Y120 remains the baseline and constraint input')
print(' - adds moderate, static center-concentrated 3x3, and aggressive bracketing probes')
print(' - uses existing orientation-aware tile medians only; no RAW/render teacher enters meter')
print(' - no Camera2, FB1, motion, constraint, renderer, JPEG or DNG mutation')