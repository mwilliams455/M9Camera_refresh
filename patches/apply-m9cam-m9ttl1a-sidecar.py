#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9ttl1a-sidecar.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('M9TTL1A: not a PhotonCamera root')

writer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java'
ttl_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9TtlSidecar1A.java'
renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
cpp_rel = 'app/src/main/cpp/m9color_jni.cpp'
spool_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
virtual_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/M9VirtualBv1A.java'


def p(rel):
    return root / rel


def read(rel):
    q = p(rel)
    if not q.exists():
        raise SystemExit('M9TTL1A missing expected file: ' + rel)
    return q.read_text()


def sha(rel):
    return hashlib.sha256(p(rel).read_bytes()).hexdigest()

writer = read(writer_rel)
virtual = read(virtual_rel)
spool = read(spool_rel)
if 'm9cam.virtualbv.v1' not in virtual:
    raise SystemExit('M9TTL1A requires VIRTUALBV1A baseline')
if 'm9cam.sidecarspool.v1.privatebundle1b' not in spool or 'public static boolean stage(' not in spool:
    raise SystemExit('M9TTL1A requires SIDECAR1B diagnostic spool')
if 'm9cam.tonebound.v1a.050ev' not in read(renderer_rel):
    raise SystemExit('M9TTL1A requires M9TONEBOUND1A 050EV baseline')

# Diagnostic-only addition. Freeze renderer/native code byte-for-byte.
renderer_before = sha(renderer_rel)
cpp_before = sha(cpp_rel)

java = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

/**
 * M9TTL1A: first-class reconstructed Leica-M9-style TTL diagnostic sidecar.
 *
 * This is deliberately NOT presented as the physical M9 optical photodiode reading.
 * The phone preview-luma signal is the existing VIRTUALBV/SPATIAL diagnostic proxy;
 * recovered M9 APEX arithmetic is then reported on top of that proxy. Nothing here
 * is allowed to change Camera2 exposure, Photon exposure, TC20, renderer pixels,
 * curve02, SAT2, DNG data, or JPEG data.
 */
public final class M9TtlSidecar1A {
    public static final String SCHEMA = "m9cam.ttl.v1a.reconstructed";
    public static final String ROLE = "m9_ttl1a_reconstructed_meter";
    public static final String SUFFIX = "_M9_TTL1A.json";

    private M9TtlSidecar1A() {}

