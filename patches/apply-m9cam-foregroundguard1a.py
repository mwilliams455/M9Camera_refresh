#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-foregroundguard1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit(f'not a PhotonCamera root: {root}')


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit(f'FOREGROUNDGUARD1A missing expected file: {rel}')
    return p.read_text()


def sha256(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

meta_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
virtual_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'
spatial_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBvSpatial1B.java'
constraint_ref_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintRef1A.java'
back_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java'
gradle_rel = 'app/build.gradle'

if 'm9cam.virtualbv.v1' not in read(virtual_rel):
    raise SystemExit('FOREGROUNDGUARD1A requires frozen VIRTUALBV1A')
if 'm9cam.virtualbv.spatial.v1b' not in read(spatial_rel):
    raise SystemExit('FOREGROUNDGUARD1A requires VIRTUALBVSPATIAL1B research build')
if 'm9cam.constraintref.v1' not in read(constraint_ref_rel):
    raise SystemExit('FOREGROUNDGUARD1A requires CONSTRAINTREF1A')
expected_version = "versionName '1.54-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b'"
if expected_version not in read(gradle_rel):
    raise SystemExit('FOREGROUNDGUARD1A expected VIRTUALBVSPATIAL1B 1.54 versionName missing')

# Diagnostic-only architecture probe. The Leica-like meter remains VIRTUALBV1A.
# Legacy FB1 is observed only as a foreground-collapse floor signal, not added on top.
# CONSTRAINTREF1A remains the only sensor-ceiling source. No live seam may change.
frozen_rels = [
    virtual_rel,
    spatial_rel,
    constraint_ref_rel,
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ConstraintSplit1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9NegativeFeedback1A.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureRenderExposureCoordinator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
    'app/src/main/cpp/m9color_jni.cpp',
]
frozen_before = {rel: sha256(rel) for rel in frozen_rels}

guard_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ForegroundGuard1A.java'
guard_p = root / guard_rel
if guard_p.exists():
    raise SystemExit('FOREGROUNDGUARD1A target class already exists; refuse ambiguous reapply')

guard = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

/**
 * FOREGROUNDGUARD1A: diagnostic-only bounded foreground-separation floor.
 *
 * Architectural intent established by test 902:
 *   1. VIRTUALBV1A remains the Leica-like signed base exposure request.
 *   2. Legacy FB1 is NOT stacked onto that request. Its already-field-tested applied
 *      target is observed only when FB1 says a foreground-collapse condition exists.
 *   3. The base may be lifted toward that FB1 target by at most +0.50 EV.
 *   4. CONSTRAINTREF1A reference-aligned RAW ceilings are then applied to both the
 *      base and guarded target for a like-for-like sensor-safety comparison.
 *
 * +0.50 EV is a provisional field-test bound, not a Leica firmware constant.
 * This class cannot mutate Camera2, exposure allocation, FB1, renderer, JPEG or DNG.
 */
public final class M9ForegroundGuard1A {
    public static final String SCHEMA = "m9cam.foregroundguard.v1a";
    private static final double MAX_FOREGROUND_BUMP_EV = 0.50;
    private static final double MATERIAL_DELTA_EV = 0.08;

    private M9ForegroundGuard1A() {}

    public static JSONObject evaluate(JSONObject root) {
        JSONObject out = contract();
        try {
            if (root == null) return invalid(out, "metadata_root_missing");
            JSONObject base = root.optJSONObject("m9VirtualBv");
            JSONObject constraint = root.optJSONObject("m9ConstraintRef");
            if (base == null || !base.optBoolean("valid", false)) {
                return invalid(out, "virtualbv1a_missing_or_invalid");
            }

            double baseEv = base.optDouble("signedMeterDeltaEv", Double.NaN);
            boolean fb1WouldApply = base.optBoolean("luma24WouldApply", false);
            double fb1Recommended = base.optDouble("luma24RecommendedEv", Double.NaN);
            double fb1Applied = base.optDouble("luma24AppliedEv", Double.NaN);
            if (!finite(baseEv) || !finite(fb1Applied)) {
                return invalid(out, "base_or_fb1_reference_missing");
            }

            // Floor, not addition: only the positive gap between the Leica-like base
            // and the legacy FB1 applied target can contribute, and only when FB1's
            // foreground-collapse classifier says it would apply.
            double requestedGap = fb1WouldApply
                    ? Math.max(0.0, fb1Applied - baseEv) : 0.0;
            double boundedBump = Math.min(MAX_FOREGROUND_BUMP_EV, requestedGap);
            double preSensorTarget = baseEv + boundedBump;

            ConstraintCoordinates sensor = coordinates(constraint);
            ConstraintResult baseAfterSensor = constrain(baseEv, sensor, "base");
            ConstraintResult guardAfterSensor = constrain(preSensorTarget, sensor, "guarded_target");

            double retainedBump = finite(baseAfterSensor.ev) && finite(guardAfterSensor.ev)
                    ? Math.max(0.0, guardAfterSensor.ev - baseAfterSensor.ev) : Double.NaN;

            out.put("valid", true);
            out.put("reason", "bounded_foreground_floor_recorded_no_live_exposure_change");
            out.put("baseVirtualBvRequestFromPhotonEv", baseEv);
            out.put("fb1WouldApply", fb1WouldApply);
            putFinite(out, "legacyFb1RecommendedEv", fb1Recommended);
            out.put("legacyFb1AppliedEv", fb1Applied);
            out.put("fb1Use", "foreground_collapse_floor_signal_only_not_additive_exposure");
            out.put("requestedForegroundGapEv", requestedGap);
            out.put("maxForegroundBumpEv", MAX_FOREGROUND_BUMP_EV);
            out.put("boundedForegroundBumpEv", boundedBump);
            out.put("guardActivated", boundedBump > 0.0);
            out.put("guardMaterialAt0p08Ev", boundedBump >= MATERIAL_DELTA_EV);
            out.put("guardLimitedByMaxBump", requestedGap > MAX_FOREGROUND_BUMP_EV + 1e-12);
            out.put("preSensorGuardedTargetFromPhotonEv", preSensorTarget);

            out.put("sensorConstraintAvailable", sensor.available);
            out.put("sensorConstraintSource", sensor.source);
            putFinite(out, "sensorPositiveCeilingFromPhotonEv", sensor.positiveCeilingEv);
            out.put("sensorMandatoryCeilingAvailable", sensor.mandatoryAvailable);
            putFinite(out, "sensorMandatoryCeilingFromPhotonEv", sensor.mandatoryCeilingEv);
            putFinite(out, "sensorConstrainedBaseFromPhotonEv", baseAfterSensor.ev);
            out.put("sensorConstrainedBaseReason", baseAfterSensor.reason);
            putFinite(out, "sensorConstrainedGuardedTargetFromPhotonEv", guardAfterSensor.ev);
            out.put("sensorConstrainedGuardReason", guardAfterSensor.reason);
            out.put("sensorChangedBase", finite(baseAfterSensor.ev)
                    && Math.abs(baseAfterSensor.ev - baseEv) > 1e-12);
            out.put("sensorChangedGuardedTarget", finite(guardAfterSensor.ev)
                    && Math.abs(guardAfterSensor.ev - preSensorTarget) > 1e-12);
            putFinite(out, "retainedForegroundBumpAfterSensorEv", retainedBump);
            putFinite(out, "finalDiagnosticTargetFromPhotonEv", guardAfterSensor.ev);
            if (finite(guardAfterSensor.ev)) {
                out.put("finalMinusVirtualBvBaseEv", guardAfterSensor.ev - baseEv);
                out.put("finalMinusLegacyFb1AppliedEv", guardAfterSensor.ev - fb1Applied);
            } else {
                out.put("finalMinusVirtualBvBaseEv", JSONObject.NULL);
                out.put("finalMinusLegacyFb1AppliedEv", JSONObject.NULL);
            }
            out.put("negativeBasePreservedWhenGuardInactive",
                    !fb1WouldApply && baseEv < 0.0 && finite(guardAfterSensor.ev)
                            ? Math.abs(guardAfterSensor.ev - baseAfterSensor.ev) < 1e-12
                            : JSONObject.NULL);
        } catch (Throwable t) {
            try { invalid(out, "foregroundguard1a_exception"); out.put("error", t.toString()); }
            catch (Exception ignored) {}
        }
        return out;
    }

    private static ConstraintCoordinates coordinates(JSONObject c) {
        if (c == null || !c.optBoolean("valid", false)) {
            return ConstraintCoordinates.none("constraintref1a_missing_or_invalid");
        }

        int envelopeCount = c.optInt("conservativeEnvelopeReferenceAlignedCandidateCount", 0);
        double envPos = c.optDouble("conservativeEnvelopePositiveCeilingFromPhotonEv", Double.NaN);
        boolean envMandAvailable = c.optBoolean("conservativeEnvelopeMandatoryCeilingFromPhotonAvailable", false);
        double envMand = c.optDouble("conservativeEnvelopeMandatoryCeilingFromPhotonEv", Double.NaN);
        if (envelopeCount > 0 && (finite(envPos) || (envMandAvailable && finite(envMand)))) {
            return new ConstraintCoordinates(true, finite(envPos) ? envPos : Double.NaN,
                    envMandAvailable && finite(envMand), envMand,
                    "constraintref1a_conservative_reference_aligned_envelope");
        }

        boolean matched = c.optBoolean("matchedRawAvailable", false);
        double matchedPos = c.optDouble("matchedSensorPositiveCeilingFromPhotonEv", Double.NaN);
        boolean matchedMandAvailable = c.optBoolean("matchedSensorMandatoryCeilingFromPhotonAvailable", false);
        double matchedMand = c.optDouble("matchedSensorMandatoryCeilingFromPhotonEv", Double.NaN);
        if (matched && (finite(matchedPos) || (matchedMandAvailable && finite(matchedMand)))) {
            return new ConstraintCoordinates(true, finite(matchedPos) ? matchedPos : Double.NaN,
                    matchedMandAvailable && finite(matchedMand), matchedMand,
                    "constraintref1a_nearest_fp1b_reference_aligned_raw");
        }
        return ConstraintCoordinates.none("no_reference_aligned_raw_ceiling_available");
    }

    private static ConstraintResult constrain(double requestEv, ConstraintCoordinates c, String source) {
        if (!finite(requestEv)) return new ConstraintResult(Double.NaN, source + "_request_invalid");
        if (c.mandatoryAvailable && finite(c.mandatoryCeilingEv)) {
            double x = Math.min(requestEv, c.mandatoryCeilingEv);
            return new ConstraintResult(x, Math.abs(x - requestEv) > 1e-12
                    ? source + "_mandatory_ceiling_limited" : source + "_within_mandatory_ceiling");
        }
        if (requestEv > 0.0 && finite(c.positiveCeilingEv)) {
            double x = Math.min(requestEv, c.positiveCeilingEv);
            return new ConstraintResult(x, Math.abs(x - requestEv) > 1e-12
                    ? source + "_positive_ceiling_limited" : source + "_within_positive_ceiling");
        }
        return new ConstraintResult(requestEv, c.available
                ? source + "_signed_request_preserved" : source + "_no_raw_constraint_preserved");
    }

    private static JSONObject contract() {
        JSONObject out = new JSONObject();
        try {
            out.put("schema", SCHEMA);
            out.put("mode", "diagnostic_only_no_exposure_mutation");
            out.put("liveEligible", false);
            out.put("usedToMutateCaptureTarget", false);
            out.put("baseMeter", "VIRTUALBV1A_signed_photon_relative_request");
            out.put("foregroundMechanism", "legacy_FB1_applied_target_as_bounded_floor_signal");
            out.put("sensorAuthority", "CONSTRAINTREF1A_reference_aligned_RAW_ceiling");
            out.put("spatialProbeAuthority", "none_observation_only");
            out.put("architecture",
                    "virtualbv1a_base_then_fb1_floor_max_plus0p50_then_constraintref1a_sensor_ceiling");
            out.put("maxBumpCalibration",
                    "provisional_plus0p50_from_test902_architecture_probe_not_leica_constant");
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

    private static void putFinite(JSONObject out, String key, double value) {
        try { out.put(key, finite(value) ? value : JSONObject.NULL); } catch (Exception ignored) {}
    }
    private static boolean finite(double x) { return !Double.isNaN(x) && !Double.isInfinite(x); }

    private static final class ConstraintCoordinates {
        final boolean available;
        final double positiveCeilingEv;
        final boolean mandatoryAvailable;
        final double mandatoryCeilingEv;
        final String source;
        ConstraintCoordinates(boolean available, double positiveCeilingEv,
                              boolean mandatoryAvailable, double mandatoryCeilingEv,
                              String source) {
            this.available = available;
            this.positiveCeilingEv = positiveCeilingEv;
            this.mandatoryAvailable = mandatoryAvailable;
            this.mandatoryCeilingEv = mandatoryCeilingEv;
            this.source = source;
        }
        static ConstraintCoordinates none(String source) {
            return new ConstraintCoordinates(false, Double.NaN, false, Double.NaN, source);
        }
    }

    private static final class ConstraintResult {
        final double ev;
        final String reason;
        ConstraintResult(double ev, String reason) { this.ev = ev; this.reason = reason; }
    }
}
'''

guard_p.parent.mkdir(parents=True, exist_ok=True)
guard_p.write_text(guard)

metadata_p = root / meta_rel
metadata = metadata_p.read_text()
metadata_anchor = '''            root.put("m9ConstraintRef", M9ConstraintRef1A.evaluateCapture(root));\n            root.put("m9VirtualBvSpatialCandidate", M9VirtualBvSpatial1B.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
metadata_repl = '''            root.put("m9ConstraintRef", M9ConstraintRef1A.evaluateCapture(root));\n            root.put("m9VirtualBvSpatialCandidate", M9VirtualBvSpatial1B.evaluate(root));\n            root.put("m9ForegroundGuard", M9ForegroundGuard1A.evaluate(root));\n            root.put("m9BacklightDiagnostic", M9BacklightDiagnostic.snapshotJson(root));\n'''
if metadata_anchor not in metadata:
    raise SystemExit('FOREGROUNDGUARD1A metadata anchor missing')
metadata_p.write_text(metadata.replace(metadata_anchor, metadata_repl, 1))

gradle_p = root / gradle_rel
gradle = gradle_p.read_text()
old_version = "versionName '1.54-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b'"
new_version = "versionName '1.55-m9r38-p3i-s1h-cs1c-rm1c-sb1b-neg1c-fp1b-sc1a-vbv1a-cs1af1-id1a-cr1a-vbvs1b-fg1a'"
if old_version not in gradle:
    raise SystemExit('FOREGROUNDGUARD1A 1.54 versionName anchor missing')
gradle_p.write_text(gradle.replace(old_version, new_version, 1))

back_p = root / back_rel
back = back_p.read_text()
marker_anchor = 'constraintref1avirtualbvspatial1bscenefingerprint1b'
marker_repl = 'constraintref1avirtualbvspatial1bforegroundguard1ascenefingerprint1b'
if marker_anchor not in back:
    raise SystemExit('FOREGROUNDGUARD1A forensic marker anchor missing')
back = back.replace(marker_anchor, marker_repl, 1)
if '1.54-' not in back:
    raise SystemExit('FOREGROUNDGUARD1A backlight version anchor missing')
back_p.write_text(back.replace('1.54-', '1.55-', 1))

for rel, before in frozen_before.items():
    after = sha256(rel)
    if after != before:
        raise SystemExit(f'FOREGROUNDGUARD1A froze seam changed unexpectedly: {rel}')

print('M9Cam FOREGROUNDGUARD1A diagnostic bounded floor applied')
print(' - VIRTUALBV1A remains Leica-like signed base meter')
print(' - FB1 applied target observed only as foreground-collapse floor, never additive')
print(' - provisional foreground lift capped at +0.50 EV over VirtualBV base')
print(' - CONSTRAINTREF1A conservative/nearest reference-aligned RAW ceiling applied after floor')
print(' - VIRTUALBVSPATIAL1B remains observation-only and is not consumed by guard math')
print(' - no Camera2, live FB1, motion, renderer, JPEG or DNG mutation')
