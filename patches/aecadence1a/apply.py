#!/usr/bin/env python3
"""Isolated 2.05 -> 2.06 AECADENCE1A timing overlay. No photo/RAW fixtures."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
HERE=Path(__file__).resolve().parent
ID='M9AECADENCE1A'
VERSION='2.06-m9aecadence1a-exactpatch1b-ae1n-perf3i'
CODE=26726
RECEIPT=ID+'_SOURCE_PROOF.json'
GRADLE='app/build.gradle'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(v,m):
    if not v:raise SystemExit(m)
def inventory(root):
    files=[root/GRADLE]
    for rel in ['app/src/main','circularbarlib/src/main']:
        files.extend(p for p in (root/rel).rglob('*') if p.is_file())
    return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(files)}
def changed(a,b):return {k for k in set(a)|set(b) if a.get(k)!=b.get(k)}
def apply(root):
    manifest=json.loads((HERE/'manifest.json').read_text())['files']
    allowed=set(manifest)|{GRADLE};now=inventory(root);proof=root/RECEIPT
    if proof.exists():
        rec=json.loads(proof.read_text());need(now==rec['after'],'Assembled candidate source drift')
    else:
        parent=json.loads((root/'M9EXACTPATCHCLIP1B_SOURCE_PROOF.json').read_text())
        need(now==parent['after'] and len(now)==1006,'Unknown or changed 2.05 parent')
        for p,s in manifest.items():need(now.get(p)==s['before'],'Parent checksum mismatch: '+p)
        before=now
        for p in manifest:
            patch=HERE/(Path(p).stem+'.diff')
            subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1','-i',str(patch)],cwd=root,check=True)
        g=(root/GRADLE).read_text()
        for old,new in [('versionCode 26725',f'versionCode {CODE}'),("versionName '2.05-m9exactpatch1b-ae1n-perf3i'",f"versionName '{VERSION}'")]:
            need(g.count(old)==1,'Gradle anchor mismatch');g=g.replace(old,new,1)
        (root/GRADLE).write_text(g);now=inventory(root)
        need(changed(before,now)==allowed,'Unexpected source changes')
        rec={'revision':ID,'before':before,'after':now};proof.write_text(json.dumps(rec,indent=2)+'\n')
    need(len(rec['before'])==1006 and len(now)==1007,'Wrong source inventory size')
    need(changed(rec['before'],now)==allowed,'Wrong change set')
    for p,s in manifest.items():need(now[p]==s['after'],'Candidate checksum mismatch: '+p)
    g=(root/GRADLE).read_text();need(f'versionCode {CODE}' in g and f"versionName '{VERSION}'" in g,'Wrong application identity')
    return {'revision':ID,'version':VERSION,'versionCode':CODE,'changedFiles':sorted(allowed),
        'frozenExistingInputs':len(now)-len(allowed),'exposureTargetsChanged':False,
        'perSampleDecisionRulesChanged':False,'tapLimitAdded':False,'nightPlacementFixed':False,
        'photographicCoreChanged':False,'phoneValidationPending':True}
def post(root,baseline,out):
    out.mkdir(parents=True,exist_ok=True);rec=json.loads((root/RECEIPT).read_text());now=inventory(root)
    modified=[p for p,h in rec['after'].items() if now.get(p)!=h]
    added={p:h for p,h in now.items() if p not in rec['after']}
    report={'modifiedAuditedInputs':modified,'addedBuildInputs':added}
    (out/'POSTBUILD_INPUTS.json').write_text(json.dumps(report,indent=2)+'\n')
    need(not modified,'Audited compilation inputs changed')
    need(all(p.startswith('app/src/main/cpp/') for p in added),'Unexpected generated source')
    apks=list((root/'app/build/outputs/apk/debug').glob('*.apk'));need(len(apks)==1,'Expected one APK')
    bs=list(baseline.rglob('M9Cam_2.05_EXACTPATCHCLIP1B.apk'));need(len(bs)==1,'Missing delivered 2.05 APK')
    old_apk=bs[0]
    need(sha(old_apk.read_bytes())==BASELINE_APK_SHA,'Incorrect baseline APK bytes')
    def frozen(z):return {n:sha(z.read(n)) for n in z.namelist() if not n.endswith('/') and n.startswith(('lib/','assets/','res/raw/'))}
    with zipfile.ZipFile(old_apk) as old,zipfile.ZipFile(apks[0]) as new:
        frozen_old=frozen(old);need(frozen_old==frozen(new),'Packaged photographic bytes changed')
        dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for token in [b'M9AECADENCE1A',b'aeLastProbeIntervalMs',b'EXACTPATCHCLIP1B',b'exact_probePixelRect_not_intersecting_fields']:
            need(token in dex,'Missing DEX marker '+str(token))
    target=out/'M9Cam_2.06_AECADENCE1A.apk';shutil.copyfile(apks[0],target)
    proof={'version':VERSION,'versionCode':CODE,'apkSha256':sha(target.read_bytes()),
        'baselineApkSha256':BASELINE_APK_SHA,'frozenPackagedEntries':len(frozen_old),'frozenEntriesByteIdentical':True,
        'allAuditedCompilationInputsUnchanged':True,'auditedInputCount':len(rec['after']),
        'photographicPolicyNotPromoted':True,'phoneValidationPending':True}
    (out/'APK_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
    (out/'SHA256SUMS.txt').write_text(proof['apkSha256']+'  '+target.name+'\n');return proof
BASELINE_APK_SHA='87541c3bbff22a2044fcfe93d05797d2ea9af92d4d502c5502d28751a6959de5'
if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='apply':r=apply(Path(sys.argv[2]).resolve())
    elif len(sys.argv)==5 and sys.argv[1]=='post':r=post(*map(Path,sys.argv[2:]))
    else:raise SystemExit('usage: apply.py apply ROOT | post ROOT BASELINE OUTPUT')
    print(json.dumps(r,indent=2))
