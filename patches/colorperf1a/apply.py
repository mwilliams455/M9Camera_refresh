#!/usr/bin/env python3
"""Apply exact COLORPERF1A persistent native colour workers after accepted 1.93."""
from pathlib import Path
import json,shutil,sys,importlib.util
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

_parent_spec=importlib.util.spec_from_file_location(
    'm9_phasenoiseperf1c_apply',REPO/'patches/phasenoiseperf1c/apply.py')
_parent_mod=importlib.util.module_from_spec(_parent_spec);_parent_spec.loader.exec_module(_parent_mod)
parent_verify=_parent_mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

CPP='app/src/main/cpp/m9color_jni.cpp'
CORE='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9NativeColorCore.java'
RENDER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE='app/build.gradle'
ID='M9COLORPERF1A'
CHANGED={CPP,CORE,RENDER,GRADLE}
VERSION='1.94-m9colorperf1a-persistentblocks-phasenoiseperf1c-tg1'
CODE=26714

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('COLORPERF1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    for rel,name in [(CPP,'m9color_jni.cpp'),(CORE,'M9NativeColorCore.java'),(RENDER,'M9R35Renderer.java')]:
        if (root/rel).read_bytes()!=(HERE/name).read_bytes(): raise SystemExit('payload mismatch '+rel)
    c=(root/CPP).read_text();j=(root/CORE).read_text();r=(root/RENDER).read_text();g=(root/GRADLE).read_text()
    checks={
      'revision':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in c,
      'persistent core':'renderFramePersistentCoreExact' in c,
      'one team source':'for (int worker = 0; worker < workerCount; ++worker)' in c,
      'block barrier':'blockDone.wait();' in c and 'blockStatsConsumed.wait();' in c,
      'scalar colour retained':'renderStripScalar(ctx,' in c,
      'orientation mapping retained':'writeCompletedSubrangeToBitmap(argbBase, bitmapBase' in c,
      'perf3i retained':'M9NativeColorCore_renderBlockParallelDirectBitmap' in c,
      'jni declaration':'renderFramePersistentDirectBitmap' in j,
      'production call':'M9NativeColorCore.renderFramePersistentDirectBitmap' in r,
      'fallback retained':'M9NativeColorCore.renderBlockParallelDirectBitmap' in r,
      'block rows frozen':'NATIVE_COLOR_BLOCK_ROWS' in r and '384' in r,
      'worker count frozen':'NATIVE_COLOR_WORKERS' in r and '8' in r,
      'diagnostics':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT' in r and 'nativeColorPersistentFrameActive' in r,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('COLORPERF1A verify failed: '+name)
    if f"versionName '{VERSION}'" not in g or f'versionCode {CODE}' not in g:
        raise SystemExit('COLORPERF1A version mismatch')
    return {
      'revision':'M9COLORPERF1A_PERSISTENTBLOCKS_EXACT',
      'version':VERSION,'versionCode':CODE,
      'parent':'1.93_M9PHASENOISEPERF1C_ADAPTIVE128_EXACT',
      'changed':sorted(CHANGED),
      'colorBlockRows':384,'workers':8,
      'persistentWorkerTeam':True,
      'persistentBitmapLock':True,
      'workerRowPartitionChanged':False,
      'scalarColourMathChanged':False,
      'orientationMappingChanged':False,
      'bt601PairingChanged':False,
      'sat2Curve02Tg1Changed':False,
      'phaseNoise1CChanged':False,
      'prepPerf1BChanged':False,
      'amazeChanged':False,
      'autoExposureChanged':False,
      'fallbackRetained':True,
      'device_performance_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.93-m9phasenoiseperf1c-adaptive128-prepperf1b-tg1'" not in gradle or 'versionCode 26713' not in gradle:
        raise SystemExit('COLORPERF1A requires exact 1.93 parent identity')

    before=inventory(root)
    for rel,name in [(CPP,'m9color_jni.cpp'),(CORE,'M9NativeColorCore.java'),(RENDER,'M9R35Renderer.java')]:
        shutil.copyfile(HERE/name,root/rel)

    gradle=one(gradle,'versionCode 26713',f'versionCode {CODE}','version code')
    gradle=one(gradle,
      "versionName '1.93-m9phasenoiseperf1c-adaptive128-prepperf1b-tg1'",
      f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
