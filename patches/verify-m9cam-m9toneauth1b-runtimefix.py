from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('PhotonCamera')
P = ROOT / 'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s = P.read_text()
checks = []


def ck(name, cond):
    checks.append((name, bool(cond)))
    print(('PASS' if cond else 'FAIL'), name)


ck('diagnostic_bank_enabled', 'private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = true;' in s)
ck('abc_suffixes_retained', all(x in s for x in ['"_TONEAUTH_A_FULL_TC20"','"_TONEAUTH_B_HALF_TC20"','"_TONEAUTH_C_ZERO_TC20"']))
ck('production_bridge_mode4_all_variants', 'int[] bridgeProbeModes = {4, 4, 4};' in s)
ck('wrong_mode0_removed_from_bank', 'int[] bridgeProbeModes = {0, 0, 0};' not in s)
ck('a_selfmeters_b_c_gainlocked', 'boolean[] selfMeterFlags = {true, false, false};' in s)
ck('half_authority_ev', 'Math.sqrt(skyChromaControlTc20BaselineGain)' in s)
ck('zero_authority_unity_before_edge', 'variantFixedGain = edgeFactor;' in s)
ck('edge_preserved_separately', 'final double edgeFactor = Math.pow(2.0, primaryEdgeEv);' in s)
ck('unrelated_stage_audits_disabled', 'hsmValueStrength, false);' in s)
ck('direct_variant_json_path_removed', 'Path variantJsonPath = Paths.get(' not in s)
ck('direct_variant_json_write_removed', 'Files.write(variantJsonPath' not in s)
ck('diagnostics_embedded_primary_sidecar', '"jsonPersistencePolicy", "embedded_primary_sidecar_only"' in s and '"outputJsonEmbeddedInPrimarySidecar", true' in s)
ck('toneauth_schema', 'm9cam.renderer.toneauth.v1a.sameRAW' in s)
ck('capture_mutation_false', '"toneAuthorityCaptureExposureMutation", false' in s and '"captureExposureChanged", false' in s)
ck('primary_mutation_false', '"toneAuthorityPrimaryJpegMutation", false' in s and '"primaryJpegChanged", false' in s)
ck('same_raw_true', '"toneAuthoritySameRaw", true' in s)
ck('sat2_constant', 'public static final int SATURATION_BANK = 2;' in s)
ck('native_sat2_selector_retained', 'SATURATION_BANK == 2 ? 9' in s)
ck('mode4_targetinput_retained', 'else if (bridgeProbeMode == 4)' in s and 'targetInputAdapter1AApplied = true;' in s)
ck('mode4_identity_hsm_retained', 'M9NATIVEHSM1A: recovered firmware evidence does not establish an' in s and 'ctx.hsm = new double[identityHsmLength];' in s)
ck('curve02_retained', 'firmware curve02' in s or 'firmwareCurve02' in s)
ck('bt601_retained', 'exact BT601 4:2:2' in s)
ck('tg1_retained', 'M9Modern TG1' in s)
ck('primary_effective_gain_formula_unchanged', 'final double effectiveRenderGain = meterParityRenderBaseGain;' in s)
ck('primary_jpeg_saved_before_bank', s.find('boolean jpgSaved = ImageSaver.Util.saveBitmapAsJPGPayloadM9') < s.find('if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED)'))

bad = [n for n, ok in checks if not ok]
if bad:
    raise SystemExit('M9TONEAUTH1B runtime verify failed: ' + ', '.join(bad))
print('M9TONEAUTH1B RUNTIME VERIFY PASS', len(checks), 'checks')
