#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-sourcecolorrole1a.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit(f'SOURCECOLORROLE1A missing renderer: {p}')
s = p.read_text()

def replace1(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'SOURCECOLORROLE1A {label}: expected 1 anchor, found {n}')
    return text.replace(old, new, 1)

const_anchor = '''    private static final double[] TARGETINPUT15_NFM2 = TARGETINPUT15_NFM1.clone();\n'''
const_insert = '''

    // SOURCECOLORROLE1A: Cobalt-table-free, device-independent common-scene
    // canonicalisation oracle candidate. These matrices operate AFTER the active
    // physical Camera2 SOURCECAL transform has produced common-scene ProPhoto RGB.
    // They do not replace physical sensor calibration and they are not claimed as
    // Leica firmware matrices. Rows sum to exactly one to preserve the neutral axis.
    private static final double[] SOURCECOLORROLE1A_A = {
            0.9254999742684094, 0.10275137158846384, -0.02825134585687324,
           -0.026874359472623753, 1.0437503072522498, -0.016875947779626015,
           -0.05084020962110854, 0.25359083086928935, 0.7972493787518191
    };
    private static final double[] SOURCECOLORROLE1A_D65 = {
            0.8240918321014137, 0.19137305210473288, -0.015464884206146556,
            0.028908005599596786, 1.045151071648237, -0.07405907724783392,
           -0.0335213050071955, 0.28400771946121767, 0.7495135855459779
    };
'''
s = replace1(s, const_anchor, const_anchor + const_insert, 'canonical matrix constants')

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

                // M9NATIVEHSM1A: recovered firmware evidence does not establish an
                // Adobe ProfileHueSatMap-equivalent target stage.  Preserve the frozen
                // 90x30 evaluator geometry but make the operation an exact no-op.
                int identityHsmCells = Math.multiplyExact(cal.hueDivisions, cal.satDivisions);
                int identityHsmLength = Math.multiplyExact(identityHsmCells, 3);
                if (cal.hueDivisions != 90 || cal.satDivisions != 30
                        || cal.hsmA.length != identityHsmLength
                        || cal.hsmD65.length != identityHsmLength) {
                    throw new IllegalStateException(
                            "M9NATIVEHSM1A unexpected historical HSM geometry");
                }
                ctx.hsm = new double[identityHsmLength];
                for (int i = 0; i < ctx.hsm.length; i += 3) {
                    ctx.hsm[i] = 0.0;
                    ctx.hsm[i + 1] = 1.0;
                    ctx.hsm[i + 2] = 1.0;
                }
                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
'''
new_mode4 = '''            } else if (bridgeProbeMode == 4) {
                bridgeProbeName = "sourcecolorrole1a_common_scene_dual3x3";
                bridgeProbeHistoricalLinearBasisApplied = false;
                bridgeProbeHistoricalHsmApplied = false;
                targetInputAdapter1AApplied = false;

                // SOURCECOLORROLE1A: the active physical sensor still owns RAW->XYZ50
                // through SOURCECAL2A. Once in common-scene ProPhoto, apply a single
                // illuminant-interpolated canonical 3x3. This replaces BOTH the
                // historical 15U target-input basis and the 90x30 HSM oracle for this
                // research candidate. No Cobalt table is evaluated at runtime.
                bridgeProbeBasis = interp9(
                        SOURCECOLORROLE1A_A, SOURCECOLORROLE1A_D65, ctx.wA);
                ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);
                targetInputAdapterBasisMaxAbsFromIdentity = maxAbsDeltaIdentity3(bridgeProbeBasis);

                // Keep the HSM seam mathematically identity. Downstream M9 bridge,
                // TC20/TONEBOUND, SAT2 M04/M05, curve02, BT.601 and TG1 are untouched.
                int identityHsmCells = Math.multiplyExact(cal.hueDivisions, cal.satDivisions);
                int identityHsmLength = Math.multiplyExact(identityHsmCells, 3);
                if (cal.hueDivisions != 90 || cal.satDivisions != 30
                        || cal.hsmA.length != identityHsmLength
                        || cal.hsmD65.length != identityHsmLength) {
                    throw new IllegalStateException(
                            "SOURCECOLORROLE1A unexpected historical HSM geometry");
                }
                ctx.hsm = new double[identityHsmLength];
                for (int i = 0; i < ctx.hsm.length; i += 3) {
                    ctx.hsm[i] = 0.0;
                    ctx.hsm[i + 1] = 1.0;
                    ctx.hsm[i + 2] = 1.0;
                }
                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
