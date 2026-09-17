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

def p(rel): return root / rel
def read(rel):
    q = p(rel)
    if not q.exists(): raise SystemExit('M9TTL1A missing expected file: ' + rel)
    return q.read_text()
def sha(rel): return hashlib.sha256(p(rel).read_bytes()).hexdigest()

writer = read(writer_rel)
virtual = read(virtual_rel)
spool = read(spool_rel)
if 'm9cam.virtualbv.v1' not in virtual:
    raise SystemExit('M9TTL1A requires VIRTUALBV1A baseline')
if 'm9cam.sidecarspool.v1.privatebundle1b' not in spool or 'public static boolean stage(' not in spool:
    raise SystemExit('M9TTL1A requires SIDECAR1B diagnostic spool')
if 'm9cam.tonebound.v1a.050ev' not in read(renderer_rel):
    raise SystemExit('M9TTL1A requires M9TONEBOUND1A 050EV baseline')
renderer_before = sha(renderer_rel)
cpp_before = sha(cpp_rel)

java = r'''package com.particlesdevs.photoncamera.m9;

import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

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
            out.put("provenance", provenance);

            JSONObject firmware = new JSONObject();
            firmware.put("recoveredReducedRelation", "Tv = Bv + Sv - 5 - Override");
            firmware.put("equivalentAutoIsoRelation", "Sv = 5 + Tv + Override - Bv");
            firmware.put("believedAutoIsoStartIso", 160);
            firmware.put("autoIsoStartStatus", "believed_not_fully_proven_as_complete_live_threshold_policy");
            firmware.put("lensDependentTvThresholdSolved", false);
            out.put("firmwareEvidence", firmware);

            JSONObject meter = new JSONObject();
            if (virtualBv != null) {
                meter.put("valid", virtualBv.optBoolean("valid", false));
                copy(virtualBv, meter, "meterProxyRaw");
                copy(virtualBv, meter, "meterProxyTemporal");
                copy(virtualBv, meter, "meterProxyFramesUsed");
                copy(virtualBv, meter, "meterProxyCenterWeight");
                copy(virtualBv, meter, "meterProxyGlobalWeight");
                copy(virtualBv, meter, "meterProxyReferenceY");
                copy(virtualBv, meter, "meterProxyRelativeEv");
                copy(virtualBv, meter, "signedMeterDeltaEv");
                copy(virtualBv, meter, "direction");
            } else {
                meter.put("valid", false);
                meter.put("reason", "virtual_bv_missing");
            }
            out.put("reconstructedMeter", meter);

            JSONObject apex = new JSONObject();
            if (virtualBv != null) {
                String[] keys = {"virtualBvEv","virtualBvQ8_8","photonEquivalentBvEv",
                        "photonEquivalentTvEv","photonEquivalentAvEv","photonEquivalentSvEv",
                        "photonReferenceIso","photonReferenceExposureNs","m9SelectedIso",
                        "m9SelectedSvEv","m9SelectedSvQ8_8","m9TvBaseEv","m9TvBaseQ8_8",
                        "predictedM9Iso","predictedM9TvEv","predictedM9TvQ8_8",
                        "predictedM9ShutterSeconds","predictedM9Assumption","autoIsoWouldActivate",
                        "autoIsoState"};
                for (String k : keys) copy(virtualBv, apex, k);
            }
            out.put("apexDecision", apex);

            JSONObject scene = metadataRoot != null ? metadataRoot.optJSONObject("m9SceneExposureDiagnostic") : null;
            if (scene != null) {
                JSONObject sceneOut = new JSONObject();
                sceneOut.put("valid", scene.optBoolean("valid", false));
                copy(scene, sceneOut, "previewLumaFrames");
                copy(scene, sceneOut, "previewExposureEnergyIsoSeconds");
                copy(scene, sceneOut, "cameraRotationDegrees");
                JSONObject inputs = scene.optJSONObject("inputs");
                if (inputs != null) sceneOut.put("inputs", new JSONObject(inputs.toString()));
                out.put("previewMeterEvidence", sceneOut);
            }

            JSONObject rawPolicy = new JSONObject();
            rawPolicy.put("availableInTtlDecision", false);
            rawPolicy.put("usedByTtlDecision", false);
            rawPolicy.put("validationMethod", "join_same_stem_M9_PRIMARY_after_render");
            rawPolicy.put("reason", "M9_optical_TTL_precedes_capture_RAW_so_completed_RAW_must_never_feed_this_TTL_observation");
            out.put("postCaptureRawAudit", rawPolicy);

            JSONObject correlation = new JSONObject();
            correlation.put("dngFilename", dngPath.getFileName().toString());
            correlation.put("ttlSidecarFilename", sidecarPath(dngPath).getFileName().toString());
            correlation.put("joinPolicy", "same_DNG_stem_join_with_M9_PRIMARY_and_other_sidecars_for_post_capture_validation_only");
            out.put("correlation", correlation);

            if (virtualBv != null) out.put("virtualBvSource", new JSONObject(virtualBv.toString()));
            Path sidecar = sidecarPath(dngPath);
            out.put("sidecarPath", sidecar.toString());
            out.put("sidecarTransport", M9DiagnosticBurstSpool.SCHEMA);
            byte[] frozen = out.toString(2).getBytes(StandardCharsets.UTF_8);
            return M9DiagnosticBurstSpool.stage(sidecar, frozen, ROLE);
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

    private static void copy(JSONObject src, JSONObject dst, String key) throws Exception {
        if (src != null && src.has(key) && !src.isNull(key)) dst.put(key, src.get(key));
    }
}
'''
p(ttl_rel).write_text(java)

# Current production metadata writer already evaluates VIRTUALBV into m9VirtualBv.
# Replace that exact two-line seam with one evaluation named m9VirtualBv1A and stage
# the TTL sidecar immediately afterward. No capture decision can consume this result.
old = '''            JSONObject m9VirtualBv = M9VirtualBv1A.evaluate(root);\n            root.put("m9VirtualBv", m9VirtualBv);\n'''
new = '''            JSONObject m9VirtualBv1A = M9VirtualBv1A.evaluate(root);\n            root.put("m9VirtualBv", m9VirtualBv1A);\n            boolean m9Ttl1AStaged = M9TtlSidecar1A.stage(dngPath, root, m9VirtualBv1A);\n            root.put("m9Ttl1A", new JSONObject()\n                    .put("schema", M9TtlSidecar1A.SCHEMA)\n                    .put("diagnosticOnly", true)\n                    .put("captureExposureMutation", false)\n                    .put("sidecarStaged", m9Ttl1AStaged)\n                    .put("sidecarSuffix", M9TtlSidecar1A.SUFFIX));\n'''
count = writer.count(old)
if count != 1:
    raise SystemExit('M9TTL1A current metadata VIRTUALBV anchor expected once, found %d' % count)
writer = writer.replace(old, new, 1)
p(writer_rel).write_text(writer)

if sha(renderer_rel) != renderer_before:
    raise SystemExit('M9TTL1A unexpectedly changed frozen renderer')
if sha(cpp_rel) != cpp_before:
    raise SystemExit('M9TTL1A unexpectedly changed frozen native color core')

print('M9TTL1A SIDECAR applied')
print(' - current VIRTUALBV metadata anchor matched')
print(' - new _M9_TTL1A.json reconstructed TTL/APEX sidecar staged through SIDECAR1B')
print(' - capture exposure, renderer, TC20, SAT2, curve02, DNG and JPEG pixels unchanged')
