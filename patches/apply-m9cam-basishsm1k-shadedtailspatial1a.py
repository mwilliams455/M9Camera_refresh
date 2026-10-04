#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1k-shadedtailspatial1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A opening brace missing: ' + marker)
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
                escape = False
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A unterminated method: ' + marker)

def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1K-SHADEDTAILSPATIAL1A {label} anchor count={count}')
    return src.replace(old, new, 1)

for marker in [
    'm9cam.renderer.basishsm.shadedguardcap20ev.finalclipaudit.v1a.main',
    'm9cam.renderer.shadedtailaudit.v1a',
    'private static ShadedTailAudit1AStats shadedTailAudit1A(',
    'private static JSONObject finalClipAudit1A(',
    'shadedGuardCap20Ev1AEnabled',
    'shadedGuardCap20Ev1ARequested',
    'shadedGuardCap20Ev1ABound',
    'shading_on_unguarded_control',
    'shading_on_guarded',
    'shading_on_guarded_cap20ev1a',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARDCAP20EV1A"',
    'boolean[] applyShadedGuard1AFlags = {false, false, true, false};',
    'boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, true};',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
    'Math.max(shadedGuard1AMeterGain, shadedGuardCap20Ev1AFloorGain)',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A requires 1J marker: ' + marker)
if '-basishsm1j-shadedguardcap20ev1a' not in gradle:
    raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A requires 1J build provenance')

for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_before = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_before = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_before = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
_, _, clip_before = extract_method(renderer, '    private static JSONObject finalClipAudit1A(')
frozen_sha = {
    'primary': hashlib.sha256(primary_before.encode()).hexdigest(),
    'shading': hashlib.sha256(shading_before.encode()).hexdigest(),
    'residual': hashlib.sha256(residual_before.encode()).hexdigest(),
    'tail': hashlib.sha256(tail_before.encode()).hexdigest(),
    'clip': hashlib.sha256(clip_before.encode()).hexdigest(),
}

helper = r'''
    // BASISHSM1K-SHADEDTAILSPATIAL1A
    // Read-only companion to SHADEDTAILAUDIT1A. It deliberately does not feed a
    // gain, pixel, capture, DNG, TC20, HSM, or tone-curve decision. It replays the
    // exact physical LensShadingMap on one private clone of the same normalized RAW
    // and measures WHERE the selected corrected tail is supported. The expensive
    // companion runs only on the shading-ON unguarded control; all shading-ON
    // variants share the same pre-meter corrected RAW and therefore the same audit.
    private static JSONObject shadedTailSpatialAudit1ASkipped(String reason) throws Exception {
        JSONObject j = new JSONObject();
        j.put("schema", "m9cam.renderer.shadedtailspatial.v1a");
        j.put("diagnosticOnly", true);
        j.put("pixelMutation", false);
        j.put("gainMutation", false);
        j.put("photographicDecisionMutation", false);
        j.put("executed", false);
        j.put("reason", reason);
        j.put("sameRawSharedAcrossShadingOnVariants", true);
        return j;
    }

    private static JSONObject shadedTailSpatialAudit1A(
            short[] originalNorm16,
            int width,
            int height,
            LensShadingMap map,
            RawTail originalTail,
            int cameraRotation) throws Exception {
        JSONObject j = new JSONObject();
        j.put("schema", "m9cam.renderer.shadedtailspatial.v1a");
        j.put("diagnosticOnly", true);
        j.put("pixelMutation", false);
        j.put("gainMutation", false);
        j.put("photographicDecisionMutation", false);
        j.put("executed", true);
        j.put("auditSource", "private_clone_of_original_normalized_Bayer");
        j.put("correctionSource", "exact_existing_applyNativeProspectiveGainMap_helper");
        j.put("stage", "lens_shading_corrected_linear_Bayer_pre_demosaic");
        j.put("sameRawSharedAcrossShadingOnVariants", true);
        j.put("executedOnlyOnRole", "shading_on_unguarded_control");
        j.put("intendedUse",
                "correlate_pre_render_corrected_tail_support_geometry_with_FINALCLIPAUDIT1A_not_a_render_policy");
        j.put("supportThresholdPolicy",
                "same_SHADEDTAIL1A_selected_tail_value_original_q_or_uq995_when_isolated");
        if (originalNorm16 == null || originalNorm16.length != Math.multiplyExact(width, height)) {
            j.put("valid", false);
            j.put("reason", "invalid_original_normalized_bayer");
            return j;
        }
        if (map == null || originalTail == null) {
            j.put("valid", false);
            j.put("reason", map == null ? "missing_live_gain_map" : "missing_original_raw_tail");
            return j;
        }

        final int rotation = ((cameraRotation % 360) + 360) % 360;
        if (rotation != 0 && rotation != 90 && rotation != 180 && rotation != 270) {
            j.put("valid", false);
            j.put("reason", "unsupported_camera_rotation");
            j.put("cameraRotation", cameraRotation);
            return j;
        }
        final int displayWidth = (rotation == 90 || rotation == 270) ? height : width;
        final int displayHeight = (rotation == 90 || rotation == 270) ? width : height;
        final int cx0 = displayWidth / 4;
        final int cx1 = (3 * displayWidth) / 4;
        final int cy0 = displayHeight / 4;
        final int cy1 = (3 * displayHeight) / 4;

        short[] correctedRepresented = originalNorm16.clone();
        NativeProspectiveShadingStats auditShading = applyNativeProspectiveGainMap(
                correctedRepresented, width, height, map);
        if (!auditShading.applied || auditShading.representationScale <= 0.0) {
            correctedRepresented = null;
            j.put("valid", false);
            j.put("reason", "exact_shading_helper_not_applied_to_private_clone");
            return j;
        }
        final double representationScale = auditShading.representationScale;

        long[] hist = new long[65536];
        long unclippedCount = 0L;
        long originalSensorClippedCount = 0L;
        for (int i = 0; i < originalNorm16.length; i++) {
            int originalCode = originalNorm16[i] & 0xffff;
            if (originalCode >= 65535) {
                originalSensorClippedCount++;
                continue;
            }
            hist[correctedRepresented[i] & 0xffff]++;
            unclippedCount++;
        }
        if (unclippedCount <= 0L) {
            correctedRepresented = null;
            j.put("valid", false);
            j.put("reason", "no_original_unclipped_sites");
            return j;
        }

        final double q = Math.max(0.0, Math.min(1.0, originalTail.q));
        final double uq99 = shadedTailQuantile1A(hist, unclippedCount, .99, representationScale);
        final double uq995 = shadedTailQuantile1A(hist, unclippedCount, .995, representationScale);
        final double uq998 = shadedTailQuantile1A(hist, unclippedCount, .998, representationScale);
        final double adaptiveUq = shadedTailQuantile1A(hist, unclippedCount, q, representationScale);
        final double d1 = Math.log(Math.max(uq995, 1e-9) / Math.max(uq99, 1e-9));
        final double d2 = Math.log(Math.max(uq998, 1e-9) / Math.max(uq995, 1e-9));
        final double curvature = d2 - .6 * d1;
        final boolean isolated = curvature > TC_TAIL_CURVATURE_THRESHOLD;
        final double tailThreshold = isolated ? uq995 : adaptiveUq;

        long[] tileSamples = new long[9];
        long[] tileTail = new long[9];
        long[] tileAboveOne = new long[9];
        double[] tileTailExcess = new double[9];
        double[] tileAboveOneExcess = new double[9];

        long totalTail = 0L, totalAboveOne = 0L;
        double totalTailExcess = 0.0, totalAboveOneExcess = 0.0;
        long centerSamples = 0L, centerTail = 0L, centerAboveOne = 0L;
        long edgeSamples = 0L, edgeTail = 0L, edgeAboveOne = 0L;
        double centerTailExcess = 0.0, centerAboveOneExcess = 0.0;
        double edgeTailExcess = 0.0, edgeAboveOneExcess = 0.0;
        int tailMinX = displayWidth, tailMaxX = -1, tailMinY = displayHeight, tailMaxY = -1;

        for (int y = 0; y < height; y++) {
            final int rowBase = y * width;
            for (int x = 0; x < width; x++) {
                final int index = rowBase + x;
                final int originalCode = originalNorm16[index] & 0xffff;
                if (originalCode >= 65535) continue;

                final int representedCode = correctedRepresented[index] & 0xffff;
                final double linear = (representedCode / 65535.0) * representationScale;
                int dx;
                int dy;
                if (rotation == 90) {
                    dx = height - 1 - y;
                    dy = x;
                } else if (rotation == 180) {
                    dx = width - 1 - x;
                    dy = height - 1 - y;
                } else if (rotation == 270) {
                    dx = y;
                    dy = width - 1 - x;
                } else {
                    dx = x;
                    dy = y;
                }

                final int col = Math.min(2, (dx * 3) / Math.max(1, displayWidth));
                final int row = Math.min(2, (dy * 3) / Math.max(1, displayHeight));
                final int tile = row * 3 + col;
                final boolean center = dx >= cx0 && dx < cx1 && dy >= cy0 && dy < cy1;
                final boolean tailSupport = linear >= tailThreshold;
                final boolean aboveOne = linear > 1.0;
                final double tailExcess = tailSupport ? Math.max(0.0, linear - tailThreshold) : 0.0;
                final double aboveOneExcess = aboveOne ? linear - 1.0 : 0.0;

                tileSamples[tile]++;
                if (center) centerSamples++; else edgeSamples++;

                if (tailSupport) {
                    totalTail++;
                    totalTailExcess += tailExcess;
                    tileTail[tile]++;
                    tileTailExcess[tile] += tailExcess;
                    if (center) {
                        centerTail++;
                        centerTailExcess += tailExcess;
                    } else {
                        edgeTail++;
                        edgeTailExcess += tailExcess;
                    }
                    tailMinX = Math.min(tailMinX, dx);
                    tailMaxX = Math.max(tailMaxX, dx);
                    tailMinY = Math.min(tailMinY, dy);
                    tailMaxY = Math.max(tailMaxY, dy);
                }
                if (aboveOne) {
                    totalAboveOne++;
                    totalAboveOneExcess += aboveOneExcess;
                    tileAboveOne[tile]++;
                    tileAboveOneExcess[tile] += aboveOneExcess;
                    if (center) {
                        centerAboveOne++;
                        centerAboveOneExcess += aboveOneExcess;
                    } else {
                        edgeAboveOne++;
                        edgeAboveOneExcess += aboveOneExcess;
                    }
                }
            }
        }
        correctedRepresented = null;

        double tailHhi = 0.0, aboveOneHhi = 0.0;
        double tailMaxCellShare = 0.0, aboveOneMaxCellShare = 0.0;
        int tailNonZeroCells = 0, aboveOneNonZeroCells = 0;
        for (int i = 0; i < 9; i++) {
            if (tileTail[i] > 0L) tailNonZeroCells++;
            if (tileAboveOne[i] > 0L) aboveOneNonZeroCells++;
            final double ts = totalTail > 0L ? tileTail[i] / (double)totalTail : 0.0;
            final double as = totalAboveOne > 0L ? tileAboveOne[i] / (double)totalAboveOne : 0.0;
            tailHhi += ts * ts;
            aboveOneHhi += as * as;
            tailMaxCellShare = Math.max(tailMaxCellShare, ts);
            aboveOneMaxCellShare = Math.max(aboveOneMaxCellShare, as);
        }

        j.put("valid", true);
        j.put("cameraRotation", cameraRotation);
        j.put("rotationNormalized", rotation);
        j.put("orientationSpace", "finished_display_orientation");
        j.put("orientationMapping", "clockwise_cameraRotation_0_90_180_270");
        j.put("sourceWidth", width);
        j.put("sourceHeight", height);
        j.put("displayWidth", displayWidth);
        j.put("displayHeight", displayHeight);
        j.put("representationScale", representationScale);
        j.put("sampleCountOriginalAllSites", originalNorm16.length);
        j.put("sampleCountOriginalUnclipped", unclippedCount);
        j.put("originalSensorClippedSiteCount", originalSensorClippedCount);
        j.put("originalRawTailQ", originalTail.q);
        j.put("correctedUq99", uq99);
        j.put("correctedUq99_5", uq995);
        j.put("correctedUq99_8", uq998);
        j.put("correctedAdaptiveUqAtOriginalQ", adaptiveUq);
        j.put("correctedTailCurvature", curvature);
        j.put("correctedTailIsolated", isolated);
        j.put("tailSupportThresholdLinear", tailThreshold);
        j.put("tailSupportCount", totalTail);
        j.put("tailSupportFractionOfOriginalUnclipped", totalTail / (double)unclippedCount);
        j.put("tailSupportExcessEnergy", totalTailExcess);
        j.put("correctedLinearAboveOneCount", totalAboveOne);
        j.put("correctedLinearAboveOneFractionOfOriginalUnclipped",
                totalAboveOne / (double)unclippedCount);
        j.put("correctedLinearAboveOneExcessEnergy", totalAboveOneExcess);
        j.put("tailSupportNonZero3x3CellCount", tailNonZeroCells);
        j.put("tailSupportMax3x3CellShare", tailMaxCellShare);
        j.put("tailSupport3x3Herfindahl", tailHhi);
        j.put("aboveOneNonZero3x3CellCount", aboveOneNonZeroCells);
        j.put("aboveOneMax3x3CellShare", aboveOneMaxCellShare);
        j.put("aboveOne3x3Herfindahl", aboveOneHhi);

        JSONObject center = new JSONObject();
        center.put("region", "center_50_percent_width_height_display_orientation");
        center.put("sampleCountOriginalUnclipped", centerSamples);
        center.put("tailSupportCount", centerTail);
        center.put("tailSupportFractionOfRegion",
                centerSamples > 0L ? centerTail / (double)centerSamples : 0.0);
        center.put("tailSupportFractionOfTotal",
                totalTail > 0L ? centerTail / (double)totalTail : 0.0);
        center.put("tailSupportExcessEnergy", centerTailExcess);
        center.put("tailSupportExcessEnergyFractionOfTotal",
                totalTailExcess > 0.0 ? centerTailExcess / totalTailExcess : 0.0);
        center.put("aboveOneCount", centerAboveOne);
        center.put("aboveOneFractionOfRegion",
                centerSamples > 0L ? centerAboveOne / (double)centerSamples : 0.0);
        center.put("aboveOneFractionOfTotal",
                totalAboveOne > 0L ? centerAboveOne / (double)totalAboveOne : 0.0);
        center.put("aboveOneExcessEnergy", centerAboveOneExcess);
        center.put("aboveOneExcessEnergyFractionOfTotal",
                totalAboveOneExcess > 0.0 ? centerAboveOneExcess / totalAboveOneExcess : 0.0);
        j.put("center50", center);

        JSONObject edge = new JSONObject();
        edge.put("region", "outside_center_50_percent_width_height_display_orientation");
        edge.put("sampleCountOriginalUnclipped", edgeSamples);
        edge.put("tailSupportCount", edgeTail);
        edge.put("tailSupportFractionOfRegion",
                edgeSamples > 0L ? edgeTail / (double)edgeSamples : 0.0);
        edge.put("tailSupportFractionOfTotal",
                totalTail > 0L ? edgeTail / (double)totalTail : 0.0);
        edge.put("tailSupportExcessEnergy", edgeTailExcess);
        edge.put("tailSupportExcessEnergyFractionOfTotal",
                totalTailExcess > 0.0 ? edgeTailExcess / totalTailExcess : 0.0);
        edge.put("aboveOneCount", edgeAboveOne);
        edge.put("aboveOneFractionOfRegion",
                edgeSamples > 0L ? edgeAboveOne / (double)edgeSamples : 0.0);
        edge.put("aboveOneFractionOfTotal",
                totalAboveOne > 0L ? edgeAboveOne / (double)totalAboveOne : 0.0);
        edge.put("aboveOneExcessEnergy", edgeAboveOneExcess);
        edge.put("aboveOneExcessEnergyFractionOfTotal",
                totalAboveOneExcess > 0.0 ? edgeAboveOneExcess / totalAboveOneExcess : 0.0);
        j.put("edgeOutsideCenter50", edge);

        final String[] tileNames = {
                "topLeft", "topCenter", "topRight",
                "middleLeft", "middleCenter", "middleRight",
                "bottomLeft", "bottomCenter", "bottomRight"
        };
        JSONObject grid = new JSONObject();
        grid.put("rows", 3);
        grid.put("columns", 3);
        grid.put("orientationSpace", "finished_display_orientation");
        for (int i = 0; i < 9; i++) {
            JSONObject t = new JSONObject();
            t.put("row", i / 3);
            t.put("column", i % 3);
            t.put("sampleCountOriginalUnclipped", tileSamples[i]);
            t.put("tailSupportCount", tileTail[i]);
            t.put("tailSupportFractionOfRegion",
                    tileSamples[i] > 0L ? tileTail[i] / (double)tileSamples[i] : 0.0);
            t.put("tailSupportFractionOfTotal",
                    totalTail > 0L ? tileTail[i] / (double)totalTail : 0.0);
            t.put("tailSupportExcessEnergy", tileTailExcess[i]);
            t.put("tailSupportExcessEnergyFractionOfTotal",
                    totalTailExcess > 0.0 ? tileTailExcess[i] / totalTailExcess : 0.0);
            t.put("aboveOneCount", tileAboveOne[i]);
            t.put("aboveOneFractionOfRegion",
                    tileSamples[i] > 0L ? tileAboveOne[i] / (double)tileSamples[i] : 0.0);
            t.put("aboveOneFractionOfTotal",
                    totalAboveOne > 0L ? tileAboveOne[i] / (double)totalAboveOne : 0.0);
            t.put("aboveOneExcessEnergy", tileAboveOneExcess[i]);
            t.put("aboveOneExcessEnergyFractionOfTotal",
                    totalAboveOneExcess > 0.0 ? tileAboveOneExcess[i] / totalAboveOneExcess : 0.0);
            grid.put(tileNames[i], t);
        }
        j.put("display3x3", grid);

        JSONObject bbox = new JSONObject();
        bbox.put("valid", totalTail > 0L);
        if (totalTail > 0L) {
            bbox.put("minX", tailMinX);
            bbox.put("maxX", tailMaxX);
            bbox.put("minY", tailMinY);
            bbox.put("maxY", tailMaxY);
            bbox.put("minXNormalized", tailMinX / (double)Math.max(1, displayWidth - 1));
            bbox.put("maxXNormalized", tailMaxX / (double)Math.max(1, displayWidth - 1));
            bbox.put("minYNormalized", tailMinY / (double)Math.max(1, displayHeight - 1));
            bbox.put("maxYNormalized", tailMaxY / (double)Math.max(1, displayHeight - 1));
        }
        j.put("tailSupportBoundingBoxDisplay", bbox);
        return j;
    }

'''

class_marker = '    private static final class NativeProspectiveShadingStats {'
if renderer.count(class_marker) != 1:
    raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A shading-stats class anchor ambiguous')
if 'private static JSONObject shadedTailSpatialAudit1A(' in renderer:
    raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A helper already present')
renderer = renderer.replace(class_marker, helper + class_marker, 1)

pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')

old_audit = '''        ShadedTailAudit1AStats shadedTailAuditStats = applyNativeShading
                ? shadedTailAudit1A(norm16, width, height, nativeLiveGainMap, tail)
                : ShadedTailAudit1AStats.skipped();
        NativeProspectiveShadingStats nativeShading = applyNativeShading'''
new_audit = '''        ShadedTailAudit1AStats shadedTailAuditStats = applyNativeShading
                ? shadedTailAudit1A(norm16, width, height, nativeLiveGainMap, tail)
                : ShadedTailAudit1AStats.skipped();
        final boolean shadedTailSpatial1ARun = applyNativeShading
                && !applyShadedGuard1A
                && !applyShadedGuardCap20Ev1A;
        final JSONObject shadedTailSpatial1AJson = shadedTailSpatial1ARun
                ? shadedTailSpatialAudit1A(
                        norm16, width, height, nativeLiveGainMap, tail, cameraRotation)
                : shadedTailSpatialAudit1ASkipped(
                        !applyNativeShading
                                ? "shading_off_control"
                                : "shared_same_raw_audit_emitted_on_shading_on_unguarded_control");
        NativeProspectiveShadingStats nativeShading = applyNativeShading'''
prospective = replace_once(prospective, old_audit, new_audit, 'spatial audit call seam')

prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.shadedguardcap20ev.finalclipaudit.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.shadedtailspatial.finalclipaudit.v1a.main");',
    'prospective schema')

