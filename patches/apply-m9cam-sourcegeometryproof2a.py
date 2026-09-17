#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourcegeometryproof2a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('SOURCEGEOMETRYPROOF2A: not a PhotonCamera root')

image_frame = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageFrame.java'
saver = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/SaverImplementation.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
for p in (image_frame, saver, renderer):
    if not p.exists():
        raise SystemExit('SOURCEGEOMETRYPROOF2A missing required file: ' + str(p))


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'SOURCEGEOMETRYPROOF2A {label}: expected 1 anchor, found {count}')
    return text.replace(old, new, 1)

# Preserve the real Camera Image -> owned ImageFrame copy facts. These fields are
# metadata only; the underlying Photon copy remains byte-for-byte unchanged.
s = image_frame.read_text()
s = replace_once(s,
'''    public IsoExpoSelector.ExpoPair pair;\n''',
'''    public IsoExpoSelector.ExpoPair pair;\n\n    // SOURCEGEOMETRYPROOF2A: exact acquisition/copy provenance for the owned RAW.\n    // These values are diagnostic/runtime-gating metadata only; they never alter pixels.\n    public int m9SourceImageFormat = -1;\n    public int m9SourceImageWidth = -1;\n    public int m9SourceImageHeight = -1;\n    public int m9SourceRowStrideBytes = -1;\n    public int m9SourcePixelStrideBytes = -1;\n    public int m9SourceCopyOffsetBytes = -1;\n    public int m9SourceCopyCapacityBytes = -1;\n    public int m9SourcePlaneCapacityBytes = -1;\n    public boolean m9SourceAspect169Requested = false;\n    public boolean m9SourceBinningRequested = false;\n''', 'ImageFrame provenance fields')
image_frame.write_text(s)

s = saver.read_text()
s = replace_once(s,
'''        ImageFrame frame = new ImageFrame(image.getPlanes()[0].getBuffer(), image.getFormat(), width, image.getPlanes()[0].getRowStride(), offset, capacity);\n        frame.timestamp = image.getTimestamp();\n''',
'''        ImageFrame frame = new ImageFrame(image.getPlanes()[0].getBuffer(), image.getFormat(), width, image.getPlanes()[0].getRowStride(), offset, capacity);\n        // SOURCEGEOMETRYPROOF2A: capture the exact source plane and copy geometry.\n        // The proof is evaluated later by the M9 route; no Photon copy behavior changes.\n        frame.m9SourceImageFormat = image.getFormat();\n        frame.m9SourceImageWidth = image.getWidth();\n        frame.m9SourceImageHeight = image.getHeight();\n        frame.m9SourceRowStrideBytes = image.getPlanes()[0].getRowStride();\n        frame.m9SourcePixelStrideBytes = image.getPlanes()[0].getPixelStride();\n        frame.m9SourceCopyOffsetBytes = offset;\n        frame.m9SourceCopyCapacityBytes = capacity;\n        frame.m9SourcePlaneCapacityBytes = image.getPlanes()[0].getBuffer().capacity();\n        frame.m9SourceAspect169Requested = PhotonCamera.getSettings().aspect169;\n        frame.m9SourceBinningRequested = PhotonCamera.getSettings().binning;\n        frame.timestamp = image.getTimestamp();\n''', 'SaverImplementation provenance capture')
saver.write_text(s)

s = renderer.read_text()
for marker in [
    'm9SensorTarget1ARuntimeVerified',
    'renderNativeSourceProduction1P(',
    'renderNativeProspectiveCore(',
    'applyNativeProspectiveGainMapLumaDecomp1A(',
    'gainMapAppliedToRender',
    'shadingRepresentationRestoreApplied',
    'm9cam.tonebound.v1a.050ev',
]:
    if marker not in s:
        raise SystemExit('SOURCEGEOMETRYPROOF2A requires assembled M9SENSORTARGET1A marker: ' + marker)

# Put the proof beside the existing physical-origin resolver. It deliberately does
# not duplicate shading math; it proves the copied RAW layout that the existing
# CFA-aware NORM030/LensShadingMap path consumes.
insert_marker = '    private static RenderCore renderNativeSourceProduction1P(ByteBuffer rawBuffer,'
if s.count(insert_marker) != 1:
    raise SystemExit('SOURCEGEOMETRYPROOF2A production-wrapper insertion marker not unique')
