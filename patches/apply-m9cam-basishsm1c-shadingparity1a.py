#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1c-shadingparity1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
if not renderer_path.exists() or not gradle_path.exists() or not frames_path.exists():
    raise SystemExit('BASISHSM1C-SHADINGPARITY1A: assembled renderer/build.gradle/FrameNumberSelector missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1C-SHADINGPARITY1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1C-SHADINGPARITY1A opening brace missing: ' + marker)
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
    raise SystemExit('BASISHSM1C-SHADINGPARITY1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BASISHSM1C-SHADINGPARITY1A {label} anchor count={count}')
    return src.replace(old, new, 1)


# This experiment begins only after field-validated BASISHSM1B METERPARITY1A.
for marker in [
    'meterParity1A',
    'meterParitySelfMeter',
    'native_basis_hsm_same_frame_tc20',
    'historical_linear_basis_then_historical_HSM',
    'basisHsmCombinedApplied',
    'historical_interpolated_table',
    'boolean[] selfMeterFlags = {false, true};',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER"',
    'NativeProspectiveShadingStats nativeShading = applyNativeShading',
    'applyNativeProspectiveGainMap(norm16, width, height, nativeLiveGainMap)',
    'NativeProspectiveShadingStats.none()',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1C-SHADINGPARITY1A requires METERPARITY1A marker: ' + marker)
if '-basishsm1b-meterparity1a' not in gradle:
    raise SystemExit('BASISHSM1C-SHADINGPARITY1A requires METERPARITY1A build provenance')

# Hard capture boundary: this is still one RAW and JPEG-side source rendering only.
frames = frames_path.read_text()
for marker in [
    'M9_NOHDR1A_SINGLE_FRAME_BOUNDARY',
    'frameCount = 1;',
    'throwCount = 0;',
    'IsoExpoSelector.HDR = false;',
]:
    if marker not in frames:
        raise SystemExit('BASISHSM1C-SHADINGPARITY1A NOHDR boundary missing: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()

# -----------------------------------------------------------------------------
# 1) Keep the validated native + historical basis + HSM + self-owned TC20 math.
# Add only truthful diagnostics for the existing optional pre-demosaic shading seam.
# -----------------------------------------------------------------------------
pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')

shade_pos = prospective.find('NativeProspectiveShadingStats nativeShading = applyNativeShading')
rawmat_pos = prospective.find('Mat rawMat = new Mat(')
if shade_pos < 0 or rawmat_pos < 0 or shade_pos >= rawmat_pos:
    raise SystemExit('BASISHSM1C-SHADINGPARITY1A shading is not before Bayer demosaic boundary')

prospective = replace_once(
    prospective,
    '            d.put("schema", "m9cam.renderer.basishsm.meterparity.v1a.main");',
    '            d.put("schema", "m9cam.renderer.basishsm.shadingparity.v1a.main");',
    'prospective schema')

old_diag = '            d.put("meterParityRawShadingForcedOffByCaller", true);'
new_diag = '''            d.put("meterParityRawShadingForcedOffByCaller", !applyNativeShading);
            d.put("shadingParity1A", true);
            d.put("shadingParityRequested", applyNativeShading);
            d.put("shadingParityLiveMapPresent", nativeLiveGainMap != null);
            d.put("shadingParityApplied", nativeShading.applied);
            d.put("shadingParityApplicationCount", nativeShading.applied ? 1 : 0);
            d.put("shadingParityApplicationStage", nativeShading.applied
                    ? "normalized_linear_Bayer_pre_demosaic_headroom_preserved" : "none");
            d.put("shadingParityExpectedBayerPixelCount", (long)width * (long)height);
            d.put("shadingParityCorrectedBayerPixelCount", nativeShading.correctedPixels);
            d.put("shadingParityAllBayerSitesCorrected", applyNativeShading
                    ? nativeShading.applied
                        && nativeShading.correctedPixels == (long)width * (long)height
                    : !nativeShading.applied && nativeShading.correctedPixels == 0L);
            d.put("shadingParitySelfMeterAfterShading",
                    meterParitySelfMeter && applyNativeShading && nativeShading.applied);'''
prospective = replace_once(prospective, old_diag, new_diag, 'shading diagnostics')
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

# -----------------------------------------------------------------------------
# 2) Field output is now one clean isolation: the validated self-meter path with
# physical-camera LensShadingMap OFF vs ON. The former fixed-gain control is retired.
# -----------------------------------------------------------------------------
renderer = replace_once(
    renderer,
    '// BASISHSM1B-METERPARITY1A: same-RAW BASIS_HSM fixed-vs-self-meter. Primary JPEG is already',
    '// BASISHSM1C-SHADINGPARITY1A: same-RAW BASIS_HSM self-meter shading OFF-vs-ON. Primary JPEG is already',
    'field hook comment')
renderer = replace_once(
    renderer,
    '"main_physical_2_primary_vs_basis_hsm_fixed_vs_basis_hsm_self_meter"',
    '"main_physical_2_primary_vs_basis_hsm_selfmeter_shading_off_on"',
    'comparison-set identity')

old_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_fixed_primary_gain",
                                "native_plus_historical_basis_hsm_self_meter"
                        };
                        int[] bridgeProbeModes = {3, 3};
                        boolean[] selfMeterFlags = {false, true};'''
new_arrays = '''                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_shading_off",
                                "native_plus_historical_basis_hsm_self_meter_shading_on"
                        };
                        int[] bridgeProbeModes = {3, 3};
                        boolean[] selfMeterFlags = {true, true};
                        boolean[] applyShadingFlags = {false, true};'''
renderer = replace_once(renderer, old_arrays, new_arrays, 'field output arrays')

old_loop = '''                            boolean selfMeter = selfMeterFlags[variantIndex];
                            boolean applyShading = false;'''
new_loop = '''                            boolean selfMeter = selfMeterFlags[variantIndex];
                            boolean applyShading = applyShadingFlags[variantIndex];'''
renderer = replace_once(renderer, old_loop, new_loop, 'field shading selector')

variant_old = '''                                variantDiag.put("bridgeProbeShadingForcedOff", true);
                                variantDiag.put("meterParitySelfMeterRequested", selfMeter);'''
variant_new = '''                                variantDiag.put("bridgeProbeShadingForcedOff", !applyShading);
                                variantDiag.put("meterParitySelfMeterRequested", selfMeter);
                                variantDiag.put("shadingParity1A", true);
                                variantDiag.put("shadingParityRequested", applyShading);'''
if renderer.count(variant_old) != 2:
    raise SystemExit('BASISHSM1C-SHADINGPARITY1A expected two variant diagnostic markers, got '
                     + str(renderer.count(variant_old)))
renderer = renderer.replace(variant_old, variant_new)

# No obsolete field products should survive as exact suffix/name literals.
for obsolete in [
    '"_M9_NATIVE_BASIS_HSM"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER"',
    '"native_plus_historical_basis_hsm_fixed_primary_gain"',
]:
    if obsolete in renderer:
        raise SystemExit('BASISHSM1C-SHADINGPARITY1A obsolete METERPARITY field output survived: ' + obsolete)

# Distinct provenance. Primary remains the production/frozen JPEG; these are additive test JPEGs.
gradle = gradle.replace('-basishsm1b-meterparity1a', '-basishsm1c-shadingparity1a', 1)
if '-basishsm1c-shadingparity1a' not in gradle:
    raise SystemExit('BASISHSM1C-SHADINGPARITY1A failed to set build provenance')

# Frozen photographic Primary must remain byte-identical at method source level.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
primary_after_sha = hashlib.sha256(primary_after.encode('utf-8')).hexdigest()
if primary_after_sha != primary_sha:
    raise SystemExit('BASISHSM1C-SHADINGPARITY1A changed frozen Primary renderCore: before='
                     + primary_sha + ' after=' + primary_after_sha)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9Cam BASISHSM1C-SHADINGPARITY1A applied')
print(' - frozen Primary renderCore sha256 preserved:', primary_sha)
print(' - native Camera2 + historical basis + historical HSM remains frozen')
print(' - both prospective variants self-meter with TC20')
print(' - only variable is physical-camera LensShadingMap OFF vs ON')
print(' - ON applies the existing headroom-preserving map once in normalized Bayer before demosaic')
print(' - single RAW / HDR=false / capture exposure / DNG remain frozen')
