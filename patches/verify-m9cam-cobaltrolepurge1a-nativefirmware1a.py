#!/usr/bin/env python3
from pathlib import Path
import hashlib, struct, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: verify-m9cam-cobaltrolepurge1a-nativefirmware1a.py <PhotonCamera-root>')
root = Path(sys.argv[1])
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
loader = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9TargetFirmwareCalibration.java'
mixed = root / 'app/src/main/assets/m9/m9_r35_calibration.bin'
target = root / 'app/src/main/assets/m9/m9_curve02_firmware.bin'
for p in (renderer, loader, mixed, target):
    if not p.exists(): raise SystemExit('missing required file: ' + str(p))
s = renderer.read_text()

def method(text, signature):
    start = text.index(signature); brace = text.index('{', start); depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return text[start:i+1]
    raise RuntimeError('unterminated method')

prod = method(s, 'private static RenderCore renderNativeSourceProduction1P(')
core = method(s, 'private static RenderCore renderNativeProspectiveCore(')
checks = {
    'production_schema': 'm9cam.renderer.nativefirmware.v1a.production' in prod,
    'architecture_revision': 'COBALTROLEPURGE1A_NATIVEFIRMWARE1A' in prod,
    'production_mode0': '                0,\n                true,\n                false, false,' in prod,
    'production_no_mode3': '                3,\n                true,\n                false, false,' not in prod,
    'production_no_basishsm_pipeline': 'BASISHSM1A historical working-basis' not in prod,
    'production_cobalt_false': 'd.put("cobaltRuntimeProductionDependency", false);' in prod,
    'production_hsm_false': 'd.put("cobaltHueSatMapApplied", false);' in prod,
    'production_basis_false': 'd.put("cobaltHistoricalLinearBasisApplied", false);' in prod,
    'production_identity_hsm': 'd.put("identityHsmApplied", true);' in prod,
    'lens_independent_target': 'd.put("m9TargetRendererLensIndependent", true);' in prod,
    'per_sensor_source': 'd.put("sourceCalibrationPerPhysicalSensor", true);' in prod,
    'production_target_asset_declared': 'm9/m9_curve02_firmware.bin' in prod,
    'mode0_does_not_load_mixed': 'historicalProbeCalibrationRequired = bridgeProbeMode != 0' in core,
    'mode0_target_loader': 'M9TargetFirmwareCalibration.get().curve02' in core,
    'historical_curve_branch_valid': '? cal.curve02 : M9TargetFirmwareCalibration.get().curve02;' in core,
    'no_self_referential_curve_decl': '? firmwareCurve02 : M9TargetFirmwareCalibration.get().curve02;' not in core,
    'core_curve_variable': 'firmwareCurve02' in core,
    'sourcecal_camera2': 'buildNativeProspectiveSource(' in core,
    'native_scene_math': 'Converter.calculateCameraToXYZD50Transform' in s,
    'm9_bridge_retained': 'ctx.ppToM9' in core,
    'sat3_retained': 'SAT3' in core,
    'bt601_retained': 'BT601' in core,
    'cfa_generic_retained': 'demosaicMhcBayer' in core,
    'cfa_rggb_legacy_retained': 'demosaicMhcRggb' in core,
}
failed = [k for k,v in checks.items() if not v]
if failed:
    for k in failed: print('FAIL', k)
    raise SystemExit('COBALTROLEPURGE verifier failed')

mix = mixed.read_bytes(); tgt = target.read_bytes()
version, hd, sd, vd = struct.unpack_from('<4I', mix, 8)
expected = 8 + 16 + (4*9*8) + (2*hd*sd*vd*3*4) + 2048
if mix[:8] != b'M9R35CAL' or (version,hd,sd,vd)!=(1,90,30,1) or len(mix)!=expected:
    raise SystemExit('mixed asset structural validation failed')
if len(tgt) != 2048 or tgt != mix[-2048:]:
    raise SystemExit('target-only curve02 is not byte-exact tail of frozen asset')
ls = loader.read_text()
if 'm9/m9_curve02_firmware.bin' not in ls or 'M9R35Calibration' in ls or '2048' not in ls:
    raise SystemExit('target loader architecture invalid')

print('COBALTROLEPURGE1A_NATIVEFIRMWARE1A VERIFY PASS')
for k in checks: print('PASS', k)
print('curve02_sha256', hashlib.sha256(tgt).hexdigest())
print('mixed_asset_loaded_by_production', False)
print('production_cobalt_basis_hsm', False)
print('production_source_calibration', 'active physical Camera2/DNG SOURCECAL2A')
print('production_target', 'shared lens-independent M9 firmware renderer')