'''
s = replace1(s, old_mode4, new_mode4, 'mode4 common-scene candidate')

ret_anchor = '''        d.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene -> TARGETINPUTADAPTER1A -> identity HSM -> M9 bridge -> TC20 -> SAT2 M04/M05 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
        return out;
'''
ret_new = '''        d.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene -> TARGETINPUTADAPTER1A -> identity HSM -> M9 bridge -> TC20 -> SAT2 M04/M05 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
        d.put("architectureRevision", "SOURCECOLORROLE1A_CANONICAL3X3_M9TTL1A_TONEBOUND050");
        d.put("sourceColorRole1A", true);
        d.put("sourceColorRole1AResearchOnly", true);
        d.put("sourceColorRole1AMethod", "dual_illuminant_neutral_axis_preserving_common_scene_3x3");
        d.put("sourceColorRole1AInterpolation", "active_physical_scene_wA_times_A_plus_one_minus_wA_times_D65");
        d.put("sourceColorRole1AOracleProvenance", "offline_fit_to_complete_historical_TARGETINPUTADAPTER1A_plus_90x30_HSM_reference_transform");
        d.put("sourceColorRole1AFirmwareProven", false);
        d.put("sourceColorRole1ACobaltTableRuntimeDependency", false);
        d.put("sourceColorRole1ATargetInput15RuntimeApplied", false);
        d.put("targetInputAdapter1AProduction", false);
        d.put("targetInputAdapter1AApplied", false);
        d.put("cobaltRuntimeProductionDependency", false);
        d.put("cobaltHueSatMapApplied", false);
        d.put("historicalBasisHsmTargetBehaviorApplied", false);
        d.put("identityHsmApplied", true);
        d.put("bridgeProbeName", "sourcecolorrole1a_common_scene_dual3x3");
        d.put("basisHsmOrdering", "active_SOURCECAL2A_then_SOURCECOLORROLE1A_common_scene_3x3_then_identity_HSM");
        d.put("basisHsmHistoricalBasisBeforeHsm", false);
        d.put("basisHsmHsmTableIdentity", "identity_90x30");
        d.put("mixedCalibrationAssetUsage", "curve02_target_component_only_no_runtime_Cobalt_HSM_or_15U_target_input_basis");
        d.put("fullColorRenderStages", "active physical Camera2 SOURCECAL2A -> common scene -> SOURCECOLORROLE1A dual 3x3 -> identity HSM -> M9 bridge -> TC20 -> SAT2 M04/M05 -> curve02 -> BT601 -> TG1");
        d.put("pipeline", "NORM030 physical LensShadingMap -> DEMOSAICMHCNEUTRAL1A -> active physical-sensor SOURCECAL2A -> common scene -> SOURCECOLORROLE1A dual 3x3 -> identity HSM -> M9 bridge -> TC20 -> SAT2 M04/M05 -> firmware curve02 -> exact BT601 4:2:2 -> M9Modern TG1");
        return out;
'''
s = replace1(s, ret_anchor, ret_new, 'production telemetry')

p.write_text(s)
print('SOURCECOLORROLE1A applied')
print('active source calibration: physical Camera2 SOURCECAL2A retained')
print('historical TARGETINPUTADAPTER1A runtime path: replaced in production mode4')
print('runtime 90x30 HSM: identity')
print('common-scene correction: dual illuminant neutral-axis-preserving 3x3')
print('M9 target downstream: untouched')
