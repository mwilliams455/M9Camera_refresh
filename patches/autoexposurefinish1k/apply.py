#!/usr/bin/env python3
"""1.99 M9AUTOEXPOSUREFINISH1K BGQUAL1A + HIGHLIGHTRET1A.

On top of 1.98 SPOOLRESET1A and FINISH1J, constrain high positive Auto exposure
with two global single-exposure policies:

1) BGQUAL1A: contrast/starvation alone may earn at most +1.0 EV for a coherent
   dark body. Additional +1.25..+2.5 EV authority requires absolute bright-
   background evidence from the same neutral-reference rendered 4x6 meter.

2) HIGHLIGHTRET1A: stop increasing capture exposure when previously non-bright
   fields are newly driven into broad near-white/clipped states. Existing blown
   windows are grandfathered using growth from the neutral reference.

No HDR, local tone mapping, multi-frame merge, renderer, TC20, SAT2, curve02,
TG1, DNG, colour, sharpness or performance path changes.
"""
from pathlib import Path
import json,shutil,sys,importlib.util

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]

spec=importlib.util.spec_from_file_location(
    'm9_spoolreset1a_apply',REPO/'patches/spoolreset1a/apply.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parent_verify=mod.verify

sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1K'
CHANGED={AUTO,GRADLE}
VERSION='1.99-m9ae1k-hlret1a-spool1a-perf3i'
CODE=26719

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']:
        raise SystemExit('AUTOEXPOSUREFINISH1K assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1K unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1K Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'revision':'M9AUTOEXPOSUREFINISH1K_BGQUAL1A_HIGHLIGHTRET1A' in auto,
      'weak background max':'WEAK_BACKGROUND_MAX_EV=1.00' in auto,
      'background score':'backlightEvidenceScore' in auto,
      'background cap':'backlightEvidenceLiftCap' in auto,
      'highlight unsafe':'highlightRetentionUnsafe' in auto,
      'highlight limit':'highlightRetentionLimit' in auto,
      'no HDR diagnostic':'multiFrameHdrUsed",false' in auto and 'localHdrUsed",false' in auto,
      'field map safeguard':'!base.fieldMapValid||!v.fieldMapValid' in auto,
      'body release retained':'released_after_two_candidate_misses' in auto,
      'safe075 retained':'SAFE_FAST_POSITIVE_SLEW_EV=.75' in auto,
      'protected anchor retained':'protectedOpenAnchorLiftCap' in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AUTOEXPOSUREFINISH1K verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in gradle or f'versionCode {CODE}' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1K version mismatch')

    return {
      'revision':'M9AUTOEXPOSUREFINISH1K_BGQUAL1A_HIGHLIGHTRET1A',
      'version':VERSION,
      'versionCode':CODE,
      'parent':'1.98_M9SPOOLRESET1A_FINISH1J_PERF3I',
      'changed':sorted(CHANGED),
      'weakBackgroundMaximumAutoEv':1.0,
      'upperBacklightRangeRequiresBrightBackgroundEvidence':True,
      'highlightRetentionGlobalCaptureOnly':True,
      'highlightRetentionUsesIncrementalFieldDamage':True,
      'preExistingBrightWindowsGrandfathered':True,
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
    if (root/AUTO).read_bytes()!=(REPO/'patches/autoexposurefinish1j/M9AutoExposure2D.java').read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1K requires exact FINISH1J Auto source at 1.98 parent')

    gradle=(root/GRADLE).read_text()
    parent_version='1.98-m9spoolreset1a-ae1j-perf3i-tg1'
    if f"versionName '{parent_version}'" not in gradle or 'versionCode 26718' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1K requires exact 1.98 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26718',f'versionCode {CODE}','version code')
    gradle=one(gradle,f"versionName '{parent_version}'",f"versionName '{VERSION}'",'version name')
    (root/GRADLE).write_text(gradle)

    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('AUTOEXPOSUREFINISH1K unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]).resolve())
