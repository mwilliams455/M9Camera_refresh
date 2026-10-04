#!/usr/bin/env python3
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-m9sensortarget1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit('M9SENSORTARGET1A missing assembled renderer')
s = p.read_text()


def method_span(text, signature):
    start = text.find(signature)
    if start < 0:
        raise SystemExit('M9SENSORTARGET1A method missing: ' + signature)
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('M9SENSORTARGET1A opening brace missing: ' + signature)
    depth = 0
    state = 'code'
    quote = ''
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ''
        if state == 'line':
            if ch == '\n': state = 'code'
        elif state == 'block':
            if ch == '*' and nxt == '/': state = 'code'; i += 1
        elif state == 'string':
            if escape: escape = False
            elif ch == '\\': escape = True
            elif ch == quote: state = 'code'
        else:
            if ch == '/' and nxt == '/': state = 'line'; i += 1
            elif ch == '/' and nxt == '*': state = 'block'; i += 1
            elif ch in ('"', "'"): state = 'string'; quote = ch; escape = False
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('M9SENSORTARGET1A unterminated method: ' + signature)

# This is intentionally a validation candidate, not a Cobalt purge. Historical
# Cobalt assets and forensic modes remain in the tree. Production must instead be:
# physical sensor Camera2/DNG -> XYZ D50 -> recovered M9 virtual sensor ->
# identity HSM -> TC20/TONEBOUND -> firmware SAT2 M04/M05 -> curve02 -> BT601 -> TG1.

required = [
    'private static NativeProspectiveSource buildNativeProspectiveSource(',
    'Converter.calculateCameraToXYZD50Transform(',
    'ctx.m9cm = interp9(M9_CM_A, M9_CM_D65, ctx.wA);',
    'final boolean historicalProbeCalibrationRequired = bridgeProbeMode != 0;',
    'M9TargetFirmwareCalibration.get().curve02',
    'final int nativeSaturationMode1A =',
]
for token in required:
    if token not in s:
        raise SystemExit('M9SENSORTARGET1A required sensor/firmware anchor missing: ' + token)

# Runtime invariant helpers. These verify the actual context used by ordinary
# bridgeProbeMode=0 rendering rather than trusting sidecar labels alone.
insert_at = s.find('    private static RenderCore renderNativeSourceProduction1P(')
if insert_at < 0:
    raise SystemExit('M9SENSORTARGET1A production method insertion anchor missing')
helpers = r'''
    private static void m9SensorTarget1AAssertMatrix(
            String name, double[] actual, double[] expected, double tolerance) {
        if (actual == null || expected == null || actual.length != 9 || expected.length != 9) {
            throw new IllegalStateException("M9SENSORTARGET1A invalid matrix " + name);
        }
        double maxAbs = 0.0;
        for (int i = 0; i < 9; i++) {
            if (!Double.isFinite(actual[i]) || !Double.isFinite(expected[i])) {
                throw new IllegalStateException("M9SENSORTARGET1A non-finite matrix " + name);
            }
            maxAbs = Math.max(maxAbs, Math.abs(actual[i] - expected[i]));
        }
        if (maxAbs > tolerance) {
            throw new IllegalStateException(
                    "M9SENSORTARGET1A matrix mismatch " + name + " maxAbs=" + maxAbs);
        }
    }

    private static void m9SensorTarget1AAssertProductionContext(
            NativeProspectiveSource source,
            ColorContext ctx,
            M9R35Calibration historicalCalibration,
            int bridgeProbeMode) {
        if (bridgeProbeMode != 0) {
            throw new IllegalStateException(
                    "M9SENSORTARGET1A production requires bridgeProbeMode=0, got " + bridgeProbeMode);
        }
        if (historicalCalibration != null) {
            throw new IllegalStateException(
                    "M9SENSORTARGET1A historical Cobalt calibration reached production context");
        }
        if (source == null || source.sensorToXyzD50 == null || source.sensorToXyzD50.length != 9) {
            throw new IllegalStateException(
                    "M9SENSORTARGET1A missing active physical sensor -> XYZ D50 transform");
        }
        if (ctx == null || ctx.hsm == null || ctx.hueDivisions != 2 || ctx.satDivisions != 2
                || ctx.hsm.length != 12) {
            throw new IllegalStateException("M9SENSORTARGET1A HSM must be topology-only 2x2 identity");
        }
        for (int i = 0; i < ctx.hsm.length; i += 3) {
            if (Math.abs(ctx.hsm[i]) > 1.0e-12
                    || Math.abs(ctx.hsm[i + 1] - 1.0) > 1.0e-12
                    || Math.abs(ctx.hsm[i + 2] - 1.0) > 1.0e-12) {
                throw new IllegalStateException("M9SENSORTARGET1A non-identity HSM reached production");
            }
        }

        // Prove the source side is derived only from the active camera's Camera2/DNG
        // sensor->XYZ D50 transform, not a historical Xiaomi/Cobalt target basis.
        double[] expectedCameraToPp = matMul3(
                XYZ_TO_PP, nativeProspectiveDouble(source.sensorToXyzD50));
        m9SensorTarget1AAssertMatrix("active_sensor_to_common_scene", ctx.camToPp,
                expectedCameraToPp, 5.0e-6);

        // Prove the target side is the recovered Leica M9 sensor calibration model.
        double[] expectedM9Cm = interp9(M9_CM_A, M9_CM_D65, ctx.wA);
        m9SensorTarget1AAssertMatrix("M9_A_D65_interpolated_sensor_matrix", ctx.m9cm,
                expectedM9Cm, 1.0e-12);
        double[] expectedPpToM9Unnormalized = matMul3(
                expectedM9Cm, matMul3(ctx.adapt50ToScene, PP_TO_XYZ));
        double[] expectedPpToM9 = new double[9];
        for (int row = 0; row < 3; row++) {
            double den = ctx.mwhite[row];
            if (!Double.isFinite(den) || den <= 0.0) {
                throw new IllegalStateException("M9SENSORTARGET1A invalid M9 white normalization");
            }
            int base = row * 3;
            expectedPpToM9[base] = expectedPpToM9Unnormalized[base] / den;
            expectedPpToM9[base + 1] = expectedPpToM9Unnormalized[base + 1] / den;
            expectedPpToM9[base + 2] = expectedPpToM9Unnormalized[base + 2] / den;
        }
        m9SensorTarget1AAssertMatrix("common_scene_to_M9_virtual_sensor", ctx.ppToM9,
                expectedPpToM9, 1.0e-12);
    }

'''
s = s[:insert_at] + helpers + s[insert_at:]

