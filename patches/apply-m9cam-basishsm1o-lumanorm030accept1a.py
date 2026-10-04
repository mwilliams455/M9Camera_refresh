#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1o-lumanorm030accept1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1O-LUMANORM030ACCEPT1A missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f'BASISHSM1O {label} anchor count={n}')
    return src.replace(old, new, 1)

required = [
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM020EV1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM040EV1A"',
    'boolean[] normalizeShadingLumaOutsideMedian1AFlags = {false, false, false, true, true, true};',
    'double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.0, 0.0, 0.20, 0.30, 0.40};',
    '"main_physical_2_primary_vs_basis_hsm_shading_luma_norm1a"',
    '"shadingLumaNorm1AUsesSceneBrightness", false',
    '"shadingLumaNorm1AUsesFinalClipFeedback", false',
    '"shadingLumaNorm1AUsesPrimaryFeedback", false',
]
for marker in required:
    if marker not in renderer:
        raise SystemExit('BASISHSM1O requires validated 1N marker: ' + marker)
if '-basishsm1n-shadinglumanorm1a' not in gradle:
    raise SystemExit('BASISHSM1O requires 1N build provenance')
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in frames:
        raise SystemExit('BASISHSM1O NOHDR boundary missing: ' + marker)

old_bank = '''                        // BASISHSM1N-SHADINGLUMANORM1A: same-RAW normalization test.
                        // Normalized candidates preserve the 1L map shape and chroma ratios,
                        // but choose alpha so the map's outside-center common-luma median applies
                        // at most the requested EV. This is map calibration, not scene exposure.
                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM020EV1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM040EV1A"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_shading_off",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",
                                "native_plus_historical_basis_hsm_self_meter_chroma_only_shading1a",
                                "native_plus_historical_basis_hsm_self_meter_lumanorm020ev1a",
                                "native_plus_historical_basis_hsm_self_meter_lumanorm030ev1a",
                                "native_plus_historical_basis_hsm_self_meter_lumanorm040ev1a"
                        };
                        int[] bridgeProbeModes = {3, 3, 3, 3, 3, 3};
                        boolean[] selfMeterFlags = {true, true, true, true, true, true};
                        boolean[] applyShadingFlags = {false, true, true, true, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true, true, true};
                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 1.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {false, false, false, true, true, true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.0, 0.0, 0.20, 0.30, 0.40};'''

new_bank = '''                        // BASISHSM1O-LUMANORM030ACCEPT1A: same-RAW photographic acceptance bank.
                        // Only the two physical endpoints and the validated 0.30 EV common-luma
                        // ceiling remain. No scene brightness, clipping, or primary feedback enters alpha.
                        String[] suffixes = {
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMANORM030EV1A",
                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"
                        };
                        String[] bridgeProbeNames = {
                                "native_plus_historical_basis_hsm_self_meter_shading_off",
                                "native_plus_historical_basis_hsm_self_meter_lumanorm030ev1a",
                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a"
                        };
                        int[] bridgeProbeModes = {3, 3, 3};
                        boolean[] selfMeterFlags = {true, true, true};
                        boolean[] applyShadingFlags = {false, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {false, true, false};
                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {false, true, false};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.0, 0.30, 0.0};'''

renderer = replace_once(renderer, old_bank, new_bank, 'acceptance output bank')
renderer = replace_once(
    renderer,
    '"main_physical_2_primary_vs_basis_hsm_shading_luma_norm1a"',
    '"main_physical_2_primary_vs_basis_hsm_lumanorm030_accept1a"',
    'comparison identity')

gradle = gradle.replace(
    '-basishsm1n-shadinglumanorm1a',
    '-basishsm1o-lumanorm030accept1a',
    1)
if '-basishsm1o-lumanorm030accept1a' not in gradle:
    raise SystemExit('BASISHSM1O failed build provenance')

for marker in [
    '"shadingLumaNorm1AUsesSceneBrightness", false',
    '"shadingLumaNorm1AUsesFinalClipFeedback", false',
    '"shadingLumaNorm1AUsesPrimaryFeedback", false',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1O feedback freeze missing: ' + marker)
for marker in ['frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in frames:
        raise SystemExit('BASISHSM1O NOHDR freeze missing: ' + marker)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1O-LUMANORM030ACCEPT1A applied')
print(' - same RAW outputs only: SHADING_OFF / LUMANORM030EV1A / exact SHADING_ON')
print(' - 0.30 EV is a LensShadingMap common-luma ceiling, not a scene exposure target')
print(' - 1N normalization math unchanged; only prospective bank narrowed')
print(' - no scene-luma, final-clip, primary, or HDR feedback')
print(' - Primary / TC20 / HSM / curve02 / BT601-TG1 / capture / DNG / JPEG math unchanged')
