#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1f-shadedtailaudit1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n':
                state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/':
                state = 'code'
                i += 1
        elif state == 'string':
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote:
                state = 'code'
        else:
            if ch == '/' and nxt == '/':
                state = 'line_comment'
                i += 1
            elif ch == '/' and nxt == '*':
                state = 'block_comment'
                i += 1
            elif ch in ('"', "'"):
                state = 'string'
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1F-SHADEDTAILAUDIT1A {label} anchor count={count}')
    return src.replace(old, new, 1)


# Start only from the field-tested SHADINGDOMAIN1A state. This experiment is
# diagnostic-only: it must not alter Primary, OFF, ON, capture, DNG, TC20 gain,
# or the physical LensShadingMap application.
for marker in [
    'shadingDomain1A',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'restored_physical_shaded_camera_RGB',
    'shadingLateRepresentationScaleApplied", false',
    'final double effectiveRenderGain = meterParityRenderBaseGain;',
    'rawShadingResidual1AEnabled',
    'm9cam.renderer.rawshadingresidual.v1a',
    'applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap)',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A requires SHADINGDOMAIN1A marker: ' + marker)
if '-basishsm1e-shadingdomain1a' not in gradle:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A requires SHADINGDOMAIN1A build provenance')

frames = frames_path.read_text()
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_before = extract_method(
    renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_before = extract_method(
    renderer, '    private static JSONObject rawShadingResidualAudit1A(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()
shading_sha = hashlib.sha256(shading_before.encode('utf-8')).hexdigest()
residual_sha = hashlib.sha256(residual_before.encode('utf-8')).hexdigest()

helper = r'''
    // BASISHSM1F-SHADEDTAILAUDIT1A
    // Diagnostic-only headroom-domain audit. The real renderer remains untouched.
    // For the shading-ON variant only, clone the original normalized Bayer and run
    // the exact existing LensShadingMap helper on that private clone. The helper's
    // headroom representation is monotonic, so an exact 65536-bin histogram plus
    // representationScale recovers the lens-shading-corrected linear Bayer tail.
    // Original sensor-clipped sites (norm16 == 65535) stay excluded, matching the
    // frozen TC20 RAW-tail definition. q is reused from that frozen unshaded tail;
    // correction-induced values above 1.0 are NOT reclassified as sensor clipping.
    private static final class ShadedTailAudit1AStats {
        final JSONObject json;
        final boolean valid;
        final double predictedGuardGain;

        ShadedTailAudit1AStats(JSONObject json, boolean valid, double predictedGuardGain) {
            this.json = json;
            this.valid = valid;
            this.predictedGuardGain = predictedGuardGain;
        }

        static ShadedTailAudit1AStats skipped() throws Exception {
            JSONObject j = new JSONObject();
            j.put("schema", "m9cam.renderer.shadedtailaudit.v1a");
            j.put("diagnosticOnly", true);
            j.put("pixelMutation", false);
            j.put("gainMutation", false);
            j.put("executed", false);
            j.put("reason", "shading_off_control");
            return new ShadedTailAudit1AStats(j, false, Double.NaN);
        }
    }

    private static int shadedTailCodeAtRank1A(long[] hist, long rank) {
        long cumulative = 0L;
        for (int code = 0; code < hist.length; code++) {
            cumulative += hist[code];
            if (cumulative > rank) return code;
        }
        return hist.length - 1;
    }

    // NumPy default quantile semantics used by the frozen Python TC20 oracle:
    // linear interpolation at q*(N-1), implemented over exact uint16 code counts.
    private static double shadedTailQuantile1A(
            long[] hist, long total, double q, double representationScale) {
        if (total <= 0L) return 1.0;
        double qq = Math.max(0.0, Math.min(1.0, q));
        double position = qq * (total - 1L);
        long loRank = (long)Math.floor(position);
        long hiRank = (long)Math.ceil(position);
        int loCode = shadedTailCodeAtRank1A(hist, loRank);
        int hiCode = shadedTailCodeAtRank1A(hist, hiRank);
        double frac = position - loRank;
        double representedCode = loCode + frac * (hiCode - loCode);
        return (representedCode / 65535.0) * representationScale;
    }

    private static ShadedTailAudit1AStats shadedTailAudit1A(
            short[] originalNorm16,
            int width,
            int height,
            LensShadingMap map,
            RawTail originalTail) throws Exception {
        JSONObject j = new JSONObject();
        j.put("schema", "m9cam.renderer.shadedtailaudit.v1a");
        j.put("diagnosticOnly", true);
        j.put("pixelMutation", false);
        j.put("gainMutation", false);
        j.put("executed", true);
        j.put("auditSource", "private_clone_of_original_normalized_Bayer");
        j.put("correctionSource", "exact_existing_applyNativeProspectiveGainMap_helper");
        j.put("tailDomain", "lens_shading_corrected_linear_Bayer_pre_demosaic");
        j.put("currentGuardDomain", "unshaded_sensor_normalized_RAW_tail");
        j.put("qPolicy", "reuse_frozen_original_RAW_tail_q_no_reclassification_of_correction_above_one");
        if (originalNorm16 == null || originalNorm16.length != Math.multiplyExact(width, height)) {
            j.put("valid", false);
            j.put("reason", "invalid_original_normalized_bayer");
            return new ShadedTailAudit1AStats(j, false, Double.NaN);
        }
        if (map == null || originalTail == null) {
            j.put("valid", false);
            j.put("reason", map == null ? "missing_live_gain_map" : "missing_original_raw_tail");
            return new ShadedTailAudit1AStats(j, false, Double.NaN);
        }

        short[] correctedRepresented = originalNorm16.clone();
        NativeProspectiveShadingStats auditShading = applyNativeProspectiveGainMap(
                correctedRepresented, width, height, map);
        if (!auditShading.applied || auditShading.representationScale <= 0.0) {
            j.put("valid", false);
            j.put("reason", "exact_shading_helper_not_applied_to_private_clone");
            return new ShadedTailAudit1AStats(j, false, Double.NaN);
        }

        long[] hist = new long[65536];
        long unclippedCount = 0L;
        long originalSensorClippedCount = 0L;
        long correctedAboveOneCount = 0L;
        final double representationScale = auditShading.representationScale;
        for (int i = 0; i < originalNorm16.length; i++) {
            int originalCode = originalNorm16[i] & 0xffff;
            if (originalCode >= 65535) {
                originalSensorClippedCount++;
                continue;
            }
            int representedCode = correctedRepresented[i] & 0xffff;
            hist[representedCode]++;
            unclippedCount++;
            if ((representedCode / 65535.0) * representationScale > 1.0) {
                correctedAboveOneCount++;
            }
        }
        correctedRepresented = null;

        final double q = Math.max(0.0, Math.min(1.0, originalTail.q));
        final double uq99 = shadedTailQuantile1A(hist, unclippedCount, .99, representationScale);
        final double uq995 = shadedTailQuantile1A(hist, unclippedCount, .995, representationScale);
        final double uq998 = shadedTailQuantile1A(hist, unclippedCount, .998, representationScale);
        final double adaptiveUq = shadedTailQuantile1A(hist, unclippedCount, q, representationScale);
        final double d1 = Math.log(Math.max(uq995, 1e-9) / Math.max(uq99, 1e-9));
        final double d2 = Math.log(Math.max(uq998, 1e-9) / Math.max(uq995, 1e-9));
        final double curvature = d2 - .6 * d1;
        final boolean isolated = curvature > TC_TAIL_CURVATURE_THRESHOLD;
        final double tailValue = isolated ? uq995 : adaptiveUq;
        final double predictedGuardGain = Math.max(
                1.0, TC_HEADROOM_TARGET / Math.max(tailValue, 1e-9));

        j.put("valid", unclippedCount > 0L);
        j.put("representationScale", representationScale);
        j.put("sampleCountOriginalAllSites", originalNorm16.length);
        j.put("sampleCountOriginalUnclipped", unclippedCount);
        j.put("originalSensorClippedSiteCount", originalSensorClippedCount);
        j.put("originalSensorClipFractionObserved",
                originalNorm16.length > 0 ? originalSensorClippedCount / (double)originalNorm16.length : 0.0);
        j.put("originalRawTailClipFraction", originalTail.clipFraction);
        j.put("originalRawTailQ", originalTail.q);
        j.put("originalRawTailValue", originalTail.tailValue);
        j.put("correctedUq99", uq99);
        j.put("correctedUq99_5", uq995);
        j.put("correctedUq99_8", uq998);
        j.put("correctedAdaptiveUqAtOriginalQ", adaptiveUq);
        j.put("correctedTailCurvature", curvature);
        j.put("correctedTailIsolated", isolated);
        j.put("correctedTailValueAtOriginalQ", tailValue);
        j.put("correctedLinearAboveOneUnclippedCount", correctedAboveOneCount);
        j.put("correctedLinearAboveOneUnclippedFraction",
                unclippedCount > 0L ? correctedAboveOneCount / (double)unclippedCount : 0.0);
        j.put("correctedAboveOneSemantics",
                "lens_correction_induced_linear_value_not_sensor_clip_reclassification");
        j.put("predictedGuardGainAtOriginalQ", predictedGuardGain);
        j.put("headroomTarget", TC_HEADROOM_TARGET);
        return new ShadedTailAudit1AStats(j, unclippedCount > 0L, predictedGuardGain);
    }

'''

class_marker = '    private static final class NativeProspectiveShadingStats {'
if renderer.count(class_marker) != 1:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A shading-stats class anchor ambiguous')
renderer = renderer.replace(class_marker, helper + class_marker, 1)

pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')

# Execute the audit only in the ON variant. It reads the pre-shading norm16 and runs
# the exact same map helper only on a private clone. The real nativeShading call and
# every later photographic operation remain source-identical.
shade_anchor = '        NativeProspectiveShadingStats nativeShading = applyNativeShading'
if prospective.count(shade_anchor) != 1:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A real shading anchor count=' + str(prospective.count(shade_anchor)))
audit_call = '''        ShadedTailAudit1AStats shadedTailAuditStats = applyNativeShading
                ? shadedTailAudit1A(norm16, width, height, nativeLiveGainMap, tail)
                : ShadedTailAudit1AStats.skipped();
        NativeProspectiveShadingStats nativeShading = applyNativeShading'''
prospective = prospective.replace(shade_anchor, audit_call, 1)

# Diagnostics only. Calculate what the already-existing TC20 decision would have been
# if *only* the headroom guard had consumed the corrected tail. Do not assign the
# predicted value back to meter.gain or effectiveRenderGain.
diag_anchor = '''            d.put("shadingDomainReason", "global headroom transport scale must be restored before nonlinear whitepoint_HSM_TC20 operations");'''
diag_insert = '''            d.put("shadingDomainReason", "global headroom transport scale must be restored before nonlinear whitepoint_HSM_TC20 operations");
            d.put("shadedTailAudit1AEnabled", applyNativeShading);
            JSONObject shadedTailAuditJson = shadedTailAuditStats.json;
            shadedTailAuditJson.put("currentBaseMedianGain", meter.baseGain);
            shadedTailAuditJson.put("currentUnshadedGuardGain", meter.guardGain);
            shadedTailAuditJson.put("currentMeterGain", meter.gain);
            shadedTailAuditJson.put("currentRenderBaseGain", meterParityRenderBaseGain);
            shadedTailAuditJson.put("edgePlacementGainEv", edgePlacementGainEv);
            if (shadedTailAuditStats.valid && Double.isFinite(shadedTailAuditStats.predictedGuardGain)) {
                double predictedMeterGainIfOnlyGuardDomainChanged = Math.min(
                        meter.baseGain, shadedTailAuditStats.predictedGuardGain);
                double predictedRenderBaseGainIfOnlyGuardDomainChanged = meterParitySelfMeter
                        ? predictedMeterGainIfOnlyGuardDomainChanged * Math.pow(2.0, edgePlacementGainEv)
                        : fixedPrimaryGain;
                shadedTailAuditJson.put("predictedMeterGainIfOnlyGuardDomainChanged",
                        predictedMeterGainIfOnlyGuardDomainChanged);
                shadedTailAuditJson.put("predictedRenderBaseGainIfOnlyGuardDomainChanged",
                        predictedRenderBaseGainIfOnlyGuardDomainChanged);
                if (meterParityRenderBaseGain > 0.0 && predictedRenderBaseGainIfOnlyGuardDomainChanged > 0.0) {
                    shadedTailAuditJson.put("predictedGainDeltaEvVsCurrent",
                            Math.log(predictedRenderBaseGainIfOnlyGuardDomainChanged / meterParityRenderBaseGain)
                                    / Math.log(2.0));
                }
            }
            shadedTailAuditJson.put("photographicDecisionMutation", false);
            d.put("shadedTailAudit1A", shadedTailAuditJson);'''
prospective = replace_once(prospective, diag_anchor, diag_insert, 'tail audit diagnostics')
prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.shadingdomain.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.shadedtailaudit.v1a.main");',
    'prospective schema')

renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

gradle = gradle.replace(
    '-basishsm1e-shadingdomain1a',
    '-basishsm1f-shadedtailaudit1a', 1)
if '-basishsm1f-shadedtailaudit1a' not in gradle:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A failed to set build provenance')

# Hard freeze checks for production Primary and both established shading diagnostics.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_after = extract_method(
    renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_after = extract_method(
    renderer, '    private static JSONObject rawShadingResidualAudit1A(')
if hashlib.sha256(primary_after.encode('utf-8')).hexdigest() != primary_sha:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A changed frozen Primary renderCore')
if hashlib.sha256(shading_after.encode('utf-8')).hexdigest() != shading_sha:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A changed LensShadingMap interpolation/application')
if hashlib.sha256(residual_after.encode('utf-8')).hexdigest() != residual_sha:
    raise SystemExit('BASISHSM1F-SHADEDTAILAUDIT1A changed RAW residual audit')

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9Cam BASISHSM1F-SHADEDTAILAUDIT1A applied')
print(' - frozen Primary renderCore sha256 preserved:', primary_sha)
print(' - LensShadingMap interpolation/application sha256 preserved:', shading_sha)
print(' - RAW residual audit sha256 preserved:', residual_sha)
print(' - ON-only corrected-tail audit uses exact map helper on private norm16 clone')
print(' - original sensor-clipped sites excluded; frozen raw-tail q reused')
print(' - predicted corrected-domain TC20 guard logged but never applied')
print(' - SHADINGDOMAIN1A photographic OFF/ON gains and pixels remain unchanged')
print(' - single RAW / HDR=false / capture exposure / DNG remain frozen')
