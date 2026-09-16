#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-hsmbypass1a-sameraw.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit(f'HSMBYPASS1A missing renderer: {p}')
s = p.read_text()

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'HSMBYPASS1A {label}: expected 1 anchor, found {n}')
    s = s.replace(old, new, 1)

old_mode4 = '''            } else if (bridgeProbeMode == 4) {
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
'''
new_mode4 = '''            } else if (bridgeProbeMode == 4) {
                bridgeProbeName = "native_plus_target_input_adapter1a_hsm_bypass1a";
                bridgeProbeHistoricalLinearBasisApplied = true;
                bridgeProbeHistoricalHsmApplied = false;
                targetInputAdapter1AApplied = true;

                // HSMBYPASS1A same-RAW experiment: retain TARGETINPUTADAPTER1A exactly,
                // but remove only the historical Cobalt-derived ProfileHueSatMap role.
                // The active physical sensor SOURCECAL, target-input basis, TC20, SAT3,
                // curve02, BT.601, TG1, demosaic, sharpening and JPEG path stay frozen.
                TargetInputAdapter1A targetInput = buildTargetInputAdapter1A(nativeSource, cal);
                bridgeProbeBasis = targetInput.sceneDomainBasis;
                ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);
                targetInputAdapterReference15Factor = targetInput.reference15Factor;
                targetInputAdapterHistorical15Cct = targetInput.historical15.cct;
                targetInputAdapterHistorical15WA = targetInput.historical15.wA;
                targetInputAdapterBasisMaxAbsFromIdentity = maxAbsDeltaIdentity3(bridgeProbeBasis);

                // Exact identity HSM used by the established native source path.
                ctx.hsm = new double[]{
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0
                };
                ctx.hueDivisions = 2;
                ctx.satDivisions = 2;
'''
once(old_mode4, new_mode4, 'mode4 identity HSM')

once('d.put("basisHsmCombinedApplied", bridgeProbeMode == 3 || bridgeProbeMode == 4);',
     'd.put("basisHsmCombinedApplied", bridgeProbeHistoricalLinearBasisApplied && bridgeProbeHistoricalHsmApplied);',
     'combined telemetry')
once('''                    bridgeProbeMode == 4 ? "target_input_adapter1a_then_historical_HSM"
                            : bridgeProbeMode == 3 ? "historical_linear_basis_then_historical_HSM"
                            : "source_only_identity_HSM");''',
     '''                    bridgeProbeMode == 4 ? "target_input_adapter1a_then_identity_HSM_HSMBYPASS1A"
                            : bridgeProbeMode == 3 ? "historical_linear_basis_then_historical_HSM"
                            : "source_only_identity_HSM");''',
     'ordering telemetry')
once('d.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeMode == 3 || bridgeProbeMode == 4);',
     'd.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeHistoricalLinearBasisApplied && bridgeProbeHistoricalHsmApplied);',
     'basis-before-hsm telemetry')

once('''            if (bridgeProbeMode == 4) {
                d.put("mixedCalibrationAssetUsage",
                        "scene_domain_target_input_adapter_plus_HSM_target_role_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "active physical Camera2 SOURCECAL2A -> common scene ProPhoto -> T(scene)=C15*inverse(N15) -> historical H25/HSM -> existing M9 bridge/SAT3/curve02/BT601/TG1");
''',
     '''            if (bridgeProbeMode == 4) {
                d.put("mixedCalibrationAssetUsage",
                        "scene_domain_target_input_adapter_reference_plus_curve02_target_component_HSM_bypassed");
                d.put("fullColorRenderStages",
                        "active physical Camera2 SOURCECAL2A -> common scene ProPhoto -> T(scene)=C15*inverse(N15) -> identity HSM -> existing M9 bridge/SAT3/curve02/BT601/TG1");
''',
     'core mode4 stage telemetry')

# Production telemetry must describe the B variant truthfully while retaining
# TARGETINPUTADAPTER1A provenance. These edits do not change render arithmetic.
once('d.put("schema", "m9cam.renderer.targetinputadapter.v1a.xiaomi17u.production");',
     'd.put("schema", "m9cam.renderer.hsmbypass1a.sameraw.production");', 'schema')
once('d.put("architectureRevision", "SOURCEADAPTER_RESCUE1A_TARGETINPUTADAPTER1A_XIAOMI17U_SETUPTRACE1A");',
     'd.put("architectureRevision", "SOURCEADAPTER_RESCUE1A_TARGETINPUTADAPTER1A_HSMBYPASS1A_SAMERAW");',
     'architecture')
once('d.put("cobaltHueSatMapApplied", true);',
     'd.put("cobaltHueSatMapApplied", false);', 'production HSM applied flag')
once('d.put("cobaltHueSatMapRole", "shared_target_H25_HSM_after_scene_domain_target_input_adapter");',
     'd.put("cobaltHueSatMapRole", "bypassed_for_HSMBYPASS1A_same_RAW_test");', 'production HSM role')
once('d.put("historicalBasisHsmTargetBehaviorApplied", true);',
     'd.put("historicalBasisHsmTargetBehaviorApplied", false);', 'production target-HSM flag')
once('d.put("identityHsmApplied", false);',
     'd.put("identityHsmApplied", true);', 'production identity flag')
once('d.put("mixedCalibrationProductionRole", "target_domain_reference_plus_H25_HSM_and_curve02_not_active_sensor_source");',
     'd.put("mixedCalibrationProductionRole", "target_domain_reference_plus_curve02_not_HSM_not_active_sensor_source");',
     'production mixed calibration role')

# Add explicit experiment labels immediately after the target-input production flag.
once('''        d.put("targetInputAdapter1AProduction", true);
''', '''        d.put("targetInputAdapter1AProduction", true);
        d.put("hsmBypass1A", true);
        d.put("sameRawColorVariant", "HSMBYPASS1A");
        d.put("sameRawColorControl", "HSMCONTROL1A_run_35085472220");
''', 'experiment telemetry')

p.write_text(s)
print('HSMBYPASS1A_SAMERAW applied')
