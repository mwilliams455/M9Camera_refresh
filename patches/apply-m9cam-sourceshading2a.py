#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourceshading2a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
repo = Path(__file__).resolve().parents[1]
if not (root / 'app').is_dir():
    raise SystemExit('not a PhotonCamera root: ' + str(root))

image_frame = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/ImageFrame.java'
saver = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/SaverImplementation.java'
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
helper_src = repo / 'payload/app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceShadingApply2A.java'
helper_dst = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9SourceShadingApply2A.java'
for p in (image_frame, saver, renderer, helper_src):
    if not p.exists():
        raise SystemExit('SOURCESHADING2A missing required file: ' + str(p))
helper_dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(helper_src, helper_dst)


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'SOURCESHADING2A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

# 1) Carry the real Camera Image->ImageFrame copy provenance with the owned frame.
s = image_frame.read_text()
s = replace_once(s,
'''    public IsoExpoSelector.ExpoPair pair;\n''',
'''    public IsoExpoSelector.ExpoPair pair;\n\n    // SOURCESHADING2A acquisition provenance. These fields describe the exact\n    // camera Image plane copied into this owned frame. They are diagnostic/gating\n    // metadata only and never alter the buffer copy itself.\n    public int m9SourceImageFormat = -1;\n    public int m9SourceImageWidth = -1;\n    public int m9SourceImageHeight = -1;\n    public int m9SourceRowStrideBytes = -1;\n    public int m9SourcePixelStrideBytes = -1;\n    public int m9SourceCopyOffsetBytes = -1;\n    public int m9SourceCopyCapacityBytes = -1;\n    public int m9SourcePlaneCapacityBytes = -1;\n    public boolean m9SourceAspect169Requested = false;\n    public boolean m9SourceBinningRequested = false;\n''', 'ImageFrame provenance fields')
image_frame.write_text(s)

s = saver.read_text()
s = replace_once(s,
'''        ImageFrame frame = new ImageFrame(image.getPlanes()[0].getBuffer(), image.getFormat(), width, image.getPlanes()[0].getRowStride(), offset, capacity);\n        frame.timestamp = image.getTimestamp();\n''',
'''        ImageFrame frame = new ImageFrame(image.getPlanes()[0].getBuffer(), image.getFormat(), width, image.getPlanes()[0].getRowStride(), offset, capacity);\n        // SOURCESHADING2A: preserve the exact acquisition/copy facts so RAW\n        // geometry can be proven at render time instead of inferred from dimensions.\n        frame.m9SourceImageFormat = image.getFormat();\n        frame.m9SourceImageWidth = image.getWidth();\n        frame.m9SourceImageHeight = image.getHeight();\n        frame.m9SourceRowStrideBytes = image.getPlanes()[0].getRowStride();\n        frame.m9SourcePixelStrideBytes = image.getPlanes()[0].getPixelStride();\n        frame.m9SourceCopyOffsetBytes = offset;\n        frame.m9SourceCopyCapacityBytes = capacity;\n        frame.m9SourcePlaneCapacityBytes = image.getPlanes()[0].getBuffer().capacity();\n        frame.m9SourceAspect169Requested = PhotonCamera.getSettings().aspect169;\n        frame.m9SourceBinningRequested = PhotonCamera.getSettings().binning;\n        frame.timestamp = image.getTimestamp();\n''', 'SaverImplementation provenance capture')
saver.write_text(s)

# 2) Keep ordinary production render byte-for-byte in behavior, but add a second
# same-RAW diagnostic render with source shading enabled and TC20 gain locked to
# the control frame's original TC20 decision. This branch is validation-only.
s = renderer.read_text()
if 'm9SensorTarget1ARuntimeVerified' not in s:
    raise SystemExit('SOURCESHADING2A requires assembled M9SENSORTARGET1A baseline')
if 'm9cam.tonebound.v1a.050ev' not in s:
    raise SystemExit('SOURCESHADING2A requires assembled TONEBOUND050 baseline')

