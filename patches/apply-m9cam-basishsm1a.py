#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('BASISHSM1A: not a PhotonCamera root')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
if not renderer_path.exists() or not gradle_path.exists():
    raise SystemExit('BASISHSM1A: assembled renderer/build.gradle missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1A opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ''
        if state == 'line_comment':
            if ch == '\n': state = 'code'
        elif state == 'block_comment':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line_comment'; i += 1
            elif ch == '/' and nxt == '*': state = 'block_comment'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1, src[start:i + 1]
        i += 1
    raise SystemExit('BASISHSM1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1A {label} anchor count={count}')
    return src.replace(old, new, 1)


for marker in [
    'NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major',
    'physical_SENSOR_NEUTRAL_COLOR_POINT_normalized_max1_clip_only',
    'd.put("bridgeProbe1A", true);',
    'bridgeProbeMode == 1',
    'bridgeProbeMode == 2',
    'historicalLinear.camToPp, inverse3(nativeCamToPpBeforeProbe)',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'prospectiveMeterRecomputed", false',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1A requires validated BRIDGEPROBE1A/v2.91 marker: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()

helper_marker = '    private static RenderCore renderNativeProspectiveCore('
if 'private static JSONObject basisHsmTraceCheckpoint(' in renderer:
    raise SystemExit('BASISHSM1A helpers already present; refuse ambiguous reapply')
helper_pos = renderer.find(helper_marker)
if helper_pos < 0:
    raise SystemExit('BASISHSM1A prospective helper insertion marker missing')

helpers = r'''
    // BASISHSM1A deterministic scientific checkpoints. These duplicate only a handful
    // of scalar operations for diagnostics and never feed the photographic output.
    private static JSONArray basisHsmVector(double[] v) throws Exception {
        JSONArray a = new JSONArray();
        a.put(v[0]); a.put(v[1]); a.put(v[2]);
        return a;
    }

    private static int basisHsmOutOfRangeChannels(double[] v) {
        int n = 0;
        if (v[0] < 0.0 || v[0] > 1.0) n++;
        if (v[1] < 0.0 || v[1] > 1.0) n++;
        if (v[2] < 0.0 || v[2] > 1.0) n++;
        return n;
    }

    private static JSONArray basisHsmHsv(double r, double g, double b) throws Exception {
        double v = Math.max(Math.max(r, g), b);
        double mn = Math.min(Math.min(r, g), b);
        double gap = v - mn;
        double h = 0.0, s = 0.0;
        if (gap > 1e-12 && v > 0.0) {
            if (r == v) { h = (g - b) / gap; if (h < 0.0) h += 6.0; }
            else if (g == v) h = 2.0 + (b - r) / gap;
            else h = 4.0 + (r - g) / gap;
            s = gap / v;
        }
        JSONArray a = new JSONArray();
        a.put(h * 60.0); a.put(s); a.put(v);
        return a;
    }

    private static JSONObject basisHsmTraceCheckpoint(
            String kind, int x, int y, double[] cameraRgb,
            double[] sensorToXyzD50, double[] nativeCamToPp,
            ColorContext ctx, double gain, byte[] curve) throws Exception {
        JSONObject o = new JSONObject();
        o.put("kind", kind); o.put("x", x); o.put("y", y);
        o.put("normalizedSensorRgb", basisHsmVector(cameraRgb));

        double[] postClip = {
                Math.min(cameraRgb[0], ctx.cw[0]),
                Math.min(cameraRgb[1], ctx.cw[1]),
                Math.min(cameraRgb[2], ctx.cw[2])
        };
        o.put("postNativeWpClipRgb", basisHsmVector(postClip));
        o.put("xyzD50", basisHsmVector(matVec3(sensorToXyzD50, postClip)));

        double[] nativeWorkingRaw = matVec3(nativeCamToPp, postClip);
        double[] basisWorkingRaw = matVec3(ctx.camToPp, postClip);
        o.put("nativeLinearWorkingRgb", basisHsmVector(nativeWorkingRaw));
        o.put("postHistoricalBasisRgb", basisHsmVector(basisWorkingRaw));
        o.put("nativeWorkingOutOfRangeChannels", basisHsmOutOfRangeChannels(nativeWorkingRaw));
        o.put("postBasisOutOfRangeChannels", basisHsmOutOfRangeChannels(basisWorkingRaw));

        double[] hsmInput = {
                clamp(basisWorkingRaw[0], 0.0, 1.0),
                clamp(basisWorkingRaw[1], 0.0, 1.0),
                clamp(basisWorkingRaw[2], 0.0, 1.0)
        };
        o.put("hsmInputWorkingRgb", basisHsmVector(hsmInput));
        o.put("hsmInputHsv", basisHsmHsv(hsmInput[0], hsmInput[1], hsmInput[2]));
        double[] hsmOut = new double[3];
        applyHsm(hsmInput[0], hsmInput[1], hsmInput[2], ctx.hsm, hsmOut);
        o.put("hsmOutputRgb", basisHsmVector(hsmOut));
        o.put("hsmOutputHsv", basisHsmHsv(hsmOut[0], hsmOut[1], hsmOut[2]));

        double[] m9 = matVec3(ctx.ppToM9, hsmOut);
        m9[0] = Math.max(m9[0], 0.0); m9[1] = Math.max(m9[1], 0.0); m9[2] = Math.max(m9[2], 0.0);
        o.put("m9BridgeInputRgb", basisHsmVector(hsmOut));
        o.put("m9BridgeOutputRgb", basisHsmVector(m9));

        long r = clipLong((long)Math.rint(m9[0] * gain * RAW_MAX), 0, RAW_MAX);
        long g = clipLong((long)Math.rint(m9[1] * gain * RAW_MAX), 0, RAW_MAX);
        long b = clipLong((long)Math.rint(m9[2] * gain * RAW_MAX), 0, RAW_MAX);
        boolean evenBranch = r >= g;
        long a0, a1, a2;
        if (evenBranch) {
            a0 = 16754 * r - 7632 * g - 922 * b;
            a1 = -3124 * r + 14774 * g - 3458 * b;
            a2 = -567 * r - 9579 * g + 18330 * b;
        } else {
            a0 = 18160 * r - 9034 * g - 922 * b;
            a1 = -3422 * r + 15080 * g - 3458 * b;
            a2 = 137 * r - 10264 * g + 18330 * b;
        }
        int i0 = (int)clipLong(a0 >> 16, 0, LUT_MAX);
        int i1 = (int)clipLong(a1 >> 16, 0, LUT_MAX);
        int i2 = (int)clipLong(a2 >> 16, 0, LUT_MAX);
        JSONArray sat = new JSONArray(); sat.put(i0); sat.put(i1); sat.put(i2);
        o.put("postSat3PreCurveIndices", sat);
        o.put("sat3Branch", evenBranch ? "M06_r_ge_g" : "M07_r_lt_g");
        JSONArray curveRgb = new JSONArray();
        curveRgb.put(curve[i0] & 0xff); curveRgb.put(curve[i1] & 0xff); curveRgb.put(curve[i2] & 0xff);
        o.put("postCurve02PreBt601Rgb8", curveRgb);
        return o;
    }

'''
renderer = renderer[:helper_pos] + helpers + renderer[helper_pos:]

pros_start, pros_end, prospective = extract_method(renderer, '    private static RenderCore renderNativeProspectiveCore(')

mode_anchor = '''            } else if (bridgeProbeMode != 0) {
                throw new IllegalArgumentException(
                        "BRIDGEPROBE1A unsupported mode " + bridgeProbeMode);
            }
            colorContextElapsedMs = (System.nanoTime() - colorContextStartedNs) / 1_000_000L;'''
mode_insert = '''            } else if (bridgeProbeMode == 3) {
                bridgeProbeName = "native_plus_historical_basis_hsm";
                bridgeProbeHistoricalLinearBasisApplied = true;
                bridgeProbeHistoricalHsmApplied = true;

                // BASISHSM1A: historical linear basis FIRST.
                ColorContext historicalLinear = buildColorContext(neutralF, cal);
                bridgeProbeBasis = matMul3(
                        historicalLinear.camToPp, inverse3(nativeCamToPpBeforeProbe));
                ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);
                for (int i = 0; i < 9; i++) {
                    bridgeProbeHistoricalLinearMaxAbsDelta = Math.max(
                            bridgeProbeHistoricalLinearMaxAbsDelta,
                            Math.abs(ctx.camToPp[i] - historicalLinear.camToPp[i]));
                }

                // Historical nonlinear HSM SECOND, now in its reconstructed basis.
                ctx.hsm = new double[cal.hsmA.length];
                for (int i = 0; i < ctx.hsm.length; i++) {
                    ctx.hsm[i] = ctx.wA * cal.hsmA[i]
                            + (1.0 - ctx.wA) * cal.hsmD65[i];
                }
                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
            } else if (bridgeProbeMode != 0) {
                throw new IllegalArgumentException(
                        "BASISHSM1A unsupported mode " + bridgeProbeMode);
            }

            long bridgeProbeHsmHash64 = 0L;
            if (bridgeProbeHistoricalHsmApplied && ctx.hsm != null) {
                bridgeProbeHsmHash64 = 1125899906842597L;
                for (double v : ctx.hsm) {
                    bridgeProbeHsmHash64 = 31L * bridgeProbeHsmHash64 + Double.doubleToLongBits(v);
                }
            }

            double[] bridgeProbeSensorToXyzD50 = new double[9];
            for (int i = 0; i < 9; i++) bridgeProbeSensorToXyzD50[i] = nativeSource.sensorToXyzD50[i];
            JSONArray basisHsmCheckpoints = new JSONArray();
            double[] neutralProbe = {nativeSource.neutral[0], nativeSource.neutral[1], nativeSource.neutral[2]};
            basisHsmCheckpoints.put(basisHsmTraceCheckpoint(
                    "capture_sensor_neutral", -1, -1, neutralProbe,
                    bridgeProbeSensorToXyzD50, nativeCamToPpBeforeProbe, ctx,
                    fixedPrimaryGain, cal.curve02));

            int[][] checkpointXy = {
                    {width / 2, height / 2},
                    {width / 4, height / 4},
                    {(3 * width) / 4, height / 4},
                    {width / 4, (3 * height) / 4},
                    {(3 * width) / 4, (3 * height) / 4}
            };
            short[] checkpointPixel = new short[3];
            for (int i = 0; i < checkpointXy.length; i++) {
                int sx = Math.max(0, Math.min(width - 1, checkpointXy[i][0]));
                int sy = Math.max(0, Math.min(height - 1, checkpointXy[i][1]));
                cam16.get(sy, sx, checkpointPixel);
                double[] checkpointCameraRgb = {
                        (checkpointPixel[0] & 0xffff) / 65535.0,
                        (checkpointPixel[1] & 0xffff) / 65535.0,
                        (checkpointPixel[2] & 0xffff) / 65535.0
                };
                basisHsmCheckpoints.put(basisHsmTraceCheckpoint(
                        "demosaic_fixed_sample_" + i, sx, sy, checkpointCameraRgb,
                        bridgeProbeSensorToXyzD50, nativeCamToPpBeforeProbe, ctx,
                        fixedPrimaryGain, cal.curve02));
            }
            colorContextElapsedMs = (System.nanoTime() - colorContextStartedNs) / 1_000_000L;'''
prospective = replace_once(prospective, mode_anchor, mode_insert, 'mode3 recombination')

return_anchor = '            return new RenderCore(oriented, d);'
diag_insert = '''            d.put("schema", "m9cam.renderer.basishsm.v1a.main.fixedgain");
            d.put("basisHsm1A", true);
            d.put("basisHsmCombinedApplied", bridgeProbeMode == 3);
            d.put("basisHsmOrdering",
                    bridgeProbeMode == 3 ? "historical_linear_basis_then_historical_HSM"
                            : "source_only_identity_HSM");
            d.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeMode == 3);
            d.put("basisHsmHsmTableIdentity",
                    bridgeProbeHistoricalHsmApplied
                            ? "cal.hsmA_plus_cal.hsmD65_interpolated_by_native_wA"
                            : "identity");
            d.put("basisHsmHsmTableHash64",
                    bridgeProbeHistoricalHsmApplied
                            ? Long.toUnsignedString(bridgeProbeHsmHash64, 16) : "identity");
            d.put("basisHsmHsmTableLength",
                    bridgeProbeHistoricalHsmApplied && ctx.hsm != null ? ctx.hsm.length : 0);
            d.put("basisHsmCheckpointSamples", basisHsmCheckpoints);
            d.put("basisHsmCheckpointNote",
                    "postCurve02PreBt601Rgb8 is the last scalar single-pixel checkpoint; exact BT601/TG1 remains pairwise in frozen output path");
            if (bridgeProbeMode == 3) {
                d.put("mixedCalibrationAssetUsage",
                        "historical_linear_basis_plus_HSM_role_diagnostic_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "native Camera2 source adapter + historical linear basis -> historical HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");
            }
            return new RenderCore(oriented, d);'''
prospective = replace_once(prospective, return_anchor, diag_insert, 'late BASISHSM diagnostics')
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

old_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_SOURCE_ONLY",
                                "_M9_NATIVE_HSM_ONLY",
                                "_M9_NATIVE_BASIS_ONLY"
                        };
                        String[] bridgeProbeNames = {
                                "source_only",
                                "native_plus_historical_hsm",
                                "native_plus_historical_linear_basis"
                        };
                        int[] bridgeProbeModes = {0, 1, 2};'''
new_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_SOURCE_ONLY",
                                "_M9_NATIVE_BASIS_HSM"
                        };
                        String[] bridgeProbeNames = {
                                "source_only",
                                "native_plus_historical_basis_hsm"
                        };
                        int[] bridgeProbeModes = {0, 3};'''
renderer = replace_once(renderer, old_arrays, new_arrays, 'minimal output arrays')
renderer = renderer.replace(
        '"main_physical_2_same_raw_primary_gain_source_only_vs_hsm_vs_linear_basis"',
        '"main_physical_2_same_raw_primary_gain_source_only_vs_basis_then_hsm"', 1)
renderer = renderer.replace(
        '// BRIDGEPROBE1A: controlled same-RAW colour-role A/B. Primary JPEG is already',
        '// BASISHSM1A: same-RAW SOURCE_ONLY vs historical-basis-then-HSM. Primary JPEG is already', 1)
renderer = renderer.replace('BRIDGEPROBE1A alternate JPEG save failed:', 'BASISHSM1A alternate JPEG save failed:')
renderer = renderer.replace('BRIDGEPROBE1A primary bright-pivot replication failed', 'BASISHSM1A primary bright-pivot replication failed')

if '-nativeapiorder1a-basishsm1a' not in gradle:
    old_suffix = '-nativeapiorder1a-bridgeprobe1a'
    if old_suffix not in gradle:
        raise SystemExit('BASISHSM1A build identity requires BRIDGEPROBE1A suffix')
    gradle = gradle.replace(old_suffix, '-nativeapiorder1a-basishsm1a', 1)

_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
primary_after_sha = hashlib.sha256(primary_after.encode('utf-8')).hexdigest()
if primary_after_sha != primary_sha:
    raise SystemExit('BASISHSM1A changed frozen primary renderCore: before=' + primary_sha + ' after=' + primary_after_sha)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9 BASISHSM1A applied')
print(' - frozen primary JPEG/renderCore preserved:', primary_sha)
print(' - SOURCE_ONLY remains validated native Camera2 baseline')
print(' - BASIS_HSM applies historical linear basis FIRST, historical HSM SECOND')
print(' - field outputs reduced to SOURCE_ONLY + BASIS_HSM; frozen Primary remains unchanged')
print(' - LensShadingMap remains forced OFF in the colour-role experiment')
print(' - same RAW and same frozen primary gain retained')
print(' - deterministic neutral + five fixed same-RAW colour checkpoints added')
print(' - no capture/exposure/HDR/SAT3/curve02/BT601/TG1 changes')
