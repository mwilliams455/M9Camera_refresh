#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: fix-m9cam-sourcecal1c-physicalresult1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('SOURCECAL1C PHYSICALRESULT1A: not a PhotonCamera root')

renderer_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
source_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceCalibrationAudit1A.java'
raw_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9RawShadingAudit1A.java'
resolver_rel = 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PhysicalCaptureResult1A.java'


def read(rel):
    p = root / rel
    if not p.exists():
        raise SystemExit('SOURCECAL1C missing expected file: ' + rel)
    return p.read_text()


def write(rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def sha(rel):
    return hashlib.sha256((root / rel).read_bytes()).hexdigest()

# Diagnostic-only hardening. These pixel/capture-policy files must remain byte-identical.
frozen_rels = [
    'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/DngCreator.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java',
    'app/src/main/cpp/m9color_jni.cpp',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
    'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
    'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java',
]
frozen_before = {rel: sha(rel) for rel in frozen_rels}

resolver_java = r'''package com.particlesdevs.photoncamera.m9.render;

import android.hardware.camera2.CaptureResult;
import android.hardware.camera2.TotalCaptureResult;
import android.os.Build;

import java.util.Map;

/**
 * SOURCECAL1C / PHYSICALRESULT1A.
 *
 * Resolve the per-physical-camera CaptureResult for diagnostic audits when Photon opens a
 * logical multi-camera but targets its surfaces at a specific physical camera. The frozen M9
 * renderer continues to receive and use the original top-level CaptureResult; only the
 * RAWSHADING/SOURCECAL observation path uses the resolved physical result.
 */
public final class M9PhysicalCaptureResult1A {
    private M9PhysicalCaptureResult1A() {}

    public static CaptureResult resolve(CaptureResult topLevel, String photonCameraID) {
        if (topLevel == null || !requestsUnderlyingPhysicalCamera(photonCameraID)) return topLevel;
        if (!(topLevel instanceof TotalCaptureResult) || Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            return topLevel;
        }

        String physical = requestedPhysicalCameraId(photonCameraID);
        if (physical == null) return topLevel;
        TotalCaptureResult total = (TotalCaptureResult) topLevel;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                Map<String, TotalCaptureResult> physicalTotals = total.getPhysicalCameraTotalResults();
                if (physicalTotals != null) {
                    TotalCaptureResult resolved = physicalTotals.get(physical);
                    if (resolved != null) return resolved;
                }
            } else {
                @SuppressWarnings("deprecation")
                Map<String, CaptureResult> physicalResults = total.getPhysicalCameraResults();
                if (physicalResults != null) {
                    CaptureResult resolved = physicalResults.get(physical);
                    if (resolved != null) return resolved;
                }
            }
        } catch (Throwable ignored) {
            // Audit must never destabilize capture/rendering. The sidecar will expose fallback.
        }
        return topLevel;
    }

    public static boolean requestsUnderlyingPhysicalCamera(String photonCameraID) {
        if (photonCameraID == null) return false;
        int split = photonCameraID.indexOf('-');
        return split > 0 && split < photonCameraID.length() - 1;
    }

    public static String requestedPhysicalCameraId(String photonCameraID) {
        if (photonCameraID == null) return null;
        int split = photonCameraID.indexOf('-');
        if (split > 0 && split < photonCameraID.length() - 1) {
            return photonCameraID.substring(split + 1);
        }
        return photonCameraID;
    }

    public static String resultCameraId(CaptureResult result) {
        if (result == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return null;
        try {
            return result.getCameraId();
        } catch (Throwable ignored) {
            return null;
        }
    }

    public static boolean resultMatchesRequestedPhysical(CaptureResult result, String photonCameraID) {
        if (!requestsUnderlyingPhysicalCamera(photonCameraID)) return true;
        String requested = requestedPhysicalCameraId(photonCameraID);
        String actual = resultCameraId(result);
        return requested != null && requested.equals(actual);
    }
}
'''
write(resolver_rel, resolver_java)

renderer = read(renderer_rel)
old_calls = '''            // M9RAWSHADING1A: metadata/semantics only. No GainMap is applied to RAW here.
            JSONObject rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(
                    dngPath, frame.width, frame.height, params, characteristics, captureResult, captureRequest);
            // M9SOURCECAL1A: native Camera2/DNG source characterization only; never feeds renderCore.
            JSONObject sourceCalibrationAudit1A = M9SourceCalibrationAudit1A.captureAndWrite(
                    dngPath, params, characteristics, captureResult);
'''
new_calls = '''            // SOURCECAL1C PHYSICALRESULT1A: when Photon opens a logical multi-camera and
            // routes outputs to an underlying physical camera, Camera2 publishes that sensor's
            // live metadata in TotalCaptureResult.getPhysicalCamera*Results(). Resolve only for
            // diagnostic audits. FillDynamicParameters/renderCore keep the original captureResult.
            CaptureResult diagnosticCaptureResult1A = M9PhysicalCaptureResult1A.resolve(
                    captureResult, params.cameraID);
            // M9RAWSHADING1A: metadata/semantics only. No GainMap is applied to RAW here.
            JSONObject rawShadingAudit1A = M9RawShadingAudit1A.captureAndWrite(
                    dngPath, frame.width, frame.height, params, characteristics,
                    diagnosticCaptureResult1A, captureRequest);
            // M9SOURCECAL1A/1C: native Camera2/DNG source characterization only; never feeds renderCore.
            JSONObject sourceCalibrationAudit1A = M9SourceCalibrationAudit1A.captureAndWrite(
                    dngPath, params, characteristics, diagnosticCaptureResult1A);
'''
if new_calls not in renderer:
    if renderer.count(old_calls) != 1:
        raise SystemExit('SOURCECAL1C renderer audit-call anchor missing/non-unique')
    renderer = renderer.replace(old_calls, new_calls, 1)
write(renderer_rel, renderer)

source = read(source_rel)
source_anchor = '''            out.put("phase", "A_native_metadata_and_transform_audit");
'''
source_insert = source_anchor + '''            String requestedPhysicalCameraId = M9PhysicalCaptureResult1A.requestedPhysicalCameraId(
                    params != null ? params.cameraID : null);
            out.put("captureResultResolutionPolicy",
                    "physical_TotalCaptureResult_for_logical_dash_physical_cameraID_else_top_level");
            out.put("physicalCaptureResultRequested",
                    M9PhysicalCaptureResult1A.requestsUnderlyingPhysicalCamera(
                            params != null ? params.cameraID : null));
            out.put("requestedPhysicalCameraId",
                    requestedPhysicalCameraId != null ? requestedPhysicalCameraId : JSONObject.NULL);
            String resolvedCaptureCameraId = M9PhysicalCaptureResult1A.resultCameraId(captureResult);
            out.put("captureResultCameraId",
                    resolvedCaptureCameraId != null ? resolvedCaptureCameraId : JSONObject.NULL);
            out.put("captureResultMatchesRequestedPhysicalCamera",
                    M9PhysicalCaptureResult1A.resultMatchesRequestedPhysical(
                            captureResult, params != null ? params.cameraID : null));
'''
if 'captureResultResolutionPolicy' not in source:
    if source.count(source_anchor) != 1:
        raise SystemExit('SOURCECAL1C SOURCECAL sidecar anchor missing/non-unique')
    source = source.replace(source_anchor, source_insert, 1)
write(source_rel, source)

raw = read(raw_rel)
raw_anchor = '''            out.put("phase", "A_metadata_semantics_audit");
'''
raw_insert = raw_anchor + '''            String requestedPhysicalCameraId = M9PhysicalCaptureResult1A.requestedPhysicalCameraId(
                    params != null ? params.cameraID : null);
            out.put("captureResultResolutionPolicy",
                    "physical_TotalCaptureResult_for_logical_dash_physical_cameraID_else_top_level");
            out.put("physicalCaptureResultRequested",
                    M9PhysicalCaptureResult1A.requestsUnderlyingPhysicalCamera(
                            params != null ? params.cameraID : null));
            out.put("requestedPhysicalCameraId",
                    requestedPhysicalCameraId != null ? requestedPhysicalCameraId : JSONObject.NULL);
            String resolvedCaptureCameraId = M9PhysicalCaptureResult1A.resultCameraId(captureResult);
            out.put("captureResultCameraId",
                    resolvedCaptureCameraId != null ? resolvedCaptureCameraId : JSONObject.NULL);
            out.put("captureResultMatchesRequestedPhysicalCamera",
                    M9PhysicalCaptureResult1A.resultMatchesRequestedPhysical(
                            captureResult, params != null ? params.cameraID : null));
'''
if 'captureResultResolutionPolicy' not in raw:
    if raw.count(raw_anchor) != 1:
        raise SystemExit('SOURCECAL1C RAWSHADING sidecar anchor missing/non-unique')
    raw = raw.replace(raw_anchor, raw_insert, 1)
write(raw_rel, raw)

# Hard invariants: diagnostic resolver must not leak into the frozen render/capture path.
renderer = read(renderer_rel)
for marker in [
    'params.FillDynamicParameters(captureResult, captureRequest, iso);',
    'CaptureResult diagnosticCaptureResult1A = M9PhysicalCaptureResult1A.resolve(',
    'diagnosticCaptureResult1A, captureRequest);',
    'dngPath, params, characteristics, diagnosticCaptureResult1A);',
    'RenderCore out = renderCore(frame.buffer, frame.width, frame.height,',
]:
    if marker not in renderer:
        raise SystemExit('SOURCECAL1C required renderer marker missing: ' + marker)
if 'params.FillDynamicParameters(diagnosticCaptureResult1A' in renderer:
    raise SystemExit('SOURCECAL1C physical audit result leaked into active Parameters path')
for rel, before in frozen_before.items():
    after = sha(rel)
    if after != before:
        raise SystemExit('SOURCECAL1C diagnostic-only invariant changed frozen file: ' + rel)

print('M9SOURCECAL1C PHYSICALRESULT1A applied')
print(' - logical->physical Camera2 TotalCaptureResult metadata is resolved for diagnostics')
print(' - RAWSHADING GainMap and SOURCECAL live neutral/CCT now observe the requested physical module')
print(' - sidecars record requested/result camera IDs and match status')
print(' - renderer Parameters, TC20, colour, exposure, DNG and JPEG paths remain frozen')
