#!/usr/bin/env python3
"""JPEGPERF346 native parity: 3.45 parent versus 3.46 candidate scheduling changes.

Usage: native_parity346.py PARENT_SOURCE CANDIDATE_SOURCE OUTPUT_DIR [--quick]

Byte-compares, between libraries compiled from the two trees:
  * chroma noise cancel (m9_noisecancel1b_apply) and its frozen scalar reference;
  * in-place pre-SAT chroma preparation (trialPrepareInPlace) and the scalar trial_prepare;
  * the production demosaic periphery: trial_variance_parallel + trial_reconstruct_perf
    (phase noise, quarter blend, float input, AMaZE, quantization) for all four CFAs.
x86 host evidence only; not handset timing.
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
REPO = HERE.parents[2]
FLAGS = ['-std=c++17', '-O2', '-fPIC', '-shared', '-pthread', '-fopenmp', '-ffp-contract=off',
         '-fno-fast-math', '-Wl,-Bsymbolic']
P, I, D = C.c_void_p, C.c_int, C.c_double


def java_include():
    javac = Path(subprocess.check_output(['bash', '-c', 'readlink -f $(which javac)'], text=True).strip())
    return javac.parent.parent / 'include'


def bitmap_stub(out):
    inc = out / 'android'
    inc.mkdir(parents=True, exist_ok=True)
    (inc / 'bitmap.h').write_text('''#pragma once
#include <jni.h>
#include <cstdint>
#define ANDROID_BITMAP_FORMAT_RGBA_8888 1
#define ANDROID_BITMAP_RESULT_SUCCESS 0
struct AndroidBitmapInfo {uint32_t width,height,stride;int32_t format;uint32_t flags;};
inline int AndroidBitmap_getInfo(JNIEnv*,jobject,AndroidBitmapInfo*){return -1;}
inline int AndroidBitmap_lockPixels(JNIEnv*,jobject,void**){return -1;}
inline int AndroidBitmap_unlockPixels(JNIEnv*,jobject){return 0;}
''')


def build_colour(root, out, name):
    cpp = root / 'app/src/main/cpp'
    ct = cpp / 'colourtrial1c'
    jinc = java_include()
    so = out / f'{name}_colour.so'
    subprocess.run(['g++', *FLAGS, '-I' + str(out), '-I' + str(jinc), '-I' + str(jinc / 'linux'),
                    '-I' + str(cpp), '-I' + str(ct / 'upstream/include'),
                    str(REPO / 'patches/prepperf1b/host.cpp'),
                    *[str(ct / f) for f in ['reconstruct.cpp', 'phase_noise.cpp', 'chroma.cpp',
                                            'upstream/amaze.cc', 'upstream/border.cc']],
                    '-o', str(so)], check=True)
    lib = C.CDLL(str(so))
    for fn, args in {
        'trial_context': [P, P], 'trial_destroy': [P],
        'trial_prepare': [P, P, I, I, D, P, I], 'trial_prepare_inplace': [P, P, I, I, D, I],
        'trial_variance_parallel': [P, I, I, I, I, P, I, P, P, I, I, D, P, P, I],
        'trial_reconstruct_perf': [P, P, P, I, I, I, D, D, D, P, I, P, P],
    }.items():
        f = getattr(lib, fn)
        f.argtypes = args
        f.restype = P if fn == 'trial_context' else (None if fn == 'trial_destroy' else I)
    return lib


def build_noise(root, out, name):
    jinc = java_include()
    so = out / f'{name}_noise.so'
    subprocess.run(['g++', *FLAGS, '-DM9NOISEPERF1A_HOST', '-I' + str(jinc), '-I' + str(jinc / 'linux'),
                    str(root / 'app/src/main/cpp/m9noisecancel1b.cpp'), '-o', str(so)], check=True)
    lib = C.CDLL(str(so))
    for fn in ('m9_noisecancel1b_apply', 'm9_noisecancel1b_apply_scalar_reference'):
        f = getattr(lib, fn)
        f.argtypes = [P, I, I, P, P, I, I, D, P]
        f.restype = I
    return lib


def noise_cases(parent, cand, quick, report):
    rng = np.random.default_rng(346)
    mw, mh, scale = 17, 13, 1.72
    profile = np.array([.00135, 6.7e-6, .00134, 6.1e-6, .00137, 6.8e-6], np.float64)
    gains = np.empty((mh, mw, 4), np.float64)
    for gy in range(mh):
        for gx in range(mw):
            common = min(scale, max(.98, 1.0 + (scale - 1.0) * ((gx / (mw - 1) - .5) ** 2 + (gy / (mh - 1) - .5) ** 2)))
            gains[gy, gx] = [common * .99, common * .985, common * .985, common * .995]
    gains = np.minimum(gains, scale).reshape(-1)
    sizes = [(768, 1024), (257, 333), (258, 64), (300, 97), (1000, 1001), (3072, 4096)]
    if quick:
        sizes = [(768, 1024), (258, 64), (300, 97)]
    rows = []
    for h, w in sizes:
        yy, xx = np.indices((h, w))
        green = np.clip(9000 + 18 * xx + 7 * yy + rng.normal(0, 170, (h, w)), 0, 65535)
        r = np.clip(green + 1300 * np.sin(xx / 21.0) + rng.normal(0, 520, (h, w)), 0, 65535)
        b = np.clip(green - 900 * np.cos(yy / 17.0) + rng.normal(0, 610, (h, w)), 0, 65535)
        rgb = np.stack([r, green, b], axis=2).astype(np.uint16)
        rgb[h // 9:h // 9 + 25, w // 7:w // 7 + 30] = 0
        rgb[h // 3:h // 3 + 30, w // 2:w // 2 + 40] = 65535
        outs = {}
        for label, fn in (('parent', parent.m9_noisecancel1b_apply), ('cand', cand.m9_noisecancel1b_apply),
                          ('scalar', parent.m9_noisecancel1b_apply_scalar_reference)):
            a = rgb.copy()
            stats = np.zeros(14)
            t = time.perf_counter()
            assert fn(a.ctypes.data, w, h, profile.ctypes.data, gains.ctypes.data, mw, mh, scale, stats.ctypes.data) == 0
            outs[label] = (a, stats, (time.perf_counter() - t) * 1000)
        exact = np.array_equal(outs['cand'][0], outs['parent'][0]) and np.array_equal(outs['cand'][0], outs['scalar'][0])
        ints = all(outs['cand'][1][i] == outs['parent'][1][i] for i in (0, 1, 2, 3, 4, 6, 7, 10, 11, 12, 13))
        floats = abs(outs['cand'][1][5] - outs['parent'][1][5]) < 1e-11 and abs(outs['cand'][1][8] - outs['parent'][1][8]) < 1e-9
        rows.append({'size': [w, h], 'pixelsExact': bool(exact), 'integerStatsExact': bool(ints),
                     'meanStatsWithin1e-9': bool(floats), 'changed': int(outs['cand'][1][1]),
                     'parentMs': round(outs['parent'][2], 1), 'candidateMs': round(outs['cand'][2], 1)})
        print(f"{'PASS' if exact and ints and floats else 'FAIL'} noise-cancel {w}x{h} "
              f"(parent {outs['parent'][2]:.1f} ms, candidate {outs['cand'][2]:.1f} ms)")
    report['noiseCancel'] = rows
    return all(r['pixelsExact'] and r['integerStatsExact'] and r['meanStatsWithin1e-9'] for r in rows)


def prep_cases(parent, cand, root, quick, report):
    rng = np.random.default_rng(1192)
    curve = np.frombuffer((root / 'app/src/main/assets/m9/m9_curve02_firmware.bin').read_bytes(), np.uint8).copy()
    ctx = np.r_[np.ones(3), np.array([[1.1, -.06, -.04], [-.07, 1.11, -.04], [-.03, -.07, 1.10]]).ravel(),
                np.tile(np.eye(3).ravel(), 4)].astype(float)
    cp, cc = parent.trial_context(ctx.ctypes.data, curve.ctypes.data), cand.trial_context(ctx.ctypes.data, curve.ctypes.data)
    sizes = [(1, 9), (3, 3), (31, 37), (129, 385), (130, 257), (385, 513), (1024, 768), (4096, 3072)]
    if quick:
        sizes = [(31, 37), (129, 385), (385, 513)]
    rows, ok = [], True
    for w, h in sizes:
        raw = rng.integers(0, 65536, (h, w, 3), np.uint16)
        oracle = np.empty_like(raw)
        assert parent.trial_prepare(cp, raw.ctypes.data, w, h, 2 ** .25, oracle.ctypes.data, 128) == 0
        for band in ([2, 31, 128, h] if w * h < 2_000_000 else [128]):
            a, b = raw.copy(), raw.copy()
            t = time.perf_counter(); assert parent.trial_prepare_inplace(cp, a.ctypes.data, w, h, 2 ** .25, band) == 0
            pms = (time.perf_counter() - t) * 1000
            t = time.perf_counter(); assert cand.trial_prepare_inplace(cc, b.ctypes.data, w, h, 2 ** .25, band) == 0
            cms = (time.perf_counter() - t) * 1000
            exact = np.array_equal(a, b) and np.array_equal(b, oracle)
            ok &= exact
            rows.append({'size': [w, h], 'band': band, 'exact': bool(exact), 'parentMs': round(pms, 1), 'candidateMs': round(cms, 1)})
            print(f"{'PASS' if exact else 'FAIL'} chroma-prep {w}x{h} band {band} (parent {pms:.1f} ms, candidate {cms:.1f} ms)")
    parent.trial_destroy(cp); cand.trial_destroy(cc)
    report['chromaPrepare'] = rows
    return ok


def reconstruct_cases(parent, cand, quick, report):
    rng = np.random.default_rng(2346)
    mw, mh, white = 17, 13, 1023
    black = np.array([64, 64, 64, 64], np.float32)
    gains = np.empty((mh, mw, 4), np.float64)
    for gy in range(mh):
        for gx in range(mw):
            g = 1 + 1.2 * (((gx - 8) / 8) ** 2 + ((gy - 6) / 6) ** 2)
            gains[gy, gx] = [g * 1.05, g, g, g * 1.08]
    scale = float(gains.max())
    gains = gains.reshape(-1)
    profile = np.array([2e-4, 2e-6, 1.6e-4, 1.5e-6, 2.2e-4, 2.1e-6], np.float64)
    # Even widths only: Bayer frames are even, and for odd widths with CFA 1/3 the unchanged 3.45
    # AMaZE reads one column past the edge, so the parent itself is not repeatable there.
    sizes = [(1024, 768), (776, 515), (4096, 3072)] if not quick else [(776, 515)]
    rows, ok = [], True
    for w, h in sizes:
        yy, xx = np.indices((h, w))
        base = 0.25 + 0.2 * np.sin(xx * 0.01) * np.cos(yy * 0.013) + np.where((xx // 256 + yy // 256) % 2 == 1, 0.1, 0)
        base[int(h * .17):int(h * .26), int(w * .73):int(w * .8)] = 1.5
        s = np.clip(base, 0, 1.2)
        v = black[0] + (white - black[0]) * np.clip(s + np.sqrt(2e-4 * s + 2e-6) * rng.normal(0, 1, (h, w)), 0, 1)
        sensor = np.minimum(white, np.round(v)).astype(np.uint16)
        norm = np.round(np.clip((v - black[0]) / (white - black[0]), 0, 1) * 65535 / scale).astype(np.uint16)
        for cfa in ([0, 1, 2, 3] if w * h < 2_000_000 else [0]):
            for workers in ([1, 3, 8] if w * h < 2_000_000 else [8]):
                res = {}
                for label, lib in (('parent', parent), ('cand', cand)):
                    var = np.zeros((h, w), np.float32); cen = np.zeros((h, w), np.uint8)
                    out = np.zeros((h, w, 3), np.uint16); stats = np.zeros(4); perf = np.zeros(5)
                    t = time.perf_counter()
                    assert lib.trial_variance_parallel(sensor.ctypes.data, w, h, cfa, 0, black.ctypes.data, white,
                                                       profile.ctypes.data, gains.ctypes.data, mw, mh, scale,
                                                       var.ctypes.data, cen.ctypes.data, workers) == 0
                    assert lib.trial_reconstruct_perf(norm.ctypes.data, var.ctypes.data, cen.ctypes.data, w, h, cfa,
                                                      0.55, 0.62, scale, out.ctypes.data, workers,
                                                      stats.ctypes.data, perf.ctypes.data) == 0
                    res[label] = (var, cen, out, stats, (time.perf_counter() - t) * 1000)
                exact = all(np.array_equal(res['parent'][i], res['cand'][i]) for i in range(4))
                ok &= exact
                rows.append({'size': [w, h], 'cfa': cfa, 'workers': workers, 'exact': bool(exact),
                             'parentMs': round(res['parent'][4], 1), 'candidateMs': round(res['cand'][4], 1)})
                print(f"{'PASS' if exact else 'FAIL'} demosaic-periphery {w}x{h} cfa {cfa} workers {workers} "
                      f"(parent {res['parent'][4]:.1f} ms, candidate {res['cand'][4]:.1f} ms)")
    report['reconstructPeriphery'] = rows
    report['reconstructPeripheryNote'] = 'even widths only; odd-width CFA 1/3 is non-repeatable in the 3.45 parent itself'
    return ok


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    quick = '--quick' in sys.argv
    parent_root, cand_root, out = (Path(a).resolve() for a in args)
    out.mkdir(parents=True, exist_ok=True)
    bitmap_stub(out)
    report = {'revision': 'M9JPEGPERF346_NATIVE_PARITY', 'scope': 'x86 host, not handset execution'}
    pn, cn = build_noise(parent_root, out, 'parent'), build_noise(cand_root, out, 'cand')
    pc, cc = build_colour(parent_root, out, 'parent'), build_colour(cand_root, out, 'cand')
    ok = noise_cases(pn, cn, quick, report)
    tsan_bin = out / 'noise_tsan'
    subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=thread', '-pthread', '-DM9NOISEPERF1A_HOST',
                    str(HERE / 'noise_tsan.cpp'), str(cand_root / 'app/src/main/cpp/m9noisecancel1b.cpp'),
                    '-o', str(tsan_bin)], check=True)
    tsan = subprocess.run([str(tsan_bin)], capture_output=True, text=True,
                          env={**os.environ, 'TSAN_OPTIONS': 'halt_on_error=1'})
    print(tsan.stdout.strip())
    report['threadSanitizerNoiseQueue'] = {'exitCode': tsan.returncode,
                                           'dataRaceReported': 'ThreadSanitizer' in tsan.stderr}
    ok &= tsan.returncode == 0 and 'ThreadSanitizer' not in tsan.stderr
    ok &= prep_cases(pc, cc, cand_root, quick, report)
    ok &= reconstruct_cases(pc, cc, quick, report)
    report['status'] = 'PASS' if ok else 'FAIL'
    (out / 'NATIVE_PARITY_346.json').write_text(json.dumps(report, indent=2) + '\n')
    print('ALL_EXACT' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
