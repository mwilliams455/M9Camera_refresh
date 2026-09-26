#!/usr/bin/env python3
"""2.01 M9BACKLIGHTROLLBACK1A — exact FINISH1J Auto-exposure control.

This is a diagnostic rollback only. It removes FINISH1K BGQUAL1A +
HIGHLIGHTRET1A and FINISH1L OPENANCHORBAL1A from the live Auto-exposure policy,
while preserving the current renderer, colour, DNG, crash/memory, spool and
performance stack.

The Auto source is byte-for-byte the accepted FINISH1J BODYLOCKRELEASE1A source.
"""
from pathlib import Path
import json,shutil,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9BACKLIGHTROLLBACK1A'
CHANGED={AUTO,GRADLE}
VERSION='2.01-m9backlightrollback1a-finish1j-perf3i'
CODE=26721

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']:
        raise SystemExit('BACKLIGHTROLLBACK1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('BACKLIGHTROLLBACK1A unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('BACKLIGHTROLLBACK1A Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'exact FINISH1J revision':'M9AUTOEXPOSUREFINISH1J_BODYLOCKRELEASE1A' in auto,
      '1K BGQUAL removed':'BGQUAL1A' not in auto,
      '1K highlight retention removed':'HIGHLIGHTRET1A' not in auto,
      '1L anchor balance removed':'OPENANCHORBAL1A' not in auto,
      'body release retained':'released_after_two_candidate_misses' in auto,
      'field ownership retained':'multifield_body_owns_backlight' in auto,
      'no HDR':'localHdrUsed' not in auto and 'multiFrameHdrUsed' not in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('BACKLIGHTROLLBACK1A verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in gradle or f'versionCode {CODE}' not in gradle:
        raise SystemExit('BACKLIGHTROLLBACK1A version mismatch')

    return {
      'revision':'M9BACKLIGHTROLLBACK1A_FINISH1J_CONTROL',
      'autoSourceRevision':'M9AUTOEXPOSUREFINISH1J_BODYLOCKRELEASE1A',
      'version':VERSION,
      'versionCode':CODE,
      'parent':'2.00_M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A',
      'changed':sorted(CHANGED),
      'bgqual1aEnabled':False,
      'highlightret1aEnabled':False,
      'openanchorbal1aEnabled':False,
      'rendererChanged':False,
      'tc20Changed':False,
      'sat2Changed':False,
      'curve02Changed':False,
      'tg1Changed':False,
      'colourChanged':False,
      'dngChanged':False,
      'performanceChanged':False,
      'purpose':'phone A/B control for backlight regression',
      'phone_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    auto=(root/AUTO).read_text()
    if 'M9AUTOEXPOSUREFINISH1L_OPENANCHORBAL1A' not in auto:
        raise SystemExit('BACKLIGHTROLLBACK1A requires FINISH1L 2.00 parent Auto source')
    gradle=(root/GRADLE).read_text()
    parent_version='2.00-m9ae1l-anchorbal1a-hlret1a-perf3i'
    if f"versionName '{parent_version}'" not in gradle or 'versionCode 26720' not in gradle:
        raise SystemExit('BACKLIGHTROLLBACK1A requires exact 2.00 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26720',f'versionCode {CODE}','version code')
    gradle=one(gradle,f"versionName '{parent_version}'",f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('BACKLIGHTROLLBACK1A unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
