#!/usr/bin/env python3
"""AMAZESIMD350 parity: the arm64 vector AMaZE must equal AMaZE's SSE2 path bit for bit.

Usage: simd_parity350.py PARENT_349_SOURCE CANDIDATE_350_SOURCE OUTPUT_DIR
Needs g++, clang++, aarch64-linux-gnu-g++ and qemu-aarch64.

Builds the same integer-generated test frames with:
  x86 SSE2 (RawTherapee's vector path, the reference),
  x86 and arm64 builds of the 3.50 portable vector path (GCC; clang for AMaZE on arm64),
  arm64 3.49 (scalar, what the phone ran before) and arm64 3.50 with the vector path disabled.
Gates: every 3.50 vector build == x86 SSE2; 3.50 scalar fallback == 3.49 on arm64.
Reports how 3.50 differs from 3.49 (the only intended change: scalar -> vector AMaZE).
"""
from pathlib import Path
import json
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
CASES = [(1024, 768, cfa, noise) for cfa in range(4) for noise in (0, 1)] + [(4096, 3072, 0, 1)]
GCC = '13'


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


def build(src, out, cxx, *flags):
    run(['bash', str(HERE / 'build.sh'), str(src), str(out), cxx, *flags])


def build_clang_arm(src, out, work):
    cpp = src / 'app/src/main/cpp'; ct = cpp / 'colourtrial1c'
    inc = ['-isystem', f'/usr/aarch64-linux-gnu/include/c++/{GCC}', '-isystem',
           f'/usr/aarch64-linux-gnu/include/c++/{GCC}/aarch64-linux-gnu', '-isystem', '/usr/aarch64-linux-gnu/include']
    obj = work / 'amaze_clang_arm.o'
    run(['clang++', '--target=aarch64-linux-gnu', '-std=c++17', '-O3', '-ffp-contract=off', '-fno-fast-math', '-w',
         *inc, '-I' + str(ct / 'upstream/include'), '-c', str(ct / 'upstream/amaze.cc'), '-o', str(obj)])
    # Link every other file with the GCC cross toolchain (OpenMP via libgomp).
    stub = work / 'stub'; (stub / 'android').mkdir(parents=True, exist_ok=True)
    (stub / 'android/bitmap.h').write_text((HERE / 'build.sh').read_text().split("<<'H'\n", 1)[1].split('\nH\n', 1)[0] + '\n')
    javac = Path(subprocess.check_output(['bash', '-c', 'readlink -f "$(which javac)"'], text=True).strip())
    jinc = javac.parent.parent / 'include'
    run(['aarch64-linux-gnu-g++', '-std=c++17', '-O3', '-pthread', '-fopenmp', '-ffp-contract=off', '-fno-fast-math',
         '-static', '-w', '-I' + str(stub), '-I' + str(jinc), '-I' + str(jinc / 'linux'), '-I' + str(cpp),
         '-I' + str(ct / 'upstream/include'), str(HERE / 'amaze_simd_parity.cpp'),
         str(HERE.parents[1] / 'prepperf1b/host.cpp'), *[str(ct / f) for f in
         ('reconstruct.cpp', 'phase_noise.cpp', 'chroma.cpp', 'upstream/border.cc')], str(obj), '-o', str(out)])
    return subprocess.check_output(['bash', '-c', f'aarch64-linux-gnu-objdump -d --no-show-raw-insn {obj} | '
                                    "grep -cE '\\s(fmul|fadd|fsub|fdiv)\\s+v[0-9]+\\.4s' || true; "
                                    f"aarch64-linux-gnu-objdump -d {obj} | grep -cE 'fmla|fmadd|fmls|fmsub' || true"],
                                   text=True).split()