old_call = '''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation);'''
new_call = '''            RenderCore out = renderCore(frame.buffer, frame.width, frame.height,\n                    encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation,\n                    false, Double.NaN, frame, characteristics, captureResult, params.cfaPattern);'''
s = replace_once(s, old_call, new_call, 'control renderCore call')

old_sig = '''    private static RenderCore renderCore(ByteBuffer rawBuffer,\n                                         int width,\n                                         int height,\n                                         float[] black,\n                                         int whiteLevel,\n                                         float[] neutralF,\n                                         int cameraRotation) throws Exception {'''
new_sig = '''    private static RenderCore renderCore(ByteBuffer rawBuffer,\n                                         int width,\n                                         int height,\n                                         float[] black,\n                                         int whiteLevel,\n                                         float[] neutralF,\n                                         int cameraRotation,\n                                         boolean sourceShading2ARequested,\n                                         double sourceShading2AForcedTc20Gain,\n                                         ImageFrame sourceFrame,\n                                         CameraCharacteristics sourceCharacteristics,\n                                         CaptureResult sourceCaptureResult,\n                                         int sourceCfaPattern) throws Exception {'''
s = replace_once(s, old_sig, new_sig, 'renderCore signature')

# Apply the physical map only after black/white normalization and before demosaic.
anchor = '''        normalizeRawElapsedMs = (System.nanoTime() - normalizeRawStartedNs) / 1_000_000L;\n\n        Mat rawMat = new Mat(height, width, CvType.CV_16UC1);'''
insertion = '''        normalizeRawElapsedMs = (System.nanoTime() - normalizeRawStartedNs) / 1_000_000L;\n\n        // SOURCESHADING2A: source-domain correction only. The helper fails closed\n        // unless the original Camera Image -> ImageFrame copy is proven tight,\n        // unshifted, uncropped RAW_SENSOR and matches the pre-correction region.\n        M9SourceShadingApply2A.Result sourceShading2A = M9SourceShadingApply2A.applyInPlace(\n                norm16, width, height, sourceFrame, sourceCharacteristics,\n                sourceCaptureResult, sourceCfaPattern, sourceShading2ARequested);\n\n        Mat rawMat = new Mat(height, width, CvType.CV_16UC1);'''
s = replace_once(s, anchor, insertion, 'pre-demosaic shading seam')

# Lock the second pass to the control's original TC20 decision before TONEBOUND.
anchor = '''            meterTc20ElapsedMs = (System.nanoTime() - meterStartedNs) / 1_000_000L;\n'''
insertion = '''            meterTc20ElapsedMs = (System.nanoTime() - meterStartedNs) / 1_000_000L;\n            final double sourceShading2AComputedTc20Gain = meter.gain;\n            final boolean sourceShading2AGainLock = sourceShading2ARequested\n                    && Double.isFinite(sourceShading2AForcedTc20Gain)\n                    && sourceShading2AForcedTc20Gain > 0.0;\n            if (sourceShading2AGainLock) {\n                meter.gain = sourceShading2AForcedTc20Gain;\n            }\n'''
s = replace_once(s, anchor, insertion, 'TC20 gain-lock seam')

# Attach source-stage telemetry to both control and diagnostic passes.
anchor = '''            d.put("inputWidth", width);\n            d.put("inputHeight", height);'''
insertion = '''            d.put("inputWidth", width);\n            d.put("inputHeight", height);\n            d.put("sourceShading2A", sourceShading2A.toJson(\n                    sourceFrame, width, height, sourceCfaPattern));\n            d.put("sourceShading2ARequested", sourceShading2ARequested);\n            d.put("sourceShading2AComputedTc20GainBeforeLock", sourceShading2AComputedTc20Gain);\n            d.put("sourceShading2AForcedTc20Gain", sourceShading2AGainLock\n                    ? sourceShading2AForcedTc20Gain : JSONObject.NULL);\n            d.put("sourceShading2ATc20GainLockedToControl", sourceShading2AGainLock);'''
s = replace_once(s, anchor, insertion, 'source shading diagnostics')

