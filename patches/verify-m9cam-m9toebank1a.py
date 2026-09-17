#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("PhotonCamera")
P = ROOT / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
s = P.read_text()
checks = []

def ck(name, cond):
    checks.append((name, bool(cond)))
    print(("PASS" if cond else "FAIL"), name)

ck("schema", "m9cam.renderer.toebank.v1a.sameRAW" in s)
ck("experiment", "M9TOEBANK1A_sameRAW_control_mild_moderate" in s)
ck("suffix_control", "_M9_TOE1A_A_CONTROL" in s)
ck("suffix_mild", "_M9_TOE1A_B_MILD20" in s)
ck("suffix_moderate", "_M9_TOE1A_C_MODERATE40" in s)
ck("strength_bank", "double[] toeStrength1AFlags = {0.0, 0.20, 0.40};" in s)
ck("mode0_all", "int[] bridgeProbeModes = {0, 0, 0};" in s)
ck("control_selfmeters", "boolean[] selfMeterFlags = {true, false, false};" in s)
ck("locked_variants_exact_control_gain", "variantFixedGain = skyChromaControlEffectiveRenderGain;" in s)
ck("old_half_removed", "Math.sqrt(skyChromaControlTc20BaselineGain)" not in s)
ck("old_zero_removed", "variantFixedGain = edgeFactor;" not in s)
ck("toe_helper", "private static JSONObject applyM9Toe1A(Bitmap bitmap, double strength)" in s)
ck("toe_bt601", "(4899 * r + 9617 * g + 1868 * b) >>> 14" in s)
ck("toe_black_anchor", 'j.put("blackAnchorY", 0)' in s)
ck("toe_cutoff", 'j.put("cutoffY", 64)' in s)
ck("toe_no_local", 'j.put("localMasking", false)' in s)
ck("toe_no_semantic", 'j.put("semanticSceneLogic", false)' in s)
ck("toe_no_global_ev", 'j.put("globalEvOffset", 0.0)' in s)
ck("high_identity", 'j.put("highTonesY64PlusExactIdentity", true)' in s)
ck("black_identity", 'j.put("blackY0ExactIdentity", true)' in s)
ck("tonebound050_retained", "m9cam.tonebound.v1a.050ev" in s)
ck("m9_sensor_target_retained", "M9SENSORTARGET1A" in s)
ck("fullsource_retained", "_M9_SOURCEFULLNORM1A_GAINLOCK.jpg" in s)
ck("identity_hsm_retained", "identity_90x30_no_Adobe_HueSatMap_target_stage" in s)
ck("sat2_retained", "SAT2_M04_M05" in s and "public static final int SATURATION_BANK = 2;" in s)
ck("curve02_retained", "m9_curve02_firmware.bin" in s or "firmware curve02" in s)
ck("bt601_retained", "exact BT601 4:2:2" in s)
ck("tg1_retained", "M9Modern TG1" in s)
ck("primary_saved_before_bank",
   s.find("boolean jpgSaved = ImageSaver.Util.saveBitmapAsJPGPayloadM9") >= 0
   and s.find("if (primaryRoute && DEMOSAIC_DIAGNOSTIC_BANK_ENABLED)") >
       s.find("boolean jpgSaved = ImageSaver.Util.saveBitmapAsJPGPayloadM9"))
ck("legacy_toneauth_outputs_removed",
   "_TONEAUTH_A_FULL_TC20" not in s and "_TONEAUTH_B_HALF_TC20" not in s and "_TONEAUTH_C_ZERO_TC20" not in s)

bad = [name for name, ok in checks if not ok]
if bad:
    raise SystemExit("M9TOEBANK1A verify failed: " + ", ".join(bad))
print("M9TOEBANK1A VERIFY PASS", len(checks), "checks")
