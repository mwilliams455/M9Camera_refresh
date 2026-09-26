#!/usr/bin/env python3
"""1.96 SAT2FIX1A: prove the active COLORPERF native kernel actually contains
Leica M9 Standard SAT2 M04/M05, then version the hotfix.

The 1.95 PRIMARY telemetry said SAT2, but COLORPERF1A's promoted native bundle
still contained the older fixed SAT3 M06/M07 coefficients. This hotfix makes
telemetry and compiled math agree. No exposure, tone, phase-noise, AMaZE,
PREPPERF, TG1, orientation, or colour-worker orchestration is changed here.
"""
from pathlib import Path
import json,sys,importlib.util

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

spec=importlib.util.spec_from_file_location(
    'm9_colorperf1b_apply',REPO/'patches/colorperf1b/apply.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent_verify=mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

CPP='app/src/main/cpp/m9color_jni.cpp'
RENDER='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
GRADLE='app/build.gradle'
ID='M9SAT2FIX1A'
CHANGED={GRADLE}
VERSION='1.96-m9sat2fix1a-actualnative-colorperf1b-phasenoiseperf1c-tg1'
CODE=26716

SAT2_QE='13659, -4457, -1004'
SAT2_QE2='-2244, 13469, -3033'
SAT2_QE3='-199, -6014, 14398'
SAT2_QO='14811, -5604, -1004'
SAT2_QO2='-2455, 13688, -3033'
SAT2_QO3='393, -6588, 14398'
SAT3_QE='16754, -7632, -922'
SAT3_QO='18160, -9034, -922'

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def sat2_checks(root):
    c=(root/CPP).read_text()
    r=(root/RENDER).read_text()
    checks={
      'native SAT2 QE': all(x in c for x in [SAT2_QE,SAT2_QE2,SAT2_QE3]),
      'native SAT2 QO': all(x in c for x in [SAT2_QO,SAT2_QO2,SAT2_QO3]),
      'native stale SAT3 absent': SAT3_QE not in c and SAT3_QO not in c,
      'native SAT2 provenance marker':'M9COLORPERF_SAT2_M04_M05_FIXED' in c,
      'Java SAT2 baseline':'public static final int SATURATION_BANK = 2;' in r,
      'Java SAT2 QE':all(x in r for x in [SAT2_QE,SAT2_QE2,SAT2_QE3]),
      'Java SAT2 QO':all(x in r for x in [SAT2_QO,SAT2_QO2,SAT2_QO3]),
      'Java stale SAT3 absent':SAT3_QE not in r and SAT3_QO not in r,
      'runtime telemetry says SAT2':'nativeSaturationBankActuallySelected' in r
          and 'SAT2_STANDARD_M04_M05' in r,
      'persistent colour still active-capable':'M9COLORPERF1B_TARGETACTIVE_EXACT' in r
          and 'renderFramePersistentDirectBitmap' in r,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('SAT2FIX1A verify failed: '+name)
    return checks

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('SAT2FIX1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('SAT2FIX1A unexpected changed files: '+repr(sorted(changed)))
    sat2_checks(root)
    g=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in g or f'versionCode {CODE}' not in g:
        raise SystemExit('SAT2FIX1A version mismatch')
    return {
      'revision':'M9SAT2FIX1A_ACTUALNATIVE_M04_M05',
      'version':VERSION,'versionCode':CODE,
      'parent':'1.95_M9COLORPERF1B_TARGETACTIVE_EXACT',
      'changed':sorted(CHANGED),
      'actualNativeSaturationBank':2,
      'actualNativeMatrixPair':'M04_M05',
      'staleSat3CoefficientsPresent':False,
      'persistentColourSchedulingChanged':False,
      'phaseNoiseChanged':False,
      'amazeChanged':False,
      'prepChanged':False,
      'autoExposureChanged':False,
      'toneChanged':False,
      'tg1Changed':False,
      'device_colour_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.95-m9colorperf1b-targetactive-colorperf1a-phasenoiseperf1c-tg1'" not in gradle or 'versionCode 26715' not in gradle:
        raise SystemExit('SAT2FIX1A requires exact 1.95 assembled parent identity')

    sat2_checks(root)
    before=inventory(root)
    gradle=one(gradle,'versionCode 26715',f'versionCode {CODE}','version code')
    gradle=one(gradle,
      "versionName '1.95-m9colorperf1b-targetactive-colorperf1a-phasenoiseperf1c-tg1'",
      f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('SAT2FIX1A unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({
      'revision':'M9SAT2FIX1A_ACTUALNATIVE_M04_M05',
      'before':before,'after':after
    },indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