# After the exact production JPEG payload/timing is frozen, run the secondary
# shaded pass from the same owned RAW. Never replace or rename the primary JPEG.
old = '''            ImageSaver.Util.M9JpegSaveTiming jpegTiming = ImageSaver.Util.consumeM9JpegSaveTiming();\n            bitmap = null;\n            if (!jpgSaved) throw new IllegalStateException("M9 JPEG payload save failed");\n            if (SAVE_PARITY_PNG && !pngSaved) throw new IllegalStateException("M9 parity PNG save failed");\n\n            long elapsedMs = (System.nanoTime() - started) / 1_000_000L;'''
new = '''            ImageSaver.Util.M9JpegSaveTiming jpegTiming = ImageSaver.Util.consumeM9JpegSaveTiming();\n            if (!jpgSaved) throw new IllegalStateException("M9 JPEG payload save failed");\n            if (SAVE_PARITY_PNG && !pngSaved) throw new IllegalStateException("M9 parity PNG save failed");\n\n            JSONObject sourceShading2ABank = new JSONObject();\n            sourceShading2ABank.put("schema", "m9cam.sourceshading.v2a.sameraw.bank");\n            sourceShading2ABank.put("controlPrimaryJpeg", jpgPath.toString());\n            sourceShading2ABank.put("controlPixelMutation", false);\n            sourceShading2ABank.put("onlyIntendedVariant",\n                    "live_Camera2_lens_shading_map_before_demosaic_gainlocked_to_control_TC20");\n            if (primaryRoute && out.diagnostics.optBoolean("m9SensorTarget1ARuntimeVerified", false)) {\n                JSONObject controlTone = out.diagnostics.optJSONObject("toneBound1A");\n                double controlOriginalTc20 = controlTone != null\n                        ? controlTone.optDouble("originalTc20Gain", Double.NaN)\n                        : out.diagnostics.optDouble("gain", Double.NaN);\n                double controlBoundedGain = controlTone != null\n                        ? controlTone.optDouble("boundedEffectiveRenderGain", Double.NaN)\n                        : Double.NaN;\n                sourceShading2ABank.put("controlOriginalTc20Gain", controlOriginalTc20);\n                sourceShading2ABank.put("controlBoundedEffectiveRenderGain", controlBoundedGain);\n                if (Double.isFinite(controlOriginalTc20) && controlOriginalTc20 > 0.0) {\n                    if (bitmap != null && !bitmap.isRecycled()) bitmap.recycle();\n                    bitmap = null;\n                    long shadingVariantStartedNs = System.nanoTime();\n                    try {\n                        RenderCore shaded = renderCore(frame.buffer, frame.width, frame.height,\n                                encodedBlack, params.whiteLevel, params.whitePoint, cameraRotation,\n                                true, controlOriginalTc20, frame, characteristics, captureResult, params.cfaPattern);\n                        JSONObject shadedSource = shaded.diagnostics.optJSONObject("sourceShading2A");\n                        boolean shadingApplied = shadedSource != null\n                                && shadedSource.optBoolean("applied", false);\n                        sourceShading2ABank.put("variantSourceShading",\n                                shadedSource != null ? shadedSource : JSONObject.NULL);\n                        sourceShading2ABank.put("variantComputedTc20GainBeforeLock",\n                                shaded.diagnostics.optDouble("sourceShading2AComputedTc20GainBeforeLock", Double.NaN));\n                        sourceShading2ABank.put("variantTc20GainLockedToControl",\n                                shaded.diagnostics.optBoolean("sourceShading2ATc20GainLockedToControl", false));\n                        JSONObject shadedTone = shaded.diagnostics.optJSONObject("toneBound1A");\n                        if (shadedTone != null) {\n                            sourceShading2ABank.put("variantToneBound1A", shadedTone);\n                            double shadedBounded = shadedTone.optDouble("boundedEffectiveRenderGain", Double.NaN);\n                            sourceShading2ABank.put("variantBoundedEffectiveRenderGain", shadedBounded);\n                            if (Double.isFinite(controlBoundedGain) && Double.isFinite(shadedBounded)) {\n                                sourceShading2ABank.put("boundedEffectiveGainDelta",\n                                        shadedBounded - controlBoundedGain);\n                            }\n                        }\n                        sourceShading2ABank.put("variantRgb8ClipFraction",\n                                shaded.diagnostics.optDouble("rgb8ClipFraction", Double.NaN));\n                        sourceShading2ABank.put("variantRenderNearWhiteFraction",\n                                shaded.diagnostics.optDouble("renderNearWhiteFraction", Double.NaN));\n                        if (shadingApplied) {\n                            Path shadingPath = Paths.get(FileManager.sDCIM_CAMERA.getAbsolutePath(),\n                                    stem + "_SOURCESHADING2A_SAMERAW_GAINLOCK.jpg");\n                            boolean shadingSaved = saveSourceShading2AJpeg(shadingPath, shaded.bitmap);\n                            sourceShading2ABank.put("status", shadingSaved ? "completed" : "jpeg_save_failed");\n                            sourceShading2ABank.put("variantJpeg", shadingPath.toString());\n                            sourceShading2ABank.put("variantJpegSaved", shadingSaved);\n                        } else {\n                            sourceShading2ABank.put("status", "skipped_source_provenance_or_map_gate");\n                        }\n                        if (shaded.bitmap != null && !shaded.bitmap.isRecycled()) shaded.bitmap.recycle();\n                    } catch (Throwable shadingError) {\n                        sourceShading2ABank.put("status", "variant_failed_primary_preserved");\n                        sourceShading2ABank.put("error", shadingError.toString());\n                    }\n                    sourceShading2ABank.put("variantElapsedMs",\n                            (System.nanoTime() - shadingVariantStartedNs) / 1_000_000.0);\n                } else {\n                    sourceShading2ABank.put("status", "skipped_missing_control_TC20_gain");\n                }\n            } else {\n                sourceShading2ABank.put("status", "skipped_nonprimary_or_unverified_sensor_target");\n            }\n            out.diagnostics.put("sourceShading2ASameRawBank", sourceShading2ABank);\n            bitmap = null;\n\n            long elapsedMs = (System.nanoTime() - started) / 1_000_000L;'''
s = replace_once(s, old, new, 'same-RAW bank insertion')

