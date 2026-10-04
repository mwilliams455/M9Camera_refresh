#!/usr/bin/env python3
"""Apply AMAZEPERF1A exact parallel peripheral optimization after exact 1.88."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

RECON='app/src/main/cpp/colourtrial1c/reconstruct.cpp'
NATIVE='app/src/main/cpp/colourtrial1c/native.inc'
JAVA='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java'
GRADLE='app/build.gradle'
ID='M9AMAZEPERF1A'
CHANGED={RECON,NATIVE,JAVA,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AMAZEPERF1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    for rel,payload in [(RECON,'reconstruct.cpp'),(NATIVE,'native.inc'),(JAVA,'M9ColourTrial1C.java')]:
        if (root/rel).read_bytes()!=(HERE/payload).read_bytes():
            raise SystemExit('payload mismatch '+rel)
    r=(root/RECON).read_text();n=(root/NATIVE).read_text();j=(root/JAVA).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9AMAZEPERF1A_PARALLEL_PERIPHERY_EXACT' in r and 'M9AMAZEPERF1A_PARALLEL_PERIPHERY_EXACT' in j,
      'scalar variance oracle retained':'extern "C" int trial_variance(const uint16_t* sensor' in r,
      'parallel variance':'extern "C" int trial_variance_parallel(' in r and '#pragma omp parallel for num_threads(workers) schedule(static)' in r,
      'scalar reconstruct oracle retained':'extern "C" int trial_reconstruct(const uint16_t* raw' in r,
      'perf reconstruct':'extern "C" int trial_reconstruct_perf(' in r,
      'chunk2 frozen':'65535.f,65535.f,2,false)' in r,
      'parallel blend':'reduction(+:changed,censoredCount) reduction(max:maxCorrection)' in r,
      'parallel input':'perf[2]=elapsed(t0,Clock::now())' in r,
      'parallel quantize':'reduction(|:invalid)' in r,
      'native perf call':'trial_reconstruct_perf(raw.data()' in n,
      'native parallel variance':'trial_variance_parallel(sensor' in n,
      'stats14':'env->GetArrayLength(statsArray)<14' in n and 'double[] stats=new double[14]' in j,
      'stage diagnostics':'amazeCoreMs' in j and 'amazeVarianceMs' in j and 'amazeOutputQuantizeMs' in j,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AMAZEPERF1A verify failed: '+name)
    if "versionName '1.89-m9amazeperf1a-parallelperiphery-prepperf1a-tg1'" not in g or 'versionCode 26709' not in g:
        raise SystemExit('AMAZEPERF1A version mismatch')
    frozen=[
      'app/src/main/cpp/colourtrial1c/chroma.cpp',
      'app/src/main/cpp/colourtrial1c/phase_noise.cpp',
      'app/src/main/cpp/colourtrial1c/upstream/amaze.cc',
      'app/src/main/cpp/m9noisecancel1b.cpp',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NoiseCancel1B.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java',
      'app/src/main/assets/m9/m9_curve02_firmware.bin',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)
    return {
      'revision':ID,
      'version':'1.89-m9amazeperf1a-parallelperiphery-prepperf1a-tg1',
      'versionCode':26709,
      'changed':sorted(CHANGED),
      'parent':'1.88_M9PREPPERF1A_PARALLEL8',
      'amazeAlgorithmChanged':False,
      'amazeChunkChanged':False,
      'phaseNoiseChanged':False,
      'rawNoiseStrengthChanged':False,
      'parallelized':['variance_transport','quarter_blend_stats','raw_to_float_input','rgb_output_quantize'],
      'diagnosticsAdded':['rawCopyMs','varianceMs','phaseNoiseMs','quarterBlendMs','floatInputMs','amazeCoreMs','outputQuantizeMs','borderMs'],
      'workers':8,
      'photographicMathChanged':False,
      'prepPerf1AChanged':False,
      'noisePerf1AChanged':False,
      'autoExposureChanged':False,
      'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return
    gradle=(root/GRADLE).read_text()
    if "versionName '1.88-m9prepperf1a-parallel8-noiseperf1a-tg1'" not in gradle or 'versionCode 26708' not in gradle:
        raise SystemExit('AMAZEPERF1A requires exact 1.88 parent identity')
    if (root/RECON).read_bytes()!=(REPO/'patches/colourtrial1d/reconstruct.cpp').read_bytes():
        raise SystemExit('AMAZEPERF1A requires frozen banded COLOURTRIAL1D reconstruct parent')
    if (root/NATIVE).read_bytes()!=(REPO/'patches/prepperf1a/native.inc').read_bytes():
        raise SystemExit('AMAZEPERF1A requires exact PREPPERF1A native parent')
    if (root/JAVA).read_bytes()!=(REPO/'patches/colourtrial1d/M9ColourTrial1C.java').read_bytes():
        raise SystemExit('AMAZEPERF1A requires exact colour trial Java parent')
    before=inventory(root)
    shutil.copyfile(HERE/'reconstruct.cpp',root/RECON)
    shutil.copyfile(HERE/'native.inc',root/NATIVE)
    shutil.copyfile(HERE/'M9ColourTrial1C.java',root/JAVA)
    gradle=one(gradle,'versionCode 26708','versionCode 26709','version code')
    gradle=one(gradle,
      "versionName '1.88-m9prepperf1a-parallel8-noiseperf1a-tg1'",
      "versionName '1.89-m9amazeperf1a-parallelperiphery-prepperf1a-tg1'",
      'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
