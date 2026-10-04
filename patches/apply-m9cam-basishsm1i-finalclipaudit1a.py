#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1i-finalclipaudit1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A opening brace missing: ' + marker)
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
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1I-FINALCLIPAUDIT1A {label} anchor count={count}')
    return src.replace(old, new, 1)


# 1I is diagnostic only. It starts from the proven 1H causal three-way experiment
# and must not modify Primary, capture, DNG, LensShadingMap, shaded-tail audit, guard
# formula, TC20 decision, HSM, tone curve, or the final bitmap pixels.
for marker in [
    'm9cam.renderer.basishsm.shadedguardab.v1a.main',
    'shadedGuardAB1A',
    'shadedGuard1ARequested',
    'shading_on_unguarded_control',
    'shading_on_guarded',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_SHADEDGUARD1A"',
    'Math.min(meter.baseGain, shadedGuard1ACorrectedGuardGain)',
    'post_EA_demosaic_camera_RGB_pre_whitepoint_pre_HSM_pre_TC20',
    'shadingLateRepresentationScaleApplied", false',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A requires 1H marker: ' + marker)
if '-basishsm1h-shadedguardab1a' not in gradle:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A requires 1H build provenance')
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_before = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_before = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_before = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
primary_sha = hashlib.sha256(primary_before.encode()).hexdigest()
shading_sha = hashlib.sha256(shading_before.encode()).hexdigest()
residual_sha = hashlib.sha256(residual_before.encode()).hexdigest()
tail_sha = hashlib.sha256(tail_before.encode()).hexdigest()

# Exact final-ARGB bitmap audit. This deliberately runs AFTER all photographic math
# and reads pixels only. It separates high-side clipping from low-side clipping and
# records whether extrema live in the central 50% or the surrounding edge region.
# The temporary row buffer is bounded to 64 rows to avoid a full-bitmap Java copy.
helper = r'''
    // BASISHSM1I-FINALCLIPAUDIT1A -- read-only final bitmap forensics.
    private static JSONObject finalClipAudit1A(Bitmap bitmap) throws Exception {
        JSONObject j = new JSONObject();
        j.put("schema", "m9cam.renderer.finalclipaudit.v1a");
        j.put("diagnosticOnly", true);
        j.put("pixelMutation", false);
        j.put("gainMutation", false);
        j.put("stage", "finished_oriented_ARGB8888_bitmap_post_curve_post_BT601_post_TG1");
        j.put("highClipDefinition", "any_RGB_channel_eq_255");
        j.put("lowClipDefinition", "any_RGB_channel_eq_0");
        j.put("upperStressDefinition", "any_RGB_channel_ge_250");
        j.put("nearWhiteLumaDefinition", "exact_BT601_Q14_luma_ge_250");
        if (bitmap == null || bitmap.isRecycled()) {
            j.put("valid", false);
            j.put("reason", "missing_or_recycled_bitmap");
            return j;
        }

        final int width = bitmap.getWidth();
        final int height = bitmap.getHeight();
        if (width <= 0 || height <= 0) {
            j.put("valid", false);
            j.put("reason", "invalid_bitmap_geometry");
            return j;
        }
        final int rowBlock = Math.min(64, height);
        final int[] pixels = new int[Math.multiplyExact(width, rowBlock)];
        final int cx0 = width / 4;
        final int cx1 = (3 * width) / 4;
        final int cy0 = height / 4;
        final int cy1 = (3 * height) / 4;

        long total = 0L;
        long highAny = 0L, lowAny = 0L, bothHighLow = 0L;
        long fullWhite = 0L, fullBlack = 0L;
        long rHigh = 0L, gHigh = 0L, bHigh = 0L;
        long rLow = 0L, gLow = 0L, bLow = 0L;
        long upperStressAny = 0L, upperStressAll = 0L;
        long lumaNearWhite = 0L;
        long centerTotal = 0L, centerHigh = 0L, centerLow = 0L;
        long centerUpperStress = 0L, centerLumaNearWhite = 0L;
        long edgeTotal = 0L, edgeHigh = 0L, edgeLow = 0L;
        long edgeUpperStress = 0L, edgeLumaNearWhite = 0L;

        for (int y0 = 0; y0 < height; y0 += rowBlock) {
            final int rows = Math.min(rowBlock, height - y0);
            bitmap.getPixels(pixels, 0, width, 0, y0, width, rows);
            for (int yy = 0; yy < rows; yy++) {
                final int y = y0 + yy;
                final int base = yy * width;
                for (int x = 0; x < width; x++) {
                    final int argb = pixels[base + x];
                    final int r = (argb >>> 16) & 0xff;
                    final int g = (argb >>> 8) & 0xff;
                    final int b = argb & 0xff;
                    final boolean rh = r == 255, gh = g == 255, bh = b == 255;
                    final boolean rl = r == 0, gl = g == 0, bl = b == 0;
                    final boolean high = rh || gh || bh;
                    final boolean low = rl || gl || bl;
                    final boolean stress = r >= 250 || g >= 250 || b >= 250;
                    final boolean stressAll = r >= 250 && g >= 250 && b >= 250;
                    final int y8 = (4899 * r + 9617 * g + 1868 * b) >> 14;
                    final boolean nw = y8 >= 250;
                    final boolean center = x >= cx0 && x < cx1 && y >= cy0 && y < cy1;

                    total++;
                    if (high) highAny++;
                    if (low) lowAny++;
                    if (high && low) bothHighLow++;
                    if (rh) rHigh++;
                    if (gh) gHigh++;
                    if (bh) bHigh++;
                    if (rl) rLow++;
                    if (gl) gLow++;
                    if (bl) bLow++;
                    if (r == 255 && g == 255 && b == 255) fullWhite++;
                    if (r == 0 && g == 0 && b == 0) fullBlack++;
                    if (stress) upperStressAny++;
                    if (stressAll) upperStressAll++;
                    if (nw) lumaNearWhite++;

                    if (center) {
                        centerTotal++;
                        if (high) centerHigh++;
                        if (low) centerLow++;
                        if (stress) centerUpperStress++;
                        if (nw) centerLumaNearWhite++;
                    } else {
                        edgeTotal++;
                        if (high) edgeHigh++;
                        if (low) edgeLow++;
                        if (stress) edgeUpperStress++;
                        if (nw) edgeLumaNearWhite++;
                    }
                }
            }
        }

        j.put("valid", true);
        j.put("width", width);
        j.put("height", height);
        j.put("pixelCount", total);
        j.put("scanRowBlock", rowBlock);
        j.put("anyHighClipPixelCount", highAny);
        j.put("anyHighClipFraction", highAny / (double)total);
        j.put("anyLowClipPixelCount", lowAny);
        j.put("anyLowClipFraction", lowAny / (double)total);
        j.put("mixedHighLowPixelCount", bothHighLow);
        j.put("mixedHighLowFraction", bothHighLow / (double)total);
        j.put("fullWhitePixelCount", fullWhite);
        j.put("fullWhiteFraction", fullWhite / (double)total);
        j.put("fullBlackPixelCount", fullBlack);
        j.put("fullBlackFraction", fullBlack / (double)total);
        j.put("redHighClipFraction", rHigh / (double)total);
        j.put("greenHighClipFraction", gHigh / (double)total);
        j.put("blueHighClipFraction", bHigh / (double)total);
        j.put("redLowClipFraction", rLow / (double)total);
        j.put("greenLowClipFraction", gLow / (double)total);
        j.put("blueLowClipFraction", bLow / (double)total);
        j.put("anyChannelGE250Fraction", upperStressAny / (double)total);
        j.put("allChannelsGE250Fraction", upperStressAll / (double)total);
        j.put("lumaGE250Fraction", lumaNearWhite / (double)total);

        JSONObject center = new JSONObject();
        center.put("region", "center_50_percent_width_height");
        center.put("pixelCount", centerTotal);
        center.put("anyHighClipFraction", centerTotal > 0 ? centerHigh / (double)centerTotal : 0.0);
        center.put("anyLowClipFraction", centerTotal > 0 ? centerLow / (double)centerTotal : 0.0);
        center.put("anyChannelGE250Fraction", centerTotal > 0 ? centerUpperStress / (double)centerTotal : 0.0);
        center.put("lumaGE250Fraction", centerTotal > 0 ? centerLumaNearWhite / (double)centerTotal : 0.0);
        j.put("center50", center);

        JSONObject edge = new JSONObject();
        edge.put("region", "outside_center_50_percent_width_height");
        edge.put("pixelCount", edgeTotal);
        edge.put("anyHighClipFraction", edgeTotal > 0 ? edgeHigh / (double)edgeTotal : 0.0);
        edge.put("anyLowClipFraction", edgeTotal > 0 ? edgeLow / (double)edgeTotal : 0.0);
        edge.put("anyChannelGE250Fraction", edgeTotal > 0 ? edgeUpperStress / (double)edgeTotal : 0.0);
        edge.put("lumaGE250Fraction", edgeTotal > 0 ? edgeLumaNearWhite / (double)edgeTotal : 0.0);
        j.put("edgeOutsideCenter50", edge);
        return j;
    }

'''

helper_marker = '    private static RenderCore renderNativeProspectiveCore('
if renderer.count(helper_marker) != 1:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A prospective helper anchor ambiguous')
if 'private static JSONObject finalClipAudit1A(' in renderer:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A helper already present')
renderer = renderer.replace(helper_marker, helper + helper_marker, 1)

# Add the read-only audit at the very end of each prospective variant. The same
# Bitmap object is returned unchanged after the scan.
pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')
return_anchor = '            return new RenderCore(oriented, d);'
return_replacement = '''            d.put("finalClipAudit1AEnabled", true);
            d.put("finalClipAudit1A", finalClipAudit1A(oriented));
            return new RenderCore(oriented, d);'''
prospective = replace_once(prospective, return_anchor, return_replacement, 'final bitmap audit seam')
prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.shadedguardab.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.finalclipaudit.v1a.main");',
    'prospective schema')
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

