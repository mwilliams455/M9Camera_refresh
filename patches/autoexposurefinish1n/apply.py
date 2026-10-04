#!/usr/bin/env python3
"""2.03 BODYQUAL1A + SUBJECTHEADROOM1A; only Auto source and version identity change."""
from pathlib import Path
import hashlib,importlib.util,json,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(HERE))
from bodyqual import patch,one
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory
spec=importlib.util.spec_from_file_location('parent_ae1m',REPO/'patches/autoexposurefinish1m/apply.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
AUTO='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1N'
REV='M9AUTOEXPOSUREFINISH1N_BODYQUAL1A_SUBJECTHEADROOM1A'
VERSION='2.03-m9ae1n-bodyqual1a-subjecthl1a-perf3i'
CODE=26723
PARENT_BLOB='4157cb98a592e006f61eda8fa73cb5117ea2e575'
CHANGED={AUTO,GRADLE}

def generate():
    raw=(REPO/'patches/autoexposurefinish1m/M9AutoExposure2D.java').read_bytes()
    blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    if blob!=PARENT_BLOB:raise SystemExit('FINISH1M source blob changed: '+blob)
    s=patch(raw.decode())
    s=one(s,'M9AUTOEXPOSUREFINISH1M_HIGHLIGHTGRANDFATHER1A',REV)
    s=one(s,'        double highlightRetentionLimit=valid?highlightRetentionLimit(sample.stats):0;',
        '        double highlightBaselineLimit=valid?highlightRetentionLimit(sample.stats):0;\n'
        '        boolean currentBodyConfirmed=qualifiedMultifieldBody&&proposedBody.valid\n'
        '                &&proposedBody.confidence>=.22\n'
        '                &&maskOverlap(proposedBody.mask,multifieldBody.mask)>=.50;\n'
        '        double highlightRetentionLimit=highlightBaselineLimit;')
    s=one(s,'            if(useBacklight&&qualifiedMultifieldBody)\n'
            '                positiveLimit=Math.min(positiveLimit,backlightEvidenceLiftCap);',
        '            if(useBacklight&&qualifiedMultifieldBody)\n'
        '                positiveLimit=Math.min(positiveLimit,backlightEvidenceLiftCap);\n'
        '            if(useBacklight&&currentBodyConfirmed)\n'
        '                highlightRetentionLimit=subjectHighlightRetentionLimit(sample.stats,multifieldBody);')
    s=one(s,'                    .put("highlightRetentionRevision","HIGHLIGHTRET1B_PREEXISTING_Q90")',
        '                    .put("bodyCandidateSelectionRevision","BODYQUAL1A_QUALIFY_BEFORE_RANK")\n'
        '                    .put("highlightRetentionRevision","HIGHLIGHTRET1C_SUBJECTHEADROOM1A")')
    s=one(s,'                    .put("highlightRetentionLimitEv",highlightRetentionLimit)',
        '                    .put("highlightRetentionLimitEv",highlightRetentionLimit)\n'
        '                    .put("subjectHighlightRetention",subjectHighlightDiagnostics(\n'
        '                            valid?sample.stats:null,multifieldBody,currentBodyConfirmed,\n'
        '                            highlightBaselineLimit,highlightRetentionLimit))')
    s=one(s,'    public static BodyCandidate multifieldBodyCandidate(Stats s) {',
        (HERE/'subject_methods.java.txt').read_text()+'    public static BodyCandidate multifieldBodyCandidate(Stats s) {')
    return s

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']:raise SystemExit('FINISH1N assembled source drift')
    changed={k for k in set(proof['before'])|set(now) if proof['before'].get(k)!=now.get(k)}
    if changed!=CHANGED:raise SystemExit('FINISH1N unexpected mutation: '+repr(sorted(changed)))
    if (root/AUTO).read_text()!=generate():raise SystemExit('FINISH1N generated policy mismatch')
    gradle=(root/GRADLE).read_text()
    if f"versionName '{VERSION}'" not in gradle or f'versionCode {CODE}' not in gradle:
        raise SystemExit('FINISH1N Android identity mismatch')
    return {'revision':REV,'version':VERSION,'versionCode':CODE,'changed':sorted(CHANGED),
        'qualificationBeforeRanking':True,'bodyGeometryChanged':False,'bodyTargetsChanged':False,
        'backgroundChannelClippingDeferredOnlyDuringUsefulBodyProgress':True,
        'sameFrameBodyConfirmationRequired':True,'globalHighlightLimitsChanged':False,
        'broadNearWhiteLimitsChanged':False,'backgroundQualificationRetained':True,
        'openAnchorRetained':True,'rendererChanged':False,'colourChanged':False,
        'tc20Changed':False,'sat2Changed':False,'curve02Changed':False,'tg1Changed':False,
        'dngPathChanged':False,'spoolChanged':False,'localHdr':False,'multiFrameHdr':False,
        'phoneValidationPending':True}

def main(root):
    root=root.resolve();receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():print(json.dumps(verify(root),indent=2));return
    parent.verify(root)
    expected=(REPO/'patches/autoexposurefinish1m/M9AutoExposure2D.java').read_bytes()
    if (root/AUTO).read_bytes()!=expected:raise SystemExit('FINISH1N requires exact 2.02 Auto parent')
    before=inventory(root)
    gradle=(root/GRADLE).read_text()
    gradle=one(gradle,'versionCode 26722',f'versionCode {CODE}')
    gradle=one(gradle,"versionName '2.02-m9ae1m-hlgrand1a-anchorbal1a-perf3i'",f"versionName '{VERSION}'")
    (root/AUTO).write_text(generate());(root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
    if changed!=CHANGED:raise SystemExit('FINISH1N unexpected changes: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':REV,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))
if __name__=='__main__':main(Path(sys.argv[1]))
