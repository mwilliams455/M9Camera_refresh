#!/usr/bin/env python3
"""1.97 AUTOEXPOSUREFINISH1J BODYLOCKRELEASE1A.

Surgically close one hysteresis bug in the rendered 4x6 Auto-exposure body lock:
a previously latched spatial mask could remain locally plausible forever even after
the current coherent-body detector stopped finding a body. One fresh miss is still
held for stability; the second consecutive fresh miss releases the stale lock.

Renderer, colour, tone, saturation, TC20, preview shader, DNG and performance paths
remain byte-frozen from the validated 1.96 COLORPERFROLLBACK1A parent.
"""
from pathlib import Path
import json,shutil,sys,importlib.util

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

spec=importlib.util.spec_from_file_location(
    'm9_colorperfrollback1a_apply',REPO/'patches/colorperfrollback1a/apply.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent_verify=mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1J'
CHANGED={AUTO,GRADLE}
VERSION='1.97-m9autoexposurefinish1j-bodylockrelease1a-colorperfrollback1a-tg1'
CODE=26717

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']:
        raise SystemExit('AUTOEXPOSUREFINISH1J assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1J unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1J Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'policy marker':'M9AUTOEXPOSUREFINISH1J_BODYLOCKRELEASE1A' in auto,
      'fresh miss increments':'if(freshSample) bodyMissConfirmations++;' in auto,
      'two-miss release':'bodyMissConfirmations>=2' in auto,
      'release reason':'released_after_two_candidate_misses' in auto,
      'one-miss hold':'held_one_candidate_miss' in auto,
      'same-sample diagnostic getter':'bodyLockMissConfirmationsForDiagnostics' in auto,
      'switch hysteresis retained':'pendingBodyConfirmations>=2' in auto,
      'safe075 retained':'SAFE_FAST_POSITIVE_SLEW_EV=.75' in auto,
      'field ownership retained':'multifield_no_qualified_body_scene_fallback' in auto,
      'soft anchor retained':'protectedOpenAnchorLiftCap' in auto,
      'M9 ceiling retained':'v.median>=72&&v.q25>=36' in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AUTOEXPOSUREFINISH1J verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in gradle or f'versionCode {CODE}' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1J version mismatch')

    return {
      'revision':'M9AUTOEXPOSUREFINISH1J_BODYLOCKRELEASE1A',
      'version':VERSION,
      'versionCode':CODE,
      'parent':'1.96_M9COLORPERFROLLBACK1A_PERF3I_EXACT',
      'changed':sorted(CHANGED),
      'bodyCandidateAbsenceReleaseFreshConfirmations':2,
      'sameMeterSampleCanAgeLock':False,
      'disjointBodySwitchFreshConfirmations':2,
      'rendererChanged':False,
      'colourMathChanged':False,
      'sat2Changed':False,
      'curve02Changed':False,
      'tc20Changed':False,
      'tg1Changed':False,
      'previewShaderChanged':False,
      'dngPathChanged':False,
      'performancePathChanged':False,
      'captureExposurePolicyChanged':True,
      'localHdrIntroduced':False,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    if (root/AUTO).read_bytes()!=(REPO/'patches/autoexposurefinish1i/M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1J requires exact FINISH1I Auto source at final parent')

    gradle=(root/GRADLE).read_text()
    parent_version="1.96-m9colorperfrollback1a-perf3i-phasenoiseperf1c-tg1"
    if f"versionName '{parent_version}'" not in gradle or 'versionCode 26716' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1J requires exact 1.96 assembled parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26716',f'versionCode {CODE}','version code')
    gradle=one(gradle,
        f"versionName '{parent_version}'",
        f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1J unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
