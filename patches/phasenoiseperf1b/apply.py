#!/usr/bin/env python3
"""Apply PHASENOISEPERF1B exact symmetric weight reuse after exact 1.90."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

PHASE='app/src/main/cpp/colourtrial1c/phase_noise.cpp'
RECON='app/src/main/cpp/colourtrial1c/reconstruct.cpp'
JAVA='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java'
GRADLE='app/build.gradle'
ID='M9PHASENOISEPERF1B'
CHANGED={PHASE,RECON,JAVA,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PHASENOISEPERF1B assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    for rel,payload in [(PHASE,'phase_noise.cpp'),(RECON,'reconstruct.cpp'),(JAVA,'M9ColourTrial1C.java')]:
        if (root/rel).read_bytes()!=(HERE/payload).read_bytes():
            raise SystemExit('payload mismatch '+rel)
    p=(root/PHASE).read_text();r=(root/RECON).read_text();j=(root/JAVA).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9PHASENOISEPERF1B_SYMMETRIC_WEIGHT_REUSE_EXACT' in p and 'M9PHASENOISEPERF1B_SYMMETRIC_WEIGHT_REUSE_EXACT' in j,
      'scalar oracle retained':'extern "C" int phase_noise(const uint16_t* raw' in p,
      '1a oracle retained':'extern "C" int phase_noise_banded_exact(' in p,
      '1b entry':'extern "C" int phase_noise_symmetric_exact(' in p,
      'canonical halfplane':'constexpr int canonicalCount=12,candidateCount=24' in p,
      'original candidate order':'constexpr int ady[candidateCount]' in p and 'for(int ai=0;ai<candidateCount;ai++)' in p,
      'same exp':'std::exp(-2.*std::max(0.,distance/count-1.))' in p,
      'bounded tile':'constexpr int tileRows=32,tileCols=256' in p,
      'production 1b':'phase_noise_symmetric_exact(raw,variance,censored,w,h,corrected.data(),workers)' in r,
      '1a diagnostic parent':'M9PHASENOISEPERF1A_BANDED_TERM_REUSE_EXACT' in j,
      'amaze frozen':'M9AMAZEPERF1A_PARALLEL_PERIPHERY_EXACT' in r and 'M9AMAZEPERF1A_PARALLEL_PERIPHERY_EXACT' in j,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PHASENOISEPERF1B verify failed: '+name)
    if "versionName '1.91-m9phasenoiseperf1b-symmetric-amazeperf1a-tg1'" not in g or 'versionCode 26711' not in g:
        raise SystemExit('PHASENOISEPERF1B version mismatch')
    frozen=[
      'app/src/main/cpp/colourtrial1c/chroma.cpp',
      'app/src/main/cpp/colourtrial1c/upstream/amaze.cc',
      'app/src/main/cpp/colourtrial1c/native.inc',
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
      'version':'1.91-m9phasenoiseperf1b-symmetric-amazeperf1a-tg1',
      'versionCode':26711,
      'changed':sorted(CHANGED),
      'parent':'1.90_M9PHASENOISEPERF1A_BANDED_TERM_REUSE_EXACT',
      'phaseNoiseMathChanged':False,
      'rawNoiseStrengthChanged':False,
      'candidateAccumulationOrderChanged':False,
      'patchAccumulationOrderChanged':False,
      'symmetricWeightIdentityUsed':True,
      'canonicalDirections':12,
      'candidateDirections':24,
      'tileRows':32,
      'tileCols':256,
      'fullFrameWeightCacheAdded':False,
      'amazeAlgorithmChanged':False,
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
    if "versionName '1.90-m9phasenoiseperf1a-banded-amazeperf1a-tg1'" not in gradle or 'versionCode 26710' not in gradle:
        raise SystemExit('PHASENOISEPERF1B requires exact 1.90 parent identity')
    if (root/PHASE).read_bytes()!=(REPO/'patches/phasenoiseperf1a/phase_noise.cpp').read_bytes():
        raise SystemExit('PHASENOISEPERF1B requires exact 1.90 phase-noise parent')
    if (root/RECON).read_bytes()!=(REPO/'patches/phasenoiseperf1a/reconstruct.cpp').read_bytes():
        raise SystemExit('PHASENOISEPERF1B requires exact 1.90 reconstruct parent')
    if (root/JAVA).read_bytes()!=(REPO/'patches/phasenoiseperf1a/M9ColourTrial1C.java').read_bytes():
        raise SystemExit('PHASENOISEPERF1B requires exact 1.90 Java parent')
    before=inventory(root)
    shutil.copyfile(HERE/'phase_noise.cpp',root/PHASE)
    shutil.copyfile(HERE/'reconstruct.cpp',root/RECON)
    shutil.copyfile(HERE/'M9ColourTrial1C.java',root/JAVA)
    gradle=one(gradle,'versionCode 26710','versionCode 26711','version code')
    gradle=one(gradle,
      "versionName '1.90-m9phasenoiseperf1a-banded-amazeperf1a-tg1'",
      "versionName '1.91-m9phasenoiseperf1b-symmetric-amazeperf1a-tg1'",
      'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