diag_anchor = '''            d.put("shadedTailAudit1AEnabled", applyNativeShading);'''
diag_repl = '''            d.put("shadedTailAudit1AEnabled", applyNativeShading);
            d.put("shadedTailSpatial1AEnabled", true);
            d.put("shadedTailSpatial1AExecuted", shadedTailSpatial1ARun);
            d.put("shadedTailSpatial1A", shadedTailSpatial1AJson);'''
prospective = replace_once(prospective, diag_anchor, diag_repl, 'spatial diagnostics')

renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

gradle = gradle.replace(
    '-basishsm1j-shadedguardcap20ev1a',
    '-basishsm1k-shadedtailspatial1a',
    1)
if '-basishsm1k-shadedtailspatial1a' not in gradle:
    raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A failed to set build provenance')

_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_after = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_after = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_after = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
_, _, clip_after = extract_method(renderer, '    private static JSONObject finalClipAudit1A(')
after = {
    'primary': hashlib.sha256(primary_after.encode()).hexdigest(),
    'shading': hashlib.sha256(shading_after.encode()).hexdigest(),
    'residual': hashlib.sha256(residual_after.encode()).hexdigest(),
    'tail': hashlib.sha256(tail_after.encode()).hexdigest(),
    'clip': hashlib.sha256(clip_after.encode()).hexdigest(),
}
for key in frozen_sha:
    if after[key] != frozen_sha[key]:
        raise SystemExit('BASISHSM1K-SHADEDTAILSPATIAL1A changed frozen helper: ' + key)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1K-SHADEDTAILSPATIAL1A applied')
print(' - retains all four 1J prospective products byte-for-photomath')
print(' - adds read-only corrected-tail spatial support audit on ON-unguarded same-RAW control')
print(' - records display-oriented center50/edge and 3x3 support concentration')
print(' - preserves SHADEDGUARD1A and cap20EV gain formulas unchanged')
print(' - Primary / LensShadingMap / residual / SHADEDTAIL1A / FINALCLIPAUDIT1A helpers frozen')
print(' - capture exposure / DNG / TC20 / HSM / tone curve / single RAW / HDR=false unchanged')
