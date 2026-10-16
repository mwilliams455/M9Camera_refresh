from pathlib import Path
import ctypes as C, json, time, subprocess, statistics, sys
import numpy as np

parent,candidate,root=(Path(x).resolve() for x in sys.argv[1:]);root.mkdir(parents=True,exist_ok=True)
functions = []
for name in ['parent', 'candidate']:
    subprocess.run(['g++', '-std=c++17', '-O3', '-fno-fast-math', '-ffp-contract=off',
                    '-shared', '-fPIC', '-fopenmp', str((parent if name=='parent' else candidate)/'app/src/main/cpp/colourtrial1c/phase_noise.cpp'),
                    '-o', str(root/(name+'.so'))], check=True)
    lib = C.CDLL(str(root/(name+'.so')))
    fn = lib.phase_noise_symtile_adaptive_exact
    fn.argtypes = [C.c_void_p,C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_void_p,C.c_int]
    fn.restype = C.c_int
    functions.append(fn)

rng = np.random.default_rng(296)
def call(fn, raw, var, mask, out, workers=8):
    start = time.perf_counter_ns()
    rc = fn(raw.ctypes.data,var.ctypes.data,mask.ctypes.data,raw.shape[1],raw.shape[0],out.ctypes.data,workers)
    assert rc == 0
    return (time.perf_counter_ns()-start)/1e6

cases = samples = 0
for w,h in [(16,16),(31,37),(65,67),(129,131),(513,257),(1031,515)]:
    for pattern in ['flat','noise','random','clipped']:
        if pattern == 'flat': raw=np.full((h,w),23000,np.uint16)
        elif pattern == 'random': raw=rng.integers(0,65536,(h,w),np.uint16)
        else: raw=np.clip(23000+rng.normal(0,150,(h,w)),0,65535).astype(np.uint16)
        var=np.full((h,w),22500,np.float32)
        mask=np.zeros((h,w),np.uint8)
        if pattern=='clipped':
            mask[h//3:h//2,w//3:w//2]=1
            mask[6::64,6::128]=1
            var[7::31,7::37]=0
        for workers in [1,2,4,8]:
            before=np.empty_like(raw);after=np.empty_like(raw)
            call(functions[0],raw,var,mask,before,workers)
            call(functions[1],raw,var,mask,after,workers)
            assert np.array_equal(before,after),(w,h,pattern,workers)
            cases+=1;samples+=raw.size
print(json.dumps({'parityCases':cases,'samples':samples,'exact':True}),flush=True)

timings=[]
w,h=4096,3072
yy,xx=np.indices((h,w))
for pattern in ['smooth_noise','fine_detail','clustered_censor']:
    if pattern=='flat': raw=np.full((h,w),23000,np.uint16)
    elif pattern=='fine_detail':raw=rng.integers(900,61000,(h,w),np.uint16)
    else:raw=np.clip(13000+7*xx+3*yy+rng.normal(0,150,(h,w)),0,65535).astype(np.uint16)
    var=(12000+0.8*raw.astype(np.float32)).astype(np.float32)
    mask=np.zeros((h,w),np.uint8)
    if pattern=='clustered_censor':
        mask[200:1100,2600:4000]=1
        mask[1400:2200,200:800]=1
        mask[::211,::223]=1
    outputs=[np.empty_like(raw),np.empty_like(raw)]
    for i in range(2):call(functions[i],raw,var,mask,outputs[i])
    runs=[]
    for rep in range(7):
        pair={}
        for i in ([0,1] if rep%2==0 else [1,0]):
            pair[['parentMs','candidateMs'][i]]=call(functions[i],raw,var,mask,outputs[i])
        assert np.array_equal(outputs[0],outputs[1])
        runs.append(pair)
    a=statistics.median(x['parentMs'] for x in runs)
    b=statistics.median(x['candidateMs'] for x in runs)
    result={'pattern':pattern,'parentMedianMs':a,'candidateMedianMs':b,'reductionPercent':100*(a-b)/a,'runs':runs}
    timings.append(result)
    print(json.dumps(result),flush=True)
report={'status':'PASS','parityCases':cases,'comparedSamples':samples,'benchmarkDimensions':[w,h],
        'timings':timings,'phonePerformanceProven':False,'inputSourceModifiedByTest':False}
(root/'RESULTS_FULL12.json').write_text(json.dumps(report,indent=2)+'\n')
