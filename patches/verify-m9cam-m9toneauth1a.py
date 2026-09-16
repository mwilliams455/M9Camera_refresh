from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv)>1 else Path('PhotonCamera')
P = ROOT/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s=P.read_text()
checks=[]

def ck(name, cond):
    checks.append((name, bool(cond)))
    print(('PASS' if cond else 'FAIL'), name)

ck('diagnostic_bank_enabled', 'private static final boolean DEMOSAIC_DIAGNOSTIC_BANK_ENABLED = true;' in s)
ck('toneauth_suffix_a', '"_TONEAUTH_A_FULL_TC20"' in s)
ck('toneauth_suffix_b', '"_TONEAUTH_B_HALF_TC20"' in s)
ck('toneauth_suffix_c', '"_TONEAUTH_C_ZERO_TC20"' in s)
ck('production_mode_zero_all_variants', 'int[] bridgeProbeModes = {0, 0, 0};' in s)
ck('a_selfmeters_b_c_gainlocked', 'boolean[] selfMeterFlags = {true, false, false};' in s)
ck('half_authority_ev', 'Math.sqrt(skyChromaControlTc20BaselineGain)' in s)
ck('zero_authority_unity_before_edge', 'variantFixedGain = edgeFactor;' in s)
ck('edge_preserved_separately', 'final double edgeFactor = Math.pow(2.0, primaryEdgeEv);' in s)
ck('toneauth_schema', 'm9cam.renderer.toneauth.v1a.sameRAW' in s)
ck('authority_fractions', '"toneAuthorityFractions", "1.0,0.5,0.0"' in s)
ck('capture_mutation_false', '"toneAuthorityCaptureExposureMutation", false' in s and '"captureExposureChanged", false' in s)
ck('primary_mutation_false', '"toneAuthorityPrimaryJpegMutation", false' in s and '"primaryJpegChanged", false' in s)
ck('same_raw_true', '"toneAuthoritySameRaw", true' in s)
ck('sat2_label', '"toneAuthoritySaturationBank", "SAT2_M04_M05"' in s)
ck('sat2_constant', 'public static final int SATURATION_BANK = 2;' in s)
ck('native_sat2_selector_retained', 'SATURATION_BANK == 2 ? 9' in s)
ck('native_context_uses_selected_mode', 'nativeSaturationMode1A);' in s)
ck('identity_hsm_retained', 'identity_90x30_no_Adobe_HueSatMap_target_stage' in s)
ck('curve02_retained', 'firmware curve02' in s or 'firmwareCurve02' in s)
ck('bt601_retained', 'exact BT601 4:2:2' in s)
ck('tg1_retained', 'M9Modern TG1' in s)
ck('tone_forensics_retained', 'm9cam.toneforensics.v1a.readonly' in s)
ck('primary_effective_gain_formula_unchanged', 'final double effectiveRenderGain = meterParityRenderBaseGain;' in s)
ck('primary_jpeg_saved_before_bank', s.find('boolean jpgSaved = ImageSaver.Util.saveBitmapAsJPGPayloadM9') < s.find('if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED)'))
ck('legacy_sat_diag_modes_not_in_tone_bank', 'int[] bridgeProbeModes = {50, 55, 54};' not in s)

bad=[n for n,ok in checks if not ok]
if bad:
    raise SystemExit('M9TONEAUTH1A verify failed: '+', '.join(bad))
print('M9TONEAUTH1A VERIFY PASS', len(checks), 'checks')
