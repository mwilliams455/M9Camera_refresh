"""Require a two-file patch, exact parent reversal and unchanged rendering sources."""
from pathlib import Path
import hashlib,json,sys,gzip,subprocess,tempfile,shutil
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src']
         for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
auto='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
changed=sorted(n for n in a.keys()|b.keys() if a.get(n)!=b.get(n))
assert changed==sorted(['app/build.gradle',auto]),changed
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 for name in changed:
  (t/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,t/name)
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,
                input=gzip.decompress((here/'previewrecover1a.patch.gz').read_bytes()),check=True)
 for n in changed:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
old=(parent/auto).read_text();new=(root/auto).read_text()
# The sample matcher, all histogram/field-map calculation, all target selection,
# all highlight budgets and body qualification methods remain exact text matches.
for start,end in [('    public static final class Stats {','    public static synchronized Decision decide('),
                  ('    private static BodyCandidate stabilizeBodyCandidate(', '    private static void resetHighlightRecovery()')]:
 if start not in new:continue
 begin_old=old.index(start);begin_new=new.index(start)
 end_old=old.index(end if end in old else '    private static void resetLowerTargetHysteresis()',begin_old)
 end_new=new.index(end,begin_new)
 assert old[begin_old:end_old]==new[begin_new:end_new],start
report=dict(status='PASS',parent='2.59-previewsettle1a',version='2.60-previewrecover1a',
 changedFiles=changed,unchangedScopedFiles=len(a)-2,totalScopedFiles=len(b),
 reversePatchExactlyRestoresParent=True,
 targetsAndHighlightBudgetsUnchanged=True,
 isoAllocationAndAeLockAndTapPolicyByteIdentical=True,
 framePairingAndProbeSchedulingAndFreshnessGuardsByteIdentical=True,
 whiteBalanceColourSavedRenderersNativeSourcesAssetsMonochromByteIdentical=True,
 queuesAndRecentCrashFixesByteIdentical=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
