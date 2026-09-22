"""Host wrapper for the standalone DETAIL1G native guard (no SciPy dependency)."""
from pathlib import Path
import ctypes as C
import subprocess
import numpy as np

class NativeGuard:
    def __init__(self, build, optimization='-O2'):
        if optimization not in ('-O0', '-O2'): raise ValueError('unsupported build option')
        build = Path(build); build.mkdir(parents=True, exist_ok=True)
        so = build / ('noise2_guard_native_' + optimization[1:] + '.so')
        self.command = ['g++', '-std=c++17', optimization, '-Wall', '-Wextra', '-Werror',
                        '-ffp-contract=off', '-fno-fast-math', '-fPIC', '-shared',
                        str(Path(__file__).with_suffix('.cpp')), '-o', str(so)]
        subprocess.run(self.command, check=True)
        self.lib = C.CDLL(str(so.resolve()))
        self.lib.noise2_guard_native.argtypes = [C.c_void_p]*3 + [C.c_int]*3 + [C.c_double]*3 + [C.c_void_p]*4
        self.lib.noise2_guard_native.restype = C.c_int
        self.lib.noise2_profile_rgb.argtypes = [C.c_void_p, C.c_int, C.c_void_p]
        self.lib.noise2_profile_rgb.restype = C.c_int

    def profile_rgb(self, cfa_pairs, cfa):
        p = np.ascontiguousarray(cfa_pairs, dtype=np.float64)
        if p.shape != (4, 2): raise ValueError('four Camera2 CFA pairs required')
        out = np.empty((3, 2), np.float64)
        if self.lib.noise2_profile_rgb(p.ctypes.data, cfa, out.ctypes.data):
            raise ValueError('invalid CFA or profile')
        return out

    def apply(self, carrier, cfa, nr, nb, raw_variance14, censored=None, strength=1.):
        c = np.ascontiguousarray(carrier, dtype=np.int32)
        v = np.ascontiguousarray(raw_variance14, dtype=np.float64)
        if c.ndim != 2 or v.shape != c.shape: raise ValueError('invalid variance or shape')
        mask = None if censored is None else np.ascontiguousarray(np.asarray(censored) != 0, dtype=np.uint8)
        if mask is not None and mask.shape != c.shape: raise ValueError('invalid censor mask')
        h, w = c.shape
        arrays = [np.empty(c.shape, dtype=t) for t in (np.int32, np.int32, np.float32, np.float32)]
        rc = self.lib.noise2_guard_native(c.ctypes.data, v.ctypes.data, None if mask is None else mask.ctypes.data,
              w, h, cfa, nr, nb, strength, *[z.ctypes.data for z in arrays])
        if rc == -2: raise MemoryError('native guard allocation failed')
        if rc: raise ValueError('outside audited native guard input range')
        return tuple(arrays)  # corrected carrier, mode1 target, residual variance, confidence
