#!/usr/bin/env python3
"""Apply PHASENOISEPERF1C adaptive exact dirty-tile subdivision after accepted 1.92."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches/prepperf1b'))
from apply import verify as parent_verify
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

PHASE='app/src/main/cpp/colourtrial1c/phase_noise.cpp'
RECON='app/src/main/cpp/colourtrial1c/reconstruct.cpp'
JAVA='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java'
GRADLE='app/build.gradle'
ID='M9PHASENOISEPERF1C'
CHANGED={PHASE,RECON,JAVA,GRADLE}
VERSION='1.93-m9phasenoiseperf1c-adaptive128-prepperf1b-tg1'
CODE=26713

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PHASENOISEPERF1C assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    for rel,name in [(PHASE,'phase_noise.cpp'),(RECON,'reconstruct.cpp'),(JAVA,'M9ColourTrial1C.java')]:
        if (root/rel).read_bytes()!=(HERE/name).read_bytes(): raise SystemExit('payload mismatch '+rel)
    p=(root/PHASE).read_text();r=(root/RECON).read_text();j=(root/JAVA).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT' in p,
      'outer rows':'m9_phasenoiseperf1c_outer_tile_rows(){return 64;}' in p,
      'outer cols':'m9_phasenoiseperf1c_outer_tile_cols(){return 512;}' in p,
      'dirty subtile cols':'m9_phasenoiseperf1c_dirty_subtile_cols(){return 128;}' in p,
      '1b oracle retained':'phase_noise_symtile_exact' in p and 'M9PHASENOISEPERF1B_SYMTILE_EXACT' in p,
      'same candidate order':'for(int dy=-4;dy<=4;dy+=2)for(int dx=-4;dx<=4;dx+=2)' in p,
      'same patch order':'for(int py=-2;py<=2;py+=2)for(int px=-2;px<=2;px+=2)' in p,
      'production 1c':'phase_noise_symtile_adaptive_exact(raw,variance,censored,w,h,corrected.data(),workers)' in r,
      'diagnostics':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT' in j and 'phaseNoisePerfDirtySubtileCols' in j,
      'prep retained':'M9PREPPERF1B_PERSISTENT8_EXACT' in j,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PHASENOISEPERF1C verify failed: '+name)
    if f"versionName '{VERSION}'" not in g or f'versionCode {CODE}' not in g:
        raise SystemExit('PHASENOISEPERF1C version mismatch')
    return {
      'revision':'M9PHASENOISEPERF1C_ADAPTIVE128_EXACT',
      'version':VERSION,'versionCode':CODE,
      'parent':'1.92_M9PREPPERF1B_PERSISTENT8_EXACT',
      'changed':sorted(CHANGED),
      'outerTileRows':64,'outerTileCols':512,'dirtySubtileCols':128,
      'cleanOuterTilePathChanged':False,
      'candidateAccumulationOrderChanged':False,
      'patchAccumulationOrderChanged':False,
      'phaseNoiseMathChanged':False,
      'rawNoiseStrengthChanged':False,
      'prepPerf1BChanged':False,
      'amazeChanged':False,
      'noiseCancelChanged':False,
      'autoExposureChanged':False,
      'TC20ToneColourChanged':False,
      'fullFrameWeightCacheAdded':False,
      'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return
    parent_verify(root)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.92-m9prepperf1b-persistent8-phasenoiseperf1b-tg1'" not in gradle or 'versionCode 26712' not in gradle:
        raise SystemExit('PHASENOISEPERF1C requires exact 1.92 parent identity')
    if (root/PHASE).read_bytes()!=(REPO/'patches/phasenoiseperf1b/phase_noise.cpp').read_bytes():
        raise SystemExit('PHASENOISEPERF1C requires exact 1.92 inherited 1B phase parent')
    if (root/RECON).read_bytes()!=(REPO/'patches/phasenoiseperf1b/reconstruct.cpp').read_bytes():
        raise SystemExit('PHASENOISEPERF1C requires exact 1.92 inherited 1B reconstruct parent')
    if (root/JAVA).read_bytes()!=(REPO/'patches/prepperf1b/M9ColourTrial1C.java').read_bytes():
        raise SystemExit('PHASENOISEPERF1C requires exact 1.92 Java parent')
    before=inventory(root)
    for rel,name in [(PHASE,'phase_noise.cpp'),(RECON,'reconstruct.cpp'),(JAVA,'M9ColourTrial1C.java')]:
        shutil.copyfile(HERE/name,root/rel)
    gradle=one(gradle,'versionCode 26712',f'versionCode {CODE}','version code')
    gradle=one(gradle,
      "versionName '1.92-m9prepperf1b-persistent8-phasenoiseperf1b-tg1'",
      f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__': main(Path(sys.argv[1]).resolve())
