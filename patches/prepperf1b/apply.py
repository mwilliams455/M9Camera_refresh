#!/usr/bin/env python3
"""Apply PREPPERF1B persistent exact worker team after the accepted 1.91 phase-noise candidate."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches/phasenoiseperf1b'))
from apply import verify as parent_verify
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

NATIVE='app/src/main/cpp/colourtrial1c/native.inc'
JAVA='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9ColourTrial1C.java'
GRADLE='app/build.gradle'
ID='M9PREPPERF1B'
CHANGED={NATIVE,JAVA,GRADLE}
VERSION='1.92-m9prepperf1b-persistent8-phasenoiseperf1b-tg1'
CODE=26712

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('PREPPERF1B assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/NATIVE).read_bytes()!=(HERE/'native.inc').read_bytes(): raise SystemExit('PREPPERF1B native payload mismatch')
    if (root/JAVA).read_bytes()!=(HERE/'M9ColourTrial1C.java').read_bytes(): raise SystemExit('PREPPERF1B Java payload mismatch')
    n=(root/NATIVE).read_text();j=(root/JAVA).read_text();g=(root/GRADLE).read_text()
    checks={
      'persistent revision':'M9PREPPERF1B_PERSISTENT8_EXACT' in n,
      'single OpenMP team':'#pragma omp parallel num_threads(prepWorkers)' in n,
      'camera transform exact':'cameraToM9(cam,3*(y*w+x),ctx,hsm,m)' in n,
      'chroma amount exact':'double nr=r+.25*(rr-r),nb=b+.25*(bb-b);' in n,
      'chroma luma exact':'double lum=.2126*q[3*i]+.7152*q[3*i+1]+.0722*q[3*i+2];' in n,
      'band frozen':'m9_prepperf1b_band_rows(){return 128;}' in n,
      'workers frozen':'m9_prepperf1b_workers(){return 8;}' in n,
      '1a revision retained':'M9PREPPERF1A_PARALLEL8_EXACT' in n,
      'diagnostics':'prepPerfRevision' in j and 'M9PREPPERF1B_PERSISTENT8_EXACT' in j,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PREPPERF1B verify failed: '+name)
    if f"versionName '{VERSION}'" not in g or f'versionCode {CODE}' not in g:
        raise SystemExit('PREPPERF1B version mismatch')
    return {
      'revision':'M9PREPPERF1B_PERSISTENT8_EXACT',
      'version':VERSION,'versionCode':CODE,
      'parent':'1.91_M9PHASENOISEPERF1B_SYMTILE_EXACT',
      'changed':sorted(CHANGED),
      'persistentWorkerTeam':True,
      'workers':8,'bandRows':128,
      'bandRowsChanged':False,
      'cameraToM9MathChanged':False,
      'preSatChromaMathChanged':False,
      'preSatChromaStrengthChanged':False,
      'phaseNoiseChanged':False,
      'amazeChanged':False,
      'noiseCancelChanged':False,
      'autoExposureChanged':False,
      'TC20ToneColourChanged':False,
      'fullFrameCopyAdded':False,
      'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return
    parent_verify(root)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.91-m9phasenoiseperf1b-symtile-phasenoiseperf1a-tg1'" not in gradle or 'versionCode 26711' not in gradle:
        raise SystemExit('PREPPERF1B requires exact 1.91 parent identity')
    if (root/NATIVE).read_bytes()!=(REPO/'patches/amazeperf1a/native.inc').read_bytes():
        raise SystemExit('PREPPERF1B requires exact 1.91 inherited AMAZEPERF1A native parent')
    if (root/JAVA).read_bytes()!=(REPO/'patches/phasenoiseperf1b/M9ColourTrial1C.java').read_bytes():
        raise SystemExit('PREPPERF1B requires exact 1.91 Java parent')
    before=inventory(root)
    shutil.copyfile(HERE/'native.inc',root/NATIVE)
    shutil.copyfile(HERE/'M9ColourTrial1C.java',root/JAVA)
    gradle=one(gradle,'versionCode 26711',f'versionCode {CODE}','version code')
    gradle=one(gradle,
      "versionName '1.91-m9phasenoiseperf1b-symtile-phasenoiseperf1a-tg1'",
      f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__': main(Path(sys.argv[1]).resolve())
