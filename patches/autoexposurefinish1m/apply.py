#!/usr/bin/env python3
"""2.02 M9AUTOEXPOSUREFINISH1M HIGHLIGHTGRANDFATHER1A.

Phone A/B after FINISH1J rollback showed the opposite failure: unrestricted
backlight placement reached +2.5 EV and materially blew the window.

The same FINISH1J bracket also exposed a bug in HIGHLIGHTRET1A: two fields that
already had neutral-reference q90 values 233 and 237 were treated as newly
emerging highlights as soon as their clip fraction rose. That contradicts the
policy's intended "pre-existing bright window is grandfathered" semantics.

1M restores the accepted 1L policy and changes only HIGHLIGHTRET field accounting:
a field with neutral-reference q90 >= 220 (within 4 code values of the >=224
near-white threshold) is considered pre-existing highlight structure for the
field-level growth counters. Global clip/bright growth remains active, and
genuinely emerging fields below q90 220 remain protected.

No HDR, local relighting, renderer, TC20, SAT2, curve02, TG1, colour, DNG,
sharpness or performance changes.
"""
from pathlib import Path
import json,shutil,sys,importlib.util

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

spec=importlib.util.spec_from_file_location(
    'm9_ae1l_apply',REPO/'patches/autoexposurefinish1l/apply.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent_verify=mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1M'
CHANGED={AUTO,GRADLE}
VERSION='2.02-m9ae1m-hlgrand1a-anchorbal1a-perf3i'
CODE=26722

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']:
        raise SystemExit('AUTOEXPOSUREFINISH1M assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1M unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1M Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'revision':'M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A' in auto,
      'q90 threshold':'PREEXISTING_HIGHLIGHT_Q90_CODE=220' in auto,
      'q90 field grandfather':'base.fieldQ90[f]>=PREEXISTING_HIGHLIGHT_Q90_CODE' in auto,
      'highlight revision':'HIGHLIGHTRET1B_PREEXISTING_Q90' in auto,
      'BGQUAL retained':'backlightEvidenceLiftCap' in auto,
      'open-anchor 1L retained':'PROTECTED_ANCHOR_DEEP_BODY_MAX_EV=.75' in auto,
      'no HDR':'multiFrameHdrUsed",false' in auto and 'localHdrUsed",false' in auto,
      'body release retained':'released_after_two_candidate_misses' in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AUTOEXPOSUREFINISH1M verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in gradle or f'versionCode {CODE}' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1M version mismatch')

    return {
      'revision':'M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A',
      'version':VERSION,
      'versionCode':CODE,
      'parent':'2.00_M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A',
      'changed':sorted(CHANGED),
      'preexistingHighlightQ90Code':220,
      'fieldLevelExistingHighlightGrandfathering':True,
      'globalHighlightGrowthProtectionPreserved':True,
      'genuinelyEmergingFieldProtectionPreserved':True,
      'backgroundQualificationPreserved':True,
      'openAnchorBalancePreserved':True,
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
      'phone_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_verify(root)
    if (root/AUTO).read_bytes()!=(REPO/'patches/autoexposurefinish1l/M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1M requires exact FINISH1L Auto source at 2.00 parent')

    gradle=(root/GRADLE).read_text()
    parent_version='2.00-m9ae1l-anchorbal1a-hlret1a-perf3i'
    if f"versionName '{parent_version}'" not in gradle or 'versionCode 26720' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1M requires exact 2.00 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26720',f'versionCode {CODE}','version code')
    gradle=one(gradle,f"versionName '{parent_version}'",f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1M unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
