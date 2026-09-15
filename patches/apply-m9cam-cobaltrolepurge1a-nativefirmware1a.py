#!/usr/bin/env python3
from pathlib import Path
import struct, sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-cobaltrolepurge1a-nativefirmware1a.py <PhotonCamera-root>')
root = Path(sys.argv[1])
renderer = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
mixed_asset = root / 'app/src/main/assets/m9/m9_r35_calibration.bin'
target_asset = root / 'app/src/main/assets/m9/m9_curve02_firmware.bin'
target_loader = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9TargetFirmwareCalibration.java'

if not renderer.exists(): raise SystemExit(f'missing renderer: {renderer}')
if not mixed_asset.exists(): raise SystemExit(f'missing mixed calibration asset: {mixed_asset}')

data = mixed_asset.read_bytes()
if len(data) < 2048 or data[:8] != b'M9R35CAL': raise SystemExit('unexpected m9_r35_calibration.bin format')
version, hd, sd, vd = struct.unpack_from('<4I', data, 8)
if (version, hd, sd, vd) != (1, 90, 30, 1): raise SystemExit(f'unexpected mixed calibration header {(version, hd, sd, vd)}')
expected = 8 + 16 + (4 * 9 * 8) + (2 * hd * sd * vd * 3 * 4) + 2048
if len(data) != expected: raise SystemExit(f'unexpected mixed calibration length {len(data)} != {expected}')
curve02 = data[-2048:]
target_asset.parent.mkdir(parents=True, exist_ok=True)
target_asset.write_bytes(curve02)

target_loader.parent.mkdir(parents=True, exist_ok=True)
target_loader.write_text(r'''package com.particlesdevs.photoncamera.m9.render;

import com.particlesdevs.photoncamera.app.PhotonCamera;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/** Production Leica-M9 target calibration: firmware curve02 only. */
public final class M9TargetFirmwareCalibration {
    private static final String ASSET = "m9/m9_curve02_firmware.bin";
    private static volatile M9TargetFirmwareCalibration INSTANCE;
    public final byte[] curve02;
    private M9TargetFirmwareCalibration(byte[] curve02) {
        if (curve02 == null || curve02.length != 2048) throw new IllegalArgumentException("curve02 must contain exactly 2048 bytes");
        this.curve02 = curve02;
    }
    public static M9TargetFirmwareCalibration get() throws Exception {
        M9TargetFirmwareCalibration c = INSTANCE;
        if (c != null) return c;
        synchronized (M9TargetFirmwareCalibration.class) {
            if (INSTANCE == null) INSTANCE = load();
            return INSTANCE;
        }
    }
    private static M9TargetFirmwareCalibration load() throws Exception {
        byte[] bytes;
        try (InputStream in = PhotonCamera.getResourcesStatic().getAssets().open(ASSET);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] tmp = new byte[4096]; int n;
            while ((n = in.read(tmp)) >= 0) out.write(tmp, 0, n);
            bytes = out.toByteArray();
        }
        if (bytes.length != 2048) throw new IllegalStateException("unexpected M9 firmware curve02 length: " + bytes.length);
        return new M9TargetFirmwareCalibration(bytes);
    }
}
''')

s = renderer.read_text()
def method_span(text, signature):
    start = text.index(signature); brace = text.index('{', start); depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0: return start, i + 1
    raise RuntimeError('unterminated method: ' + signature)

prod_start, prod_end = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
prod = s[prod_start:prod_end]
prod = prod.replace(
'''    // BASISHSM1P-NATIVESOURCE1A production route.
    // Photographic math is the validated 1O middle candidate exactly:
    // native SOURCECAL2A + historical basis/H25 target role + self-meter TC20 + NORM030.
    // The old Cobalt-source renderCore remains only as a dormant forensic reference.
''',
'''    // COBALTROLEPURGE1A-NATIVEFIRMWARE1A production route.
    // Architecture contract: physical-sensor Camera2/DNG SOURCECAL2A ends at the
    // common scene-referred handoff. The shared M9 target renderer is lens-independent
    // and must not consume Cobalt CM/FM/HSM or any basis derived from them.
    // Historical Cobalt probe modes remain dormant forensic code only.
''')
old_call = '''                1.0,
                true,
                3,
                true,
                false, false,
                true, 1.0,
                true, 0.30,
                1.0, false);'''
new_call = '''                1.0,
                true,
                0,
                true,
                false, false,
                true, 1.0,
                true, 0.30,
                1.0, false);'''
