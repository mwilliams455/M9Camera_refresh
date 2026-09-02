#!/usr/bin/env python3
from pathlib import Path
import hashlib, re, sys

if len(sys.argv) != 2:
    raise SystemExit("usage: verify-m9cam-v0.7-r35.py <PhotonCamera-root>")
root = Path(sys.argv[1]).resolve()

checks = []
failures = []

def load(rel):
    p = root / rel
    if not p.is_file():
        failures.append(f"MISSING FILE: {rel}")
        return ""
    return p.read_text(errors="replace")

def require(label, ok, detail=""):
    if ok:
        checks.append(label)
        print(f"OK   {label}")
    else:
        msg = f"FAIL {label}" + (f": {detail}" if detail else "")
        failures.append(msg)
        print(msg)

policy_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/M9ModernExposurePolicy.java"
analyzer_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/M9SubjectMotionAnalyzer.java"
backlight_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/M9BacklightDiagnostic.java"
isosel_rel = "app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java"
meta_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/M9CaptureMetadataWriter.java"
saver_rel = "app/src/main/java/com/particlesdevs/photoncamera/processing/DefaultSaver.java"
image_saver_rel = "app/src/main/java/com/particlesdevs/photoncamera/processing/ImageSaver.java"
render_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
queue_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java"
finalizer_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9JpegFinalizeQueue.java"
timing_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java"
pathalloc_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/M9CapturePathAllocator.java"
ui_rel = "app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraUIController.java"
cal_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Calibration.java"
asset_rel = "app/src/main/assets/m9/m9_r35_calibration.bin"
native_java_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java"
native_cpp_rel = "app/src/main/cpp/m9color_jni.cpp"
cmake_rel = "app/src/main/cpp/CMakeLists.txt"
gradle_rel = "app/build.gradle"

policy = load(policy_rel)
analyzer = load(analyzer_rel)
backlight = load(backlight_rel)
isosel = load(isosel_rel)
meta = load(meta_rel)
saver = load(saver_rel)
image_saver = load(image_saver_rel)
render = load(render_rel)
queue = load(queue_rel)
finalizer = load(finalizer_rel)
timing = load(timing_rel)
pathalloc = load(pathalloc_rel)
ui = load(ui_rel)
cal = load(cal_rel)
native_java = load(native_java_rel)
native_cpp = load(native_cpp_rel)
cmake = load(cmake_rel)
gradle = load(gradle_rel)
asset = root / asset_rel

# Frozen v0.6.1 exposure invariants; tolerate whitespace and Java numeric suffixes.
def const(name, value):
    pat = rf"\b{name}\s*=\s*{re.escape(value)}(?:[dDfF])?\s*;"
    require(f"exposure {name}={value}", re.search(pat, policy) is not None)

