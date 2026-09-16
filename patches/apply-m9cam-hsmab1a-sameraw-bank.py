#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: apply-m9cam-hsmab1a-sameraw-bank.py <PhotonCamera-root>')
root = Path(sys.argv[1]).resolve()
p = root / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
if not p.exists():
    raise SystemExit(f'HSMAB1A missing renderer: {p}')
s = p.read_text()

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'HSMAB1A {label}: expected 1 anchor, found {n}')
    s = s.replace(old, new, 1)

once('private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = false;',
     'private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = true; // HSMAB1A same-RAW research bank',
     'enable diagnostic bank')

once('''                    if ((params.cfaPattern & 0xff) != 0) {
                        nativeAb1A.put("status", "skipped_legacy_diagnostic_requires_RGGB");
                        nativeAb1A.put("legacyDiagnosticRequiredCfa", 0);
                    } else {''',
     '''                    if (sourceCfaPattern < 0 || sourceCfaPattern > 3) {
                        nativeAb1A.put("status", "skipped_hsmab1a_requires_conventional_bayer");
                        nativeAb1A.put("resolvedSourceCfaPattern", sourceCfaPattern);
                    } else {''',
     'generic Bayer gate')

old_variants = '''                        // BASISHSM1P-SKYSAT1A: same-RAW authentic Leica saturation-family bank.
                        // A meters exactly as frozen 1P/SAT3. B/C/D reuse A's exact effective render gain.
                        // SAT2=04/05 is literal Leica Standard, SAT3=06/07 is current colourful production,
                        // SAT4=08/09 is authentic High Saturation. D keeps the already-proven identity anchor.
                        // No sky classifier, scene guard, exposure change, HSM change, or generic desaturation exists.
                        // DEMOSAICAB1A: same RAW and same NORM030 Bayer; only demosaic changes.
                        // A is MHC production and meters normally. B is OpenCV EA and reuses A's
                        // exact effective render gain. SOURCECAL2A/HSM/TC20 placement/SAT3/curve02/
                        // BT601/TG1 are otherwise identical.
                        String[] suffixes = {
                                "_DEMOSAICNEUTRAL_MHCNB_SAT3",
                                "_DEMOSAICNEUTRAL_MHCPLAIN_SAT3_GAINLOCK",
                                "_DEMOSAICNEUTRAL_EA_SAT3_GAINLOCK"
                        };
                        String[] bridgeProbeNames = {
                                "demosaicneutral_mhcnb_sat3_control",
                                "demosaicneutral_mhcplain_sat3_gainlocked",
                                "demosaicneutral_ea_sat3_gainlocked"
                        };
                        int[] bridgeProbeModes = {50, 55, 54};
                        boolean[] selfMeterFlags = {true, false, false};
                        double[] hsmValueStrengthFlags = {1.0, 1.0, 1.0};
                        boolean[] applyShadingFlags = {true, true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {true, true, true};
                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true, true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30, 0.30};'''
new_variants = '''                        // HSMAB1A: exact same RAW / same source metadata / same NORM030 / same
                        // TARGETINPUTADAPTER1A / same SAT3 / curve02 / BT.601 / TG1 comparison.
                        // A is the frozen mode-4 historical Cobalt-HSM control and meters normally.
                        // B retains the identical mode-4 target-input basis but substitutes an exact
                        // identity HSM; it reuses A's exact effective render gain. No exposure/tone,
                        // demosaic, sharpening, shading, SAT-bank, curve or JPEG-quality change is allowed.
                        String[] suffixes = {
                                "_HSMCONTROL1A_SAMERAW",
                                "_HSMBYPASS1A_SAMERAW_GAINLOCK"
                        };
                        String[] bridgeProbeNames = {
                                "hsmcontrol1a_targetinputadapter1a_historical_hsm",
                                "hsmbypass1a_targetinputadapter1a_identity_hsm_gainlocked"
                        };
                        int[] bridgeProbeModes = {4, 60};
                        boolean[] selfMeterFlags = {true, false};
                        double[] hsmValueStrengthFlags = {1.0, 1.0};
                        boolean[] applyShadingFlags = {true, true};
                        boolean[] applyShadedGuard1AFlags = {false, false};
                        boolean[] applyShadedGuardCap20Ev1AFlags = {false, false};
                        boolean[] applyShadingLumaDecomp1AFlags = {true, true};
                        double[] shadingLumaAuthorityAlphaFlags = {1.0, 1.0};
                        boolean[] normalizeShadingLumaOutsideMedian1AFlags = {true, true};
                        double[] shadingLumaTargetOutsideMedianEv1AFlags = {0.30, 0.30};'''
