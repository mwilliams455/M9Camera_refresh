#!/usr/bin/env python3
from pathlib import Path
import hashlib
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-fullsourcenorm1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle = root / 'app/build.gradle'
if not renderer.exists():
    raise SystemExit('FULLSOURCENORM1A missing renderer')


def method_bytes(src: str, signature: str) -> bytes:
    start = src.find(signature)
    if start < 0:
        raise SystemExit('FULLSOURCENORM1A method missing: ' + signature)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('FULLSOURCENORM1A opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return src[start:i + 1].encode('utf-8')
        i += 1
    raise SystemExit('FULLSOURCENORM1A unterminated method: ' + signature)

s = renderer.read_text()
required = [
    'sourceGeometryProof2ARuntimeVerified',
    'm9SensorTarget1ARuntimeVerified',
    'm9cam.tonebound.v1a.050ev',
    'SAT2_M04_M05',
    'private static RenderCore renderNativeSourceProduction1P(',
    'private static RenderCore renderNativeProspectiveCore(',
]
for marker in required:
    if marker not in s:
        raise SystemExit('FULLSOURCENORM1A requires marker: ' + marker)

frozen_sigs = [
    '    private static RenderCore renderNativeSourceProduction1P(',
    '    private static RenderCore renderNativeProspectiveCore(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1ABayer(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapBayer(',
    '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(',
]
frozen_before = {sig: hashlib.sha256(method_bytes(s, sig)).hexdigest() for sig in frozen_sigs}

const_old = '    private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = false;\n'
const_new = const_old + '''    // FULLSOURCENORM1A: temporary scientific same-RAW source-normalization A/B.\n    // Primary production stays NORM030; secondary candidate restores full common luma\n    // authority from the live physical remaining LensShadingMap at the primary final gain.\n    private static final boolean SOURCE_FULL_NORM_1A_ENABLED = true;\n'''
if s.count(const_old) != 1:
    raise SystemExit('FULLSOURCENORM1A constant anchor count=' + str(s.count(const_old)))
s = s.replace(const_old, const_new, 1)

anchor = '''            // Do not overwrite capture-time lastDiagnostics here: a later shutter may already\n'''
if s.count(anchor) != 1:
    raise SystemExit('FULLSOURCENORM1A orchestration anchor count=' + str(s.count(anchor)))

block = r'''            // FULLSOURCENORM1A: same-RAW, gain-locked source-normalization experiment.
            // Control is the already-saved production JPEG (NORM030). Candidate changes only
            // the common-luminance authority of the live remaining LensShadingMap from the
            // production bounded value to alpha=1.0. Source calibration, demosaic, M9 target,
            // identity HSM, SAT2 M04/M05, curve02, BT.601, TG1 and final linear gain stay fixed.
            if (primaryRoute && SOURCE_FULL_NORM_1A_ENABLED) {
                JSONObject fullSourceNorm1A = new JSONObject();
                Bitmap fullSourceNormBitmap = null;
                Path fullSourceNormPath = Paths.get(
                        FileManager.sDCIM_CAMERA.getAbsolutePath(),
                        stem + "_M9_SOURCEFULLNORM1A_GAINLOCK.jpg");
                Path fullSourceNormJsonPath = Paths.get(
                        FileManager.sDCIM_CAMERA.getAbsolutePath(),
                        stem + "_M9_SOURCEFULLNORM1A_GAINLOCK.json");
                long fullSourceNormStartedNs = System.nanoTime();
                try {
                    JSONObject toneBound = diag.optJSONObject("toneBound1A");
                    double primaryBoundedCoreGain = toneBound != null
                            ? toneBound.optDouble("boundedEffectiveRenderGain", Double.NaN)
                            : Double.NaN;
                    if (!Double.isFinite(primaryBoundedCoreGain) || primaryBoundedCoreGain <= 0.0) {
                        primaryBoundedCoreGain = diag.optDouble(
                                "edgePlacementEffectiveGain", Double.NaN);
                    }
                    if (!Double.isFinite(primaryBoundedCoreGain) || primaryBoundedCoreGain <= 0.0) {
                        throw new IllegalStateException(
                                "FULLSOURCENORM1A missing primary bounded effective render gain");
                    }

                    JSONObject primaryEdge = diag.optJSONObject("edgePlacementBestFit2A");
                    String primaryTreatment = primaryEdge != null
                            ? primaryEdge.optString("treatment", "FROZEN") : "FROZEN";
                    boolean primaryEdgeApplied = primaryEdge != null
                            && primaryEdge.optBoolean("applied", false);
                    double primaryFinalLinearGain = primaryBoundedCoreGain;
                    if (primaryEdgeApplied
                            && "DARK_EXACT_RERENDER_GAIN_OFFSET".equals(primaryTreatment)) {
                        double primaryDarkEv = primaryEdge.optDouble("appliedEv", 0.0);
                        if (!Double.isFinite(primaryDarkEv)) {
                            throw new IllegalStateException(
                                    "FULLSOURCENORM1A invalid primary DARK edge EV");
                        }
                        primaryFinalLinearGain *= Math.pow(2.0, primaryDarkEv);
                    }
                    if (!Double.isFinite(primaryFinalLinearGain) || primaryFinalLinearGain <= 0.0) {
                        throw new IllegalStateException(
                                "FULLSOURCENORM1A invalid reconstructed primary final linear gain");
                    }

                    RenderCore fullSourceNormCore = renderNativeProspectiveCore(
                            frame.buffer, frame.width, frame.height,
                            encodedBlack, params.whiteLevel, params.whitePoint,
                            cameraRotation, 0.0,
                            characteristics, diagnosticCaptureResult1A, sourceCfaPattern,
                            primaryFinalLinearGain,
                            true,
                            0,
                            false,
                            false, false,
                            true,
                            1.0,
                            false,
                            0.0,
                            1.0,
                            false);
                    fullSourceNormBitmap = fullSourceNormCore.bitmap;
                    fullSourceNorm1A = fullSourceNormCore.diagnostics;

                    boolean brightPivotReplicated = false;
                    if (primaryEdgeApplied && "BRIGHT_RGB_PIVOT".equals(primaryTreatment)) {
                        Bitmap pivoted = M9EdgePlacementBestFit2AController.applyBrightPivot(
                                fullSourceNormBitmap,
                                M9EdgePlacementBestFit2AController.BRIGHT_MILD_STRENGTH);
                        if (pivoted == null) {
                            throw new IllegalStateException(
                                    "FULLSOURCENORM1A primary bright-pivot replication failed");
                        }
                        if (fullSourceNormBitmap != pivoted
                                && fullSourceNormBitmap != null
                                && !fullSourceNormBitmap.isRecycled()) {
                            fullSourceNormBitmap.recycle();
                        }
                        fullSourceNormBitmap = pivoted;
                        brightPivotReplicated = true;
                    }

                    double candidateEffectiveGain = fullSourceNorm1A.optDouble(
                            "effectiveRenderGainAfterRepresentationScale", Double.NaN);
                    if (!Double.isFinite(candidateEffectiveGain) || candidateEffectiveGain <= 0.0) {
                        throw new IllegalStateException(
                                "FULLSOURCENORM1A candidate effective gain unavailable");
                    }
                    double gainRatio = candidateEffectiveGain / primaryFinalLinearGain;
                    double gainDeltaEv = Math.log(gainRatio) / Math.log(2.0);
                    if (!Double.isFinite(gainDeltaEv) || Math.abs(gainDeltaEv) > 1.0e-9) {
                        throw new IllegalStateException(
                                "FULLSOURCENORM1A gain lock failed: deltaEV=" + gainDeltaEv);
                    }

                    JSONObject sourceGeometry = diag.optJSONObject("sourceGeometryProof2A");
                    if (sourceGeometry == null
                            || !sourceGeometry.optBoolean("runtimeGatePassed", false)) {
                        throw new IllegalStateException(
                                "FULLSOURCENORM1A requires proven SOURCEGEOMETRYPROOF2A runtime geometry");
                    }

                    JSONObject candidateLuma = M9RenderedLumaDiagnostic.measure(fullSourceNormBitmap);
                    fullSourceNorm1A.put("schema", "m9cam.sourcefullnorm.v1a.sameraw_gainlocked");
                    fullSourceNorm1A.put("revision", "FULLSOURCENORM1A");
                    fullSourceNorm1A.put("status", "success");
                    fullSourceNorm1A.put("sameRawAsPrimary", true);
                    fullSourceNorm1A.put("inputDngPath", dngPath.toString());
                    fullSourceNorm1A.put("primaryControlJpegPath", jpgPath.toString());
                    fullSourceNorm1A.put("outputPath", fullSourceNormPath.toString());
                    fullSourceNorm1A.put("outputJsonPath", fullSourceNormJsonPath.toString());
                    fullSourceNorm1A.put("control", "production_NORM030_common_luma_target_0p30EV");
                    fullSourceNorm1A.put("candidate", "full_live_remaining_LensShadingMap_common_luma_alpha_1p0");
                    fullSourceNorm1A.put("onlyIntendedPixelChange",
                            "source_common_luminance_shading_authority_NORM030_to_full_physical_remaining_map");
                    fullSourceNorm1A.put("productionPrimaryMutated", false);
                    fullSourceNorm1A.put("captureExposureMutated", false);
                    fullSourceNorm1A.put("tc20Remetered", false);
                    fullSourceNorm1A.put("toneBoundPolicyRetuned", false);
                    fullSourceNorm1A.put("primaryBoundedCoreGain", primaryBoundedCoreGain);
                    fullSourceNorm1A.put("primaryFinalLinearGain", primaryFinalLinearGain);
                    fullSourceNorm1A.put("candidateEffectiveRenderGain", candidateEffectiveGain);
                    fullSourceNorm1A.put("gainDeltaEvVsPrimaryFinal", gainDeltaEv);
                    fullSourceNorm1A.put("gainLockPassed", true);
                    fullSourceNorm1A.put("primaryEdgeTreatment", primaryTreatment);
                    fullSourceNorm1A.put("primaryEdgeApplied", primaryEdgeApplied);
                    fullSourceNorm1A.put("brightPivotReplicated", brightPivotReplicated);
                    fullSourceNorm1A.put("sourceGeometryProof2ARuntimeVerified", true);
                    fullSourceNorm1A.put("bridgeProbeMode", 0);
                    fullSourceNorm1A.put("cobaltRuntimeProductionDependency", false);
                    fullSourceNorm1A.put("targetInputAdapterApplied", false);
                    fullSourceNorm1A.put("identityHsmRetained", true);
                    fullSourceNorm1A.put("firmwareSaturation", "SAT2_M04_M05_native_mode9");
                    fullSourceNorm1A.put("firmwareCurve", "curve02");
                    fullSourceNorm1A.put("fullPhysicalShadingLumaAuthorityAlpha", 1.0);
                    fullSourceNorm1A.put("productionNorm030TargetOutsideMedianEv", 0.30);
                    fullSourceNorm1A.put("directRenderedLuma", candidateLuma);

                    ParseExif.ExifData fullSourceNormExif = ParseExif.parse(captureResult, captureRequest);
                    Integer fullSourceNormIso = captureResult.get(CaptureResult.SENSOR_SENSITIVITY);
                    if (fullSourceNormIso != null && fullSourceNormIso > 0) {
                        fullSourceNormExif.PHOTOGRAPHIC_SENSITIVITY = String.valueOf(
                                Math.min(65535, fullSourceNormIso));
                    }
                    boolean fullSourceNormSaved = ImageSaver.Util.saveBitmapAsJPG(
                            fullSourceNormPath, fullSourceNormBitmap, JPEG_QUALITY, fullSourceNormExif);
                    if (fullSourceNormSaved) fullSourceNormBitmap = null;
                    if (!fullSourceNormSaved) {
                        throw new IllegalStateException(
                                "FULLSOURCENORM1A candidate JPEG save failed");
                    }
                } catch (Throwable fullSourceNormError) {
                    if (fullSourceNormBitmap != null && !fullSourceNormBitmap.isRecycled()) {
                        fullSourceNormBitmap.recycle();
                    }
                    JSONObject failure = new JSONObject();
                    failure.put("schema", "m9cam.sourcefullnorm.v1a.sameraw_gainlocked");
                    failure.put("revision", "FULLSOURCENORM1A");
                    failure.put("status", "failed_isolated_primary_preserved");
                    failure.put("productionPrimaryMutated", false);
                    failure.put("sameRawAsPrimary", true);
                    failure.put("error", fullSourceNormError.toString());
                    failure.put("outputPath", fullSourceNormPath.toString());
                    failure.put("outputJsonPath", fullSourceNormJsonPath.toString());
                    fullSourceNorm1A = failure;
                }
                fullSourceNorm1A.put("elapsedMs",
                        (System.nanoTime() - fullSourceNormStartedNs) / 1_000_000.0);
                try {
                    Files.write(fullSourceNormJsonPath,
                            fullSourceNorm1A.toString(2).getBytes(StandardCharsets.UTF_8));
                    fullSourceNorm1A.put("jsonPersisted", true);
                } catch (Throwable jsonError) {
                    fullSourceNorm1A.put("jsonPersisted", false);
                    fullSourceNorm1A.put("jsonError", jsonError.toString());
                }
                try {
                    diag.put("sourceFullNorm1A", fullSourceNorm1A);
                } catch (Throwable ignored) {}
            }

'''
s = s.replace(anchor, block + anchor, 1)

if gradle.exists():
    g = gradle.read_text()
    m = re.search(r'versionName\s+["\']([^"\']+)["\']', g)
    if m and 'fullsourcenorm1a' not in m.group(1).lower():
        old = m.group(0)
        quote = '"' if '"' in old else "'"
        new_name = m.group(1) + '-fullsourcenorm1a'
        g = g.replace(old, 'versionName ' + quote + new_name + quote, 1)
        gradle.write_text(g)

renderer.write_text(s)

after = renderer.read_text()
for sig in frozen_sigs:
    h = hashlib.sha256(method_bytes(after, sig)).hexdigest()
    if h != frozen_before[sig]:
        raise SystemExit('FULLSOURCENORM1A changed frozen photographic method: ' + sig)

print('FULLSOURCENORM1A applied')
print(' - production NORM030 primary renderer unchanged')
print(' - SOURCEGEOMETRYPROOF2A remains prerequisite runtime gate')
print(' - same RAW candidate: production shading decomposition with common-luma alpha 1.0')
print(' - candidate bridge mode 0: no historical/Cobalt target-input path')
print(' - candidate fixed to actual primary bounded/final linear gain; no TC20 re-meter')
print(' - only intended candidate pixel change: source common-luminance shading authority')
for sig in frozen_sigs:
    print(frozen_before[sig], sig.strip())
