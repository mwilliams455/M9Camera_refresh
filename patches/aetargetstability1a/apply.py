#!/usr/bin/env python3
"""2.07 -> 2.08 AETARGETSTABILITY1A persistent photographic-target overlay."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile

HERE=Path(__file__).resolve().parent
ID='M9AETARGETSTABILITY1A'
VERSION='2.08-m9aetargetstability1a-aestability1a-aecadence1a'
CODE=26728
AUTO='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
PARENT_AUTO='7f7d6e8de85960d36d5389907d413e93c069676a2a83bd6fa0c1aaf6df90e0f1'
NEW_AUTO='684500e769d4ba8ea4006ed5285ec35e8b9ac73897349eaccaa96df4e8945456'
PARENT_GRADLE='b3f0be6b559af675eee63d9a45cc95c7b0793ba9e68af70b2e56c2de11668d05'
NEW_GRADLE='dc76816465b97958660fbfde97072fb17624ca0a493a96ea12cc805e1f6650d0'
BASE_APK='52520130e890f618df7eea4df3df18aaa2498a5d38a67dbd2561b016f2fe33bc'
RECEIPT=ID+'_SOURCE_PROOF.json'

def sha(b): return hashlib.sha256(b).hexdigest()
def need(v,m):
    if not v: raise SystemExit(m)
def inventory(root):
    files=[root/GRADLE]
    for rel in ['app/src/main','circularbarlib/src/main']:
        files.extend(p for p in (root/rel).rglob('*') if p.is_file())
    return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(files)}
def changed(a,b): return {k for k in set(a)|set(b) if a.get(k)!=b.get(k)}
def once(s,a,b):
    need(s.count(a)==1,'Gradle anchor mismatch: '+a)
    return s.replace(a,b,1)

def apply(root):
    root=root.resolve();proof=root/RECEIPT;now=inventory(root)
    if proof.exists():
        rec=json.loads(proof.read_text())
        need(now==rec['after'],'AETARGETSTABILITY1A assembled source drift')
    else:
        parent=json.loads((root/'M9AESTABILITY1A_SOURCE_PROOF.json').read_text())
        need(now==parent['after'] and len(now)==1007,'Unknown or changed 2.07 parent')
        need(now.get(AUTO)==PARENT_AUTO,'Wrong 2.07 exposure source')
        need(now.get(GRADLE)==PARENT_GRADLE,'Wrong 2.07 Gradle source')
        before=now
        subprocess.run(['patch','--batch','--forward','--fuzz=0','-p1',
                        '-i',str(HERE/'M9AutoExposure2D.diff')],cwd=root,check=True)
        need(sha((root/AUTO).read_bytes())==NEW_AUTO,'Candidate exposure source hash mismatch')
        g=(root/GRADLE).read_text()
        g=once(g,'versionCode 26727',f'versionCode {CODE}')
        g=once(g,"versionName '2.07-m9aestability1a-aecadence1a-exactpatch1b-ae1n-perf3i'",
               f"versionName '{VERSION}'")
        (root/GRADLE).write_text(g)
        need(sha((root/GRADLE).read_bytes())==NEW_GRADLE,'Candidate Gradle hash mismatch')
        now=inventory(root)
        need(changed(before,now)=={AUTO,GRADLE},'Unexpected production source mutation')
        rec={'revision':ID,'before':before,'after':now}
        proof.write_text(json.dumps(rec,indent=2)+'\n')
    need(len(rec['before'])==1007 and len(now)==1007,'Wrong source inventory size')
    need(changed(rec['before'],now)=={AUTO,GRADLE},'Wrong child mutation set')
    need(now[AUTO]==NEW_AUTO and now[GRADLE]==NEW_GRADLE,'Candidate source mismatch')
    return {'revision':ID,'version':VERSION,'versionCode':CODE,
            'changedFiles':[AUTO,GRADLE],
            'probeCadenceChanged':False,'appliedExposureRampChanged':False,
            'photographicBrightnessThresholdsChanged':False,'tapSearchRangeChanged':False,
            'nightAutoRetuned':False,'subjectTrackingAdded':False,'rendererChanged':False,
            'targetPersistenceAdded':True,'phoneValidationPending':True}

def post(root,baseline,out):
    root=root.resolve();out.mkdir(parents=True,exist_ok=True)
    rec=json.loads((root/RECEIPT).read_text());now=inventory(root)
    modified=[p for p,h in rec['after'].items() if now.get(p)!=h]
    added={p:h for p,h in now.items() if p not in rec['after']}
    report={'modifiedAuditedInputs':modified,'addedBuildInputs':added}
    (out/'POSTBUILD_INPUTS.json').write_text(json.dumps(report,indent=2)+'\n')
    need(not modified,'Audited compilation input changed after build')
    need(all(p.startswith('app/src/main/cpp/') for p in added),'Unexpected generated source input')
    apks=list((root/'app/build/outputs/apk/debug').glob('*.apk'));need(len(apks)==1,'Expected one APK')
    bases=list(baseline.rglob('M9Cam_2.07_AESTABILITY1A.apk'));need(len(bases)==1,'Missing delivered 2.07 APK')
    old=bases[0];need(sha(old.read_bytes())==BASE_APK,'Incorrect delivered 2.07 APK bytes')
    def frozen(z):
        return {n:sha(z.read(n)) for n in z.namelist()
                if not n.endswith('/') and n.startswith(('lib/','assets/','res/raw/'))}
    with zipfile.ZipFile(old) as a,zipfile.ZipFile(apks[0]) as b:
        fa=frozen(a);fb=frozen(b);need(fa==fb,'Packaged photographic/native resources changed')
        dex=b''.join(b.read(n) for n in b.namelist() if n.endswith('.dex'))
        for token in [b'M9AETARGETSTABILITY1A',b'aeTargetRawEv',b'aeTargetAcceptedEv',
                      b'M9AESTABILITY1A',b'M9AECADENCE1A',b'EXACTPATCHCLIP1B']:
            need(token in dex,'Missing DEX marker '+repr(token))
    target=out/'M9Cam_2.08_AETARGETSTABILITY1A.apk';shutil.copyfile(apks[0],target)
    proof={'version':VERSION,'versionCode':CODE,'apkSha256':sha(target.read_bytes()),
           'baselineApkSha256':BASE_APK,'frozenEntriesCompared':len(fa),
           'frozenEntriesByteIdentical':True,'allAuditedCompilationInputsUnchanged':True,
           'phoneValidationPending':True}
    (out/'APK_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
    (out/'SHA256SUMS.txt').write_text(proof['apkSha256']+'  '+target.name+'\n')
    return proof

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='apply': result=apply(Path(sys.argv[2]))
    elif len(sys.argv)==5 and sys.argv[1]=='post': result=post(*map(Path,sys.argv[2:]))
    else: raise SystemExit('usage: apply.py apply ROOT | post ROOT BASELINE OUTPUT')
    print(json.dumps(result,indent=2))