once(old_variants, new_variants, 'A/B variant bank')

once('''                                variantDiag.put("skinLumaHsmHueAuthority", HSM_H);
                                variantDiag.put("skinLumaHsmSaturationAuthority", HSM_S);
                                variantDiag.put("skinLumaHsmValueAuthority", hsmValueStrength);
                                variantDiag.put("skinLumaNoProductionMutation", true);
                                variantDiag.put("primaryTreatment", primaryTreatment);
                                variantDiag.put("mainPhysicalCameraId", "2");''',
     '''                                variantDiag.put("skinLumaHsmHueAuthority",
                                        variantDiag.optDouble("hsmHueStrength", 0.0));
                                variantDiag.put("skinLumaHsmSaturationAuthority",
                                        variantDiag.optDouble("hsmSaturationStrength", 0.0));
                                variantDiag.put("skinLumaHsmValueAuthority",
                                        variantDiag.optDouble("hsmValueStrength", 0.0));
                                variantDiag.put("skinLumaNoProductionMutation", true);
                                variantDiag.put("primaryTreatment", primaryTreatment);
                                variantDiag.put("sourceCameraIdUsedAsSemanticRole", false);''',
     'truthful HSM authority telemetry')

once('''                        nativeAb1A.put("schema", "m9cam.renderer.satdomain.v1a");
                        nativeAb1A.put("experiment", "BASISHSM1P-DEMOSAICAB1A");''',
     '''                        nativeAb1A.put("schema", "m9cam.renderer.hsmab1a.sameraw.v1");
                        nativeAb1A.put("experiment", "HSMCONTROL1A_vs_HSMBYPASS1A_same_RAW");''',
     'bank schema')

once('''                        nativeAb1A.put("productionBehaviorChanged", false);
                        nativeAb1A.put("tc20GainIsolation",
                                "EA_B_locked_to_MHC_A_exact_effective_render_gain");
                        nativeAb1A.put("skinChromaProxyApplied", false);
                        nativeAb1A.put("status", "completed_demosaicab1a");''',
     '''                        nativeAb1A.put("productionBehaviorChanged", false);
                        nativeAb1A.put("tc20GainIsolation",
                                "HSMBYPASS1A_B_locked_to_HSMCONTROL1A_A_exact_effective_render_gain");
                        nativeAb1A.put("hsmOnlyVariable", true);
                        nativeAb1A.put("skinChromaProxyApplied", false);
                        nativeAb1A.put("status", "completed_hsmab1a");''',
     'bank status')

mode_anchor = '''                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
            } else if (bridgeProbeMode != 0) {
                throw new IllegalArgumentException(
                        "BASISHSM1A unsupported mode " + bridgeProbeMode);
            }
'''
mode_replacement = '''                ctx.hueDivisions = cal.hueDivisions;
                ctx.satDivisions = cal.satDivisions;
            } else if (bridgeProbeMode == 60) {
                bridgeProbeName = "native_plus_target_input_adapter1a_identity_hsm_hsmab1a";
                bridgeProbeHistoricalLinearBasisApplied = true;
                bridgeProbeHistoricalHsmApplied = false;
                targetInputAdapter1AApplied = true;

                // HSMAB1A B: preserve the exact mode-4 scene-domain adapter and replace
                // only the historical Cobalt-derived Adobe ProfileHueSatMap with identity.
                TargetInputAdapter1A targetInput = buildTargetInputAdapter1A(nativeSource, cal);
                bridgeProbeBasis = targetInput.sceneDomainBasis;
                ctx.camToPp = matMul3(bridgeProbeBasis, nativeCamToPpBeforeProbe);
                targetInputAdapterReference15Factor = targetInput.reference15Factor;
                targetInputAdapterHistorical15Cct = targetInput.historical15.cct;
                targetInputAdapterHistorical15WA = targetInput.historical15.wA;
                targetInputAdapterBasisMaxAbsFromIdentity = maxAbsDeltaIdentity3(bridgeProbeBasis);

                ctx.hsm = new double[]{
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0,
                        0.0, 1.0, 1.0
                };
                ctx.hueDivisions = 2;
                ctx.satDivisions = 2;
            } else if (bridgeProbeMode != 0) {
                throw new IllegalArgumentException(
                        "BASISHSM1A unsupported mode " + bridgeProbeMode);
            }
'''
once(mode_anchor, mode_replacement, 'mode60 identity HSM')