gradle = gradle.replace('-basishsm1h-shadedguardab1a', '-basishsm1i-finalclipaudit1a', 1)
if '-basishsm1i-finalclipaudit1a' not in gradle:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A failed to set build provenance')

# Frozen photographic/physical helpers remain byte-identical. The prospective
# renderer changes only by appending a read-only bitmap scan after render completion.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
_, _, shading_after = extract_method(renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
_, _, residual_after = extract_method(renderer, '    private static JSONObject rawShadingResidualAudit1A(')
_, _, tail_after = extract_method(renderer, '    private static ShadedTailAudit1AStats shadedTailAudit1A(')
if hashlib.sha256(primary_after.encode()).hexdigest() != primary_sha:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A changed frozen Primary renderCore')
if hashlib.sha256(shading_after.encode()).hexdigest() != shading_sha:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A changed LensShadingMap helper')
if hashlib.sha256(residual_after.encode()).hexdigest() != residual_sha:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A changed RAW residual audit')
if hashlib.sha256(tail_after.encode()).hexdigest() != tail_sha:
    raise SystemExit('BASISHSM1I-FINALCLIPAUDIT1A changed shaded-tail audit helper')

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1I-FINALCLIPAUDIT1A applied')
print(' - 1H OFF / ON-unguarded / ON-guarded photographic math unchanged')
print(' - exact final bitmap audit splits 255-side vs 0-side clipping')
print(' - per-channel and center-vs-edge support recorded')
print(' - Primary / LensShadingMap / residual audit / shaded-tail audit SHA preserved')
print(' - single RAW / HDR=false / capture exposure / DNG remain frozen')