const("MOTION_ACTIVATE", "0.52")
const("PERSISTENCE_PEAK_SCALE", "0.96")
const("PERSISTENCE_MAX_BOOST", "0.08")
const("ANALOG_HEADROOM_FRACTION", "0.95")
require("motion analyzer recent-peak getter", "getRecentPeakScore" in analyzer)
require("LUMA1 subject-motion schema", "m9cam.subjectmotion.v3.luma1" in analyzer)
require("LUMA2.3 preview schema", "m9cam.previewluma.v2.spatial1" in analyzer)
require("LUMA1 global percentile diagnostics", all(k in analyzer for k in ["q95MinusMedian", "darkFractionLE48", "brightFractionGE224"]))
require("legacy LUMA1 spatial diagnostics retained", all(k in analyzer for k in ["center_50_percent_width_height", "topMinusBottomMedian"]))
require("LUMA2.3 orientation-aware 3x3 diagnostics", all(k in analyzer for k in ["m9cam.previewluma.spatial3x3.v1", "display_after_cameraRotation", "displayHorizontalThirds", "displayVerticalThirds", "rotationAppliedDegrees"]))
require("metadata passes camera rotation to analyzer snapshot", "M9SubjectMotionAnalyzer.snapshotJson(cameraRotation)" in meta)
require("LUMA2.4 diagnostic scorer present", bool(backlight))
require("LUMA2.4 diagnostic schema", "m9cam.backlightdiagnostic.v4.luma2p4" in backlight)
require("DNGASYNC1A TIMINGFREEZE1A NAME1A QUEUE1B backlight build marker", "1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a" in backlight)
require("PRIMARY2.4 TC20NATIVE1B ORIENT1A renderer schema declared by build identity", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1" in backlight)
require("LUMA2.4 live applied EV is logged", "appliedExposureCorrectionEv" in backlight and "feedbackSnapshotJson" in backlight)
require("LUMA2.4 FB1 feedback enabled", 'out.put("feedbackEnabled", true)' in backlight and 'o.put("exposureFeedbackEnabled", true)' in backlight)
require("LUMA2.4 bounded recommendation", "MAX_RECOMMENDED_EV = 0.75" in backlight)
require("LUMA2.4 retained scalar component scoring", all(k in backlight for k in ["darkBodyScore", "brightPopulationScore", "bodyHighlightSeparationScore", "relativeBodyHighlightStructureScore", "absoluteBrightConfidenceMultiplier", "energyStarvationScore", "backlightStarvationScore"]))
require("LUMA2.4 retained absolute-bright confidence floor", "ABSOLUTE_BRIGHT_CONFIDENCE_FLOOR = 0.62" in backlight)
require("LUMA2.4 retained center-body protection ramp", all(k in backlight for k in ["CENTER_PROTECTION_START_Y = 16.0", "CENTER_PROTECTION_FULL_Y = 28.0", "centerBodyProtectionMultiplier"]))
require("LUMA2.4 retained catastrophic preview-collapse branch", all(k in backlight for k in ["CATA_ENERGY_FULL_SCORE = 0.03", "catastrophicMedianDarkScore", "catastrophicQ95DarkScore", "catastrophicQ99DarkScore", "catastrophicAeStarvationScore"]))
require("LUMA2.4 final union score", "Math.max(" in backlight and "protectedRelativeBacklightStarvationScore" in backlight and "protectedSpatialBacklightStarvationScore" in backlight and "catastrophicAeStarvationScore" in backlight)
require("SPATIAL2 landscape protection", all(k in backlight for k in ["LANDSCAPE_BRIGHT192_LOW = 0.15", "LANDSCAPE_TOP_BRIGHT_SHARE_LOW = 0.72", "LANDSCAPE_TOP_MEDIAN_HETERO_LOW = 0.28", "landscapeHighContrastProtectionScore"]))
require("SPATIAL2 high-energy foreground branch", all(k in backlight for k in ["SPATIAL_DARK64_LOW = 0.28", "SPATIAL_Q95_LOW_Y = 135.0", "SPATIAL_AXIS_SPREAD_LOW = 0.30", "rawSpatialBacklightStarvationScore"]))
require("SPATIAL2 catastrophic branch cannot be guard-suppressed", "catastrophicAeStarvationScore" in backlight and "landscapeProtectionMultiplier" in backlight)
require("FB1 live classifier called by IsoExpoSelector", "M9BacklightDiagnostic.evaluateLiveFeedback" in isosel)
require("FB1 target energy correction uses existing ExpoPair compensation", "pair.ExpoCompensateLower(1.0 / m9FeedbackFactor)" in isosel)
require("FB1 correction precedes M9Modern cap allocation", isosel.find("M9BacklightDiagnostic.evaluateLiveFeedback") < isosel.find("M9ModernExposurePolicy.adjustCaps"))
require("FB1 bypasses GenerateExpoPair(-1) preflight", "step >= 0" in isosel and "feedback_bypassed_preflight_probe" in isosel)
require("FB1 resolves live rotation before classifier", "PhotonCamera.getGravity().getCameraRotation(captureController.mSensorOrientation)" in isosel and "m9FeedbackRotationDegrees" in isosel)
require("M9Modern exposure policy called by IsoExpoSelector", "M9ModernExposurePolicy.adjustCaps" in isosel)
require("PhotonCurrent reference logging retained", "recordPhotonCurrentReference" in isosel)
require("PhotonCurrent reference remains pre-feedback", isosel.find("recordPhotonCurrentReference") < isosel.find("M9BacklightDiagnostic.evaluateLiveFeedback"))

# Renderer payload and calibration.
require("R3.5 renderer source present", bool(render))
require("R3.5 calibration loader present", bool(cal))
require("R3.5 calibration asset present", asset.is_file())
if asset.is_file():
    got = hashlib.sha256(asset.read_bytes()).hexdigest()
    want = "5568978ea42e7c65b51f26ffc2d56479418ec6c8d98b242199bab08acb62cbca"
    require("R3.5 calibration SHA-256", got == want, f"got {got}")

# Verify PRIMARY1 functional seams rather than comments/formatting.
require("DefaultSaver uses PRIMARY1 route", "M9 PRIMARY1" in saver)
require("DefaultSaver transfers existing Photon ImageFrame", "ImageFrame primaryFrame" in saver and "IMAGE_BUFFER.get(0)" in saver)
require("DefaultSaver does not make ASYNC1 RAW copy", "detachForBackground" not in saver)
require("DefaultSaver releases buffer before PRIMARY1 enqueue", saver.find("bufferLock = false") < saver.find("M9PrimaryRenderQueue.enqueue"))
require("DefaultSaver queues primary renderer", "M9PrimaryRenderQueue.enqueue" in saver)
require("PRIMARY1 queue owns original frame", "direct_Photon_ImageFrame_transfer" in queue and "ownedFrame.close()" in queue)
require("PRIMARY1 queue is bounded", "MAX_PENDING = 2" in queue and "ArrayBlockingQueue" in queue)
require("QUEUE1B fallback queue-full path is nonblocking", "getQueue().put(job)" not in queue and "primary_queue_full_nonblocking_reject" in queue)
require("QUEUE1B enqueue fallback reports acceptance", "public static boolean enqueue" in queue and "return false" in queue and "return true" in queue)
require("QUEUE1B rejection/in-flight counters present", "AtomicLong" in queue and "QUEUE_FULL_COUNT" in queue and "ADMISSION_REJECT_COUNT" in queue and "IN_FLIGHT_COUNT" in queue and "MAX_IN_FLIGHT" in queue)
require("QUEUE1B DefaultSaver keeps boolean fallback result", "queued = M9PrimaryRenderQueue.enqueue" in saver)
require("QUEUE1B telemetry fields", all(k in timing for k in ["queueDepthAtEnqueue", "activeRenderCountAtEnqueue", "queueCapacity", "queueFullCountAtEnqueue", "enqueueWaitElapsedMs", "queueAccepted", "queueOutcome", "shutterAdmissionPolicy", "admissionRejectCountSnapshot", "captureStemPolicy"]))
require("QUEUE1B fallback rejected timing write is asynchronous", "writeRejectedAsync" in timing and "Executors.newSingleThreadExecutor" in timing)
require("TIMINGFREEZE1A accepted timing freeze is asynchronous I/O", "freezeAndWriteAsync" in timing and "TIMING_WRITER.execute" in timing and "persistFrozen" in timing)
require("TIMINGFREEZE1A freezes immutable bytes before I/O", "FrozenTiming" in timing and "byte[] bytes" in timing and "new JSONObject(rendererDiagnostics.toString())" in timing)
require("DNGASYNC1A bounded single DNG worker", "DNG_MAX_PENDING = 1" in queue and "M9PrimaryDngIO" in queue and "new ArrayBlockingQueue<>(DNG_MAX_PENDING)" in queue)
require("DNGASYNC1A capture metadata describes bounded async DNG policy", "bounded_async_single_worker_after_jpeg_with_sync_fallback" in render and "primary_worker_after_jpeg" not in render)
require("DNGASYNC1A render worker hands RAW to DNG executor", "DNG_EXECUTOR.execute" in queue and "frameTransferredToDngWorker = true" in queue and "RAW ownership handoff accepted" in queue)
require("DNGASYNC1A bounded saturation falls back synchronously", "RejectedExecutionException dngFull" in queue and "DNG_HANDOFF_FALLBACK_COUNT.incrementAndGet" in queue and "runDngAndFinalize(dngJob, false, true" in queue)
require("DNGASYNC1A async DNG owns final RAW close", queue.find("runDngAndFinalize(job, true, false") >= 0 and queue.find("job.ownedFrame.close()", queue.find("runDngAndFinalize")) >= 0)
require("TIMINGFREEZE1A final timing freezes before DNG-owned RAW close", queue.find("M9PrimaryTimingWriter.freezeAndWriteAsync", queue.find("runDngAndFinalize")) >= 0 and queue.find("M9PrimaryTimingWriter.freezeAndWriteAsync", queue.find("runDngAndFinalize")) < queue.find("job.ownedFrame.close()", queue.find("runDngAndFinalize")))
require("DNGASYNC1A render in-flight releases independently of async RAW lifetime", "RAW owned by M9PrimaryDngIO; next render may start now" in queue and "IN_FLIGHT_COUNT.decrementAndGet()" in queue)
require("TIMINGFREEZE1A no synchronous accepted timing writer", "M9PrimaryTimingWriter.write(" not in queue)
require("TIMINGFREEZE1A+DNGASYNC1A telemetry fields", all(k in timing for k in ["primaryTimingMode", "primaryTimingFrozenBeforeFrameRelease", "primaryTimingIoOffRenderWorker", "primaryTimingFreezeElapsedMs", "workerElapsedBoundary", "dngPersistMode", "dngAsyncAccepted", "dngQueueWaitElapsedMs", "dngWorkerElapsedMs", "rawFrameCloseOwner"]))
require("QUEUE1B shutter admission preflight exists", "preflightCaptureAdmission" in queue and "ADMISSION_REJECT_COUNT" in queue)
require("QUEUE1B gates before takePicture", ui.find("M9PrimaryRenderQueue.preflightCaptureAdmission()") >= 0 and ui.find("M9PrimaryRenderQueue.preflightCaptureAdmission()") < ui.find("cameraFragment.captureController.takePicture()"))
require("QUEUE1B gate is M9-only", "M9Config.isCaptureTest()" in ui)
require("NAME1A allocator present", "System.currentTimeMillis()" in pathalloc and "sameTokenSequence" in pathalloc and "resolveSibling" in pathalloc)
require("NAME1A allocated path feeds primary route", "M9CapturePathAllocator.allocate(ImagePath.newDNGFilePath())" in saver)
require("PRIMARY1 queue is single-worker", "1, 1, 0L" in queue)
require("PRIMARY1 worker uses normal processing priority", "THREAD_PRIORITY_DEFAULT" in queue)
require("PRIMARY1 renders finished JPEG before dev DNG", queue.find("renderAndSavePrimary") < queue.find("saveSingleRaw"))
require("PRIMARY1 keeps temporary untouched DNG", "ImageSaver.Util.saveSingleRaw" in queue)
require("EXIFASYNC1A surfaces JPEG completion only from finalizer", "notifyImageSavedStatus(true, jpegPath)" in finalizer and "processingEventsListener.notifyImageSavedStatus(true, jpegPath)" not in queue)
require("EXIFASYNC1A+DNGASYNC1A timing writer present", "m9cam.primarytiming.v6.exifasync1a.dngasync1a" in timing and "TIMINGFREEZE1A" in timing and "DNGASYNC1A" in timing and "EXIFASYNC1A" in timing)
require("PRIMARY1 timing uses Photon SAF storage helper", "SimpleStorageHelper.openOutputStreamByAbsPath(frozen.timingPath.toString())" in timing)
require("PRIMARY1 timing avoids direct java.nio file output", "Files.newOutputStream(timingPath)" not in timing and "java.nio.file.Files" not in timing)
require("PRIMARY1 timing records ownership/copy elimination", all(k in timing for k in ["rawHandoffCopy", "ownershipTransferElapsedMs", "queueWaitElapsedMs", "renderElapsedMs", "dngSaveElapsedMs"]))
require("capture JSON remains frozen synchronously", "M9CaptureMetadataWriter.write" in saver and saver.find("M9CaptureMetadataWriter.write") < saver.find("bufferLock = false"))
require("renderer exposes primary save entry", "renderAndSavePrimary" in render)
require("primary JPEG uses normal Photon filename", 'stem + (primaryRoute ? ".jpg" : "_M9.jpg")' in render)
require("renderer exposes stage timing", all(k in render for k in ["normalizeRawElapsedMs", "demosaicElapsedMs", "meterTc20ElapsedMs", "fullColorRenderElapsedMs", "jpegEncodeWriteElapsedMs"]))
require("background renderer does not race capture JSON", render.count("lastDiagnostics = diag;") == 0)
require("metadata captures renderer diagnostics", "M9R35Renderer.snapshotJson" in meta and "m9Renderer" in meta)
require("metadata captures LUMA2.4 build identity", "M9BacklightDiagnostic.buildIdentityJson" in meta and "m9Build" in meta)
require("metadata captures FB1 audit record", "M9BacklightDiagnostic.feedbackSnapshotJson" in meta and "m9ExposureFeedback" in meta)
require("metadata captures LUMA2.4 scorer", "M9BacklightDiagnostic.snapshotJson" in meta and "m9BacklightDiagnostic" in meta)

# R3.8-H25/TG1 implementation landmarks; exposure and the rest of the colour pipeline remain frozen.
require("OpenCV EA Bayer demosaic", "COLOR_BayerRG2BGR_EA" in render)
require("OpenCV frozen meter INTER_AREA resize", "INTER_AREA" in render and "METER_LONG_SIDE = 1600" in render)
require("FULL12 native long side", "LONG_SIDE = 4096" in render)
require("COLORNATIVE2A bounded native blocks", "NATIVE_COLOR_BLOCK_ROWS = 384" in render and "cam16.get(y0, 0, camBlock)" in render)
require("COLORNATIVE2A bounded native colour workers", "NATIVE_COLOR_WORKERS" in render and "Math.min(8, Runtime.getRuntime().availableProcessors())" in render)
require("NORMNATIVE1A bounded native RAW normalization workers", "PARALLEL_NORMALIZE_WORKERS" in render and "M9NativeColorCore.normalizeRawDirect" in render)
require("NORMNATIVE1A direct RAW ByteBuffer bridge", "normalizeRawDirect" in native_java and "GetDirectBufferAddress" in native_cpp)
require("NORMNATIVE1A native disjoint row normalization", "normalizeRangeNative" in native_cpp and "workerHistograms" in native_cpp and "workerClipped" in native_cpp)
require("NORMNATIVE1A records normalization mode", "native_directbuffer_disjoint_row_ranges_histogram_reduce" in render and "parallelNormalizeWorkers" in render)
require("NORMNATIVE1A detailed timing", all(k in render for k in ["nativeNormalizeRawElapsedMs", "nativeNormalizeComputeElapsedMs", "nativeNormalizeOutputCopyElapsedMs", "nativeLibraryLoadElapsedMs"]))
deferred_rel = "app/src/main/java/com/particlesdevs/photoncamera/m9/M9DeferredMetadataStore.java"
deferred = load(deferred_rel)
require("METAFREEZE1A writer stages frozen bytes", "M9DeferredMetadataStore.stage" in meta)
require("METAFREEZE1A deferred store present", "persistAsyncForDng" in deferred and "THREAD_PRIORITY_BACKGROUND" in deferred)
require("METAFREEZE1A queue schedules persistence", "persistAsyncForDng" in queue)
require("METAFREEZE1A timing identity", "METAFREEZE1A" in timing and "captureMetadataPersistScheduled" in timing)
perf3h_cvdirect = ("PERF3H_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A" in render
        or "PERF3I_BITMAPDIRECT1A_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A" in render)
if perf3h_cvdirect:
    require(
        "COLORNATIVE2A guarded direct OpenCV handoff with copied fallback",
        all(k in render for k in [
            "M9NativeColorCore.renderBlockParallelDirect",
            "M9NativeColorCore.renderBlockParallel",
            "cam16.get(y0, 0, camBlock)",
            "opencv_mat_dataaddr_direct1a",
            "nativeColorCvDirectEligible",
            "nativeColorCvFallbackBlocks",
        ])
    )
else:
    require(
        "COLORNATIVE2A serializes OpenCV extraction before JNI",
        render.find("cam16.get(y0, 0, camBlock)") >= 0
        and render.find("M9NativeColorCore.renderBlockParallel") >= 0
        and render.find("cam16.get(y0, 0, camBlock)") < render.find("M9NativeColorCore.renderBlockParallel")
    )
require("ORIENT1A commits after native block completion", render.find("M9NativeColorCore.renderBlockParallel") >= 0 and render.find("oriented.setPixels(argbBlock") >= 0 and render.find("M9NativeColorCore.renderBlockParallel") < render.find("oriented.setPixels(argbBlock"))
require("PRIMARY2.3 native preserves horizontal pair stepping", "for (int x = 0; x < w2; x += 2)" in native_cpp)
require("COLORNATIVE2A records native parallel mode", "native_block_internal_threads_scalar_math" in render and "parallelColorWorkers" in render)
require("PRIMARY2.2 precomposes PP-to-M9 bridge", "ppToM9Unnormalized" in render and "ctx.ppToM9" in render and "matMul3(ctx.m9cm, matMul3(ctx.adapt50ToScene, PP_TO_XYZ))" in render)
require("PRIMARY2.2 removes HSM floating remainder", "hsv6ToRgbWrapped" in render and "double hue = h + HSM_H * d0 * (6.0 / 360.0)" in render and "h % 6.0" not in render)
require("PRIMARY2.3 JNI1 records colour hot-loop mode", "primary22_scalar_cpp_jni_parity1" in render and "9frame_1600_precurve14bit_zero_diff" in render)
require("FULL12 avoids full-res m9 double array", "new double[outPixels * 3]" not in render)
require("FULL12 avoids full-res ylin double array", "new double[outPixels]" not in render)
require("FULL12 parity PNG disabled", "SAVE_PARITY_PNG = false" in render)
require("PRIMARY2.4 TC20NATIVE1B ORIENT1A renderer schema", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1" in render)
require("PRIMARY2.3 JNI FIX7 lazy loader present", 'ensureLoaded' in native_java and 'System.loadLibrary("m9color")' in native_java and 'static {' not in native_java)
cmake = load(cmake_rel)
require("FIX7 restored Photon native ncnnMl target", re.search(r"add_library\s*\(\s*ncnnMl\b", cmake, re.IGNORECASE | re.DOTALL) is not None)
require("FIX7 restored Photon dngCreator target", "dngCreator.cpp" in cmake and "project(dngCreator)" in cmake)
require("FIX7 restored Photon allocator/flac/camera native targets", all(k in cmake for k in ["allocator.cpp", "flacRecorder.cpp", "native-engine.cpp"]))
require("FIX7 exactly one CMake m9color target", len(re.findall(r"add_library\s*\(\s*m9color\b", cmake, re.IGNORECASE | re.DOTALL)) == 1)
require("FIX7 m9color scalar compile flags", all(k in cmake for k in ["target_compile_options(m9color", "-O3", "-ffp-contract=off", "-fno-fast-math"]))
require("PERF3I m9color links jnigraphics", all(k in cmake for k in ["find_library(M9_JNIGRAPHICS_LIB jnigraphics)", "target_link_libraries(m9color PRIVATE ${M9_JNIGRAPHICS_LIB})"]))
for abi in ("arm64-v8a", "armeabi-v7a"):
    so = root / "app/src/main/jniLibs" / abi / "libm9color.so"
    require(f"FIX7 no duplicate {abi} jniLibs m9color", not so.exists())
require("COLORNATIVE2A JNI context lifecycle", all(k in native_java for k in ["createContext", "destroyContext", "renderBlockParallel"]))
require("COLORNATIVE2A JNI is batched per 384-row block", "M9NativeColorCore.renderBlockParallel" in render and "cam16.get(y0, 0, camBlock)" in render)
require("PRIMARY2.3 JNI native kernel present", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderStrip" in native_cpp)
require("COLORNATIVE2A JNI entry present", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_renderBlockParallel" in native_cpp and "renderStripScalar(*ctx" in native_cpp)
require("COLORNATIVE2A FIX1 freezes caller thread_local scratch pointers before child threads", all(k in native_cpp for k in ["const jshort* const camBase = camScratch.data()", "jint* const argbBase = argbScratch.data()", "camBase + camOffset", "argbBase + pixelOffset"]))
require("NORMNATIVE1A JNI entry present", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_normalizeRawDirect" in native_cpp)
require("PRIMARY2.4 native TC20 JNI entry present", "Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_meterTc20WeightedSelect" in native_cpp)
require("PRIMARY2.4 native TC20 bridge present", "M9NativeColorCore.meterTc20WeightedSelect" in render and "tc20MeterNative" in render)
require("PRIMARY2.4 TC20 uses weighted selection", "meterTc20WeightedSelectScalar" in native_cpp and "partitionIndicesByValue" in native_cpp and "weighted_selection_partition_p98_select" in render and "std::sort(order.begin(), order.end()" not in native_cpp)
require("PRIMARY2.4 TC20 keeps Java gain/headroom decision", "tc20JavaGainMath" in render and "out.gain = Math.min(out.baseGain, out.guardGain)" in render)
require("PRIMARY2.4 TC20 has detailed timing", all(k in render for k in ["meterResizeElapsedMs", "meterTransferElapsedMs", "meterWeightElapsedMs", "nativeTc20ElapsedMs"]))
require("PRIMARY2.4 reuses one native context", "final long nativeContextForFrame = nativeColorContext" in render and "tc20MeterNative(meterCam" in render)
require("PRIMARY2.3 native PRIMARY2.2 division semantics", "/ 65535.0" in native_cpp)
require("PRIMARY2.3 native H25 scalar constants", all(k in native_cpp for k in ["HSM_H = 0.25", "HSM_S = 0.85", "HSM_V = 1.00"]))
require("PRIMARY2.3 native exact BT601 pair coefficients", all(k in native_cpp for k in ["4899 * r0", "9617 * g0", "1868 * b0", "-2765 * rs", "8192 * bs"]))
require("PRIMARY2.3 native TG1 reconstruction", all(k in native_cpp for k in ["1.402 * crModern", ".344136 * cbModern", ".714136 * crModern", "1.772 * cbModern"]))

require("normal-ISO sRGB Standard curve02", "curve02 normal-ISO sRGB Standard" in render)
require("R3.6 corrected McCamy denominator", "double n = (x - .3320) / (y - .1858);" in render)
require("TG1 negative-Cb compression", "TG_NEG_CB_COMPRESSION = 0.25" in render)
require("TG1 negative-Cr compression", "TG_NEG_CR_COMPRESSION = 0.16" in render)
require("TG1 warm-light smoothstep", "tungstenGuardWeight" in render and "TG_START_K = 4500.0" in render and "TG_FULL_K = 3200.0" in render)
require("legacy wrong McCamy denominator absent", "double n = (x - .3320) / (.1858 - y);" not in render)
require("R3.8 H25/TG1 PRIMARY2.4 TC20NATIVE1B ORIENT1A diagnostic schema", "m9cam.renderer.r38.h25tg1.full12.android.v19.primary2p4tc20native1borient1anormnative1acolornative2afix1" in render)
require("R3.8 H25 hue strength", "HSM_H = 0.25" in render)
require("ORIENT1A no Android Matrix rotation", "android.graphics.Matrix" not in render and "Bitmap.createBitmap(src" not in render)
require("ORIENT1A direct destination bitmap", "native_strip_destination_layout_orient1a" in render and "orientationFusedIntoColorOutput" in render and "directOrientedCommitElapsedMs" in render)
require("ORIENT1A preserves source-horizontal pairing declaration", "source_horizontal_pre_orientation" in render and "for (int x = 0; x < w2; x += 2)" in native_cpp)
require("ORIENT1A native completed-strip mapper", "orientCompletedStrip" in native_cpp and "cameraRotation" in native_cpp)
require("ORIENT1A supports 90/180/270 mappings", all(k in native_cpp for k in ["rotation == 90", "rotation == 180", "rotation == 270"]))
require("PERF3G ORIENTFUSE8A disjoint subrange mapper", all(k in native_cpp for k in ["orientCompletedSubrange", "orientationElapsedNs", "combinedElapsedNs", "orientedBase"]))
require("PERF3G removes serial block orientation from parallel path", "no serial post-worker orientation pass remains here" in native_cpp)
require("PERF3G renderer declares no serial orientation pass", all(k in render for k in ["orientfuse8a_worker_subranges_exact", "nativeColorSerialOrientationPass", "false"]))
require("PERF3H direct OpenCV JNI seams", all(k in native_cpp for k in ["renderBlockParallelDirect", "meterTc20WeightedSelectDirect", "PERF3H CVDIRECT1A"]))
require("PERF3H renderer validates Mat layout and has fallback", all(k in render for k in ["isContinuous()", "elemSize1() == 2L", "step1() == (long)width * 3L", "java_short_array_fallback", "opencv_mat_dataaddr_direct1a"]))
require("PERF3H color direct blocks diagnosed", all(k in render for k in ["nativeColorCvDirectBlocks", "nativeColorCvFallbackBlocks", "nativeColorCvDirectEligible"]))
require("PERF3H meter direct input diagnosed", all(k in render for k in ["meterCvDirectEligible", "meterCvDirectFallback", "meterInputMode"]))
require("PERF3I native Android Bitmap seam", all(k in native_cpp for k in ["renderBlockParallelDirectBitmap", "AndroidBitmap_getInfo", "AndroidBitmap_lockPixels", "ANDROID_BITMAP_FORMAT_RGBA_8888", "storeArgbAsRgba8888", "writeCompletedSubrangeToBitmap"]))
require("PERF3I Java Bitmap eligibility and fallback", all(k in render for k in ["nativeColorBitmapDirectEligible", "oriented.isMutable()", "Bitmap.Config.ARGB_8888", "renderBlockParallelDirectBitmap", "nativeColorBitmapDirectActive = false", "oriented.setPixels(argbBlock"]))
require("PERF3I direct output diagnostics", all(k in render for k in ["nativeColorBitmapOutputMode", "nativeColorBitmapDirectBlocks", "nativeColorBitmapFallbackBlocks", "nativeColorBitmapRowBytes"]))
require("PERF3I no full-frame output staging buffer", "new int[orientedWidth * orientedHeight]" not in render and "new int[Math.multiplyExact(orientedWidth, orientedHeight)]" not in render)

# Build wiring.
require("OpenCV 4.13.0 dependency", "org.opencv:opencv:4.13.0" in gradle)
require("PERF3I BITMAPDIRECT1A renderer marker", "PERF3I_BITMAPDIRECT1A_CVDIRECT1A_ORIENTFUSE8A_EXIFASYNC1A_JPEGBUF64K1A_TC20LUMA8A_COLOR8A" in render)
require("PERF3C retained color timing fields", all(k in render for k in ["nativeColorOpenCvTransferElapsedMsSum", "nativeColorInputCopyElapsedMsSum", "nativeColorWorkerWallElapsedMsSum", "nativeColorThreadOverheadApproxMsSum", "nativeColorOrientationElapsedMsSum", "nativeColorOutputCopyElapsedMsSum"]))
require("PERF3C retained TC20 timing fields", all(k in render for k in ["tc20NativeLumaPopulationElapsedMs", "tc20NativeWeightedMedianElapsedMs", "tc20NativeP98ElapsedMs"]))
require("PERF3C retained native timing probes", all(k in native_cpp for k in ["workerWallStarted", "totalWeightStarted", "p98Started"]))
require("PERF3C TC20 luma parallelism present", all(k in native_cpp for k in ["lumaWorkerCount", "lumaThreads", "orderBuildStarted"]))
require("PERF3C TC20 rebuilds ordered valid index scan", "for (int p = 0; p < pixelCount; ++p)" in native_cpp and "order.push_back(p)" in native_cpp)
require("PERF3C TC20 detailed luma timing fields", all(k in render for k in ["tc20NativeLumaComputeElapsedMs", "tc20NativeOrderBuildElapsedMs", "tc20NativeLumaWorkersUsed"]))
require("PERF3F retains PERF3E JPEG timing probe", all(k in image_saver for k in ["M9JpegSaveTiming", "M9TimingOutputStream", "consumeM9JpegSaveTiming"]))
require("PERF3F M9 payload helper present", "saveBitmapAsJPGPayloadM9" in image_saver)
require("PERF3F retains 64KiB JPEG transport buffer", "new java.io.BufferedOutputStream(timedRawOutputStream, 64 * 1024)" in image_saver)
require("PERF3F payload helper preserves JPEG encoder/quality path", all(k in image_saver for k in ["img.compress(Bitmap.CompressFormat.JPEG, jpgQuality, outputStream)", "img.recycle()"]))
require("PERF3F finalizer uses exact Photon EXIF operations", all(k in finalizer for k in ["ParseExif.setAllAttributes(jpegPath.toFile(), exifData)", "inter.saveAttributes()", "notifyImageSavedStatus(true, jpegPath)"]))
require("PERF3F publication strictly follows EXIF save", finalizer.find("inter.saveAttributes()") < finalizer.find("notifyImageSavedStatus(true, jpegPath)"))
require("PERF3F bounded EXIF queue with sync preservation fallback", all(k in finalizer for k in ["new ArrayBlockingQueue<>(MAX_PENDING)", "MAX_PENDING = 2", "RejectedExecutionException", "runFinalize(ticket, jpegPath, exifData, processingEventsListener, false)"]))
require("PERF3F render worker no longer publishes JPEG directly", "processingEventsListener.notifyImageSavedStatus(true, jpegPath)" not in queue)
require("PERF3F DNG finalization waits for JPEG metadata ticket", all(k in queue for k in ["jpegFinalizeTicket.awaitCompletion()", "jpegFinalizeTicket.isSuccess()", "jpegFinalizeTicket.appendDiagnostics(rendererDiagnostics)"]))
require("PERF3F preserves JPEG-before-DNG publication order", queue.find("job.processingEventsListener.notifyImageSavedStatus(true, job.dngPath)") > queue.find("jpegFinalizeTicket.awaitCompletion()") >= 0)
require("PERF3F renderer consumes exact payload timing", all(k in render for k in ["consumeM9JpegSaveTiming", "jpegCompressElapsedMs", "jpegStreamWriteElapsedMs", "jpegCompressCpuApproxElapsedMs", "jpegStreamWriteCalls", "jpegPayloadSaveHelperElapsedMs"]))
require("PERF3F timing schema declares off-render EXIF", all(k in timing for k in ["m9cam.primarytiming.v6.exifasync1a.dngasync1a", "jpegExifFinalizationOffRenderWorker", "jpegPublicationAfterExif"]))
require("v0.7ZQ PERF3I BITMAPDIRECT1A build identity", "1.32-m9modern7r38luma24fb1primary25perf3ibitmapdirect1acvdirect1aorientfuse8aexifasync1ajpegbuf64k1atc20luma8acolor8adngasync1a" in gradle)
require("stale v0.7M LUMA2.4 verifier alias", "0.97-m9modern7r38luma24" in gradle)
require("stale v0.7K LUMA2.2 verifier alias", "0.97-m9modern7r38luma22" in gradle)
require("stale v0.7L LUMA2.3-SPATIAL1 verifier alias", "0.97-m9modern7r38luma23" in gradle)
require("stale v0.7J LUMA2.1 verifier alias", "0.97-m9modern7r38luma21" in gradle)
require("stale v0.7I LUMA2 verifier alias", "0.97-m9modern7r38luma2" in gradle)
require("stale v0.7H LUMA1 verifier alias", "0.97-m9modern7r38luma1" in gradle)
require("stale v0.7G verifier alias", "0.97-m9modern7r38a" in gradle)
require("stale v0.7F verifier alias", "0.97-m9modern7r37a" in gradle)
require("stale v0.7E verifier alias", "0.97-m9modern7r36a" in gradle)
require("stale v0.7D verifier alias", "0.97-m9modern7r35d" in gradle)
require("stale v0.7A verifier alias", "0.97-m9modern7r35a" in gradle)
require("stale v0.7B verifier alias", "0.97-m9modern7r35b" in gradle)

print(f"\nVerified {len(checks)} M9 v0.7ZQ-PERF3I-BITMAPDIRECT1A-CVDIRECT1A-ORIENTFUSE8A-EXIFASYNC1A-JPEGBUF64K1A-TC20LUMA8A-COLOR8A-DNGASYNC1A-TIMINGFREEZE1A-NAME1A-QUEUE1B-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A-COLORNATIVE2A-PRIMARY2.5 R3.8-H25/TG1 LUMA2.4-SPATIAL2-FB1 seams.")
if failures:
    print(f"{len(failures)} verification failure(s):")
    for f in failures:
        print(" - " + f)
    raise SystemExit(1)
print("M9 v0.7ZQ-PERF3I-BITMAPDIRECT1A-CVDIRECT1A-ORIENTFUSE8A-EXIFASYNC1A-JPEGBUF64K1A-TC20LUMA8A-COLOR8A-DNGASYNC1A-TIMINGFREEZE1A-NAME1A-QUEUE1B-TC20NATIVE1B-ORIENT1A-NORMNATIVE1A-METAFREEZE1A-COLORNATIVE2A-PRIMARY2.5 R3.8-H25/TG1 LUMA2.4-SPATIAL2-FB1 semantic verification PASSED")
