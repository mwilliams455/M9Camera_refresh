#!/usr/bin/env python3
from pathlib import Path
import hashlib
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-bridgeprobe1a.py <PhotonCamera-root>')

root = Path(sys.argv[1]).resolve()
if not (root / 'app').is_dir():
    raise SystemExit('BRIDGEPROBE1A: not a PhotonCamera root')

renderer_path = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
gradle_path = root / 'app/build.gradle'
if not renderer_path.exists() or not gradle_path.exists():
    raise SystemExit('BRIDGEPROBE1A: assembled renderer/build.gradle missing')

renderer = renderer_path.read_text()
gradle = gradle_path.read_text()


def extract_method(src, marker):
    start = src.find(marker)
    if start < 0:
        raise SystemExit('BRIDGEPROBE1A method marker missing: ' + marker)
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('BRIDGEPROBE1A opening brace missing: ' + marker)
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
    raise SystemExit('BRIDGEPROBE1A unterminated method: ' + marker)


def replace_once(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise SystemExit(f'BRIDGEPROBE1A {label} anchor count={count}')
    return src.replace(old, new, 1)


# This experiment is allowed only after the field-validated native Camera2 path.
for marker in [
    'NATIVEAPIORDER1A_ColorSpaceTransform_copyElements_row_major',
    'physical_SENSOR_NEUTRAL_COLOR_POINT_normalized_max1_clip_only',
    'tc20DecisionSource", "frozen_primary_same_frame"',
    'prospectiveMeterRecomputed", false',
]:
    if marker not in renderer:
        raise SystemExit('BRIDGEPROBE1A requires validated v2.91 marker: ' + marker)

_, _, primary_before = extract_method(renderer, '    private static RenderCore renderCore(')
primary_sha = hashlib.sha256(primary_before.encode('utf-8')).hexdigest()

# -----------------------------------------------------------------------------
# 1) Extend ONLY the additive native prospective signature with a probe selector.
# Frozen primary renderCore is never touched.
# -----------------------------------------------------------------------------
pros_start, pros_end, prospective = extract_method(
    renderer, '    private static RenderCore renderNativeProspectiveCore(')
old_sig = '''                                         double fixedPrimaryGain,\n                                         boolean applyNativeShading) throws Exception {'''
new_sig = '''                                         double fixedPrimaryGain,\n                                         boolean applyNativeShading,\n                                         int bridgeProbeMode) throws Exception {'''
prospective = replace_once(prospective, old_sig, new_sig, 'prospective signature')

# -----------------------------------------------------------------------------
# 2) Add two scientific role probes at the existing native Camera2 -> ProPhoto boundary.
# mode 0 = current SOURCE_ONLY baseline
# mode 1 = historical Cobalt HSM only, interpolated with NATIVE scene illuminant weight
# mode 2 = explicit linear change-of-basis into the historical source ProPhoto basis
#          while retaining identity HSM and the native scene/target bridge.
# -----------------------------------------------------------------------------
old_context = '''            NativeProspectiveSource nativeSource = buildNativeProspectiveSource(\n                    nativeCharacteristics, nativeCaptureResult);\n            ColorContext ctx = nativeSource.ctx;\n            colorContextElapsedMs = (System.nanoTime() - colorContextStartedNs) / 1_000_000L;'''
new_context = '''            NativeProspectiveSource nativeSource = buildNativeProspectiveSource(\n                    nativeCharacteristics, nativeCaptureResult);\n            ColorContext ctx = nativeSource.ctx;\n\n            // BRIDGEPROBE1A: locate the missing M9 character without changing capture,\n            // exposure, shading, target bridge, SAT3, curve02, BT.601, TG1, or primary output.\n            final double[] nativeCamToPpBeforeProbe = ctx.camToPp.clone();\n            double[] bridgeProbeBasis = {\n                    1.0, 0.0, 0.0,\n                    0.0, 1.0, 0.0,\n                    0.0, 0.0, 1.0\n            };\n            double bridgeProbeHistoricalLinearMaxAbsDelta = 0.0;\n            String bridgeProbeName = "source_only";\n            boolean bridgeProbeHistoricalHsmApplied = false;\n            boolean bridgeProbeHistoricalLinearBasisApplied = false;\n\n            if (bridgeProbeMode == 1) {\n                bridgeProbeName = "native_plus_historical_hsm";\n                bridgeProbeHistoricalHsmApplied = true;\n                // Deliberately reuse ONLY the historical nonlinear HSM role. The\n                // interpolation weight remains the native Camera2-derived scene weight.\n                ctx.hsm = new double[cal.hsmA.length];\n                for (int i = 0; i < ctx.hsm.length; i++) {\n                    ctx.hsm[i] = ctx.wA * cal.hsmA[i]\n                            + (1.0 - ctx.wA) * cal.hsmD65[i];\n                }\n                ctx.hueDivisions = cal.hueDivisions;\n                ctx.satDivisions = cal.satDivisions;\n            } else if (bridgeProbeMode == 2) {\n                bridgeProbeName = "native_plus_historical_linear_basis";\n                bridgeProbeHistoricalLinearBasisApplied = true;\n                // Derive an explicit change-of-basis from the current native linear\n                // ProPhoto coordinates to the historical source-adapter ProPhoto basis.\n                // Only the historical linear camToPp role is sampled; HSM remains identity.\n                ColorContext historicalLinear = buildColorContext(neutralF, cal);\n                bridgeProbeBasis = matMul3(\n                        historicalLinear.camToPp, inverse3(nativeCamToPpBeforeProbe));\n                ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);\n                for (int i = 0; i < 9; i++) {\n                    bridgeProbeHistoricalLinearMaxAbsDelta = Math.max(\n                            bridgeProbeHistoricalLinearMaxAbsDelta,\n                            Math.abs(ctx.camToPp[i] - historicalLinear.camToPp[i]));\n                }\n            } else if (bridgeProbeMode != 0) {\n                throw new IllegalArgumentException(\n                        "BRIDGEPROBE1A unsupported mode " + bridgeProbeMode);\n            }\n            colorContextElapsedMs = (System.nanoTime() - colorContextStartedNs) / 1_000_000L;'''
prospective = replace_once(prospective, old_context, new_context, 'native color context')

# Add late diagnostic overrides just before the prospective method returns. JSONObject.put
# replaces the earlier generic NATIVEAB1A role labels, so the underlying math stays isolated.
return_anchor = '            return new RenderCore(oriented, d);'
probe_diag = '''            d.put("schema", "m9cam.renderer.bridgeprobe.v1a.main.fixedgain");\n            d.put("bridgeProbe1A", true);\n            d.put("bridgeProbeMode", bridgeProbeMode);\n            d.put("bridgeProbeName", bridgeProbeName);\n            d.put("bridgeProbeShadingApplied", nativeShading.applied);\n            d.put("bridgeProbeExposureDecision", "frozen_primary_same_frame");\n            d.put("bridgeProbeTargetBridge", "native_scene_white_existing_M9_bridge_unchanged");\n            d.put("cobaltColorMatrixApplied", false);\n            d.put("cobaltForwardMatrixApplied", false);\n            d.put("cobaltHueSatMapApplied", bridgeProbeHistoricalHsmApplied);\n            d.put("identityHsmApplied", !bridgeProbeHistoricalHsmApplied);\n            d.put("historicalLinearBasisDiagnosticApplied",\n                    bridgeProbeHistoricalLinearBasisApplied);\n            d.put("historicalLinearBasisDerivedFromCobaltSourceProfile",\n                    bridgeProbeHistoricalLinearBasisApplied);\n            d.put("bridgeProbeHistoricalLinearMaxAbsDelta",\n                    bridgeProbeHistoricalLinearMaxAbsDelta);\n            JSONArray bridgeProbeBasisRows = new JSONArray();\n            for (int r = 0; r < 3; r++) {\n                JSONArray row = new JSONArray();\n                for (int c = 0; c < 3; c++) row.put(bridgeProbeBasis[r * 3 + c]);\n                bridgeProbeBasisRows.put(row);\n            }\n            d.put("bridgeProbeBasisMatrix", bridgeProbeBasisRows);\n            d.put("hsmHueStrength", bridgeProbeHistoricalHsmApplied ? HSM_H : 0.0);\n            d.put("hsmSaturationStrength", bridgeProbeHistoricalHsmApplied ? HSM_S : 0.0);\n            d.put("hsmValueStrength", bridgeProbeHistoricalHsmApplied ? HSM_V : 0.0);\n            if (bridgeProbeMode == 0) {\n                d.put("mixedCalibrationAssetUsage", "curve02_target_component_only");\n                d.put("fullColorRenderStages",\n                        "native Camera2 source adapter + identity HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");\n            } else if (bridgeProbeMode == 1) {\n                d.put("mixedCalibrationAssetUsage",\n                        "historical_HSM_role_diagnostic_plus_curve02_target_component");\n                d.put("fullColorRenderStages",\n                        "native Camera2 source adapter + historical HSM role + existing M9 bridge/SAT3/curve02/BT601/TG1");\n            } else {\n                d.put("mixedCalibrationAssetUsage",\n                        "historical_linear_basis_role_diagnostic_plus_curve02_target_component");\n                d.put("fullColorRenderStages",\n                        "native Camera2 source adapter + explicit historical linear basis + identity HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");\n            }\n            return new RenderCore(oriented, d);'''
prospective = replace_once(prospective, return_anchor, probe_diag, 'prospective return diagnostics')
renderer = renderer[:pros_start] + prospective + renderer[pros_end:]

# -----------------------------------------------------------------------------
# 3) Replace the old SOURCE_ONLY vs SOURCE_SHADING hook with three colour-role probes.
# All three force applyShading=false so LensShadingMap cannot confound this experiment.
# -----------------------------------------------------------------------------
hook_start = renderer.find('            // NATIVEAB1A: controlled same-RAW scientific A/B.')
hook_end = renderer.find('\n            // Do not overwrite capture-time lastDiagnostics here:', hook_start)
if hook_start < 0 or hook_end < 0:
    raise SystemExit('BRIDGEPROBE1A NATIVEAB1A hook boundary missing')
hook = renderer[hook_start:hook_end]
hook = hook.replace('// NATIVEAB1A: controlled same-RAW scientific A/B. Primary JPEG is already',
                    '// BRIDGEPROBE1A: controlled same-RAW colour-role A/B. Primary JPEG is already', 1)
hook = hook.replace('"m9cam.renderer.nativeab.v1a.main.fixedgain"',
                    '"m9cam.renderer.bridgeprobe.v1a.main.fixedgain"')
hook = hook.replace('"main_physical_2_same_raw_primary_gain_source_only_vs_source_plus_shading"',
                    '"main_physical_2_same_raw_primary_gain_source_only_vs_hsm_vs_linear_basis"')

old_arrays = '''                        String[] suffixes = {\n                                "_M9_NATIVE_SOURCE_ONLY",\n                                "_M9_NATIVE_SOURCE_SHADING"\n                        };\n                        boolean[] shadingFlags = {false, true};\n                        JSONArray variants = new JSONArray();'''
new_arrays = '''                        String[] suffixes = {\n                                "_M9_NATIVE_SOURCE_ONLY",\n                                "_M9_NATIVE_HSM_ONLY",\n                                "_M9_NATIVE_BASIS_ONLY"\n                        };\n                        String[] bridgeProbeNames = {\n                                "source_only",\n                                "native_plus_historical_hsm",\n                                "native_plus_historical_linear_basis"\n                        };\n                        int[] bridgeProbeModes = {0, 1, 2};\n                        JSONArray variants = new JSONArray();'''
hook = replace_once(hook, old_arrays, new_arrays, 'hook arrays')

old_loop_vars = '''                            String suffix = suffixes[variantIndex];\n                            boolean applyShading = shadingFlags[variantIndex];'''
new_loop_vars = '''                            String suffix = suffixes[variantIndex];\n                            String bridgeProbeName = bridgeProbeNames[variantIndex];\n                            int bridgeProbeMode = bridgeProbeModes[variantIndex];\n                            boolean applyShading = false;'''
hook = replace_once(hook, old_loop_vars, new_loop_vars, 'hook loop vars')

old_call = '''                                        cameraRotation, 0.0, characteristics, physicalResult,\n                                        fixedPrimaryGain, applyShading);'''
new_call = '''                                        cameraRotation, 0.0, characteristics, physicalResult,\n                                        fixedPrimaryGain, applyShading, bridgeProbeMode);'''
hook = replace_once(hook, old_call, new_call, 'prospective call')

old_variant_success = '''                                variantDiag.put("variant",\n                                        applyShading ? "source_plus_shading" : "source_only");'''
new_variant_success = '''                                variantDiag.put("variant", bridgeProbeName);\n                                variantDiag.put("bridgeProbeMode", bridgeProbeMode);\n                                variantDiag.put("bridgeProbeShadingForcedOff", true);'''
if hook.count(old_variant_success) != 2:
    raise SystemExit('BRIDGEPROBE1A expected two original variant label anchors, got ' + str(hook.count(old_variant_success)))
hook = hook.replace(old_variant_success, new_variant_success, 1)

old_variant_fail = '''                                variantDiag.put("variant",\n                                        applyShading ? "source_plus_shading" : "source_only");'''
# It appears twice in the original hook; after replacing the success occurrence exactly one remains.
hook = replace_once(hook, old_variant_fail,
                    '''                                variantDiag.put("variant", bridgeProbeName);\n                                variantDiag.put("bridgeProbeMode", bridgeProbeMode);\n                                variantDiag.put("bridgeProbeShadingForcedOff", true);''',
                    'failure variant label')

# Make error text/provenance distinguish the new experiment while retaining primary-preserved behavior.
hook = hook.replace('NATIVEAB1A alternate JPEG save failed:',
                    'BRIDGEPROBE1A alternate JPEG save failed:')
hook = hook.replace('NATIVEAB1A primary bright-pivot replication failed',
                    'BRIDGEPROBE1A primary bright-pivot replication failed')

if '_M9_NATIVE_SOURCE_SHADING' in hook or 'source_plus_shading' in hook or 'shadingFlags' in hook:
    raise SystemExit('BRIDGEPROBE1A old shading comparison survived in output hook')
renderer = renderer[:hook_start] + hook + renderer[hook_end:]

# Distinct APK provenance without disturbing the already-validated source-cal suffixes.
if '-bridgeprobe1a' not in gradle:
    if '-nativeapiorder1a' not in gradle:
        raise SystemExit('BRIDGEPROBE1A build identity requires -nativeapiorder1a')
    gradle = gradle.replace('-nativeapiorder1a', '-nativeapiorder1a-bridgeprobe1a', 1)

# Frozen production photographic core must remain byte-identical.
_, _, primary_after = extract_method(renderer, '    private static RenderCore renderCore(')
primary_after_sha = hashlib.sha256(primary_after.encode('utf-8')).hexdigest()
if primary_after_sha != primary_sha:
    raise SystemExit('BRIDGEPROBE1A changed frozen primary renderCore: before=' +
                     primary_sha + ' after=' + primary_after_sha)

renderer_path.write_text(renderer)
gradle_path.write_text(gradle)

print('M9 BRIDGEPROBE1A applied')
print(' - frozen primary JPEG/renderCore preserved:', primary_sha)
print(' - SOURCE_ONLY remains current validated native Camera2 baseline')
print(' - HSM_ONLY reuses historical HSM role only, interpolated by native scene weight')
print(' - BASIS_ONLY applies explicit historical linear-basis diagnostic with identity HSM')
print(' - all BRIDGEPROBE outputs force LensShadingMap OFF and reuse primary gain')
print(' - no capture/exposure/HDR/target-bridge/SAT3/curve02/BT601/TG1 changes')
