"""Compare the actual parent and candidate JNI reconstruction; synthetic data only."""
from pathlib import Path
import ctypes as C
import importlib.util
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
parent, candidate, output = (Path(x).resolve() for x in sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('trial', REPO/'patches/tests/colourtrial1c/run.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.HERE = REPO/'patches/tests/colourtrial1d'
libraries = []
P, I, D = C.c_void_p, C.c_int, C.c_double
for name, source in [('parent', parent), ('candidate', candidate)]:
    binary, _ = module.build(source, output/name)
    lib = module.configure(C.CDLL(str(binary)))
    lib.phase_noise_symtile_adaptive_exact.argtypes = [P,P,P,I,I,P,I]
    lib.phase_noise_symtile_adaptive_exact.restype = I
    lib.trial_reconstruct_perf.argtypes = [P,P,P,I,I,I,D,D,D,P,I,P,P]
    lib.trial_reconstruct_perf.restype = I
    libraries.append(lib)

rng = np.random.default_rng(296)
raw_cases = rgb_cases = compared = 0
for w,h in [(16,16),(31,37),(65,67),(129,131),(513,257),(1031,515)]:
    for pattern in ['flat', 'noise', 'random', 'clipped']:
        if pattern == 'flat': raw = np.full((h,w),23000,np.uint16)
        elif pattern == 'random': raw = rng.integers(0,65536,(h,w),np.uint16)
        else: raw = np.clip(23000+rng.normal(0,150,(h,w)),0,65535).astype(np.uint16)
        var = np.full((h,w),22500,np.float32)
        mask = np.zeros((h,w),np.uint8)
        if pattern == 'clipped':
            mask[h//3:h//2,w//3:w//2] = 1
            mask[6::64,6::128] = 1
            var[7::31,7::37] = 0
        expected = np.empty_like(raw)
        assert libraries[0].phase_noise(raw.ctypes.data,var.ctypes.data,mask.ctypes.data,w,h,expected.ctypes.data,1) == 0
        for workers in [1,2,4,8]:
            for lib in libraries:
                actual = np.empty_like(raw)
                assert lib.phase_noise_symtile_adaptive_exact(raw.ctypes.data,var.ctypes.data,mask.ctypes.data,w,h,actual.ctypes.data,workers) == 0
                assert np.array_equal(expected,actual), (w,h,pattern,workers)
            raw_cases += 1
            compared += raw.size

# Compare the complete existing reconstruction, including quarter blend, AMaZE,
# output quantization, border and statistics. Check every Bayer arrangement.
for cfa in range(4):
    w,h = 385,321
    raw = rng.integers(900,61000,(h,w),np.uint16)
    var = np.exp(rng.uniform(np.log(100),np.log(90000),(h,w))).astype(np.float32)
    mask = np.zeros((h,w),np.uint8)
    mask[30:70,80:125] = 1
    for workers in [1,2,4,8]:
        results = []
        for lib in libraries:
            rgb = np.empty((h,w,3),np.uint16)
            stats = np.zeros(4,np.float64)
            timing = np.zeros(5,np.float64)
            assert lib.trial_reconstruct_perf(raw.ctypes.data,var.ctypes.data,mask.ctypes.data,w,h,cfa,.42,.61,1.7,rgb.ctypes.data,workers,stats.ctypes.data,timing.ctypes.data) == 0
            results.append((rgb,stats))
        for i in [0,1]: assert np.array_equal(results[0][i],results[1][i]), (cfa,workers,i)
        rgb_cases += 1

report = {'status':'PASS','revision':'M9PHASENOISEPERF1D_DYNAMIC_EXACT',
          'rawParityCases':raw_cases,'rawSamplesCompared':compared,
          'scalarParentAndCandidateExact':True,'fullReconstructionCases':rgb_cases,
          'allFourCfaRgbAndStatsExact':True,'workers':[1,2,4,8],
          'phonePerformanceProven':False}
(output/'HOST_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