    public static boolean stage(Path dngPath, JSONObject metadataRoot, JSONObject virtualBv) {
        if (dngPath == null) return false;
        try {
            JSONObject out = new JSONObject();
            out.put("schema", SCHEMA);
            out.put("diagnosticOnly", true);
            out.put("photographicPixelChange", false);
            out.put("captureExposureMutation", false);
            out.put("rendererMutation", false);
            out.put("tc20Mutation", false);
            out.put("curve02Mutation", false);
            out.put("saturationMutation", false);
            out.put("physicalM9TtlReadingAvailable", false);
            out.put("modelStatus", "reconstructed_virtual_ttl_proxy_not_physical_M9_photodiode");
            out.put("purpose", "observe_M9_style_TTL_APEX_decision_before_any_live_capture_meter_change");

            JSONObject provenance = new JSONObject();
            provenance.put("meterSignal", "existing_Xiaomi_preview_luma_snapshot");
            provenance.put("meterGeometry", "existing_VIRTUALBV_SPATIAL_preview_geometry_not_proven_M9_optical_field");
            provenance.put("apexArithmetic", "recovered_M9_reduced_APEX_Q8_8_model");
            provenance.put("absoluteCalibration", "provisional_not_absolute_M9_TTL_calibration");
            provenance.put("sceneClassifierUsed", false);
            provenance.put("finishedJpegBrightnessUsed", false);
            provenance.put("completedRawUsedByTtlDecision", false);
            provenance.put("crossGenerationConstantsImported", false);
            out.put("provenance", provenance);

            JSONObject firmware = new JSONObject();
            firmware.put("recoveredReducedRelation", "Tv = Bv + Sv - 5 - Override");
            firmware.put("equivalentAutoIsoRelation", "Sv = 5 + Tv + Override - Bv");
            firmware.put("relationStatus", "M9_firmware_reverse_engineering_believed_recovered");
            firmware.put("believedAutoIsoStartIso", 160);
            firmware.put("autoIsoStartStatus", "believed_not_fully_proven_as_complete_live_threshold_policy");
            firmware.put("lensDependentTvThresholdSolved", false);
            firmware.put("warning", "do_not_treat_predicted_ISO_or_shutter_as_literal_M9_meter_until_optical_meter_calibration_and_Tv_threshold_are_closed");
            out.put("firmwareEvidence", firmware);

            JSONObject correlation = new JSONObject();
            correlation.put("dngFilename", dngPath.getFileName().toString());
            correlation.put("ttlSidecarFilename", sidecarPath(dngPath).getFileName().toString());
            correlation.put("joinPolicy", "same_DNG_stem_join_with_M9_PRIMARY_and_other_sidecars_for_post_capture_validation_only");
            out.put("correlation", correlation);

            JSONObject meter = new JSONObject();
            if (virtualBv != null) {
                meter.put("valid", virtualBv.optBoolean("valid", false));
                copyIfPresent(virtualBv, meter, "meterProxyRaw");
                copyIfPresent(virtualBv, meter, "meterProxyTemporal");
                copyIfPresent(virtualBv, meter, "meterProxyFramesUsed");
                copyIfPresent(virtualBv, meter, "meterProxyCenterWeight");
                copyIfPresent(virtualBv, meter, "meterProxyGlobalWeight");
                copyIfPresent(virtualBv, meter, "meterProxyReferenceY");
                copyIfPresent(virtualBv, meter, "meterProxyRelativeEv");
                copyIfPresent(virtualBv, meter, "direction");
                copyIfPresent(virtualBv, meter, "signedMeterDeltaEv");
            } else {
                meter.put("valid", false);
                meter.put("reason", "virtual_bv_missing");
            }
            out.put("reconstructedMeter", meter);

            JSONObject apex = new JSONObject();
            if (virtualBv != null) {
                copyIfPresent(virtualBv, apex, "virtualBvEv");
                copyIfPresent(virtualBv, apex, "virtualBvQ8_8");
                copyIfPresent(virtualBv, apex, "photonEquivalentBvEv");
                copyIfPresent(virtualBv, apex, "photonEquivalentTvEv");
                copyIfPresent(virtualBv, apex, "photonEquivalentAvEv");
                copyIfPresent(virtualBv, apex, "photonEquivalentSvEv");
                copyIfPresent(virtualBv, apex, "photonReferenceIso");
                copyIfPresent(virtualBv, apex, "photonReferenceExposureNs");
                copyIfPresent(virtualBv, apex, "m9SelectedIso");
                copyIfPresent(virtualBv, apex, "m9SelectedSvEv");
                copyIfPresent(virtualBv, apex, "m9SelectedSvQ8_8");
                copyIfPresent(virtualBv, apex, "m9TvBaseEv");
                copyIfPresent(virtualBv, apex, "m9TvBaseQ8_8");
                copyIfPresent(virtualBv, apex, "predictedM9Iso");
                copyIfPresent(virtualBv, apex, "predictedM9TvEv");
                copyIfPresent(virtualBv, apex, "predictedM9TvQ8_8");
                copyIfPresent(virtualBv, apex, "predictedM9ShutterSeconds");
                copyIfPresent(virtualBv, apex, "predictedM9Assumption");
                copyIfPresent(virtualBv, apex, "autoIsoWouldActivate");
                copyIfPresent(virtualBv, apex, "autoIsoState");
            }
            out.put("apexDecision", apex);

            JSONObject scene = metadataRoot != null ? metadataRoot.optJSONObject("m9SceneExposureDiagnostic") : null;
            if (scene != null) {
                JSONObject sceneOut = new JSONObject();
                sceneOut.put("valid", scene.optBoolean("valid", false));
                copyIfPresent(scene, sceneOut, "previewLumaFrames");
                copyIfPresent(scene, sceneOut, "previewExposureEnergyIsoSeconds");
                copyIfPresent(scene, sceneOut, "cameraRotationDegrees");
                JSONObject inputs = scene.optJSONObject("inputs");
                if (inputs != null) sceneOut.put("inputs", new JSONObject(inputs.toString()));
                out.put("previewMeterEvidence", sceneOut);
            }

            JSONObject actual = metadataRoot != null ? metadataRoot.optJSONObject("captureResult") : null;
            JSONObject requested = metadataRoot != null ? metadataRoot.optJSONObject("captureRequest") : null;
            JSONObject exposure = new JSONObject();
            if (requested != null) exposure.put("camera2Request", new JSONObject(requested.toString()));
            if (actual != null) exposure.put("camera2Result", new JSONObject(actual.toString()));
            exposure.put("ttlDecisionAppliedToCapture", false);
            out.put("captureComparison", exposure);

            // Preserve the complete diagnostic source so future firmware work can reinterpret
            // the sidecar without taking the photograph again. This remains evidence only.
            if (virtualBv != null) out.put("virtualBvSource", new JSONObject(virtualBv.toString()));

            JSONObject rawPolicy = new JSONObject();
            rawPolicy.put("availableInTtlDecision", false);
            rawPolicy.put("usedByTtlDecision", false);
            rawPolicy.put("validationMethod", "join_same_stem_M9_PRIMARY_after_render");
            rawPolicy.put("reason", "M9_optical_TTL_precedes_capture_RAW_so_completed_RAW_must_never_feed_this_TTL_observation");
            out.put("postCaptureRawAudit", rawPolicy);

            Path sidecar = sidecarPath(dngPath);
            out.put("sidecarPath", sidecar.toString());
            out.put("sidecarTransport", M9DiagnosticBurstSpool.SCHEMA);
            byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
            boolean staged = M9DiagnosticBurstSpool.stage(sidecar, frozen, ROLE);
            return staged;
        } catch (Exception ignored) {
            return false;
        }
    }

