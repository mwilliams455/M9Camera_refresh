from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
P = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = P.read_text()
checks = []


def ck(name, cond):
    ok = bool(cond)
    checks.append((name, ok))
    print(('PASS' if ok else 'FAIL'), name)


ck('diagnostic_bank_enabled', 'private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = true;' in s)
ck('toneauth_suffix_a', '"_TONEAUTH_A_FULL_TC20"' in s)
ck('toneauth_suffix_b', '"_TONEAUTH_B_HALF_TC20"' in s)
ck('toneauth_suffix_c', '"_TONEAUTH_C_ZERO_TC20"' in s)
ck('targetdirect_mode0_all_variants', 'int[] bridgeProbeModes = {0, 0, 0};' in s)
ck('historical_mode4_absent', 'int[] bridgeProbeModes = {4, 4, 4};' not in s)
ck('a_selfmeters_b_c_gainlocked', 'boolean[] selfMeterFlags = {true, false, false};' in s)
ck('half_authority_ev', 'Math.sqrt(skyChromaControlTc20BaselineGain)' in s)
ck('zero_authority_unity_before_edge', 'variantFixedGain = edgeFactor;' in s)
ck('edge_preserved_separately', 'final double edgeFactor = Math.pow(2.0, primaryEdgeEv);' in s)
ck('toneauth_schema', 'm9cam.renderer.toneauth.v1a.sameRAW' in s)
ck('authority_fractions', '"toneAuthorityFractions", "1.0,0.5,0.0"' in s)
ck('capture_mutation_false', '"toneAuthorityCaptureExposureMutation", false' in s and '"captureExposureChanged", false' in s)
ck('primary_mutation_false', '"toneAuthorityPrimaryJpegMutation", false' in s and '"primaryJpegChanged", false' in s)
ck('same_raw_true', '"toneAuthoritySameRaw", true' in s)

ck('tonebound050_retained', 'm9cam.tonebound.v1a.050ev' in s)
ck('tonebound_limit_retained', 'final double toneBoundLimitEv1A = 0.5;' in s)
ck('tonebound_bounded_gain_retained', 'final double effectiveRenderGain = toneBoundUnboundedEffectiveGain1A * toneBoundScale1A;' in s)
ck('original_tc20_decision_retained', 'final double toneBoundOriginalTc20Gain1A = meter.gain;' in s)

ck('m9_sensor_target_retained', 'M9SENSORTARGET1A' in s)
ck('fullsource_gainlock_retained', '_M9_SOURCEFULLNORM1A_GAINLOCK.jpg' in s)
ck('fullsource_alpha1_retained', 'full_live_remaining_LensShadingMap_common_luma_alpha_1p0' in s)
ck('fullsource_authority_role_retained', 'source_common_luminance_shading_authority_NORM030_to_full_physical_remaining_map' in s)
ck('fullsource_primary_final_gain_lock_retained', 'primaryFinalLinearGain' in s and 'gainLockPassed' in s)
ck('identity_hsm_retained', 'identity_90x30_no_Adobe_HueSatMap_target_stage' in s)
ck('sat2_label', '"toneAuthoritySaturationBank", "SAT2_M04_M05"' in s)
ck('sat2_constant', 'public static final int SATURATION_BANK = 2;' in s)
ck('native_sat2_selector_retained', 'SATURATION_BANK == 2 ? 9' in s)
ck('curve02_retained', 'firmware curve02' in s or 'firmwareCurve02' in s or 'm9_curve02_firmware.bin' in s)
ck('bt601_retained', 'exact BT601 4:2:2' in s)
ck('tg1_retained', 'M9Modern TG1' in s)

ck('variant_json_path_removed', 'Path variantJsonPath = Paths.get(' not in s)
ck('variant_json_embedded', '"outputJsonEmbeddedInPrimarySidecar", true' in s)
ck('variant_json_policy', '"jsonPersistencePolicy", "embedded_primary_sidecar_only"' in s)
ck('direct_variant_files_write_removed', 'Files.write(variantJsonPath' not in s)

save_anchor = s.find('boolean jpgSaved = ImageSaver.Util.saveBitmapAsJPGPayloadM9')
bank_anchor = s.find('if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED)')
ck('primary_jpeg_saved_before_bank', save_anchor >= 0 and bank_anchor >= 0 and save_anchor < bank_anchor)
ck('legacy_sat_diag_modes_not_in_tone_bank', 'int[] bridgeProbeModes = {50, 55, 54};' not in s)

bad = [name for name, ok in checks if not ok]
if bad:
    raise SystemExit('M9 TONEBANK1A TARGETDIRECTFIX verify failed: ' + ', '.join(bad))
print('M9 TONEBANK1A TARGETDIRECTFIX VERIFY PASS', len(checks), 'checks')
print('Current TARGETDIRECT mode0 + TONEBOUND050 baseline retained; only same-RAW TC20 authority variants added')
