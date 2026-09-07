#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1b-meterparity1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
iso_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
if not renderer_path.exists() or not gradle_path.exists():
    raise SystemExit('BASISHSM1B-METERPARITY1A: assembled renderer/build.gradle missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1B-METERPARITY1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1B-METERPARITY1A opening brace missing: ' + marker)
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
    raise SystemExit('BASISHSM1B-METERPARITY1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1B-METERPARITY1A {label} anchor count={count}')
    return src.replace(old, new, 1)


# This experiment starts only from the validated FIX2 three-way state.
for marker in [
    'basisHsmCombinedApplied',
    'historical_linear_basis_then_historical_HSM',
    'checkpointIdentityHsmSentinel',
    'ctx.hsm.length == 12',
    'checkpointHsmMode',
    'historical_interpolated_table',
    'int[] bridgeProbeModes = {0, 3};',
    '"_M9_NATIVE_SOURCE_ONLY"',
    '"_M9_NATIVE_BASIS_HSM"',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'prospectiveMeterRecomputed", false',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1B-METERPARITY1A requires validated BASISHSM1A-FIX2 marker: ' + marker)
if '-basishsm1a-fix2' not in gradle:
    raise SystemExit('BASISHSM1B-METERPARITY1A requires FIX2 build provenance')

# Capture exposure / no-HDR boundary remains frozen. This is JPEG-side diagnostic work only.
if frames_path.exists():
    frames = frames_path.read_text()
    for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;']:
        if marker not in frames:
            raise SystemExit('BASISHSM1B-METERPARITY1A NOHDR boundary missing: ' + marker)
if iso_path.exists() and 'IsoExpoSelector.HDR = false;' not in iso_path.read_text():
    raise SystemExit('BASISHSM1B-METERPARITY1A HDR=false boundary missing')

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()

# -----------------------------------------------------------------------------
# 1) Extend only the additive prospective renderer with a self-meter selector.
# The finite fixedPrimaryGain remains available as the same-frame control/reference
# and for deterministic BASIS/HSM checkpoints even when the self-meter variant runs.
# -----------------------------------------------------------------------------
pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')
old_sig = '''                                         double fixedPrimaryGain,
                                         boolean applyNativeShading,
                                         int bridgeProbeMode) throws Exception {'''
new_sig = '''                                         double fixedPrimaryGain,
                                         boolean applyNativeShading,
                                         int bridgeProbeMode,
                                         boolean selfMeter) throws Exception {'''
prospective = replace_once(prospective, old_sig, new_sig, 'prospective signature')

# Replace FIXEDGAIN1A's meter no-op with a controlled fixed-vs-self TC20 branch.
meter_start = prospective.find(
        '            // FIXEDGAIN1A: same-frame primary exposure decision is injected by the caller.')
meter_end = prospective.find(
        '            long fullRenderStartedNs = System.nanoTime();', meter_start)
if meter_start < 0 or meter_end < 0:
    raise SystemExit('BASISHSM1B-METERPARITY1A fixed meter block boundary missing')

meter_block = '''            // BASISHSM1B-METERPARITY1A: role-validated colour path, two meter treatments.
            // FIXED keeps the exact frozen Primary effective gain. SELFMETER recomputes TC20
            // on the native Camera2 -> historical basis -> historical HSM context, then applies
            // only the already-selected Primary edge-placement gain offset. Capture exposure,
            // DNG, shading status and Primary JPEG remain untouched.
            final boolean meterParitySelfMeter = selfMeter;
            boolean meterCvDirectEligible = false;
            Meter meter = new Meter();
            if (meterParitySelfMeter) {
                long meterStartedNs = System.nanoTime();
                int meterW = width;
                int meterH = height;
                long meterResizeStartedNs = System.nanoTime();
                if (Math.max(width, height) > METER_LONG_SIDE) {
                    double sc = METER_LONG_SIDE / (double)Math.max(width, height);
                    meterW = pyRoundPositive(width * sc);
                    meterH = pyRoundPositive(height * sc);
                    Imgproc.resize(cam16, meterCam16, new Size(meterW, meterH),
                            0.0, 0.0, Imgproc.INTER_AREA);
                } else {
                    cam16.copyTo(meterCam16);
                }
                meterResizeElapsedMs = (System.nanoTime() - meterResizeStartedNs) / 1_000_000L;
                int meterPixels = Math.multiplyExact(meterW, meterH);
                meterCvDirectEligible = meterCam16.isContinuous()
                        && meterCam16.channels() == 3
                        && meterCam16.elemSize1() == 2L
                        && meterCam16.step1() == (long)meterW * 3L
                        && meterCam16.dataAddr() != 0L;
                short[] meterCam = null;
                long meterCamAddress = 0L;
                long meterTransferStartedNs = System.nanoTime();
                if (meterCvDirectEligible) {
                    meterCamAddress = meterCam16.dataAddr();
                } else {
                    meterCam = new short[Math.multiplyExact(meterPixels, 3)];
                    meterCam16.get(0, 0, meterCam);
                }
                meterTransferElapsedMs = (System.nanoTime() - meterTransferStartedNs) / 1_000_000L;

                long meterWeightStartedNs = System.nanoTime();
                double[] rowW = new double[meterH];
                double[] colW = new double[meterW];
                double h2 = meterH / 2.0, w2 = meterW / 2.0;
                double den = 2.0 * METER_CW * METER_CW;
                for (int yy = 0; yy < meterH; yy++) {
                    double ry = (yy - h2) / h2;
                    rowW[yy] = Math.exp(-(ry * ry) / den);
                }
                for (int xx = 0; xx < meterW; xx++) {
                    double rx = (xx - w2) / w2;
                    colW[xx] = Math.exp(-(rx * rx) / den);
                }
                meterWeightElapsedMs = (System.nanoTime() - meterWeightStartedNs) / 1_000_000L;

                long nativeTc20StartedNs = System.nanoTime();
                if (meterCvDirectEligible) {
                    meter = tc20MeterNativeDirect(
                            meterCamAddress, meterW, meterH, tail,
                            nativeContextForFrame, rowW, colW);
                } else {
                    meter = tc20MeterNative(
                            meterCam, meterW, meterH, tail,
                            nativeContextForFrame, rowW, colW);
                }
                nativeTc20ElapsedMs = (System.nanoTime() - nativeTc20StartedNs) / 1_000_000L;
                meterCam16.release();
                meterCam = null;
                meterTc20ElapsedMs = (System.nanoTime() - meterStartedNs) / 1_000_000L;
            } else {
                meterCam16.release();
                meter.gain = fixedPrimaryGain;
                meter.baseGain = fixedPrimaryGain;
                meter.legacyGain = fixedPrimaryGain;
                meter.guardGain = fixedPrimaryGain;
                meter.p98 = Double.NaN;
                meterResizeElapsedMs = 0L;
                meterTransferElapsedMs = 0L;
                meterWeightElapsedMs = 0L;
                nativeTc20ElapsedMs = 0L;
                meterTc20ElapsedMs = 0L;
            }

            // Self-meter changes only TC20's baseline gain. Reapply the already-selected
            // Primary DARK exact-render offset through edgePlacementGainEv; BRIGHT pivot is
            // still replicated outside this method exactly as in BASISHSM1A.
            final double meterParityRenderBaseGain = meterParitySelfMeter
                    ? meter.gain * Math.pow(2.0, edgePlacementGainEv)
                    : fixedPrimaryGain;
            final double effectiveRenderGain =
                    meterParityRenderBaseGain * nativeShading.representationScale;

'''
prospective = prospective[:meter_start] + meter_block + prospective[meter_end:]

# Make the inherited NATIVEAB diagnostics truthful for both treatments.
prospective = replace_once(
    prospective,
    '            d.put("tc20DecisionSource", "frozen_primary_same_frame");',
    '            d.put("tc20DecisionSource", meterParitySelfMeter\n'
    '                    ? "native_basis_hsm_same_frame_tc20" : "frozen_primary_same_frame");',
    'tc20 source diagnostic')
prospective = replace_once(
    prospective,
    '            d.put("prospectiveMeterRecomputed", false);',
    '            d.put("prospectiveMeterRecomputed", meterParitySelfMeter);',
    'meter recompute diagnostic')
prospective = replace_once(
    prospective,
    '            d.put("effectiveRenderGainAfterRepresentationScale", effectiveRenderGain);',
    '''            d.put("effectiveRenderGainAfterRepresentationScale", effectiveRenderGain);
            d.put("meterParity1A", true);
            d.put("meterParitySelfMeter", meterParitySelfMeter);
            d.put("meterParityCaptureExposureMutation", false);
            d.put("meterParityRawShadingForcedOffByCaller", true);
            d.put("meterParityReferencePrimaryEffectiveGain", fixedPrimaryGain);
            d.put("meterParityNativeTc20BaselineGain", meter.gain);
            d.put("meterParityPrimaryEdgePlacementGainEv", edgePlacementGainEv);
            d.put("meterParityRenderBaseGain", meterParityRenderBaseGain);
            if (fixedPrimaryGain > 0.0 && meterParityRenderBaseGain > 0.0) {
                d.put("meterParityGainRatioVsPrimary",
                        meterParityRenderBaseGain / fixedPrimaryGain);
                d.put("meterParityGainDeltaEvVsPrimary",
                        Math.log(meterParityRenderBaseGain / fixedPrimaryGain) / Math.log(2.0));
            }''',
    'meter parity diagnostics')
prospective = replace_once(
    prospective,
    '            d.put("bridgeProbeExposureDecision", "frozen_primary_same_frame");',
    '            d.put("bridgeProbeExposureDecision", meterParitySelfMeter\n'
    '                    ? "native_basis_hsm_self_tc20_plus_frozen_edge_policy"\n'
    '                    : "frozen_primary_same_frame");',
    'bridge probe exposure diagnostic')
prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.v1a.main.fixedgain");',
    '            d.put("schema", "m9cam.renderer.basishsm.meterparity.v1a.main");',
    'schema promotion')

renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

# -----------------------------------------------------------------------------
# 2) Retire SOURCE_ONLY from field output. Keep two BASIS_HSM renders only:
# same frozen Primary gain (colour control) vs native BASIS_HSM's own TC20 meter.
# -----------------------------------------------------------------------------
hook_start = renderer.find(
        '            // BASISHSM1A: same-RAW SOURCE_ONLY vs historical-basis-then-HSM. Primary JPEG is already')
hook_end = renderer.find(
        '\n            // Do not overwrite capture-time lastDiagnostics here:', hook_start)
if hook_start < 0 or hook_end < 0:
    raise SystemExit('BASISHSM1B-METERPARITY1A BASISHSM1A hook boundary missing')
hook = renderer[hook_start:hook_end]
hook = hook.replace(
    '// BASISHSM1A: same-RAW SOURCE_ONLY vs historical-basis-then-HSM. Primary JPEG is already',
    '// BASISHSM1B-METERPARITY1A: same-RAW BASIS_HSM fixed-vs-self-meter. Primary JPEG is already', 1)
hook = hook.replace(
    '"main_physical_2_same_raw_primary_gain_source_only_vs_basis_then_hsm"',
    '"main_physical_2_primary_vs_basis_hsm_fixed_vs_basis_hsm_self_meter"', 1)

