"""Generic offline ABI for the two independent RAW experiments."""
from pathlib import Path
import ctypes as C
import subprocess
import numpy as np

class Reconstruction:
    def __init__(self, build):
        build = Path(build); build.mkdir(parents=True, exist_ok=True)
        so = build / 'reconstruct.so'
        subprocess.run(['g++', '-O3', '-std=c++17', '-shared', '-fPIC',
                        '-fopenmp', '-ffp-contract=off', '-fno-fast-math',
                        str(Path(__file__).with_name('reconstruct.cpp')),
                        '-o', str(so)], check=True)
        self.lib = C.CDLL(str(so.resolve()))
        self.lib.phase_noise.argtypes = [C.c_void_p]*3+[C.c_int]*2+[C.c_void_p,C.c_int]
        self.lib.clipped_ratio.argtypes = [C.c_void_p]*4+[C.c_int]*3+[C.c_double]*2+[C.c_void_p,C.c_int]

    @staticmethod
    def arrays(raw, variance, flags):
        raw = np.ascontiguousarray(raw, np.uint16)
        variance = np.ascontiguousarray(variance, np.float32)
        flags = np.ascontiguousarray(flags, np.uint8)
        assert raw.ndim == 2 and variance.shape == flags.shape == raw.shape
        assert np.isfinite(variance).all() and (variance >= 0).all()
        return raw, variance, flags

    def noise(self, raw, variance, censored, workers=4):
        raw, variance, censored = self.arrays(raw, variance, censored)
        out = np.empty_like(raw)
        rc = self.lib.phase_noise(raw.ctypes.data, variance.ctypes.data,
              censored.ctypes.data, raw.shape[1], raw.shape[0], out.ctypes.data, workers)
        assert rc == 0, rc
        assert np.array_equal(out[censored != 0], raw[censored != 0])
        return out

    @staticmethod
    def blend(raw, estimate, amount):
        """Bound a proposed RAW correction; no output-colour guarantee implied."""
        raw = np.asarray(raw, np.uint16); estimate = np.asarray(estimate, np.uint16)
        assert raw.shape == estimate.shape and np.isfinite(amount) and 0 <= amount <= 1
        return np.floor(raw.astype(float)+amount*(estimate.astype(float)-raw)+.5).astype(np.uint16)

    def highlights(self, raw, rgb, variance, clipped, cfa, neutral, workers=4):
        raw, variance, clipped = self.arrays(raw, variance, clipped)
        rgb = np.ascontiguousarray(rgb, np.uint16); neutral = np.asarray(neutral)
        assert rgb.shape == (*raw.shape, 3) and neutral.shape == (3,)
        assert np.isfinite(neutral).all() and (neutral > 0).all()
        assert neutral[1] == 1
        out = np.empty_like(raw)
        rc = self.lib.clipped_ratio(raw.ctypes.data, rgb.ctypes.data, clipped.ctypes.data,
              variance.ctypes.data, raw.shape[1], raw.shape[0], cfa,
              neutral[0], neutral[2], out.ctypes.data, workers)
        assert rc == 0, rc
        assert np.array_equal(out[clipped == 0], raw[clipped == 0])
        assert (out >= raw).all()
        return out
