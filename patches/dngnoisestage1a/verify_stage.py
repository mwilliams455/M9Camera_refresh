#!/usr/bin/env python3
"""Production RAW adapter vs independent reference, plus optional real host JNI."""
from pathlib import Path
import ctypes, hashlib, json, os, shutil, subprocess, sys
import numpy as np

HERE=Path(__file__).resolve().parent
def verify(root, out):
    root,out=Path(root).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    ref=out/'reference';shutil.copytree(HERE/'reference',ref,dirs_exist_ok=True)
    cpp=root/'app/src/main/cpp/m9dngnoise'
    flags=['g++','-std=c++17','-O2','-ffp-contract=off','-fno-fast-math','-Wall','-Wextra','-pedantic','-shared','-fPIC']
    library=ref/'libshaded_noise.so'
    subprocess.run(flags+[str(cpp/'shaded_noise.cpp'),str(cpp/'raw16_adapter.cpp'),'-o',str(library)],check=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ref),'-v'],check=True)
    sys.path.insert(0,str(ref))
    from shaded_noise import reference
    fn=ctypes.CDLL(str(library)).m9_dng_noise_raw16
    ptr=ctypes.c_void_p
    fn.argtypes=[ptr,ctypes.c_size_t,ptr,ctypes.c_size_t,*([ctypes.c_int]*4),ptr,ptr,ptr,ctypes.c_int,ctypes.c_int]
    fn.restype=ctypes.c_int
    p=np.array([[.0004,.000001],[.00038,.0000008],[.00039,.0000009],[.00042,.0000011]],float)
    b=np.array([64,65,66,67],float)
    g=(1+(np.arange(24)%7)*.125).astype(np.float32).reshape(2,3,4)
    channel_phases=[[0,1,2,3],[1,0,3,2],[2,0,3,1],[3,1,2,0]]
    expected_jni=[];samples=0
    for cfa in range(4):
        phases=np.empty((4,2,3),np.float32)
        for channel,phase in enumerate(channel_phases[cfa]):phases[phase]=g[:,:,channel]
        raw=(140+np.arange(66*138)*73%31).astype(np.uint16).reshape(138,66)
        for bits in [8,10,12,14]:
            white=(1<<bits)-1;scale=1<<(14-bits);output=np.empty_like(raw);before=raw.copy()
            rc=fn(raw.ctypes.data,raw.nbytes,output.ctypes.data,output.nbytes,66,138,white,scale,
                  b.ctypes.data,p.ctypes.data,phases.ctypes.data,3,2)
            assert rc==0,rc
            expected=reference(raw*scale,1,1,p,b*scale,white*scale,phases,np.array([1.,.5,0,0]))
            np.testing.assert_array_equal(output,expected);np.testing.assert_array_equal(raw,before)
            assert np.count_nonzero(output!=raw*scale)>0
            samples+=raw.size
            if bits==10:expected_jni.append(expected)
        # Defensive native ABI gates: no unsafe dereference on bad capacities, overlap or range.
        args=[raw.ctypes.data,raw.nbytes,output.ctypes.data,output.nbytes,66,138,1023,16,
              b.ctypes.data,p.ctypes.data,phases.ctypes.data,3,2]
        bad=args.copy();bad[1]-=1;assert fn(*bad)==-1
        bad=args.copy();bad[2]=raw.ctypes.data;assert fn(*bad)==-2
        bad=args.copy();bad[7]=3;assert fn(*bad)==-1
        raw[0,0]=1024;assert fn(*args)==-4
    jni=False
    if shutil.which('javac'):
        java=Path(shutil.which('javac')).resolve().parents[1]
        subprocess.run(flags+['-I'+str(java/'include'),'-I'+str(java/'include/linux'),
            str(cpp/'shaded_noise.cpp'),str(cpp/'raw16_adapter.cpp'),str(cpp/'noise_jni.cpp'),
            '-o',str(out/'libm9dngnoise.so')],check=True)
        subprocess.run(['javac','-d',str(out),str(root/'app/src/main/java/com/particlesdevs/photoncamera/processing/M9DngNoiseStage.java'),str(HERE/'StageJniProbe.java')],check=True)
        subprocess.run(['java','-Djava.library.path='+str(out),'-cp',str(out),
            'com.particlesdevs.photoncamera.processing.StageJniProbe',str(out)],check=True)
        for cfa,expected in enumerate(expected_jni):
            np.testing.assert_array_equal(np.fromfile(out/f'jni_cfa{cfa}.bin','<u2').reshape(expected.shape),expected)
        jni=True
    elif os.environ.get('CI'):raise RuntimeError('CI requires real JNI execution')
    report=dict(status='passed',referenceTests=11,nativeAdapterSamples=samples,physicalCfas=4,
        sourceBitsTested=[8,10,12,14],sourceAndBufferStateUnchanged=True,realHostJniPassed=jni,
        coreSha256=hashlib.sha256((cpp/'shaded_noise.cpp').read_bytes()).hexdigest(),
        scope='host production adapter/JNI; device execution remains pending')
    (out/'STAGE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':verify(*sys.argv[1:])
