#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-targethsm1a-rescue.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit('TARGETINPUTADAPTER1A missing renderer')
s = p.read_text()

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'TARGETINPUTADAPTER1A {label}: expected 1 anchor, found {n}')
    s = s.replace(old, new, 1)

def method_span(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0; state = 'code'; quote = ''; escape = False; i = brace
    while i < len(text):
        ch = text[i]; nxt = text[i+1] if i+1 < len(text) else ''
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
            elif ch in ('"', "'"): state = 'string'; quote = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('TARGETINPUTADAPTER1A unterminated method')

# Frozen 15U metadata is used only to reconstruct the historical target-domain delta.
const_anchor = '    private static final double[] XYZ_TO_PP = inverse3(PP_TO_XYZ);\n'
const_insert = '''

    // TARGETINPUTADAPTER1A: frozen Xiaomi 15 Ultra native Camera2 characterization.
    // This is a historical target-domain reference only. It is never used as the
    // active phone's source calibration.
    private static final double[] TARGETINPUT15_CAL1 = {
            1.03125, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.015625
    };
    private static final double[] TARGETINPUT15_CAL2 = TARGETINPUT15_CAL1.clone();
    private static final double[] TARGETINPUT15_CM1 = {
            0.8359375, -0.171875, -0.1328125,
            -0.46875, 1.3984375, 0.046875,
            -0.0859375, 0.3359375, 0.40625
    };
    private static final double[] TARGETINPUT15_CM2 = {
            1.28125, -0.484375, -0.2265625,
            -0.5859375, 1.59375, 0.140625,
            -0.046875, 0.1796875, 0.703125
    };
    // Photon Converter.normalizeFM() result for the 15U main ForwardMatrix.
    private static final double[] TARGETINPUT15_NFM1 = {
            0.63496098, 0.10974634, 0.21949268,
            0.21875, 0.7578125, 0.0234375,
            -0.03891038, -0.45136038, 1.31517075
    };
    private static final double[] TARGETINPUT15_NFM2 = TARGETINPUT15_NFM1.clone();
'''
once(const_anchor, const_anchor + const_insert, 'reference constants')

helper_anchor = '    private static final class NativeProspectiveSource {\n'
helper = '''    private static final class TargetInputAdapter1A {
        final double[] sceneDomainBasis;
        final double reference15Factor;
        final ColorContext historical15;
        TargetInputAdapter1A(double[] sceneDomainBasis, double reference15Factor,
                             ColorContext historical15) {
            this.sceneDomainBasis = sceneDomainBasis;
            this.reference15Factor = reference15Factor;
            this.historical15 = historical15;
        }
    }

    private static TargetInputAdapter1A buildTargetInputAdapter1A(
            NativeProspectiveSource activeSource, M9R35Calibration historicalCal) {
        if (activeSource == null || historicalCal == null) {
            throw new IllegalArgumentException("TARGETINPUTADAPTER1A missing source/calibration");
        }
        double[] sceneXy = {activeSource.sceneX, activeSource.sceneY};
        double sceneCct = cctFromXy(sceneXy);
        double referenceFactor;
        if (sceneCct <= 2856.0) referenceFactor = 1.0;
        else if (sceneCct >= 6504.0) referenceFactor = 0.0;
        else referenceFactor = (1.0 / sceneCct - 1.0 / 6504.0)
                / (1.0 / 2856.0 - 1.0 / 6504.0);
        referenceFactor = clamp(referenceFactor, 0.0, 1.0);

        double[] xyzToCamera1 = matMul3(TARGETINPUT15_CAL1, TARGETINPUT15_CM1);
        double[] xyzToCamera2 = matMul3(TARGETINPUT15_CAL2, TARGETINPUT15_CM2);
        double[] xyzToCamera = new double[9];
        for (int i = 0; i < 9; i++) {
            xyzToCamera[i] = (1.0 - referenceFactor) * xyzToCamera1[i]
                    + referenceFactor * xyzToCamera2[i];
        }
        double[] neutralD = matVec3(xyzToCamera, xyToXyz(sceneXy));
        double neutralMax = Math.max(neutralD[0], Math.max(neutralD[1], neutralD[2]));
        if (!Double.isFinite(neutralMax) || neutralMax <= 1.0e-12) {
            throw new IllegalStateException("TARGETINPUTADAPTER1A invalid reference neutral");
        }
        float[] referenceNeutral = new float[3];
        for (int i = 0; i < 3; i++) {
            double q = neutralD[i] / neutralMax;
            if (!Double.isFinite(q) || q <= 0.0) {
                throw new IllegalStateException("TARGETINPUTADAPTER1A invalid neutral channel " + i);
            }
            referenceNeutral[i] = (float)q;
        }

        double[] referenceCal = new double[9];
        double[] referenceFm = new double[9];
        for (int i = 0; i < 9; i++) {
            referenceCal[i] = (1.0 - referenceFactor) * TARGETINPUT15_CAL1[i]
                    + referenceFactor * TARGETINPUT15_CAL2[i];
            referenceFm[i] = (1.0 - referenceFactor) * TARGETINPUT15_NFM1[i]
                    + referenceFactor * TARGETINPUT15_NFM2[i];
        }
        double[] inverseReferenceCal = inverse3(referenceCal);
        double[] calibratedNeutral = matVec3(inverseReferenceCal,
                new double[]{referenceNeutral[0], referenceNeutral[1], referenceNeutral[2]});
        double calibratedMax = Math.max(calibratedNeutral[0],
                Math.max(calibratedNeutral[1], calibratedNeutral[2]));
        if (!Double.isFinite(calibratedMax) || calibratedMax <= 1.0e-12) {
            throw new IllegalStateException("TARGETINPUTADAPTER1A invalid calibrated neutral");
        }
        double[] whiteScale = {
                calibratedMax / calibratedNeutral[0], 0.0, 0.0,
                0.0, calibratedMax / calibratedNeutral[1], 0.0,
                0.0, 0.0, calibratedMax / calibratedNeutral[2]
        };
        double[] reference15SensorToXyzD50 = matMul3(referenceFm,
                matMul3(whiteScale, inverseReferenceCal));
        double[] reference15NativeCamToPp = matMul3(XYZ_TO_PP, reference15SensorToXyzD50);

        ColorContext historical15 = buildColorContext(referenceNeutral, historicalCal);
        double[] sceneDomainBasis = matMul3(historical15.camToPp,
                inverse3(reference15NativeCamToPp));
        return new TargetInputAdapter1A(sceneDomainBasis, referenceFactor, historical15);
    }

    private static double maxAbsDeltaIdentity3(double[] m) {
        double max = 0.0;
        for (int i = 0; i < 9; i++) {
            double id = (i == 0 || i == 4 || i == 8) ? 1.0 : 0.0;
            max = Math.max(max, Math.abs(m[i] - id));
        }
        return max;
    }

'''
once(helper_anchor, helper + helper_anchor, 'helper')

once('''            boolean bridgeProbeHistoricalHsmApplied = false;
            boolean bridgeProbeHistoricalLinearBasisApplied = false;
''', '''            boolean bridgeProbeHistoricalHsmApplied = false;
            boolean bridgeProbeHistoricalLinearBasisApplied = false;
            boolean targetInputAdapter1AApplied = false;
            double targetInputAdapterReference15Factor = Double.NaN;
            double targetInputAdapterHistorical15Cct = Double.NaN;
            double targetInputAdapterHistorical15WA = Double.NaN;
            double targetInputAdapterBasisMaxAbsFromIdentity = Double.NaN;
''', 'core state')

once('''            } else if (bridgeProbeMode != 0) {
                throw new IllegalArgumentException(
                        "BASISHSM1A unsupported mode " + bridgeProbeMode);
            }
''', '''            } else if (bridgeProbeMode == 4) {
                bridgeProbeName = "native_plus_target_input_adapter1a_historical_hsm";
                bridgeProbeHistoricalLinearBasisApplied = true;
                bridgeProbeHistoricalHsmApplied = true;
                targetInputAdapter1AApplied = true;

                // Preserve the active sensor transform. Apply only the historical
                // scene-domain delta T(scene)=C15_historical*inverse(N15_native).
                TargetInputAdapter1A targetInput = buildTargetInputAdapter1A(nativeSource, cal);
                bridgeProbeBasis = targetInput.sceneDomainBasis;
                ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);
                targetInputAdapterReference15Factor = targetInput.reference15Factor;
                targetInputAdapterHistorical15Cct = targetInput.historical15.cct;
                targetInputAdapterHistorical15WA = targetInput.historical15.wA;
                targetInputAdapterBasisMaxAbsFromIdentity = maxAbsDeltaIdentity3(bridgeProbeBasis);

                ctx.hsm = new double[cal.hsmA.length];
                for (int i = 0; i < ctx.hsm.length; i++) {
                    ctx.hsm[i] = targetInput.historical15.wA * cal.hsmA[i]
                            + (1.0 - targetInput.historical15.wA) * cal.hsmD65[i];
                }
                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
            } else if (bridgeProbeMode != 0) {
                throw new IllegalArgumentException(
                        "BASISHSM1A unsupported mode " + bridgeProbeMode);
            }
''', 'mode4')

once('d.put("basisHsmCombinedApplied", bridgeProbeMode == 3);',
     'd.put("basisHsmCombinedApplied", bridgeProbeMode == 3 || bridgeProbeMode == 4);', 'combined diag')
once('''                    bridgeProbeMode == 3 ? "historical_linear_basis_then_historical_HSM"
                            : "source_only_identity_HSM");''',
     '''                    bridgeProbeMode == 4 ? "target_input_adapter1a_then_historical_HSM"
                            : bridgeProbeMode == 3 ? "historical_linear_basis_then_historical_HSM"
                            : "source_only_identity_HSM");''', 'ordering diag')
once('d.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeMode == 3);',
     'd.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeMode == 3 || bridgeProbeMode == 4);', 'basis diag')
once('''                            ? "cal.hsmA_plus_cal.hsmD65_interpolated_by_native_wA"
                            : "identity");''',
     '''                            ? (bridgeProbeMode == 4
                                    ? "cal.hsmA_plus_cal.hsmD65_interpolated_by_reference15_historical_wA"
                                    : "cal.hsmA_plus_cal.hsmD65_interpolated_by_native_wA")
                            : "identity");''', 'hsm diag')
once('''            d.put("schema", "m9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main");
            d.put("basisHsm1A", true);
''', '''            d.put("targetInputAdapter1AApplied", targetInputAdapter1AApplied);
            d.put("targetInputAdapterReference15Factor",
                    Double.isFinite(targetInputAdapterReference15Factor) ? targetInputAdapterReference15Factor : JSONObject.NULL);
            d.put("targetInputAdapterHistorical15Cct",
                    Double.isFinite(targetInputAdapterHistorical15Cct) ? targetInputAdapterHistorical15Cct : JSONObject.NULL);
            d.put("targetInputAdapterHistorical15WA",
                    Double.isFinite(targetInputAdapterHistorical15WA) ? targetInputAdapterHistorical15WA : JSONObject.NULL);
            d.put("targetInputAdapterBasisMaxAbsFromIdentity",
                    Double.isFinite(targetInputAdapterBasisMaxAbsFromIdentity) ? targetInputAdapterBasisMaxAbsFromIdentity : JSONObject.NULL);
            d.put("schema", "m9cam.renderer.basishsm.shadinglumadecomp.finalclipaudit.v1a.main");
            d.put("basisHsm1A", true);
''', 'adapter diagnostics')
once('''            if (bridgeProbeMode == 3) {
                d.put("mixedCalibrationAssetUsage",
                        "historical_linear_basis_plus_HSM_role_diagnostic_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "native Camera2 source adapter + historical linear basis -> historical HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");
            }
''', '''            if (bridgeProbeMode == 4) {
                d.put("mixedCalibrationAssetUsage",
                        "scene_domain_target_input_adapter_plus_HSM_target_role_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "active physical Camera2 SOURCECAL2A -> common scene ProPhoto -> T(scene)=C15*inverse(N15) -> historical H25/HSM -> existing M9 bridge/SAT3/curve02/BT601/TG1");
            } else if (bridgeProbeMode == 3) {
                d.put("mixedCalibrationAssetUsage",
                        "historical_linear_basis_plus_HSM_role_diagnostic_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "native Camera2 source adapter + historical linear basis -> historical HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");
            }
''', 'stage diag')

start, end = method_span(s, 'private static RenderCore renderNativeSourceProduction1P(')
prod = s[start:end]
mode0 = '                0,\n                true,\n                false, false,'
mode3 = '                3,\n                true,\n                false, false,'
mode4 = '                4,\n                true,\n                false, false,'
if prod.count(mode4) == 0:
    if prod.count(mode0) == 1:
        prod = prod.replace(mode0, mode4, 1)
    elif prod.count(mode3) == 1:
        prod = prod.replace(mode3, mode4, 1)
    else:
        raise SystemExit('TARGETINPUTADAPTER1A production bridge mode anchor missing')

replacements = [
    ('d.put("schema", "m9cam.renderer.nativefirmware.v1a.production");',
     'd.put("schema", "m9cam.renderer.targetinputadapter.v1a.xiaomi17u.production");'),
    ('d.put("schema", "m9cam.renderer.targethsm.v1a.sourceadapterrescue.production");',
     'd.put("schema", "m9cam.renderer.targetinputadapter.v1a.xiaomi17u.production");'),
    ('d.put("architectureRevision", "COBALTROLEPURGE1A_NATIVEFIRMWARE1A");',
     'd.put("architectureRevision", "SOURCEADAPTER_RESCUE1A_TARGETINPUTADAPTER1A_XIAOMI17U_SETUPTRACE1A");'),
    ('d.put("architectureRevision", "SOURCEADAPTER_RESCUE1A_TARGETHSM1A_PERF1A");',
     'd.put("architectureRevision", "SOURCEADAPTER_RESCUE1A_TARGETINPUTADAPTER1A_XIAOMI17U_SETUPTRACE1A");'),
    ('d.put("cobaltRuntimeProductionDependency", false);',
     'd.put("cobaltRuntimeProductionDependency", true);\n        d.put("cobaltRuntimeDependencyRole", "historical_target_reference_only_not_live_sensor_source_CM_FM");'),
    ('d.put("cobaltRuntimeDependencyRole", "frozen_shared_target_H25_HSM_only_not_source_CM_FM");',
     'd.put("cobaltRuntimeDependencyRole", "historical_target_reference_only_not_live_sensor_source_CM_FM");'),
    ('d.put("cobaltHueSatMapApplied", false);',
     'd.put("cobaltHueSatMapApplied", true);\n        d.put("cobaltHueSatMapRole", "shared_target_H25_HSM_after_scene_domain_target_input_adapter");'),
    ('d.put("cobaltHueSatMapRole", "shared_target_H25_HSM_after_native_common_scene");',
     'd.put("cobaltHueSatMapRole", "shared_target_H25_HSM_after_scene_domain_target_input_adapter");'),
    ('d.put("cobaltHistoricalLinearBasisApplied", false);',
     'd.put("cobaltHistoricalLinearBasisApplied", true);'),
    ('d.put("historicalBasisHsmTargetBehaviorApplied", false);',
     'd.put("historicalBasisHsmTargetBehaviorApplied", true);'),
    ('d.put("historicalBasisHsmRole", "disabled_removed_from_production");',
     'd.put("historicalBasisHsmRole", "T_scene_equals_C15_historical_times_inverse_N15_native_after_active_SOURCECAL2A");'),
    ('d.put("historicalBasisHsmRole", "frozen_shared_target_behavior_after_native_SOURCECAL2A");',
     'd.put("historicalBasisHsmRole", "T_scene_equals_C15_historical_times_inverse_N15_native_after_active_SOURCECAL2A");'),
    ('d.put("historicalBasisDataProvenance", "none_production");',
     'd.put("historicalBasisDataProvenance", "legacy_15U_profile_target_domain_reference_only");'),
    ('d.put("historicalBasisDataProvenance", "legacy_profile_target_role_control_pending_firmware_replacement");',
     'd.put("historicalBasisDataProvenance", "legacy_15U_profile_target_domain_reference_only");'),
    ('d.put("identityHsmApplied", true);', 'd.put("identityHsmApplied", false);'),
    ('d.put("mixedCalibrationAssetUsedByProduction", false);',
     'd.put("mixedCalibrationAssetUsedByProduction", true);\n        d.put("mixedCalibrationProductionRole", "target_domain_reference_plus_H25_HSM_and_curve02_not_active_sensor_source");'),
    ('d.put("mixedCalibrationProductionRole", "target_H25_HSM_plus_byte_identical_curve02_only_source_CM_FM_disabled");',
     'd.put("mixedCalibrationProductionRole", "target_domain_reference_plus_H25_HSM_and_curve02_not_active_sensor_source");'),
    ('d.put("tc20DecisionSource", "native_source_identity_hsm_same_frame_tc20");',
     'd.put("tc20DecisionSource", "active_native_source_targetinputadapter1a_H25_HSM_same_frame_tc20");'),
    ('d.put("tc20DecisionSource", "native_source_shared_target_H25_HSM_same_frame_tc20");',
     'd.put("tc20DecisionSource", "active_native_source_targetinputadapter1a_H25_HSM_same_frame_tc20");'),
    ('d.put("bridgeProbeName", "production_source_only_identity_hsm");',
     'd.put("bridgeProbeName", "production_targetinputadapter1a_xiaomi17u");'),
    ('d.put("bridgeProbeName", "production_native_source_shared_target_H25_HSM");',
     'd.put("bridgeProbeName", "production_targetinputadapter1a_xiaomi17u");'),
    ('d.put("historicalLinearBasisDiagnosticApplied", false);',
     'd.put("historicalLinearBasisDiagnosticApplied", true);'),
    ('d.put("historicalLinearBasisDerivedFromCobaltSourceProfile", false);',
     'd.put("historicalLinearBasisDerivedFromCobaltSourceProfile", true);'),
    ('d.put("basisHsm1A", false);', 'd.put("basisHsm1A", true);'),
    ('d.put("basisHsmCombinedApplied", false);', 'd.put("basisHsmCombinedApplied", true);'),
    ('d.put("basisHsmOrdering", "not_in_production");',
     'd.put("basisHsmOrdering", "active_SOURCECAL2A_then_T_scene_target_adapter_then_H25_HSM");'),
    ('d.put("basisHsmHistoricalBasisBeforeHsm", false);',
     'd.put("basisHsmHistoricalBasisBeforeHsm", true);'),
    ('d.put("basisHsmHsmTableIdentity", "identity");',
     'd.put("basisHsmHsmTableIdentity", "historical_H25_S85_V100_reference15_scene_weight");'),
    ('d.put("mixedCalibrationAssetUsage", "none_production");',
     'd.put("mixedCalibrationAssetUsage", "target_reference_only_no_active_sensor_source_CM_FM");'),
]
for old, new in replacements:
    if old in prod:
        prod = prod.replace(old, new, 1)

marker = '        d.put("identityHsmApplied", false);\n'
if marker not in prod:
    raise SystemExit('TARGETINPUTADAPTER1A production telemetry marker missing')
prod = prod.replace(marker, '''        d.put("targetInputAdapter1AProduction", true);
        d.put("targetInputAdapterFormula", "T_scene=C15_historical_scene*inverse(N15_native_scene); output=T_scene*N_active");
        d.put("targetInputAdapterActiveSensorPreserved", true);
        d.put("targetInputAdapterPhysicalCameraIdIndependent", true);
        d.put("targetInputAdapterReferenceSensorRole", "historical_target_domain_reference_only");
''' + marker, 1)

for required in [
    'd.put("cobaltSourceAdapterApplied", false);',
    'd.put("cobaltSourceColorMatrixApplied", false);',
    'd.put("cobaltSourceForwardMatrixApplied", false);',
    'active_physical_Xiaomi_Camera2_DNG_SOURCECAL2A_CMFIX',
]:
    if required not in prod:
        raise SystemExit('TARGETINPUTADAPTER1A required source invariant missing: ' + required)
for forbidden in [
    'd.put("cobaltSourceAdapterApplied", true);',
    'd.put("cobaltSourceColorMatrixApplied", true);',
    'd.put("cobaltSourceForwardMatrixApplied", true);',
]:
    if forbidden in prod:
        raise SystemExit('TARGETINPUTADAPTER1A forbidden live Cobalt source role: ' + forbidden)

s = s[:start] + prod + s[end:]
p.write_text(s)
print('TARGETINPUTADAPTER1A applied')
print(' - active physical SOURCECAL2A preserved for Xiaomi 17 Ultra and other sensors')
print(' - historical 15U calibration used only to reconstruct scene-domain target delta T')
print(' - production bridge mode 4 avoids C15*inverse(Nactive)*Nactive cancellation')