proof_code = r'''    private static final class SourceGeometryProof2A {
        final int originX;
        final int originY;
        final String originEvidence;
        final long expectedTightBytes;
        final boolean proven;

        SourceGeometryProof2A(int originX, int originY, String originEvidence,
                              long expectedTightBytes, boolean proven) {
            this.originX = originX;
            this.originY = originY;
            this.originEvidence = originEvidence;
            this.expectedTightBytes = expectedTightBytes;
            this.proven = proven;
        }

        JSONObject toJson(ImageFrame frame, int sourceCfaPattern) throws Exception {
            JSONObject j = new JSONObject();
            j.put("schema", "m9cam.sourcegeometryproof.v2a.acquisition_copy");
            j.put("revision", "SOURCEGEOMETRYPROOF2A");
            j.put("runtimeGatePassed", proven);
            j.put("photographicPixelChange", false);
            j.put("sourceImageFormat", frame.m9SourceImageFormat);
            j.put("sourceImageWidth", frame.m9SourceImageWidth);
            j.put("sourceImageHeight", frame.m9SourceImageHeight);
            j.put("sourceRowStrideBytes", frame.m9SourceRowStrideBytes);
            j.put("sourcePixelStrideBytes", frame.m9SourcePixelStrideBytes);
            j.put("sourceCopyOffsetBytes", frame.m9SourceCopyOffsetBytes);
            j.put("sourceCopyCapacityBytes", frame.m9SourceCopyCapacityBytes);
            j.put("sourcePlaneCapacityBytes", frame.m9SourcePlaneCapacityBytes);
            j.put("ownedBufferCapacityBytes", frame.buffer != null ? frame.buffer.capacity() : -1);
            j.put("frameWidth", frame.width);
            j.put("frameHeight", frame.height);
            j.put("aspect169RequestedAtAcquisition", frame.m9SourceAspect169Requested);
            j.put("binningRequestedAtAcquisition", frame.m9SourceBinningRequested);
            j.put("expectedTightRawBytes", expectedTightBytes);
            j.put("sourceCfaPattern", sourceCfaPattern);
            j.put("resolvedSensorOriginX", originX);
            j.put("resolvedSensorOriginY", originY);
            j.put("resolvedSensorOriginEvidence", originEvidence);
            j.put("originNowProvenFromAcquisitionAndPhysicalGeometry", true);
            j.put("productionLensShadingAlreadyApplied", true);
            j.put("productionLensShadingPolicy", "existing_NORM030_CFA_aware_pre_demosaic_path_unchanged");
            j.put("proofScope", "tight_unshifted_unbinned_RAW_SENSOR_copy_plus_physical_geometry");
            return j;
        }
    }

    /**
     * Prove that the RAW lattice consumed by the existing source-normalization path
     * is exactly the Camera2 RAW_SENSOR plane we think it is. Dimension-only origin
     * inference is not sufficient for a portable renderer: Photon can optionally
     * shift/crop a source plane, and row padding would make frame.width describe the
     * stride rather than the active Image width. Unsupported layouts fail closed.
     *
     * No photographic arithmetic changes here. On a proven layout the existing
     * SOURCECAL/NORM030/M9 target path receives the identical bytes as before.
     */
    private static SourceGeometryProof2A proveSourceGeometry2A(
            ImageFrame frame,
            CameraCharacteristics characteristics,
            int sourceCfaPattern) {
        if (frame == null || frame.buffer == null) {
            throw new IllegalStateException("SOURCEGEOMETRYPROOF2A missing owned ImageFrame RAW buffer");
        }
        if (frame.m9SourceImageFormat != android.graphics.ImageFormat.RAW_SENSOR) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A requires RAW_SENSOR format; got "
                            + frame.m9SourceImageFormat);
        }
        if (frame.m9SourceAspect169Requested) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A rejects acquisition-time 16:9 crop/shift");
        }
        if (frame.m9SourceBinningRequested) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A rejects acquisition-time Photon binning");
        }
        if (!M9CfaResolver.isSupported(sourceCfaPattern)) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A unsupported Bayer CFA=" + sourceCfaPattern);
        }
        if (frame.m9SourceImageWidth <= 0 || frame.m9SourceImageHeight <= 0) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A source Image dimensions unavailable");
        }
        if (frame.m9SourceImageWidth != frame.width
                || frame.m9SourceImageHeight != frame.height) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A ImageFrame dimensions differ from source Image; source="
                            + frame.m9SourceImageWidth + "x" + frame.m9SourceImageHeight
                            + "; frame=" + frame.width + "x" + frame.height);
        }
        if (frame.m9SourcePixelStrideBytes != 2) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A unsupported RAW pixel stride="
                            + frame.m9SourcePixelStrideBytes);
        }
        final long expectedRowBytes = Math.multiplyExact((long)frame.m9SourceImageWidth, 2L);
        if (frame.m9SourceRowStrideBytes != expectedRowBytes) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A padded/non-tight RAW row stride unsupported; rowStride="
                            + frame.m9SourceRowStrideBytes + "; expected=" + expectedRowBytes);
        }
        if (frame.m9SourceCopyOffsetBytes != 0) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A shifted RAW copy unsupported; offset="
                            + frame.m9SourceCopyOffsetBytes);
        }
        final long expectedBytes = Math.multiplyExact(
                expectedRowBytes, (long)frame.m9SourceImageHeight);
        final long ownedCapacity = frame.buffer.capacity();
        if (frame.m9SourceCopyCapacityBytes != expectedBytes
                || frame.m9SourcePlaneCapacityBytes != expectedBytes
                || ownedCapacity != expectedBytes) {
            throw new IllegalStateException(
                    "SOURCEGEOMETRYPROOF2A RAW capacity mismatch; expected=" + expectedBytes
                            + "; copy=" + frame.m9SourceCopyCapacityBytes
                            + "; plane=" + frame.m9SourcePlaneCapacityBytes
                            + "; owned=" + ownedCapacity);
        }

        // Only after the actual copy layout is proven do dimensions become valid
        // evidence for mapping sample (0,0) into the physical sensor coordinate system.
        SourceRawOrigin1A origin = resolveSourceRawOrigin1A(
                characteristics, frame.m9SourceImageWidth, frame.m9SourceImageHeight);
        return new SourceGeometryProof2A(
                origin.x, origin.y, origin.evidence, expectedBytes, true);
    }

'''
s = s.replace(insert_marker, proof_code + insert_marker, 1)