once('''            d.put("basisHsmOrdering",
                    bridgeProbeMode == 4 ? "target_input_adapter1a_then_historical_HSM"
                            : bridgeProbeMode == 3 ? "historical_linear_basis_then_historical_HSM"
                            : "source_only_identity_HSM");''',
     '''            d.put("basisHsmOrdering",
                    bridgeProbeMode == 4 ? "target_input_adapter1a_then_historical_HSM"
                            : bridgeProbeMode == 60 ? "target_input_adapter1a_then_identity_HSM_HSMAB1A"
                            : bridgeProbeMode == 3 ? "historical_linear_basis_then_historical_HSM"
                            : "source_only_identity_HSM");''',
     'ordering telemetry')

once('d.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeMode == 3 || bridgeProbeMode == 4);',
     'd.put("basisHsmHistoricalBasisBeforeHsm", bridgeProbeHistoricalLinearBasisApplied);',
     'basis-before-HSM telemetry')

once('''            if (bridgeProbeMode == 4) {
                d.put("mixedCalibrationAssetUsage",
                        "scene_domain_target_input_adapter_plus_HSM_target_role_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "active physical Camera2 SOURCECAL2A -> common scene ProPhoto -> T(scene)=C15*inverse(N15) -> historical H25/HSM -> existing M9 bridge/SAT3/curve02/BT601/TG1");
            } else if (bridgeProbeMode == 3) {''',
     '''            if (bridgeProbeMode == 4) {
                d.put("mixedCalibrationAssetUsage",
                        "scene_domain_target_input_adapter_plus_HSM_target_role_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "active physical Camera2 SOURCECAL2A -> common scene ProPhoto -> T(scene)=C15*inverse(N15) -> historical H25/HSM -> existing M9 bridge/SAT3/curve02/BT601/TG1");
            } else if (bridgeProbeMode == 60) {
                d.put("mixedCalibrationAssetUsage",
                        "scene_domain_target_input_adapter_reference_plus_curve02_target_component_HSM_identity");
                d.put("fullColorRenderStages",
                        "active physical Camera2 SOURCECAL2A -> common scene ProPhoto -> T(scene)=C15*inverse(N15) -> identity HSM -> existing M9 bridge/SAT3/curve02/BT601/TG1");
            } else if (bridgeProbeMode == 3) {''',
     'late mode60 stage telemetry')

once('''            } else {
                d.put("mixedCalibrationAssetUsage",
                        "historical_linear_basis_role_diagnostic_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "native Camera2 source adapter + explicit historical linear basis + identity HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");
            }
            d.put("sourceRawOriginX", sourceRawOriginX);''',
     '''            } else if (bridgeProbeMode == 60) {
                d.put("mixedCalibrationAssetUsage",
                        "target_input_adapter1a_reference_plus_curve02_target_component_identity_HSM_HSMAB1A");
                d.put("fullColorRenderStages",
                        "active physical Camera2 SOURCECAL2A -> common scene ProPhoto -> T(scene)=C15*inverse(N15) -> identity HSM -> existing M9 bridge/SAT3/curve02/BT601/TG1");
            } else {
                d.put("mixedCalibrationAssetUsage",
                        "historical_linear_basis_role_diagnostic_plus_curve02_target_component");
                d.put("fullColorRenderStages",
                        "native Camera2 source adapter + explicit historical linear basis + identity HSM + existing M9 bridge/SAT3/curve02/BT601/TG1");
            }
            d.put("sourceRawOriginX", sourceRawOriginX);''',
     'early mode60 stage telemetry')

p.write_text(s)
print('HSMAB1A_SAMERAW_BANK applied')
