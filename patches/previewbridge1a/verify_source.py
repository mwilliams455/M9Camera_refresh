"""Verify the bounded reference transition and exact preservation of other paths."""
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
                input=gzip.decompress((here/'previewbridge1a.patch.gz').read_bytes()),check=True)
 for n in changed:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
old=(parent/auto).read_text();new=(root/auto).read_text()
def between(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
start='    public static final class Stats {';end='    public static synchronized Decision decide('
assert between(old,start,end)==between(new,start,end),'probe validation/statistics changed'
start='    private static BodyCandidate stabilizeBodyCandidate('
assert between(old,start,'    private static void resetHighlightRecovery()')==between(new,start,'    private static boolean canBridgeReference('),'body/highlight policy changed'
start='        } else if(valid) {'
valid_old=between(old,start,'        } else {\n            double bounded=legacy>0?0:legacy;')
valid_new=between(new,start,'        } else if(canBridgeReference(')
anchor='''            if(freshSample) {
                trustedSampleNs=sample.submittedNs;
                trustedReferenceEnergy=referenceEnergy;
                trustedAutoEv=result;
            }
'''
assert valid_new.replace(anchor,'')==valid_old,'valid-sample decisions changed'
start='    private static void resetHighlightRecovery()'
assert old[old.index(start):]==new[new.index(start):],'tap or later policy changed'
report=dict(status='PASS',parent='2.60-previewrecover1a',version='2.61-previewbridge1a',
 changedFiles=changed,unchangedScopedFiles=len(a)-2,totalScopedFiles=len(b),
 reversePatchExactlyRestoresParent=True,validSampleDecisionsUnchanged=True,
 targetsAndHighlightBudgetsUnchanged=True,probeValidationTolerancesUnchanged=True,
 isoAllocationAeLockTapPolicyAfAndControlsByteIdentical=True,
 framePairingProbeSchedulingAndTc20ByteIdentical=True,
 whiteBalanceColourSavedRenderersNativeSourcesAssetsMonochromByteIdentical=True,
 queuesAndRecentCrashFixesByteIdentical=True,
 behaviorChange='short energy-capped transition on rejected reference-energy mismatch only; capture follows resulting displayed plan')
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
