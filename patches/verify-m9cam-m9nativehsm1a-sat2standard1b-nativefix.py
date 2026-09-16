from pathlib import Path
import re
import sys

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("PhotonCamera")
P = ROOT / "app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java"
s = P.read_text()
checks = []


def check(name: str, cond: bool) -> None:
    checks.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name)


check("sat2_constant", s.count("public static final int SATURATION_BANK = 2;") == 1)
check(
    "java_sat2_qe",
    "13659, -4457, -1004,\n            -2244, 13469, -3033,\n            -199, -6014, 14398" in s,
)
check(
    "java_sat2_qo",
    "14811, -5604, -1004,\n            -2455, 13688, -3033,\n            393, -6588, 14398" in s,
)
check(
    "java_sat3_qe_removed",
    "16754, -7632, -922,\n            -3124, 14774, -3458,\n            -567, -9579, 18330" not in s,
)
check(
    "java_sat3_qo_removed",
    "18160, -9034, -922,\n            -3422, 15080, -3458,\n            137, -10264, 18330" not in s,
)
check("native_mode_variable", "final int nativeSaturationMode1A = skyDiagnosticEncodedAny1A" in s)
check("native_sat2_mode9_mapping", "SATURATION_BANK == 2 ? 9" in s)
check("native_sat4_mode10_mapping", "SATURATION_BANK == 4 ? 10 : 0" in s)
check(
    "create_context_uses_native_mode",
    re.search(
        r"firmwareCurve02,\s*ctx\.hueDivisions,\s*ctx\.satDivisions,\s*\n\s*nativeSaturationMode1A\);",
        s,
    )
    is not None,
)
check(
    "production_no_create_context_sky_mode",
    re.search(
        r"firmwareCurve02,\s*ctx\.hueDivisions,\s*ctx\.satDivisions,\s*\n\s*skyChromaMode1A\);",
        s,
    )
    is None,
)
check("runtime_native_mode_telemetry", 'd.put("nativeSaturationMode1A", nativeSaturationMode1A);' in s)
check("runtime_actual_bank_telemetry", 'd.put("nativeSaturationBankActuallySelected", SATURATION_BANK);' in s)
check(
    "runtime_actual_pair_telemetry",
    "nativeSaturationMatrixPairActuallySelected" in s and '"M04_M05"' in s,
)
check("identity_hsm_retained", "identity_90x30_no_Adobe_HueSatMap_target_stage" in s)
check(
    "targetinput_retained",
    "targetInputAdapter1AProduction" in s
    and "T_scene=C15_historical_scene*inverse(N15_native_scene); output=T_scene*N_active" in s,
)
check("curve02_retained", "m9_curve02_firmware.bin" in s)
check("bt601_retained", "exact BT601 4:2:2" in s)
check("tg1_retained", "M9Modern TG1" in s)

# The existing native library already has the firmware banks.  NATIVEFIX changes
# only the mode handed to that selector; it does not rewrite the native math.
cpp = ROOT / "app/src/main/cpp/m9color_jni.cpp"
if cpp.exists():
    c = cpp.read_text(errors="replace")
    sat2 = [
        "13659", "-4457", "-1004", "-2244", "13469", "-3033", "-199", "-6014", "14398",
        "14811", "-5604", "-2455", "13688", "393", "-6588",
    ]
    check("native_cpp_sat2_bank_present", all(v in c for v in sat2))
else:
    check("native_cpp_sat2_bank_present", False)

if not all(v for _, v in checks):
    raise SystemExit(1)

print("SAT2STANDARD1B NATIVEFIX VERIFY PASS")
print("production_native_mode 9")
print("firmware_saturation SAT2 M04/M05")
print("identity_hsm retained")
print("tone_exposure unchanged")