    private static Path sidecarPath(Path dngPath) {
        String f = dngPath.getFileName().toString();
        int dot = f.lastIndexOf('.');
        String stem = dot > 0 ? f.substring(0, dot) : f;
        return dngPath.resolveSibling(stem + SUFFIX);
    }

    private static void copyIfPresent(JSONObject src, JSONObject dst, String key) throws Exception {
        if (src != null && src.has(key) && !src.isNull(key)) dst.put(key, src.get(key));
    }
}
'''

p(ttl_rel).write_text(java)

old = '            root.put("m9VirtualBv", M9VirtualBv1A.evaluate(root));\n'
new = '''            JSONObject m9VirtualBv1A = M9VirtualBv1A.evaluate(root);\n            root.put("m9VirtualBv", m9VirtualBv1A);\n            boolean m9Ttl1AStaged = M9TtlSidecar1A.stage(dngPath, root, m9VirtualBv1A);\n            root.put("m9Ttl1A", new JSONObject()\n                    .put("schema", M9TtlSidecar1A.SCHEMA)\n                    .put("diagnosticOnly", true)\n                    .put("captureExposureMutation", false)\n                    .put("sidecarStaged", m9Ttl1AStaged)\n                    .put("sidecarSuffix", M9TtlSidecar1A.SUFFIX));\n'''
count = writer.count(old)
if count != 1:
    raise SystemExit('M9TTL1A metadata VIRTUALBV anchor expected once, found %d' % count)
writer = writer.replace(old, new, 1)
p(writer_rel).write_text(writer)

if sha(renderer_rel) != renderer_before:
    raise SystemExit('M9TTL1A unexpectedly changed frozen renderer')
if sha(cpp_rel) != cpp_before:
    raise SystemExit('M9TTL1A unexpectedly changed frozen native color core')

print('M9TTL1A SIDECAR applied')
print(' - new _M9_TTL1A.json reconstructed TTL/APEX sidecar staged through SIDECAR1B')
print(' - physical M9 optical TTL reading explicitly unavailable; phone preview signal is a proxy')
print(' - recovered M9 APEX relation logged with Auto-ISO threshold uncertainty')
print(' - completed RAW explicitly excluded from TTL decision and reserved for same-stem validation')
print(' - capture exposure, renderer, TC20, SAT2, curve02, DNG and JPEG pixels unchanged')
