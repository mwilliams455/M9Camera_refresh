#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-physicalsourceagnostic1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit(f'PHYSICALSOURCEAGNOSTIC1A missing renderer: {p}')
s = p.read_text()

old_origin = '''        // DEVICEPORT1A deliberately did not infer RAW origin from active-array metadata.\n        // Current Xiaomi 15 Ultra full-frame RAW validation is origin0; keep this explicit.\n        final int sourceRawOriginX = 0;\n        final int sourceRawOriginY = 0;\n'''
new_origin = '''        // PHYSICALSOURCEAGNOSTIC1A: derive RAW sensor-coordinate origin from the\n        // active physical camera geometry. Camera ID, focal length and marketing lens\n        // role are intentionally absent from this decision. When dimensions do not\n        // prove a mapping, fail closed instead of silently assuming a Bayer phase.\n        final SourceRawOrigin1A sourceRawOrigin = resolveSourceRawOrigin1A(\n                nativeCharacteristics, width, height);\n        final int sourceRawOriginX = sourceRawOrigin.x;\n        final int sourceRawOriginY = sourceRawOrigin.y;\n'''
if s.count(old_origin) != 1:
    raise SystemExit('PHYSICALSOURCEAGNOSTIC1A raw-origin anchor missing/ambiguous')
s = s.replace(old_origin, new_origin, 1)

# Make the dormant same-RAW diagnostic bank topology agnostic. It may still be
# restricted by the diagnostic demosaic implementation (RGGB), but never by a camera ID.
s = s.replace('nativeAb1A.put("schema", "m9cam.renderer.bridgeprobe.v1a.main.fixedgain");',
              'nativeAb1A.put("schema", "m9cam.renderer.bridgeprobe.v1a.physical_source.fixedgain");', 1)
s = s.replace('nativeAb1A.put("scope", "main_physical_2_native_source_production_vs_same_math_norm030_parity1p");',
              'nativeAb1A.put("scope", "active_physical_RAW_source_production_vs_same_math_norm030_parity1p");', 1)
old_gate = '''                    if (!"2".equals(requestedPhysicalId)) {\n                        nativeAb1A.put("status", "skipped_non_main_physical_camera");\n                        nativeAb1A.put("mainPhysicalCameraRequired", "2");\n                    } else {\n                        CaptureResult physicalResult = M9PhysicalCaptureResult1A.resolve(\n                                captureResult, params.cameraID);\n                        if (M9PhysicalCaptureResult1A.requestsUnderlyingPhysicalCamera(params.cameraID)\n                                && !M9PhysicalCaptureResult1A.resultMatchesRequestedPhysical(\n                                        physicalResult, params.cameraID)) {\n                            throw new IllegalStateException(\n                                    "NATIVEAB1A physical CaptureResult mismatch for main camera 2");\n                        }\n                        String resultCameraId = M9PhysicalCaptureResult1A.resultCameraId(physicalResult);\n                        nativeAb1A.put("captureResultCameraId",\n                                resultCameraId != null ? resultCameraId : JSONObject.NULL);\n                        nativeAb1A.put("cfaPattern", params.cfaPattern & 0xff);\n                        if ((params.cfaPattern & 0xff) != 0) {\n                            throw new IllegalStateException(\n                                    "NATIVEAB1A main physical 2 requires RGGB CFA=0, got "\n                                            + (params.cfaPattern & 0xff));\n                        }\n'''
new_gate = '''                    CaptureResult physicalResult = M9PhysicalCaptureResult1A.resolve(\n                            captureResult, params.cameraID);\n                    if (M9PhysicalCaptureResult1A.requestsUnderlyingPhysicalCamera(params.cameraID)\n                            && !M9PhysicalCaptureResult1A.resultMatchesRequestedPhysical(\n                                    physicalResult, params.cameraID)) {\n                        throw new IllegalStateException(\n                                "NATIVEAB1A physical CaptureResult mismatch for requested physical source");\n                    }\n                    String resultCameraId = M9PhysicalCaptureResult1A.resultCameraId(physicalResult);\n                    nativeAb1A.put("captureResultCameraId",\n                            resultCameraId != null ? resultCameraId : JSONObject.NULL);\n                    nativeAb1A.put("cfaPattern", params.cfaPattern & 0xff);\n                    nativeAb1A.put("physicalCameraIdUsedAsSemanticRole", false);\n                    nativeAb1A.put("cameraArrayTopologyUsedForRendering", false);\n                    if ((params.cfaPattern & 0xff) != 0) {\n                        nativeAb1A.put("status", "skipped_legacy_diagnostic_requires_RGGB");\n                        nativeAb1A.put("legacyDiagnosticRequiredCfa", 0);\n                    } else {\n'''
if s.count(old_gate) != 1:
    raise SystemExit('PHYSICALSOURCEAGNOSTIC1A NATIVEAB camera-2 gate anchor missing/ambiguous')
s = s.replace(old_gate, new_gate, 1)
# old gate and new gate each open one conditional block, so existing closing brace is balanced.

# Insert conservative geometry resolver immediately before renderNativeProspectiveCore.
anchor = '    private static RenderCore renderNativeProspectiveCore(ByteBuffer rawBuffer,\n'
if s.count(anchor) != 1:
    raise SystemExit('PHYSICALSOURCEAGNOSTIC1A renderer helper insertion anchor missing/ambiguous')