# Evaluate the proof immediately before the production render. If it fails, the M9
# route fails closed before any source shading/CFA operation can consume guessed geometry.
old_call = '''            long renderCoreStartedNs = System.nanoTime();\n            RenderCore out = renderNativeSourceProduction1P(\n                    frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0,\n                    characteristics, diagnosticCaptureResult1A, sourceCfaPattern);\n            long renderCoreElapsedMs = (System.nanoTime() - renderCoreStartedNs) / 1_000_000L;'''
new_call = '''            SourceGeometryProof2A sourceGeometryProof2A = proveSourceGeometry2A(\n                    frame, characteristics, sourceCfaPattern);\n            long renderCoreStartedNs = System.nanoTime();\n            RenderCore out = renderNativeSourceProduction1P(\n                    frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation, 0.0,\n                    characteristics, diagnosticCaptureResult1A, sourceCfaPattern);\n            long renderCoreElapsedMs = (System.nanoTime() - renderCoreStartedNs) / 1_000_000L;\n            out.diagnostics.put("sourceGeometryProof2A",\n                    sourceGeometryProof2A.toJson(frame, sourceCfaPattern));'''
s = replace_once(s, old_call, new_call, 'production proof gate')

# Make the relationship to the pre-existing shading path explicit in top-level telemetry.
old_diag = '''            out.diagnostics.put("resolvedSourceCfaPattern", sourceCfaPattern);'''
new_diag = '''            out.diagnostics.put("resolvedSourceCfaPattern", sourceCfaPattern);\n            out.diagnostics.put("sourceGeometryProof2ARuntimeVerified", true);\n            out.diagnostics.put("sourceGeometryProof2APixelMutation", false);\n            out.diagnostics.put("sourceGeometryProof2AExistingShadingPathChanged", false);'''
s = replace_once(s, old_diag, new_diag, 'top-level proof telemetry')

renderer.write_text(s)
print('SOURCEGEOMETRYPROOF2A applied')
print(' - Image -> ImageFrame source copy facts recorded')
print(' - production M9 route fails closed on shifted/cropped/binned/padded/unproven RAW layouts')
print(' - source sensor origin is accepted only after acquisition copy geometry is proven')
print(' - existing NORM030 LensShadingMap/CFA/source calibration/M9 target arithmetic is unchanged')
print(' - photographic pixel change: none on proven layouts')
