#!/usr/bin/env python3
"""EXACTPERF1A native parity: build the 3.42 parent and 3.43 candidate kernels on the host.

Usage: native_parity.py PARENT_SOURCE CANDIDATE_SOURCE OUTPUT_DIR [--quick]

Compares, byte for byte:
  * the DNG noise filter: parent serial vs candidate serial and band-parallel (1..64 workers),
    plus the production RAW16 adapter end to end;
  * the phase-noise kernel: parent static scheduling vs candidate dynamic scheduling
    (1..8 workers), and the parent against its scalar oracle;
  * the DNG writer (dngCreator.cpp): candidate built at -O0 vs -O2.
The std::thread DNG noise kernel is also run under ThreadSanitizer.
These are x86 host results, not phone measurements.
"""
from pathlib import Path
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FLAGS = ["-std=c++17", "-O2", "-ffp-contract=off", "-fno-fast-math"]


def exported(source):
    return sorted(set(re.findall(r'extern "C"[^(;{]*?\b(\w+)\s*\(', source.read_text())))


def compile_object(source, output, defines=(), extra=()):
    cmd = ["g++", *FLAGS, *extra, "-fopenmp", "-pthread", "-c", str(source), "-o", str(output)]
    cmd += [f"-D{d}" for d in defines]
    subprocess.run(cmd, check=True)
    return output


def build_parity(parent, candidate, out, extra=(), name="native_parity"):
    cpp_p, cpp_c = parent / "app/src/main/cpp", candidate / "app/src/main/cpp"
    objs = []
    phase_names = [n for n in exported(cpp_p / "colourtrial1c/phase_noise.cpp")]
    objs.append(compile_object(cpp_p / "colourtrial1c/phase_noise.cpp", out / f"{name}_parent_phase.o",
                               [f"{n}=parent_{n}" for n in phase_names], extra))
    objs.append(compile_object(cpp_p / "m9dngnoise/shaded_noise.cpp", out / f"{name}_parent_shaded.o",
                               ["phone_noise_shaded=parent_phone_noise_shaded"], extra))
    objs.append(compile_object(cpp_p / "m9dngnoise/raw16_adapter.cpp", out / f"{name}_parent_adapter.o",
                               ["phone_noise_shaded=parent_phone_noise_shaded",
                                "m9_dng_noise_raw16=parent_m9_dng_noise_raw16"], extra))
    objs.append(compile_object(cpp_c / "colourtrial1c/phase_noise.cpp", out / f"{name}_cand_phase.o", (), extra))
    objs.append(compile_object(cpp_c / "m9dngnoise/shaded_noise.cpp", out / f"{name}_cand_shaded.o", (), extra))
    objs.append(compile_object(cpp_c / "m9dngnoise/raw16_adapter.cpp", out / f"{name}_cand_adapter.o", (), extra))
    harness = compile_object(HERE / "native_parity.cpp", out / f"{name}_harness.o", (), extra)
    binary = out / name
    subprocess.run(["g++", *extra, "-fopenmp", "-pthread", str(harness), *map(str, objs), "-o", str(binary)], check=True)
    return binary


def run(binary, *args):
    result = subprocess.run([str(binary), *args], text=True, capture_output=True)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result


def dng_writer_levels(candidate, out):
    cpp = candidate / "app/src/main/cpp"
    java_home = Path(subprocess.check_output(["bash", "-c", "dirname $(dirname $(readlink -f $(which javac)))"], text=True).strip())
    outputs = {}
    for level in ["-O0", "-O2"]:
        directory = out / f"dng_writer{level}"
        directory.mkdir(exist_ok=True)
        subprocess.run(["g++", "-std=c++14", level, "-ffp-contract=off", "-fno-fast-math",
                        "-I", str(HERE / "stub"), "-I", str(java_home / "include"),
                        "-I", str(java_home / "include/linux"), "-I", str(cpp), "-I", str(cpp / "deps"),
                        str(HERE / "dng_writer_probe.cpp"), "-o", str(directory / "probe"), "-ldl"], check=True)
        subprocess.run([str(directory / "probe"), str(directory)], check=True)
        outputs[level] = {p.name: p.read_bytes() for p in sorted(directory.glob("probe*.dng"))}
    names = sorted(outputs["-O0"])
    same = names == sorted(outputs["-O2"]) and len(names) == 4 and all(outputs["-O0"][n] == outputs["-O2"][n] for n in names)
    return {"files": {n: len(outputs["-O0"][n]) for n in names}, "identical": same}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    quick = "--quick" in sys.argv
    parent, candidate, out = (Path(a).resolve() for a in args)
    out.mkdir(parents=True, exist_ok=True)
    report = {"revision": "M9EXACTPERF1A_NATIVE_PARITY", "scope": "x86 host, not handset execution"}

    binary = build_parity(parent, candidate, out)
    main_run = run(binary, *(["--quick"] if quick else []))
    report["kernelParity"] = {"exitCode": main_run.returncode,
                              "lines": [l for l in main_run.stdout.splitlines() if l]}

    tsan = build_parity(parent, candidate, out, ["-fsanitize=thread", "-g"], "native_parity_tsan")
    tsan_run = run(tsan, "--dng-quick")
    report["threadSanitizerDngNoise"] = {"exitCode": tsan_run.returncode,
                                         "dataRaceReported": "ThreadSanitizer" in tsan_run.stderr}

    report["dngWriterOptimizationLevels"] = dng_writer_levels(candidate, out)

    ok = (main_run.returncode == 0 and tsan_run.returncode == 0
          and not report["threadSanitizerDngNoise"]["dataRaceReported"]
          and report["dngWriterOptimizationLevels"]["identical"])
    report["status"] = "PASS" if ok else "FAIL"
    (out / "NATIVE_PARITY.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "kernelParity"}, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
