#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1d-rawshadingresidual1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A assembled inputs missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A opening brace missing: ' + marker)
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
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A unterminated method: ' + marker)

def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1D-RAWSHADINGRESIDUAL1A {label} anchor count={count}')
    return src.replace(old, new, 1)

for marker in [
    'shadingParity1A',
    'normalized_linear_Bayer_pre_demosaic_headroom_preserved',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"',
    'historical_linear_basis_then_historical_HSM',
    'historical_interpolated_table',
    'meterParitySelfMeter',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A requires SHADINGPARITY1A marker: ' + marker)
if '-basishsm1c-shadingparity1a' not in gradle:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A requires SHADINGPARITY1A build provenance')

frames = frames_path.read_text()
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()
_, _, shading_before = extract_method(
    renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
shading_sha = hashlib.sha256(shading_before.encode('utf-8')).hexdigest()

helper = r'''
    // BASISHSM1D-RAWSHADINGRESIDUAL1A
    // Diagnostic-only flat-field audit. It reads the normalized Bayer before any
    // LensShadingMap application and compares measured centre-to-corner falloff with
    // the live Camera2 map prediction. The metrics are physically interpretable only
    // for a spatially uniform target (flat wall / overcast sky / diffuser).
    private static JSONObject rawShadingResidualAudit1A(
            short[] norm16, int width, int height, LensShadingMap map) throws Exception {
        JSONObject out = new JSONObject();
        out.put("schema", "m9cam.renderer.rawshadingresidual.v1a");
        out.put("diagnosticOnly", true);
        out.put("flatFieldInterpretationOnly", true);
        out.put("pixelMutation", false);
        out.put("sampleStrideRawPixels", 8);
        if (map == null) {
            out.put("mapPresent", false);
            return out;
        }

        final int mapW = map.getColumnCount();
        final int mapH = map.getRowCount();
        float[] gains = new float[map.getGainFactorCount()];
        map.copyGainFactors(gains, 0);
        if (mapW < 1 || mapH < 1 || gains.length != mapW * mapH * 4) {
            out.put("mapPresent", true);
            out.put("valid", false);
            out.put("reason", "invalid_map_dimensions");
            return out;
        }

        final int REGION_CENTER = 0;
        final int REGION_TL = 1;
        final int REGION_TR = 2;
        final int REGION_BL = 3;
        final int REGION_BR = 4;
        final String[] regionNames = {"center", "topLeft", "topRight", "bottomLeft", "bottomRight"};
        final String[] planeNames = {"R", "Geven", "Godd", "B"};
        final int REGION_COUNT = 5;
        final int PLANE_COUNT = 4;
        final int BINS = 512;
        long[][] counts = new long[REGION_COUNT][PLANE_COUNT];
        double[][] sums = new double[REGION_COUNT][PLANE_COUNT];
        double[][] gainSums = new double[REGION_COUNT][PLANE_COUNT];
        long[][][] hist = new long[REGION_COUNT][PLANE_COUNT][BINS];

        final int cx0 = (int)Math.floor(width * 0.30);
        final int cx1 = (int)Math.ceil(width * 0.70);
        final int cy0 = (int)Math.floor(height * 0.30);
        final int cy1 = (int)Math.ceil(height * 0.70);
        final int left1 = (int)Math.ceil(width * 0.20);
        final int right0 = (int)Math.floor(width * 0.80);
        final int top1 = (int)Math.ceil(height * 0.20);
        final int bottom0 = (int)Math.floor(height * 0.80);
        final double xScale = width > 1 ? (mapW - 1.0) / (width - 1.0) : 0.0;
        final double yScale = height > 1 ? (mapH - 1.0) / (height - 1.0) : 0.0;

        for (int plane = 0; plane < PLANE_COUNT; plane++) {
            final int yParity = (plane >> 1) & 1;
            final int xParity = plane & 1;
            for (int y = yParity; y < height; y += 8) {
                final int row = y * width;
                final double gy = y * yScale;
                final int y0 = (int)Math.floor(gy);
                final int y1 = Math.min(mapH - 1, y0 + 1);
                final double fy = gy - y0;
                for (int x = xParity; x < width; x += 8) {
                    int region = -1;
                    if (x >= cx0 && x < cx1 && y >= cy0 && y < cy1) {
                        region = REGION_CENTER;
                    } else if (x < left1 && y < top1) {
                        region = REGION_TL;
                    } else if (x >= right0 && y < top1) {
                        region = REGION_TR;
                    } else if (x < left1 && y >= bottom0) {
                        region = REGION_BL;
                    } else if (x >= right0 && y >= bottom0) {
                        region = REGION_BR;
                    }
                    if (region < 0) continue;

                    double raw = (norm16[row + x] & 0xffff) / 65535.0;
                    int bin = (int)Math.floor(raw * (BINS - 1) + 0.5);
                    if (bin < 0) bin = 0;
                    if (bin >= BINS) bin = BINS - 1;

                    final double gx = x * xScale;
                    final int x0 = (int)Math.floor(gx);
                    final int x1 = Math.min(mapW - 1, x0 + 1);
                    final double fx = gx - x0;
                    final int i00 = ((y0 * mapW + x0) * 4) + plane;
                    final int i01 = ((y0 * mapW + x1) * 4) + plane;
                    final int i10 = ((y1 * mapW + x0) * 4) + plane;
                    final int i11 = ((y1 * mapW + x1) * 4) + plane;
                    final double g0 = gains[i00] + fx * (gains[i01] - gains[i00]);
                    final double g1 = gains[i10] + fx * (gains[i11] - gains[i10]);
                    final double gain = g0 + fy * (g1 - g0);

                    counts[region][plane]++;
                    sums[region][plane] += raw;
                    gainSums[region][plane] += gain;
                    hist[region][plane][bin]++;
                }
            }
        }

        double[][] medians = new double[REGION_COUNT][PLANE_COUNT];
        double[][] meanGains = new double[REGION_COUNT][PLANE_COUNT];
        JSONObject regions = new JSONObject();
        for (int region = 0; region < REGION_COUNT; region++) {
            JSONObject regionJson = new JSONObject();
            for (int plane = 0; plane < PLANE_COUNT; plane++) {
                long n = counts[region][plane];
                JSONObject p = new JSONObject();
                p.put("sampleCount", n);
                if (n > 0) {
                    long target = (n - 1L) / 2L;
                    long cumulative = 0L;
                    int medianBin = 0;
                    for (int b = 0; b < BINS; b++) {
                        cumulative += hist[region][plane][b];
                        if (cumulative > target) {
                            medianBin = b;
                            break;
                        }
                    }
                    double median = medianBin / (double)(BINS - 1);
                    double mean = sums[region][plane] / n;
                    double meanGain = gainSums[region][plane] / n;
                    medians[region][plane] = median;
                    meanGains[region][plane] = meanGain;
                    p.put("rawMedian", median);
                    p.put("rawMean", mean);
                    p.put("mapMeanGain", meanGain);
                } else {
                    p.put("rawMedian", JSONObject.NULL);
                    p.put("rawMean", JSONObject.NULL);
                    p.put("mapMeanGain", JSONObject.NULL);
                }
                regionJson.put(planeNames[plane], p);
            }
            regions.put(regionNames[region], regionJson);
        }
        out.put("mapPresent", true);
        out.put("valid", true);
        out.put("mapWidth", mapW);
        out.put("mapHeight", mapH);
        out.put("regions", regions);

        JSONObject comparisons = new JSONObject();
        for (int region = REGION_TL; region <= REGION_BR; region++) {
            JSONObject corner = new JSONObject();
            for (int plane = 0; plane < PLANE_COUNT; plane++) {
                JSONObject p = new JSONObject();
                double center = medians[REGION_CENTER][plane];
                double edge = medians[region][plane];
                double centerGain = meanGains[REGION_CENTER][plane];
                double edgeGain = meanGains[region][plane];
                if (center > 0.0 && edge > 0.0 && centerGain > 0.0 && edgeGain > 0.0) {
                    double observedEv = Math.log(center / edge) / Math.log(2.0);
                    double predictedEv = Math.log(edgeGain / centerGain) / Math.log(2.0);
                    p.put("observedCenterToCornerFalloffEv", observedEv);
                    p.put("mapPredictedCorrectionEv", predictedEv);
                    p.put("residualAfterMapPredictionEv", observedEv - predictedEv);
                } else {
                    p.put("observedCenterToCornerFalloffEv", JSONObject.NULL);
                    p.put("mapPredictedCorrectionEv", JSONObject.NULL);
                    p.put("residualAfterMapPredictionEv", JSONObject.NULL);
                }
                corner.put(planeNames[plane], p);
            }
            comparisons.put(regionNames[region], corner);
        }
        out.put("cornerComparisons", comparisons);
        return out;
    }

'''

class_marker = '    private static final class NativeProspectiveShadingStats {'
if renderer.count(class_marker) != 1:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A shading-stats class anchor ambiguous')
renderer = renderer.replace(class_marker, helper + class_marker, 1)

pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')
audit_anchor = '        NativeProspectiveShadingStats nativeShading = applyNativeShading'
audit_call = '''        JSONObject rawShadingResidual1A = rawShadingResidualAudit1A(
                norm16, width, height, nativeLiveGainMap);
        NativeProspectiveShadingStats nativeShading = applyNativeShading'''
if prospective.count(audit_anchor) != 1:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A shading call anchor count='
                     + str(prospective.count(audit_anchor)))
prospective = prospective.replace(audit_anchor, audit_call, 1)

diag_anchor = '            d.put("shadingParitySelfMeterAfterShading",'
diag_pos = prospective.find(diag_anchor)
if diag_pos < 0:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A shading diagnostic anchor missing')
stmt_end = prospective.find(';', diag_pos)
if stmt_end < 0:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A diagnostic semicolon missing')
stmt_end += 1
prospective = prospective[:stmt_end] + '''
            d.put("rawShadingResidual1AEnabled", true);
            d.put("rawShadingResidual1A", rawShadingResidual1A);''' + prospective[stmt_end:]

prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.shadingparity.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.rawshadingresidual.v1a.main");',
    'prospective schema')
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

gradle = gradle.replace(
    '-basishsm1c-shadingparity1a',
    '-basishsm1d-rawshadingresidual1a', 1)
if '-basishsm1d-rawshadingresidual1a' not in gradle:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A failed to set build provenance')

_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
if hashlib.sha256(primary_after.encode('utf-8')).hexdigest() != primary_sha:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A changed frozen Primary renderCore')

_, _, shading_after = extract_method(
    renderer, '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(')
if hashlib.sha256(shading_after.encode('utf-8')).hexdigest() != shading_sha:
    raise SystemExit('BASISHSM1D-RAWSHADINGRESIDUAL1A changed LensShadingMap application math')

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9Cam BASISHSM1D-RAWSHADINGRESIDUAL1A applied')
print(' - frozen Primary renderCore sha256 preserved:', primary_sha)
print(' - SHADINGPARITY1A OFF/ON pixels and TC20 logic preserved')
print(' - LensShadingMap application helper sha256 preserved:', shading_sha)
print(' - diagnostic-only pre-shading Bayer flat-field residual audit added')
print(' - single RAW / HDR=false / capture exposure / DNG remain frozen')