def main():
    parent, cand, out = (Path(a).resolve() for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    builds = {
        'x86_sse2_350': (cand, 'g++', [], False),
        'x86_portable_350': (cand, 'g++', ['-U__SSE2__', '-DM9_PORTABLE_SIMD'], False),
        'arm64_gcc_portable_350': (cand, 'aarch64-linux-gnu-g++', ['-static', '-w'], True),
        'arm64_scalar_349': (parent, 'aarch64-linux-gnu-g++', ['-static', '-w'], True),
        'arm64_forced_scalar_350': (cand, 'aarch64-linux-gnu-g++', ['-static', '-w', '-DM9_AMAZE_FORCE_SCALAR'], True),
    }
    for name, (src, cxx, flags, _) in builds.items():
        build(src, out / name, cxx, *flags)
    vec_ops, fma_ops = build_clang_arm(cand, out / 'arm64_clang_portable_350', out)
    builds['arm64_clang_portable_350'] = (cand, 'clang++', [], True)
    report = {'revision': 'M9AMAZESIMD350_PARITY', 'scope': 'x86 host and arm64 under qemu; not handset timing',
              'clangArm64AmazeVectorFloatOps': int(vec_ops), 'clangArm64AmazeFusedMultiplyAdds': int(fma_ops),
              'cases': []}
    ok = int(vec_ops) > 100 and int(fma_ops) == 0
    for w, h, cfa, noise in CASES:
        res, paths = {}, {}
        for name, (_, _, _, arm) in builds.items():
            path = out / f'{name}_{w}x{h}_{cfa}_{noise}.bin'
            cmd = ([ 'qemu-aarch64'] if arm else []) + [str(out / name), str(path), str(w), str(h), str(cfa), str(noise), '4', '1']
            paths[name] = subprocess.check_output(cmd, text=True).split()[0]
            res[name] = np.fromfile(path, np.uint16)
        ref = res['x86_sse2_350']
        vector_equal = all(np.array_equal(res[n], ref) for n in res if 'portable' in n)
        scalar_equal = np.array_equal(res['arm64_forced_scalar_350'], res['arm64_scalar_349'])
        path_ok = (paths['arm64_gcc_portable_350'] == paths['arm64_clang_portable_350'] == 'path=M9AMAZESIMD350_PORTABLE_VECTOR'
                   and paths['x86_sse2_350'] == 'path=SSE2' and paths['arm64_scalar_349'] == 'path=SCALAR_349'
                   and paths['arm64_forced_scalar_350'] == 'path=SCALAR')
        old, new = res['arm64_scalar_349'].astype(np.int32), res['arm64_gcc_portable_350'].astype(np.int32)
        d = np.abs(new - old)
        row = {'size': [w, h], 'cfa': cfa, 'phaseNoise': bool(noise), 'arm64VectorEqualsSse2': bool(vector_equal),
               'arm64ScalarFallbackEquals349': bool(scalar_equal), 'differsFrom349Percent': round(float(np.mean(d > 0)) * 100, 3),
               'maxAbsDiff16bit': int(d.max()), 'meanAbsDiff16bit': round(float(d.mean()), 4),
               'samplesDifferingAtLeast1of256': int(np.sum(d >= 256))}
        row['compiledPathsReported'] = bool(path_ok)
        ok &= vector_equal and scalar_equal and path_ok
        report['cases'].append(row)
        print(f"{'PASS' if vector_equal and scalar_equal else 'FAIL'} {w}x{h} cfa {cfa} noise {noise}: "
              f"vector==SSE2 {vector_equal}, scalar==3.49 {scalar_equal}, differs from 3.49 in {row['differsFrom349Percent']}% "
              f"(max {row['maxAbsDiff16bit']}/65535)", flush=True)
    report['status'] = 'PASS' if ok else 'FAIL'
    (out / 'AMAZE_SIMD_PARITY_350.json').write_text(json.dumps(report, indent=2) + '\n')
    print('ALL_PASS' if ok else 'FAILED', f'(clang arm64 AMaZE: {vec_ops} vector float ops, {fma_ops} fused multiply-adds)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
