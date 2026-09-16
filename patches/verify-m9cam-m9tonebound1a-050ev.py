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

ck("tone-bound schema", 'm9cam.tonebound.v1a.050ev' in s)
ck("authority limit 0.5 EV", 'final double toneBoundLimitEv1A = 0.5;' in s)
ck("original TC20 retained", 'final double toneBoundOriginalTc20Gain1A = meter.gain;' in s)
ck("EV clamp symmetric", 'Math.max(-toneBoundLimitEv1A, Math.min(toneBoundLimitEv1A, toneBoundOriginalTc20Ev1A))' in s)
ck("gain reconstructed from EV", 'Math.pow(2.0, toneBoundAppliedTc20Ev1A)' in s)
ck("composed effective gain scaled by ratio", 'toneBoundUnboundedEffectiveGain1A * toneBoundScale1A' in s)
ck("self-meter only", 'meterParitySelfMeter' in s and 'fixedPrimaryPathBypassed' in s)
ck("clamp telemetry", 'toneBound1AJson.put("clampEngaged", toneBoundClampEngaged1A);' in s)
ck("direction telemetry", 'toneBound1AJson.put("clampDirection"' in s)
ck("unbounded gain telemetry", 'toneBound1AJson.put("unboundedEffectiveRenderGain"' in s)
ck("bounded gain telemetry", 'toneBound1AJson.put("boundedEffectiveRenderGain"' in s)
ck("tone-bound json attached", 'd.put("toneBound1A", toneBound1AJson);' in s)
ck("capture exposure frozen", 'toneBound1AJson.put("captureExposureMutation", false);' in s)
ck("meter calculation frozen", 'toneBound1AJson.put("tc20MeterMutation", false);' in s)
ck("curve02 frozen", 'toneBound1AJson.put("curve02Mutation", false);' in s)
ck("saturation frozen", 'toneBound1AJson.put("saturationColorMutation", false);' in s)
ck("identity HSM retained telemetry", 'toneBound1AJson.put("identityHsmRetained", true);' in s)
ck("SAT2 retained telemetry", 'toneBound1AJson.put("saturationBank", "SAT2_M04_M05");' in s)

# The build must be a single primary render, not the expensive same-RAW A/B/C bank.
ck("no TONEAUTH ABC render hook", 'M9TONEAUTH1A_sameRAW_ABC' not in s)
ck("no half variant output", '_TONEAUTH_B_HALF_TC20.jpg' not in s)
ck("no zero variant output", '_TONEAUTH_C_ZERO_TC20.jpg' not in s)

# Frozen recovered M9 stages.
ck("true SAT2 maps bank2 to native mode9", 'SATURATION_BANK == 2 ? 9' in s)
ck("SAT2 selected telemetry", 'SAT2_STANDARD_M04_M05' in s)
ck("identity HSM", 'identity_90x30_no_Adobe_HueSatMap_target_stage' in s)
ck("Cobalt HSM disabled", 'cobaltHueSatMapApplied", false' in s)
ck("curve02", 'curve02 normal-ISO sRGB Standard' in s)
ck("BT601", 'exact BT601 4:2:2' in s)
ck("TG1", 'M9Modern TG1' in s)
ck("native cpp exists", CPP.exists())

# Clamp must not overwrite the frozen meter itself.
for bad in [
    r'meter\.gain\s*=\s*toneBound',
    r'meter\.baseGain\s*=\s*toneBound',
    r'meter\.guardGain\s*=\s*toneBound',
]:
    ck("no meter feedback: " + bad, re.search(bad, s) is None)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS " if ok else "FAIL ") + name)
if failed:
    raise SystemExit("M9TONEBOUND1A verify failed: " + ", ".join(failed))
print("M9TONEBOUND1A VERIFY PASS")
print("Only TC20 render authority is bounded; capture, meter, SAT2 and curve02 remain frozen")
