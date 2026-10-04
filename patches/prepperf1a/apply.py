#!/usr/bin/env python3
"""Apply PREPPERF1A exact 8-way in-place pre-SAT preparation after exact 1.87."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

NATIVE='app/src/main/cpp/colourtrial1c/native.inc'
CHROMA='app/src/main/cpp/colourtrial1c/chroma.cpp'
GRADLE='app/build.gradle'
ID='M9PREPPERF1A'
CHANGED={NATIVE,CHROMA,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PREPPERF1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/NATIVE).read_bytes()!=(HERE/'native.inc').read_bytes(): raise SystemExit('native.inc payload mismatch')
    if (root/CHROMA).read_bytes()!=(HERE/'chroma.cpp').read_bytes(): raise SystemExit('chroma payload mismatch')
    n=(root/NATIVE).read_text();c=(root/CHROMA).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9PREPPERF1A_PARALLEL8_EXACT' in n,
      'workers':'m9_prepperf1a_workers(){return 8;}' in n,
      'scalar prepare retained':'int rc=partial_chroma(q.data(),w,bh,.25,corrected.data())' in n,
      'parallel in-place':'partial_chroma_parallel(q.data(),w,bh,.25,corrected.data(),prepWorkers)' in n,
      'camera transform parallel':'prepParallelRows(top,end,prepWorkers' in n,
      'frozen halo':'Preserve the next band' in n and 'previous.data()' in n,
      'scalar chroma retained':'extern "C" int partial_chroma(const uint16_t* src' in c,
      'parallel chroma added':'extern "C" int partial_chroma_parallel(' in c,
      'row-disjoint chroma':'const int y0=1+(rows*t)/used' in c,
      'amount frozen':'.25,corrected.data(),prepWorkers' in n,
      'band frozen':'bandRows=128' in n,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PREPPERF1A verify failed: '+name)
    if "versionName '1.88-m9prepperf1a-parallel8-noiseperf1a-tg1'" not in g or 'versionCode 26708' not in g:
        raise SystemExit('PREPPERF1A version mismatch')
    frozen=[
      'app/src/main/cpp/m9noisecancel1b.cpp',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NoiseCancel1B.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java',
      'app/src/main/cpp/colourtrial1c/reconstruct.cpp',
      'app/src/main/cpp/colourtrial1c/phase_noise.cpp',
      'app/src/main/cpp/m9color_jni.cpp',
      'app/src/main/assets/m9/m9_curve02_firmware.bin',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)
    return {
      'revision':ID,
      'version':'1.88-m9prepperf1a-parallel8-noiseperf1a-tg1',
      'versionCode':26708,
      'changed':sorted(CHANGED),
      'parent':'1.87_M9NOISEPERF1A_PARALLEL8',
      'photographicMathChanged':False,
      'preSatChromaStrengthChanged':False,
      'cameraToM9MathChanged':False,
      'bandRowsChanged':False,
      'inPlaceMemoryModelChanged':False,
      'parallelWorkers':8,
      'parallelizedStages':['camera_to_m9_per_pixel_within_band','partial_chroma_disjoint_rows'],
      'fullFrameCopyAdded':False,
      'noiseCancel1BChanged':False,
      'autoExposureChanged':False,
      'TC20ToneColourChanged':False,
      'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return
    gradle=(root/GRADLE).read_text()
    if "versionName '1.87-m9noiseperf1a-parallel8-noisecancel1b-tg1'" not in gradle or 'versionCode 26707' not in gradle:
        raise SystemExit('PREPPERF1A requires exact 1.87 parent identity')
    if (root/NATIVE).read_bytes()!=(REPO/'patches/colourtrial1d/native.inc').read_bytes():
        raise SystemExit('PREPPERF1A requires exact frozen COLOURTRIAL1D native.inc parent')
    if (root/CHROMA).read_bytes()!=(REPO/'patches/colourtrial1c/chroma.cpp').read_bytes():
        raise SystemExit('PREPPERF1A requires exact frozen COLOURTRIAL1C chroma parent')
    before=inventory(root)
    shutil.copyfile(HERE/'native.inc',root/NATIVE)
    shutil.copyfile(HERE/'chroma.cpp',root/CHROMA)
    gradle=one(gradle,'versionCode 26707','versionCode 26708','version code')
    gradle=one(gradle,
      "versionName '1.87-m9noiseperf1a-parallel8-noisecancel1b-tg1'",
      "versionName '1.88-m9prepperf1a-parallel8-noiseperf1a-tg1'",
      'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
