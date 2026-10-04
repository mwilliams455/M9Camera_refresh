#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
R = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
B = ROOT / 'app/build.gradle'
if not R.exists() or not B.exists():
    raise SystemExit('DEMOSAICAB1A assembled PhotonCamera files missing')

text = R.read_text()
gradle = B.read_text()

def replace1(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'DEMOSAICAB1A {label}: expected 1 anchor, found {n}')
    return s.replace(old, new, 1)

def method_bounds(s, marker):
    start = s.find(marker)
    if start < 0:
        raise SystemExit('DEMOSAICAB1A active method marker missing')
    brace = s.find('{', start)
    if brace < 0:
        raise SystemExit('DEMOSAICAB1A active method opening brace missing')
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    esc = False
    while i < len(s):
        ch = s[i]
        nxt = s[i+1] if i+1 < len(s) else ''
        if state == 'line':
            if ch == '\n':
                state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/':
                state = 'code'
                i += 1
        elif state == 'string':
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == quote:
                state = 'code'
        else:
            if ch == '/' and nxt == '/':
                state = 'line'
                i += 1
            elif ch == '/' and nxt == '*':
                state = 'block'
                i += 1
            elif ch in ('"', "'"):
                state = 'string'
                quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return start, i + 1
        i += 1
    raise SystemExit('DEMOSAICAB1A active method unterminated')

for token in (
    'DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct',
    'reachabilityFence(mhcRgbBuffer)',
    'demosaicMhcRggb(',
    '_SKYSAT_CONTROL_SAT3',
    'int[] bridgeProbeModes = {50, 51, 52, 53};',
    'boolean[] selfMeterFlags = {true, false, false, false};',
):
    if token not in text:
        raise SystemExit('DEMOSAICAB1A requires validated MHC/SKYSAT parent: missing ' + token)

text = replace1(text, '''                        String[] suffixes = {
                                "_SKYSAT_CONTROL_SAT3",
                                "_SKYSAT_SAT2_STANDARD",
                                "_SKYSAT_SAT4_HIGH",
                                "_SKYSAT_SAT3_BYPASS"
                        };''', '''                        // DEMOSAICAB1A: same RAW and same NORM030 Bayer; only demosaic changes.
                        // A is MHC production and meters normally. B is OpenCV EA and reuses A's
                        // exact effective render gain. SOURCECAL2A/HSM/TC20 placement/SAT3/curve02/
                        // BT601/TG1 are otherwise identical.
                        String[] suffixes = {
                                "_DEMOSAICAB_MHC_SAT3",
                                "_DEMOSAICAB_EA_SAT3_GAINLOCK"
                        };''', 'suffix bank')

text = replace1(text, '''                        String[] bridgeProbeNames = {
                                "skysat_control_sat3",
                                "skysat_sat2_standard_gainlocked",
                                "skysat_sat4_high_gainlocked",
                                "skysat_sat3_bypass_gainlocked"
                        };''', '''                        String[] bridgeProbeNames = {
                                "demosaicab_mhc_sat3_control",
                                "demosaicab_ea_sat3_gainlocked"
                        };''', 'name bank')

for old, new, label in (
    ('                        int[] bridgeProbeModes = {50, 51, 52, 53};',
     '                        int[] bridgeProbeModes = {50, 54};', 'mode bank'),
    ('                        boolean[] selfMeterFlags = {true, false, false, false};',
     '                        boolean[] selfMeterFlags = {true, false};', 'gain lock bank'),
    ('                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0, 1.0};',
     '                        double[] hsmValueStrengthFlags = {1.0, 1.0};', 'HSM V bank'),
    ('                        boolean[] applyShadingFlags = {true, true, true, true};',
     '                        boolean[] applyShadingFlags = {true, true};', 'shading bank'),
    ('                        boolean[] applyShadedGuard1AFlags = {false, false, false, false};',
     '                        boolean[] applyShadedGuard1AFlags = {false, false};', 'shaded guard bank'),
    ('                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false};',
     '                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false};', 'shaded guard cap bank'),
    ('                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true, true};',
     '                        boolean[] applyShadingLumaDecomp1AFlags = {true, true};', 'luma decomp bank'),
    ('                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0, 1.0};',
     '                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0};', 'luma authority bank'),
    ('                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true, true};',
     '                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true};', 'luma norm bank'),
    ('                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30, 0.30};',
     '                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30};', 'NORM030 target bank'),
):
    text = replace1(text, old, new, label)