# Enforce the invariant in the actual core after the active source context has
# been built and before any target rendering can consume it. Match only the
# context assignment so later diagnostic/timing insertions cannot invalidate the patch.
cs, ce = method_span(s, 'private static RenderCore renderNativeProspectiveCore(')
core = s[cs:ce]
context_matches = list(re.finditer(r'(?m)^(\s*)ColorContext\s+ctx\s*=\s*nativeSource\.ctx\s*;\s*$', core))
if len(context_matches) != 1:
    occurrences = [m.start() for m in re.finditer(r'nativeSource\.ctx', core)]
    raise SystemExit('M9SENSORTARGET1A context assignment matches=' + str(len(context_matches))
                     + ' nativeSource.ctx occurrences=' + str(occurrences))
m = context_matches[0]
indent = m.group(1)
insertion = m.group(0) + '\n' + indent + '''if (bridgeProbeMode == 0) {
''' + indent + '''    m9SensorTarget1AAssertProductionContext(
''' + indent + '''            nativeSource, ctx, cal, bridgeProbeMode);
''' + indent + '''}'''
core = core[:m.start()] + insertion + core[m.end():]

diag_anchor = '                d.put("targetCalibrationAsset", "m9/m9_curve02_firmware.bin");'
if core.count(diag_anchor) != 1:
    raise SystemExit('M9SENSORTARGET1A target calibration diagnostic anchor count=' + str(core.count(diag_anchor)))
core = core.replace(diag_anchor, diag_anchor + '''
                d.put("m9SensorTarget1ARuntimeVerified", true);
                d.put("m9SensorTarget1ACommonScene", "XYZ_D50_from_active_physical_Camera2_DNG");
                d.put("m9SensorTarget1ATarget", "Leica_M9_recovered_sensor_calibration_A_D65");
                d.put("m9SensorTarget1AHsm", "identity_no_Adobe_HSM_target_stage");
                d.put("m9SensorTarget1AHistoricalCobaltCalibrationLoaded", false);
                d.put("m9SensorTarget1AHistoricalTargetInputApplied", false);''', 1)
s = s[:cs] + core + s[ce:]

# Production must be mode 0. Make a future accidental mode switch fail at runtime
# even if telemetry is edited to claim otherwise.
ps, pe = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
prod = s[ps:pe]
ret = prod.rfind('        return out;')
if ret < 0:
    raise SystemExit('M9SENSORTARGET1A production return anchor missing')
telemetry = '''        if (!out.diagnostics.optBoolean("m9SensorTarget1ARuntimeVerified", false)) {
            throw new IllegalStateException(
                    "M9SENSORTARGET1A production did not traverse verified sensor-derived M9 path");
        }
        d.put("architectureRevision", "M9SENSORTARGET1A_TARGETDIRECT1A_SAT2STANDARD1B_TONEBOUND050");
        d.put("m9SensorTarget1A", true);
        d.put("m9SensorTarget1ATestPhase", "parallel_validation_Cobalt_assets_retained_but_not_consumed");
        d.put("m9SensorTarget1ASourceAuthority", "active_physical_Camera2_DNG_matrices_and_live_neutral");
        d.put("m9SensorTarget1ACommonSceneAuthority", "XYZ_D50");
        d.put("m9SensorTarget1ATargetAuthority", "recovered_Leica_M9_sensor_calibration_A_D65_plus_firmware_render_states");
        d.put("m9SensorTarget1ACobaltAssetRetainedForControl", true);
        d.put("m9SensorTarget1ACobaltAssetUsedByRender", false);
        d.put("m9SensorTarget1ATargetInputAdapterUsed", false);
        d.put("m9SensorTarget1AHsmApplied", false);
        d.put("m9SensorTarget1AFirmwareSaturation", "SAT2_M04_M05_native_mode9");
        d.put("m9SensorTarget1AFirmwareCurve", "curve02");
        d.put("fullColorRenderStages", "active physical Camera2/DNG sensor -> XYZ D50 common scene -> recovered M9 A/D65 virtual sensor -> identity HSM -> TC20/TONEBOUND050 -> SAT2 M04/M05 native mode9 -> curve02 -> exact BT601 4:2:2 -> TG1");
        d.put("pipeline", "physical RAW/CFA/black/white + physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active Camera2/DNG dual-illuminant sensor calibration -> XYZ D50 -> recovered Leica M9 sensor calibration -> TC20/TONEBOUND050 -> SAT2 M04/M05 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
'''
prod = prod[:ret] + telemetry + prod[ret:]
s = s[:ps] + prod + s[pe:]

p.write_text(s)
print('M9SENSORTARGET1A applied')
print('production source: active physical Camera2/DNG -> XYZ D50')
print('production target: recovered Leica M9 A/D65 sensor calibration')
print('historical Cobalt asset: retained, not consumed by production test')
print('HSM: identity; firmware SAT2 native mode 9 retained; tone/exposure untouched')