helper = r'''    private static final class SourceRawOrigin1A {
        final int x;
        final int y;
        final String evidence;
        SourceRawOrigin1A(int x, int y, String evidence) {
            this.x = x;
            this.y = y;
            this.evidence = evidence;
        }
    }

    /**
     * Resolve the first RAW sample's sensor-coordinate origin from the active physical
     * camera geometry only. No camera ID, focal length, phone model, camera count or
     * marketing role is consulted.
     *
     * A RAW matching the full pixel array begins at sensor (0,0). A RAW matching the
     * pre-correction or active array begins at that rectangle's left/top. Ambiguous
     * dimensions fail closed because guessing an origin can swap Bayer phase and the
     * four LensShadingMap planes.
     */
    private static SourceRawOrigin1A resolveSourceRawOrigin1A(
            CameraCharacteristics characteristics, int rawWidth, int rawHeight) {
        if (characteristics == null) {
            throw new IllegalStateException(
                    "PHYSICALSOURCEAGNOSTIC1A requires active physical CameraCharacteristics");
        }
        android.util.Size pixel = characteristics.get(
                CameraCharacteristics.SENSOR_INFO_PIXEL_ARRAY_SIZE);
        android.graphics.Rect pre = characteristics.get(
                CameraCharacteristics.SENSOR_INFO_PRE_CORRECTION_ACTIVE_ARRAY_SIZE);
        android.graphics.Rect active = characteristics.get(
                CameraCharacteristics.SENSOR_INFO_ACTIVE_ARRAY_SIZE);

        if (pixel != null && rawWidth == pixel.getWidth() && rawHeight == pixel.getHeight()) {
            return new SourceRawOrigin1A(0, 0, "raw_dimensions_match_full_pixel_array");
        }
        if (pre != null && rawWidth == pre.width() && rawHeight == pre.height()) {
            return new SourceRawOrigin1A(pre.left, pre.top,
                    "raw_dimensions_match_pre_correction_active_array");
        }
        if (active != null && rawWidth == active.width() && rawHeight == active.height()) {
            return new SourceRawOrigin1A(active.left, active.top,
                    "raw_dimensions_match_active_array");
        }
        throw new IllegalStateException(
                "PHYSICALSOURCEAGNOSTIC1A cannot prove RAW sensor origin for "
                        + rawWidth + "x" + rawHeight
                        + "; pixel=" + (pixel != null
                                ? pixel.getWidth() + "x" + pixel.getHeight() : "null")
                        + "; pre=" + (pre != null
                                ? pre.left + "," + pre.top + ":" + pre.width() + "x" + pre.height() : "null")
                        + "; active=" + (active != null
                                ? active.left + "," + active.top + ":" + active.width() + "x" + active.height() : "null"));
    }

'''
s = s.replace(anchor, helper + anchor, 1)

# Record the physical-source invariants next to existing target-input telemetry.
tele_anchor = '''        d.put("targetInputAdapterPhysicalCameraIdIndependent", true);\n        d.put("targetInputAdapterReferenceSensorRole", "historical_target_domain_reference_only");\n'''
tele_new = '''        d.put("targetInputAdapterPhysicalCameraIdIndependent", true);\n        d.put("sourceCameraSelectionPolicy", "opaque_physical_id_lookup_then_metadata_driven_SOURCECAL");\n        d.put("sourceCameraIdUsedAsSemanticRole", false);\n        d.put("sourceCameraArrayTopologyUsedForRendering", false);\n        d.put("sourceFocalLengthUsedForRendering", false);\n        d.put("sourceCalibrationEligibility", "physical_RAW_camera_with_required_Camera2_DNG_metadata");\n        d.put("targetInputAdapterReferenceSensorRole", "historical_target_domain_reference_only");\n'''
if s.count(tele_anchor) != 1:
    raise SystemExit('PHYSICALSOURCEAGNOSTIC1A production telemetry anchor missing/ambiguous')
s = s.replace(tele_anchor, tele_new, 1)

# Emit resolved origin evidence from the actual pixel path diagnostics.
diag_anchor = '''            d.put("targetInputAdapter1AApplied", targetInputAdapter1AApplied);\n'''
diag_new = '''            d.put("sourceRawOriginX", sourceRawOriginX);\n            d.put("sourceRawOriginY", sourceRawOriginY);\n            d.put("sourceRawOriginEvidence", sourceRawOrigin.evidence);\n            d.put("sourceRawOriginDerivedFromPhysicalGeometry", true);\n            d.put("sourceCameraIdUsedAsSemanticRole", false);\n            d.put("sourceCameraArrayTopologyUsedForRendering", false);\n            d.put("targetInputAdapter1AApplied", targetInputAdapter1AApplied);\n'''
if s.count(diag_anchor) != 1:
    raise SystemExit('PHYSICALSOURCEAGNOSTIC1A render diagnostics anchor missing/ambiguous')
s = s.replace(diag_anchor, diag_new, 1)

p.write_text(s)
print('PHYSICALSOURCEAGNOSTIC1A applied')
print(' - physical camera ID is lookup/provenance only')
print(' - RAW origin is derived from active physical sensor geometry and fails closed if ambiguous')
print(' - source CFA/shading plane phase follows the proven sensor-coordinate origin')
print(' - dormant NATIVEAB bank no longer keys on physical camera 2')