text = text.replace('"m9cam.renderer.skysat.v1a"', '"m9cam.renderer.demosaicab.v1a"')
text = text.replace('"BASISHSM1P-SKYSAT1A"', '"BASISHSM1P-DEMOSAICAB1A"')
text = text.replace('"completed_skysat1a"', '"completed_demosaicab1a"')
text = text.replace('"B_C_D_locked_to_A_exact_effective_render_gain"',
                    '"EA_B_locked_to_MHC_A_exact_effective_render_gain"')

start, end = method_bounds(text, '    private static RenderCore renderNativeProspectiveCore(')
active = text[start:end]
brace = active.find('{')
active = active[:brace+1] + '''
        // DEMOSAICAB1A encoded mode 54 is diagnostic-only. It is consumed before
        // bridge decoding and never changes production mode 0/3 arithmetic.
        final boolean demosaicAbEaRequested1A = bridgeProbeMode == 54;
''' + active[brace+1:]

active = replace1(active,
                  'final boolean skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 53;',
                  'final boolean skySatDiagnosticEncoded1A = bridgeProbeMode >= 50 && bridgeProbeMode <= 54;',
                  'SKYSAT encoded range')
active = replace1(active,
                  'bridgeProbeMode == 52 ? 10 : 7)',
                  'bridgeProbeMode == 52 ? 10 : bridgeProbeMode == 53 ? 7 : 0)',
                  'mode54 production SAT3 decode')

old_decl = '''        // DEMOSAICMHC1A owns one direct RGB16 frame. The backing ByteBuffer must
        // stay strongly reachable until cam16.release() because OpenCV wraps, not copies, it.
        final int mhcBytes = Math.multiplyExact(Math.multiplyExact(width, height), 6);
        ByteBuffer mhcRgbBuffer = ByteBuffer.allocateDirect(mhcBytes).order(ByteOrder.nativeOrder());
        Mat rawMat = new Mat(); // dormant compatibility handle; production MHC needs no Bayer Mat copy.
        Mat cam16 = new Mat(height, width, CvType.CV_16UC3, mhcRgbBuffer);
        Mat meterCam16 = new Mat();
'''
new_decl = '''        // DEMOSAICAB1A keeps the production MHC direct RGB16 path exact. Only encoded
        // diagnostic mode 54 allocates a Bayer Mat for the historical OpenCV EA control.
        final int mhcBytes = Math.multiplyExact(Math.multiplyExact(width, height), 6);
        ByteBuffer mhcRgbBuffer = demosaicAbEaRequested1A
                ? null
                : ByteBuffer.allocateDirect(mhcBytes).order(ByteOrder.nativeOrder());
        Mat rawMat = demosaicAbEaRequested1A
                ? new Mat(height, width, CvType.CV_16UC1)
                : new Mat();
        Mat cam16 = demosaicAbEaRequested1A
                ? new Mat()
                : new Mat(height, width, CvType.CV_16UC3, mhcRgbBuffer);
        Mat meterCam16 = new Mat();
'''
active = replace1(active, old_decl, new_decl, 'demosaic allocation')

