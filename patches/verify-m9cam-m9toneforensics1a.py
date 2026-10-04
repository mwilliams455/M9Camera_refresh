from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("PhotonCamera")
P = ROOT / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
CPP = ROOT / "app/src/main/cpp/m9color_jni.cpp"
s = P.read_text()

checks = []
def ck(name, cond):
    checks.append((name, bool(cond)))

# Read-only tone-forensics anchors.
ck("tone schema", 'm9cam.toneforensics.v1a.readonly' in s)
ck("diagnostic only", 'j.put("diagnosticOnly", true)' in s)
ck("no photographic pixel change", 'j.put("photographicPixelChange", false)' in s)
ck("no capture exposure mutation", 'j.put("captureExposureMutation", false)' in s)
ck("no tc20 mutation", 'j.put("tc20Mutation", false)' in s)
ck("no curve02 mutation", 'j.put("curve02Mutation", false)' in s)
ck("no saturation mutation", 'j.put("saturationColorMutation", false)' in s)
ck("native weighted median captured", 'out.median = validCount > 0 ? nativeStats[0] : Double.NaN;' in s)
ck("java weighted median captured", 'out.median = median;' in s)
ck("valid count captured", 'out.validCount = validCount;' in s)
ck("tone json attached", 'd.put("toneForensics1A", toneForensics1AJson);' in s)
ck("current TC20 gain observed", 'final double currentGain = meter.gain;' in s)
ck("half authority prospective only", 'final double halfGain = Math.sqrt(Math.max(currentGain, 0.0));' in s)
ck("zero authority prospective only", 'final double zeroGain = 1.0;' in s)
ck("raw span q998 q50", 'q99_8_over_q50_ev' in s)
ck("limiter telemetry", 'limitingDecision' in s and 'raw_tail_headroom_guard' in s and 'median_target' in s)
ck("proxy warning", 'raw_linear_proxy_only_downstream_M9_matrix_curve_can_clip_differently' in s)

# Guard against accidentally feeding a prospective tone probe back into rendering.
for bad in [
    r'meter\.gain\s*=\s*halfGain',
    r'meter\.gain\s*=\s*zeroGain',
    r'meterParityRenderBaseGain\s*=\s*halfGain',
    r'meterParityRenderBaseGain\s*=\s*zeroGain',
    r'effectiveRenderGain\s*=\s*halfGain',
    r'effectiveRenderGain\s*=\s*zeroGain',
]:
    ck("no feedback: " + bad, re.search(bad, s) is None)

# Freeze the true-SAT2 colour baseline while tone is diagnosed. The reconstructed
# parent executes the dedicated SAT2STANDARD1B verifier first, so here we guard
# the actual production selection seams rather than duplicating its source-format
# check for the SATURATION_BANK declaration.
ck("production SAT2 maps bank2 to native mode9", 'SATURATION_BANK == 2 ? 9' in s)
ck("native context consumes selected mode", 'nativeSaturationMode1A);' in s)
ck("runtime native mode telemetry", 'd.put("nativeSaturationMode1A", nativeSaturationMode1A);' in s)
ck("runtime actual bank telemetry", 'd.put("nativeSaturationBankActuallySelected", SATURATION_BANK);' in s)
ck("runtime M04/M05 telemetry", 'nativeSaturationMode1A == 9 ? "M04_M05"' in s)
ck("SAT2 selected telemetry", 'SAT2_STANDARD_M04_M05' in s)
ck("identity HSM retained", 'identity_90x30_no_Adobe_HueSatMap_target_stage' in s)
ck("Cobalt HSM disabled", 'cobaltHueSatMapApplied", false' in s)
ck("curve02 retained", 'curve02 normal-ISO sRGB Standard' in s)
ck("BT601 retained", 'exact BT601 4:2:2' in s)
ck("TG1 retained", 'M9Modern TG1' in s)
ck("native cpp exists", CPP.exists())

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS " if ok else "FAIL ") + name)
if failed:
    raise SystemExit("M9TONEFORENSICS1A verify failed: " + ", ".join(failed))
print("M9TONEFORENSICS1A VERIFY PASS")
print("Tone/exposure/color pixels remain frozen; telemetry only")
