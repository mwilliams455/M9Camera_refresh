#!/usr/bin/env python3
"""Apply NOISEPERF1A exact parallel row-band optimization after exact 1.86."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

CPP='app/src/main/cpp/m9noisecancel1b.cpp'
JAVA='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NoiseCancel1B.java'
GRADLE='app/build.gradle'
ID='M9NOISEPERF1A'
CHANGED={CPP,JAVA,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('NOISEPERF1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/CPP).read_bytes()!=(HERE/'m9noisecancel1b.cpp').read_bytes(): raise SystemExit('native payload mismatch')
    if (root/JAVA).read_bytes()!=(HERE/'M9NoiseCancel1B.java').read_bytes(): raise SystemExit('Java payload mismatch')
    c=(root/CPP).read_text();j=(root/JAVA).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9NOISEPERF1A_PARALLEL8_EXACT' in c and 'M9NOISEPERF1A_PARALLEL8_EXACT' in j,
      'eight workers':'std::min(8,innerRows)' in c,
      'boundary preload':'boundaryAfter' in c and 'exact-parity race barrier' in c,
      'disjoint output bands':'starts[i]' in c and 'ends[i]' in c and 'threads.emplace_back' in c,
      'green frozen':'greenMutatedSamples",0' in j,
      'math frozen':'NOISECANCEL1B_FROZEN_EXACT' in j,
      'confidence gate frozen':'stats[10]=0.65' in c,
      'blend frozen':'stats[11]=0.50' in c,
      'parallel diagnostics':'parallelWorkers' in j and 'parallelParityPolicy' in j,
      'stats14':'double[] stats=new double[14]' in j,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('NOISEPERF1A verify failed: '+name)
    if "versionName '1.87-m9noiseperf1a-parallel8-noisecancel1b-tg1'" not in g or 'versionCode 26707' not in g:
        raise SystemExit('NOISEPERF1A version mismatch')
    frozen=[
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryTimingWriter.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9PrimaryRenderQueue.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java',
      'app/src/main/cpp/m9detail1h_guard.cpp',
      'app/src/main/cpp/m9detail1h.cpp',
      'app/src/main/cpp/m9color_jni.cpp',
      'app/src/main/assets/m9/m9_curve02_firmware.bin',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)
    return {
      'revision':ID,
      'version':'1.87-m9noiseperf1a-parallel8-noisecancel1b-tg1',
      'versionCode':26707,
      'changed':sorted(CHANGED),
      'parent':'1.86_M9NOISECANCEL1B_DECOUPLED',
      'pixelMathChanged':False,
      'noiseStrengthChanged':False,
      'confidenceGateChanged':False,
      'maxBlendChanged':False,
      'greenPolicyChanged':False,
      'parallelWorkersMax':8,
      'boundaryPolicy':'preload_cross_worker_neighbour_rows_before_launch',
      'extraFullFrameCopy':False,
      'expectedMemoryGrowth':'row_buffers_only',
      'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return
    gradle=(root/GRADLE).read_text()
    if "versionName '1.86-m9noisecancel1b-decoupled-primaryexport1b-tg1'" not in gradle or 'versionCode 26706' not in gradle:
        raise SystemExit('NOISEPERF1A requires exact 1.86 parent identity')
    parent_cpp=REPO/'patches/noisecancel1b/m9noisecancel1b.cpp'
    parent_java=REPO/'patches/noisecancel1b/M9NoiseCancel1B.java'
    if (root/CPP).read_bytes()!=parent_cpp.read_bytes(): raise SystemExit('NOISEPERF1A requires exact 1.86 native source')
    if (root/JAVA).read_bytes()!=parent_java.read_bytes(): raise SystemExit('NOISEPERF1A requires exact 1.86 Java source')
    before=inventory(root)
    shutil.copyfile(HERE/'m9noisecancel1b.cpp',root/CPP)
    shutil.copyfile(HERE/'M9NoiseCancel1B.java',root/JAVA)
    gradle=one(gradle,'versionCode 26706','versionCode 26707','version code')
    gradle=one(gradle,
      "versionName '1.86-m9noisecancel1b-decoupled-primaryexport1b-tg1'",
      "versionName '1.87-m9noiseperf1a-parallel8-noisecancel1b-tg1'",
      'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