old_demo = '''            long demosaicStartedNs = System.nanoTime();
            long[] mhcStats = new long[2];
            long mhcNativeNs = M9NativeColorCore.demosaicMhcRggb(
                    norm16, width, height, mhcRgbBuffer, NATIVE_COLOR_WORKERS, mhcStats);
            if (mhcNativeNs < 0) {
                throw new IllegalStateException("DEMOSAICMHC1A native failure: " + mhcNativeNs);
            }
            norm16 = null;
            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;
'''
new_demo = '''            long demosaicStartedNs = System.nanoTime();
            long[] mhcStats = new long[2];
            if (demosaicAbEaRequested1A) {
                rawMat.put(0, 0, norm16);
                Imgproc.cvtColor(rawMat, cam16, Imgproc.COLOR_BayerRG2BGR_EA);
                rawMat.release();
            } else {
                long mhcNativeNs = M9NativeColorCore.demosaicMhcRggb(
                        norm16, width, height, mhcRgbBuffer, NATIVE_COLOR_WORKERS, mhcStats);
                if (mhcNativeNs < 0) {
                    throw new IllegalStateException("DEMOSAICMHC1A native failure: " + mhcNativeNs);
                }
            }
            norm16 = null;
            demosaicElapsedMs = (System.nanoTime() - demosaicStartedNs) / 1_000_000L;
'''
active = replace1(active, old_demo, new_demo, 'demosaic switch')

old_mode = '            d.put("demosaicMode", "DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct");\n'
new_mode = '''            d.put("demosaicMode", demosaicAbEaRequested1A
                    ? "DEMOSAICAB1A_OpenCV_COLOR_BayerRG2BGR_EA_sameRAW_gainlocked"
                    : "DEMOSAICMHC1A_MalvarHeCutler5x5_RGGB_native_direct");
            d.put("demosaicAb1A", true);
            d.put("demosaicAbVariant", demosaicAbEaRequested1A
                    ? "EA_SAT3_GAINLOCK" : "MHC_SAT3_CONTROL");
            d.put("demosaicAbSameRawBayer", true);
            d.put("demosaicAbOnlyPhotographicDifference", "demosaic_kernel");
            d.put("demosaicAbDownstreamFrozen",
                    "WB_shading_SOURCECAL2A_basis_H25_TC20_gain_SAT3_curve02_BT601_TG1");
'''
active = replace1(active, old_mode, new_mode, 'mode telemetry')

old_control = '            d.put("demosaicControl", "dormant_legacy_OpenCV_COLOR_BayerRG2BGR_EA_retained");\n'
new_control = '''            d.put("demosaicControl", demosaicAbEaRequested1A
                    ? "active_sameRAW_OpenCV_EA_gainlocked_control"
                    : "legacy_OpenCV_EA_available_as_mode54_sameRAW_control");
'''
active = replace1(active, old_control, new_control, 'control telemetry')

old_perf = '''            d.put("demosaicNativeElapsedMs", mhcStats[0] / 1_000_000.0);
            d.put("demosaicWorkersUsed", mhcStats[1]);
            d.put("demosaicBackingLifetime", "direct_ByteBuffer_reachabilityFence_through_Mat_release");
'''
new_perf = '''            if (demosaicAbEaRequested1A) {
                d.put("demosaicNativeElapsedMs", JSONObject.NULL);
                d.put("demosaicWorkersUsed", JSONObject.NULL);
                d.put("demosaicBackingLifetime", "OpenCV_owned_Mat_control");
            } else {
                d.put("demosaicNativeElapsedMs", mhcStats[0] / 1_000_000.0);
                d.put("demosaicWorkersUsed", mhcStats[1]);
                d.put("demosaicBackingLifetime",
                        "direct_ByteBuffer_reachabilityFence_through_Mat_release");
            }
'''
active = replace1(active, old_perf, new_perf, 'performance telemetry')

text = text[:start] + active + text[end:]

if gradle.count('-demosaicmhc1a') != 1:
    raise SystemExit(f'DEMOSAICAB1A version anchor count={gradle.count("-demosaicmhc1a")}')
gradle = gradle.replace('-demosaicmhc1a', '-demosaicmhc1a-demosaicab1a', 1)

R.write_text(text)
B.write_text(gradle)

print('DEMOSAICAB1A applied')
print(' - primary production MHC JPEG preserved')
print(' - same RAW/NORM030 bank emits MHC SAT3 control + EA SAT3 gain-locked control')
print(' - encoded mode 54 decodes to exact production bridge/SAT3 downstream arithmetic')
print(' - no WB/shading/SOURCECAL2A/HSM/SAT3/curve02/BT601/TG1 changes')
