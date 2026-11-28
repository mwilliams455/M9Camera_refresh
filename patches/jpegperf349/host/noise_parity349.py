#!/usr/bin/env python3
"""JPEGPERF349 noise-cancel parity: 3.48 parent versus the 3.49 wide-frame row floor.

Usage: noise_parity349.py PARENT_SOURCE CANDIDATE_SOURCE OUTPUT_DIR

Pixels must equal the 3.48 parent and the frozen scalar reference at every size. Frames up
to 4096 wide must also schedule exactly as 3.48 (same workers, bit-identical statistics);
wider frames must keep 8 workers. Also runs the band queue under ThreadSanitizer on a wide,
short frame. x86 host evidence only; not handset timing.
"""
from pathlib import Path
import ctypes as C
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
P, I, D = C.c_void_p, C.c_int, C.c_double


def build(root, out, name):
    so = out / f'{name}_noise.so'
    subprocess.run(['g++', '-std=c++17', '-O2', '-fPIC', '-shared', '-pthread', '-ffp-contract=off', '-fno-fast-math',
                    '-DM9NOISEPERF1A_HOST', str(root / 'app/src/main/cpp/m9noisecancel1b.cpp'), '-o', str(so)], check=True)
    lib = C.CDLL(str(so))
    for fn in ('m9_noisecancel1b_apply', 'm9_noisecancel1b_apply_scalar_reference'):
        getattr(lib, fn).argtypes = [P, I, I, P, P, I, I, D, P]
        getattr(lib, fn).restype = I
    return lib


def frame(w, h, rng):
    yy, xx = np.indices((h, w))
    g = np.clip(9000 + 18 * (xx % 1024) + 7 * (yy % 1024) + rng.normal(0, 170, (h, w)), 0, 65535)
    r = np.clip(g + 1300 * np.sin(xx / 21.0) + rng.normal(0, 520, (h, w)), 0, 65535)
    b = np.clip(g - 900 * np.cos(yy / 17.0) + rng.normal(0, 610, (h, w)), 0, 65535)
    rgb = np.stack([r, g, b], axis=2).astype(np.uint16)
    rgb[h // 9:h // 9 + 25, w // 7:w // 7 + 30] = 0
    rgb[h // 3:h // 3 + 30, w // 2:w // 2 + 40] = 65535
    return rgb


def main():
    parent_root, cand_root, out = (Path(a).resolve() for a in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    parent, cand = build(parent_root, out, 'parent348'), build(cand_root, out, 'cand349')
    mw, mh, scale = 17, 13, 1.72
    profile = np.array([.00135, 6.7e-6, .00134, 6.1e-6, .00137, 6.8e-6], np.float64)
    gains = np.empty((mh, mw, 4))
    for gy in range(mh):
        for gx in range(mw):
            c = min(scale, max(.98, 1 + (scale - 1) * ((gx / (mw - 1) - .5) ** 2 + (gy / (mh - 1) - .5) ** 2)))
            gains[gy, gx] = [c * .99, c * .985, c * .985, c * .995]
    gains = gains.reshape(-1)
    rng = np.random.default_rng(349)
    rows, ok = [], True
    for w, h in [(4096, 3072), (3072, 4096), (4000, 3000), (1024, 768), (300, 97), (4097, 400),
                 (6000, 1200), (8000, 6000), (8160, 6144), (8192, 260)]:
        rgb = frame(w, h, rng)
        runs = {}
        for label, fn in (('parent', parent.m9_noisecancel1b_apply), ('cand', cand.m9_noisecancel1b_apply),
                          ('scalar', parent.m9_noisecancel1b_apply_scalar_reference)):
            best, result = None, None
            for _ in range(3):
                a = rgb.copy(); st = np.zeros(14); t = time.perf_counter()
                assert fn(a.ctypes.data, w, h, profile.ctypes.data, gains.ctypes.data, mw, mh, scale, st.ctypes.data) == 0
                ms = (time.perf_counter() - t) * 1000
                best = ms if best is None else min(best, ms); result = (a, st)
                if label == 'scalar':
                    break
            runs[label] = (*result, best)
        pa, ps, pms = runs['parent']; ca, cs, cms = runs['cand']; sa = runs['scalar'][0]
        pixels = np.array_equal(ca, pa) and np.array_equal(ca, sa)
        ints = all(cs[i] == ps[i] for i in (0, 1, 2, 3, 4, 6, 7, 10, 11, 13))
        means = abs(cs[5] - ps[5]) < 1e-11 and abs(cs[8] - ps[8]) < 1e-9
        narrow = w <= 4096
        schedule = (cs[12] == ps[12] and cs[5] == ps[5] and cs[8] == ps[8]) if narrow else cs[12] == 8
        passed = bool(pixels and ints and means and schedule)
        ok &= passed
        rows.append({'size': [w, h], 'pixelsExact': bool(pixels), 'integerStatsExact': bool(ints),
                     'meanStatsWithinTolerance': bool(means), 'parentWorkers': int(ps[12]), 'candidateWorkers': int(cs[12]),
                     'scheduleCheck': 'identical to 3.48' if narrow else '8 workers', 'scheduleOk': bool(schedule),
                     'parentMs': round(pms, 1), 'candidateMs': round(cms, 1)})
        print(f"{'PASS' if passed else 'FAIL'} noise-cancel {w}x{h}: workers {int(ps[12])} -> {int(cs[12])}, "
              f"{pms:.0f} ms -> {cms:.0f} ms", flush=True)
    tsan = out / 'noise_tsan349'
    subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=thread', '-pthread', '-DM9NOISEPERF1A_HOST',
                    str(HERE / 'noise_tsan349.cpp'), str(cand_root / 'app/src/main/cpp/m9noisecancel1b.cpp'),
                    '-o', str(tsan)], check=True)
    run = subprocess.run([str(tsan)], capture_output=True, text=True, env={**os.environ, 'TSAN_OPTIONS': 'halt_on_error=1'})
    print(run.stdout.strip())
    race = 'ThreadSanitizer' in run.stderr
    ok &= run.returncode == 0 and not race
    report = {'revision': 'M9JPEGPERF349_NOISE_PARITY', 'scope': 'x86 host, not handset execution',
              'cases': rows, 'threadSanitizerWideQueue': {'exitCode': run.returncode, 'dataRaceReported': race},
              'status': 'PASS' if ok else 'FAIL'}
    (out / 'NOISE_PARITY_349.json').write_text(json.dumps(report, indent=2) + '\n')
    print('ALL_EXACT' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
