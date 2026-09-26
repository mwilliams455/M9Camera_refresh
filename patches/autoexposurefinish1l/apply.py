#!/usr/bin/env python3
"""2.00 M9AUTOEXPOSUREFINISH1L OPENANCHORBAL1A.

On top of 1.99 BGQUAL1A + HIGHLIGHTRET1A, rebalance one legacy soft-anchor
interaction revealed by the 26 September phone test.

A protected textured open anchor still caps ordinary ambiguous dark material at
+0.25 EV. But when a coherent body is profoundly starved (high severity, very low
median/q25, good confidence) and BGQUAL1A says the absolute background is weak,
the anchor now allows a middle +0.75 EV ceiling.

This remains one global capture exposure. BGQUAL1A, HIGHLIGHTRET1A, body-lock
release, renderer, TC20, SAT2, curve02, TG1, DNG, colour, sharpness and performance
paths remain otherwise frozen.
"""
from pathlib import Path
import json,shutil,sys,importlib.util

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

spec=importlib.util.spec_from_file_location(
    'm9_ae1k_apply',REPO/'patches/autoexposurefinish1k/apply.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent_verify=mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1L'
CHANGED={AUTO,GRADLE}
VERSION='2.00-m9ae1l-anchorbal1a-hlret1a-perf3i'
CODE=26720

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']:
        raise SystemExit('AUTOEXPOSUREFINISH1L assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1L unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1L Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'revision':'M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A' in auto,
      'deep body cap':'PROTECTED_ANCHOR_DEEP_BODY_MAX_EV=.75' in auto,
      'deep body helper':'protectedOpenAnchorDeepBodyAssist' in auto,
      'weak BG gate':'backlightEvidenceScore(s,body)<=.15' in auto,
      'ordinary cap retained':'PROTECTED_ANCHOR_ORDINARY_MAX_EV=.25' in auto,
      'severe cap retained':'PROTECTED_ANCHOR_SEVERE_MAX_EV=.50' in auto,
      'BGQUAL retained':'backlightEvidenceLiftCap' in auto,
      'highlight retention retained':'highlightRetentionLimit' in auto,
      'no HDR':'multiFrameHdrUsed",false' in auto and 'localHdrUsed",false' in auto,
      'body release retained':'released_after_two_candidate_misses' in auto,
      'diagnostic reason':'rendered_open_anchor_deep_body_cap' in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AUTOEXPOSUREFINISH1L verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in gradle or f'versionCode {CODE}' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1L version mismatch')

    return {
      'revision':'M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A',
      'version':VERSION,
      'versionCode':CODE,
      'parent':'1.99_M9AUTOEXPOSUREFINISH1K_BGQUAL1A_HIGHLIGHTRET1A',
      'changed':sorted(CHANGED),
      'ordinaryOpenAnchorMaxEv':0.25,
      'severeBrightBackgroundAnchorMaxEv':0.50,
      'deepStarvedWeakBackgroundAnchorMaxEv':0.75,
      'deepBodyRequiresWeakBgqual':True,
      'backgroundQualificationPreserved':True,
      'highlightRetentionPreserved':True,
      'localHdrIntroduced':False,
      'multiFrameHdrIntroduced':False,
      'rendererChanged':False,
      'tc20Changed':False,
      'sat2Changed':False,
      'curve02Changed':False,
      'tg1Changed':False,
      'colourChanged':False,
      'dngChanged':False,
      'performanceChanged':False,
      'spoolResetPreserved':True,
      'phone_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    if (root/AUTO).read_bytes()!=(REPO/'patches/autoexposurefinish1k/M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1L requires exact FINISH1K Auto source at 1.99 parent')

    gradle=(root/GRADLE).read_text()
    parent_version='1.99-m9ae1k-hlret1a-spool1a-perf3i'
    if f"versionName '{parent_version}'" not in gradle or 'versionCode 26719' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1L requires exact 1.99 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26719',f'versionCode {CODE}','version code')
    gradle=one(gradle,f"versionName '{parent_version}'",f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1L unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