old_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_SOURCE_ONLY",
                                "_M9_NATIVE_BASIS_HSM"
                        };
                        String[] bridgeProbeNames = {
                                "source_only",
                                "native_plus_historical_basis_hsm"
                        };
                        int[] bridgeProbeModes = {0, 3};'''
new_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_fixed_primary_gain",
                                "native_plus_historical_basis_hsm_self_meter"
                        };
                        int[] bridgeProbeModes = {3, 3};
                        boolean[] selfMeterFlags = {false, true};'''
hook = replace_once(hook, old_arrays, new_arrays, 'field output arrays')

old_loop = '''                            String suffix = suffixes[variantIndex];
                            String bridgeProbeName = bridgeProbeNames[variantIndex];
                            int bridgeProbeMode = bridgeProbeModes[variantIndex];
                            boolean applyShading = false;'''
new_loop = '''                            String suffix = suffixes[variantIndex];
                            String bridgeProbeName = bridgeProbeNames[variantIndex];
                            int bridgeProbeMode = bridgeProbeModes[variantIndex];
                            boolean selfMeter = selfMeterFlags[variantIndex];
                            boolean applyShading = false;'''
hook = replace_once(hook, old_loop, new_loop, 'field loop vars')

old_call = '''                                        cameraRotation, 0.0, characteristics, physicalResult,
                                        fixedPrimaryGain, applyShading, bridgeProbeMode);'''