if old_call not in prod: raise SystemExit('production bridge mode 3 call anchor missing')
prod = prod.replace(old_call, new_call, 1)
start = prod.index('        JSONObject d = out.diagnostics;')
end_anchor = '        d.put("demosaicDiagnosticBankEnabled", DEMOSAIC_DIAGNOSTIC_BANK_ENABLED);'
end = prod.index(end_anchor, start) + len(end_anchor)
telemetry = '''        JSONObject d = out.diagnostics;
        d.put("schema", "m9cam.renderer.nativefirmware.v1a.production");
        d.put("nativeSourceProduction1A", true);
        d.put("architectureRevision", "COBALTROLEPURGE1A_NATIVEFIRMWARE1A");
        d.put("sourceTargetBoundary", "physical_sensor_SOURCECAL2A_to_common_scene_space_then_shared_M9_target");
        d.put("nativeSourceTransformApplied", true);
        d.put("sourceAdapterProvider", "active_physical_Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX");
        d.put("sourceTransformFamily", "SOURCECAL2A_CMFIX_DNG_dual_illuminant_math_CM_unchanged_FM_D50_normalized_live_neutral");
        d.put("sourceCalibrationPerPhysicalSensor", true);
        d.put("m9TargetRendererLensIndependent", true);
        d.put("cobaltRuntimeProductionDependency", false);
        d.put("cobaltSourceAdapterApplied", false);
        d.put("cobaltSourceColorMatrixApplied", false);
        d.put("cobaltSourceForwardMatrixApplied", false);
        d.put("cobaltSourceHsmRoleApplied", false);
        d.put("cobaltHueSatMapApplied", false);
        d.put("cobaltHistoricalLinearBasisApplied", false);
        d.put("historicalBasisHsmTargetBehaviorApplied", false);
        d.put("historicalBasisHsmRole", "disabled_removed_from_production");
        d.put("historicalBasisDataProvenance", "none_production");
        d.put("identityHsmApplied", true);
        d.put("m9FirmwareCurve02Retained", true);
        d.put("m9FirmwareCurve02Asset", "m9/m9_curve02_firmware.bin");
        d.put("mixedCalibrationAssetUsedByProduction", false);
        d.put("norm030ProductionApplied", true);
        d.put("norm030TargetOutsideMedianEv", 0.30);
        d.put("norm030UsesSceneBrightness", false);
        d.put("norm030UsesFinalClipFeedback", false);
        d.put("norm030UsesPrimaryFeedback", false);
        d.put("productionSelfMeter", true);
        d.put("fixedPrimaryGainReferenceRole", "diagnostic_placeholder_only_not_render_gain_when_selfMeter_true");
        d.remove("meterParityGainRatioVsPrimary");
        d.remove("meterParityGainDeltaEvVsPrimary");
        d.put("tc20DecisionSource", "native_source_identity_hsm_same_frame_tc20");
        d.put("bridgeProbeName", "production_source_only_identity_hsm");
        d.put("bridgeProbeHistoricalLinearMaxAbsDelta", 0.0);
        d.put("historicalLinearBasisDiagnosticApplied", false);
        d.put("historicalLinearBasisDerivedFromCobaltSourceProfile", false);
        d.put("basisHsm1A", false);
        d.put("basisHsmCombinedApplied", false);
        d.put("basisHsmOrdering", "not_in_production");
        d.put("basisHsmHistoricalBasisBeforeHsm", false);
        d.put("basisHsmHsmTableIdentity", "identity");
        d.put("basisHsmHsmTableHash64", "identity");
        d.put("basisHsmHsmTableLength", 0);
        d.put("mixedCalibrationAssetUsage", "none_production");
        d.put("fullColorRenderStages", "active physical Camera2 SOURCECAL2A -> common scene space -> identity HSM -> shared M9 bridge/SAT3/curve02/BT601/TG1");
        d.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene space -> shared M9 bridge -> TC20 -> SAT3 M06/M07 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
        d.put("demosaicFoundation", "DEMOSAICMHCNEUTRAL1A_FROZEN1A");
        d.put("demosaicDiagnosticBankEnabled", DEMOSAIC_DIAGNOSTIC_BANK_ENABLED);'''
prod = prod[:start] + telemetry + prod[end:]
s = s[:prod_start] + prod + s[prod_end:]

core_start, core_end = method_span(s, 'private static RenderCore renderNativeProspectiveCore(')
core = s[core_start:core_end]
old_cal = '''            // The mixed calibration asset is loaded only to retain Leica firmware curve02.
            // Cobalt ColorMatrix/ForwardMatrix/HSM components are not read into this context.
            M9R35Calibration cal = M9R35Calibration.get();
            NativeProspectiveSource nativeSource = buildNativeProspectiveSource(
                    nativeCharacteristics, nativeCaptureResult);'''
new_cal = '''            // Production bridgeProbeMode=0 loads a target-only Leica firmware asset.
            // The historical mixed Cobalt payload is instantiated only by explicit nonzero
            // forensic probe modes and is never a production dependency.
            final boolean historicalProbeCalibrationRequired = bridgeProbeMode != 0;
            final M9R35Calibration cal = historicalProbeCalibrationRequired
                    ? M9R35Calibration.get() : null;
            final byte[] firmwareCurve02 = historicalProbeCalibrationRequired
                    ? cal.curve02 : M9TargetFirmwareCalibration.get().curve02;
            NativeProspectiveSource nativeSource = buildNativeProspectiveSource(
                    nativeCharacteristics, nativeCaptureResult);'''
if old_cal not in core: raise SystemExit('mixed calibration load anchor missing')
core = core.replace(old_cal, new_cal, 1)
core = core.replace('cal.curve02', 'firmwareCurve02')
core = core.replace('? firmwareCurve02 : M9TargetFirmwareCalibration.get().curve02;', '? cal.curve02 : M9TargetFirmwareCalibration.get().curve02;', 1)
core = core.replace(
'''            if (bridgeProbeMode == 0) {
                d.put("mixedCalibrationAssetUsage", "curve02_target_component_only");
                d.put("fullColorRenderStages",
                        "native Camera2 source adapter + identity HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");''',
'''            if (bridgeProbeMode == 0) {
                d.put("mixedCalibrationAssetUsage", "none_production");
                d.put("targetCalibrationAsset", "m9/m9_curve02_firmware.bin");
                d.put("cobaltRuntimeProductionDependency", false);
                d.put("fullColorRenderStages",
                        "native Camera2 source adapter + identity HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");''', 1)
s = s[:core_start] + core + s[core_end:]
renderer.write_text(s)
print('COBALTROLEPURGE1A_NATIVEFIRMWARE1A applied')
print(f'curve02 extracted: {len(curve02)} bytes -> {target_asset}')
