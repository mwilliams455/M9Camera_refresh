"""Prove the only functional source edit is an allowed profile-name delimiter."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root);export='app/src/main/java/com/particlesdevs/photoncamera/processing/M9DngProfileExport.java'
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p));assert changed==['app/build.gradle',export],changed
old=(parent/export).read_text();new=(root/export).read_text()
assert old.count('+" C:"+')==new.count('+" C-"+')==1
assert new.replace('+" C-"+','+" C:"+')==old
old=(parent/'app/build.gradle').read_text();new=(root/'app/build.gradle').read_text()
assert new.replace('27252','27251').replace('2.52-dngnamefix1a','2.51-m9perf1b').replace('2.52_DNGNAMEFIX1A','2.51_M9PERF1B')==old
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
report=dict(status='PASS',parent='2.51-m9perf1b',version='2.52-dngnamefix1a',changedFiles=changed,
 unchangedScopedFiles=len(a)-2,onlyFunctionalEdit='Profile name uses C- instead of forbidden C:',
 profileGeneratorAndWriterByteIdentical=True,rendererAndExposureByteIdentical=True,
 nativeSourcesAndAssetsByteIdentical=True,monochromByteIdentical=True,
 previousPerformanceChangesRetained=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
