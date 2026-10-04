#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-basishsm1m-shadingalphasweep1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
frames_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/FrameNumberSelector.java'
for p in (renderer_path, gradle_path, frames_path):
    if not p.exists():
        raise SystemExit('BASISHSM1M-SHADINGALPHASWEEP1A missing: ' + str(p))

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()
frames = frames_path.read_text()

def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BASISHSM1M method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BASISHSM1M opening brace missing: ' + marker)
    depth = 0
    i = brace
    state = 'code'
    quote = ''
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i+1] if i+1 < len(src) else ''
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
                if depth == 0:
                    return start, i + 1, src[start:i+1]
        i += 1
    raise SystemExit('BASISHSM1M unterminated method: ' + marker)

def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise SystemExit(f'BASISHSM1M {label} anchor count={n}')
    return src.replace(old, new, 1)

# Require the validated 1L decomposition architecture and NOHDR capture boundary.
for marker in [
    'm9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main',
    'm9cam.renderer.shadinglumadecomp.v1a',
    'private static JSONObject shadingLumaDecomp1AAudit(',
    'private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A"',
    '"_M9_NATIVE_BASIS_HSM_SELFMETER_PARTIAL_LUMA_SHADING1A"',
    'double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.5};',
]:
    if marker not in renderer:
        raise SystemExit('BASISHSM1M requires validated 1L marker: ' + marker)
if '-basishsm1l-shadinglumadecomp1a' not in gradle:
    raise SystemExit('BASISHSM1M requires 1L build provenance')
for marker in ['M9_NOHDR1A_SINGLE_FRAME_BOUNDARY', 'frameCount = 1;', 'throwCount = 0;', 'IsoExpoSelector.HDR = false;']:
    if marker not in frames:
        raise SystemExit('BASISHSM1M NOHDR boundary missing: ' + marker)

# Freeze the photographic and decomposition math. 1M may change only the prospective
# output bank / labels and build provenance.
frozen_markers = {
    'primary': '    private static RenderCore renderCore(',
    'prospective_core': '    private static RenderCore renderNativeProspectiveCore(',
    'full_shading': '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMap(',
    'decomp_shading': '    private static NativeProspectiveShadingStats applyNativeProspectiveGainMapLumaDecomp1A(',
    'decomp_audit': '    private static JSONObject shadingLumaDecomp1AAudit(',
    'residual': '    private static JSONObject rawShadingResidualAudit1A(',
    'tail': '    private static ShadedTailAudit1AStats shadedTailAudit1A(',
    'clip': '    private static JSONObject finalClipAudit1A(',
    'spatial': '    private static JSONObject shadedTailSpatialAudit1A(',
}
frozen_sha = {}
for k, marker in frozen_markers.items():
    _, _, method = extract_method(renderer, marker)
    frozen_sha[k] = hashlib.sha256(method.encode()).hexdigest()

old_arrays = '''                        String[] suffixes = {\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_PARTIAL_LUMA_SHADING1A"\n                        };\n                        String[] bridgeProbeNames = {\n                                "native_plus_historical_basis_hsm_self_meter_shading_off",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",\n                                "native_plus_historical_basis_hsm_self_meter_chroma_only_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_partial_luma_shading1a"\n                        };\n                        int[] bridgeProbeModes = {3, 3, 3, 3};\n                        boolean[] selfMeterFlags = {true, true, true, true};\n                        boolean[] applyShadingFlags = {false, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, false, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false};\n                        boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true};\n                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.5};'''

new_arrays = '''                        // BASISHSM1M-SHADINGALPHASWEEP1A: diagnostic same-RAW bank only.\n                        // OFF and exact full physical ON are endpoints. The remaining outputs\n                        // preserve physical per-channel shading ratios while varying only the\n                        // common geometric-mean luminance gain authority.\n                        String[] suffixes = {\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_OFF",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_SHADING_ON_UNGUARDED1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_CHROMA_ONLY_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA025_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA040_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA055_SHADING1A",\n                                "_M9_NATIVE_BASIS_HSM_SELFMETER_LUMA070_SHADING1A"\n                        };\n                        String[] bridgeProbeNames = {\n                                "native_plus_historical_basis_hsm_self_meter_shading_off",\n                                "native_plus_historical_basis_hsm_self_meter_shading_on_unguarded1a",\n                                "native_plus_historical_basis_hsm_self_meter_chroma_only_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma025_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma040_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma055_shading1a",\n                                "native_plus_historical_basis_hsm_self_meter_luma070_shading1a"\n                        };\n                        int[] bridgeProbeModes = {3, 3, 3, 3, 3, 3, 3};\n                        boolean[] selfMeterFlags = {true, true, true, true, true, true, true};\n                        boolean[] applyShadingFlags = {false, true, true, true, true, true, true};\n                        boolean[] applyShadedGuard1AFlags = {false, false, false, false, false, false, false};\n                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false, false, false, false, false};\n                        boolean[] applyShadingLumaDecomp1AFlags = {false, false, true, true, true, true, true};\n                        double[] shadingLumaAuthorityAlphaFlags = {0.0, 1.0, 0.0, 0.25, 0.40, 0.55, 0.70};'''

renderer = replace_once(renderer, old_arrays, new_arrays, 'alpha sweep output bank')
renderer = replace_once(
    renderer,
    '"main_physical_2_primary_vs_basis_hsm_shading_luma_decomp1a"',
    '"main_physical_2_primary_vs_basis_hsm_shading_alpha_sweep1a"',
    'comparison identity')

gradle = gradle.replace('-basishsm1l-shadinglumadecomp1a', '-basishsm1m-shadingalphasweep1a', 1)
if '-basishsm1m-shadingalphasweep1a' not in gradle:
    raise SystemExit('BASISHSM1M failed build provenance')

# Methods must remain byte-identical. The output bank lives outside these methods.
for k, marker in frozen_markers.items():
    _, _, method = extract_method(renderer, marker)
    if hashlib.sha256(method.encode()).hexdigest() != frozen_sha[k]:
        raise SystemExit('BASISHSM1M changed frozen method: ' + k)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)
print('M9Cam BASISHSM1M-SHADINGALPHASWEEP1A applied')
print(' - same RAW endpoints: SHADING_OFF and exact full SHADING_ON retained')
print(' - alpha candidates: 0.00, 0.25, 0.40, 0.55, 0.70; full physical ON is alpha=1 endpoint')
print(' - only common geometric-mean luminance authority varies between decomposed candidates')
print(' - physical per-channel chroma ratios remain governed by the validated 1L decomposition')
print(' - Primary / prospective core / TC20 / HSM / tone / DNG / capture / JPEG math byte-frozen')
print(' - global SHADEDGUARD/CAP20 outputs remain disabled')
print(' - single RAW / HDR=false boundary preserved')