new_call = '''                                        cameraRotation, selfMeter ? primaryEdgeEv : 0.0,
                                        characteristics, physicalResult,
                                        fixedPrimaryGain, applyShading, bridgeProbeMode, selfMeter);'''
hook = replace_once(hook, old_call, new_call, 'prospective call')

variant_marker = '''                                variantDiag.put("variant", bridgeProbeName);
                                variantDiag.put("bridgeProbeMode", bridgeProbeMode);
                                variantDiag.put("bridgeProbeShadingForcedOff", true);'''
variant_replacement = '''                                variantDiag.put("variant", bridgeProbeName);
                                variantDiag.put("bridgeProbeMode", bridgeProbeMode);
                                variantDiag.put("bridgeProbeShadingForcedOff", true);
                                variantDiag.put("meterParitySelfMeterRequested", selfMeter);'''
if hook.count(variant_marker) != 2:
    raise SystemExit('BASISHSM1B-METERPARITY1A expected two variant markers, got ' + str(hook.count(variant_marker)))
hook = hook.replace(variant_marker, variant_replacement)

hook = hook.replace(
    'nativeAb1A.put("tc20DecisionSource", "frozen_primary_same_frame");',
    'nativeAb1A.put("tc20DecisionSource", "frozen_primary_same_frame_reference");\n'
    '                        nativeAb1A.put("meterParity1A", true);', 1)
hook = hook.replace('BASISHSM1A alternate JPEG save failed:',
                    'BASISHSM1B-METERPARITY1A alternate JPEG save failed:')
hook = hook.replace('BASISHSM1A primary bright-pivot replication failed',
                    'BASISHSM1B-METERPARITY1A primary bright-pivot replication failed')

if '"_M9_NATIVE_SOURCE_ONLY"' in hook or 'int[] bridgeProbeModes = {0, 3};' in hook:
    raise SystemExit('BASISHSM1B-METERPARITY1A SOURCE_ONLY field output survived')
renderer = renderer[:hook_start] + hook + renderer[hook_end:]

# Distinct build provenance. This is still an additive diagnostic; frozen Primary remains the
# actual Photon JPEG until meter parity is measured and a separate promotion decision is made.
if '-basishsm1b-meterparity1a' not in gradle:
    gradle = gradle.replace('-basishsm1a-fix2', '-basishsm1b-meterparity1a', 1)

_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
primary_after_sha = hashlib.sha256(primary_after.encode('utf-8')).hexdigest()
if primary_after_sha != primary_sha:
    raise SystemExit('BASISHSM1B-METERPARITY1A changed frozen Primary renderCore: before='
                     + primary_sha + ' after=' + primary_after_sha)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9 BASISHSM1B-METERPARITY1A applied')
print(' - frozen Primary JPEG/renderCore preserved:', primary_sha)
print(' - SOURCE_ONLY field JPEG retired after Outcome A role validation')
print(' - BASIS_HSM fixed-primary-gain control retained')
print(' - BASIS_HSM SELFMETER recomputes TC20 on the validated native+basis+HSM context')
print(' - same Primary edge-placement policy is reapplied; bright pivot replication remains unchanged')
print(' - RAW shading remains forced OFF; capture exposure and DNG are unchanged')
print(' - next decision is meter parity, not another colour-role change')