# Standalone diagnostic JPEG writer; intentionally does not touch primary EXIF/publication.
anchor = '''    private static synchronized void ensureOpenCv() {'''
helper = '''    private static boolean saveSourceShading2AJpeg(Path path, Bitmap bitmap) {\n        if (path == null || bitmap == null || bitmap.isRecycled()) return false;\n        try {\n            Files.createDirectories(path.getParent());\n            try (OutputStream os = Files.newOutputStream(path)) {\n                return bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, os);\n            }\n        } catch (Throwable t) {\n            Log.e(TAG, "SOURCESHADING2A diagnostic JPEG save failed", t);\n            return false;\n        }\n    }\n\n    private static synchronized void ensureOpenCv() {'''
s = replace_once(s, anchor, helper, 'diagnostic JPEG helper')

renderer.write_text(s)
print('SOURCESHADING2A applied')
print(' - primary JPEG remains the M9SENSORTARGET1A/TONEBOUND050 control')
print(' - secondary JPEG uses the identical owned RAW with Camera2 lens shading before demosaic')
print(' - secondary TC20 gain is locked to the control original TC20 decision')
print(' - RAW acquisition provenance is captured at Image -> ImageFrame copy')
print(' - map application fails closed for cropped/padded/offset/binned/unproven RAWs')
print(' - native M9 colour core and target assets are untouched')
