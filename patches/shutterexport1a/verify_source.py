"""Verify that only diagnostic delivery and version metadata change from 2.61."""
from pathlib import Path
import hashlib,json,sys,gzip,subprocess,tempfile,shutil
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src']
         for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
spool='app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java'
changed=sorted(n for n in a.keys()|b.keys() if a.get(n)!=b.get(n))
assert changed==sorted(['app/build.gradle',spool]),changed
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 for name in changed:
  (t/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,t/name)
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,
                input=gzip.decompress((here/'shutterexport1a.patch.gz').read_bytes()),check=True)
 for n in changed:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
old=(parent/spool).read_text();new=(root/spool).read_text()
def between(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
for start,end in [
 ('    private static void purgeLegacyBacklogOnce()', '    private static boolean isPriorityRole'),
 ('    private static void recoverPrivate()', '    private static void exportIndividual'),
 ('    private static boolean writePublicBytes(', '    public static JSONObject snapshotJson()')]:
 # New helper methods precede isPriorityRole; the legacy purge itself must stay exact.
 end_new='    private static boolean isShutterTraceRole' if 'purgeLegacy' in start else end
 assert between(old,start,end)==between(new,start,end_new),start
report=dict(status='PASS',parent='2.61-previewbridge1a',version='2.62-shutterexport1a',
 changedFiles=changed,unchangedScopedFiles=len(a)-2,totalScopedFiles=len(b),
 reversePatchExactlyRestoresParent=True,legacyResetNotRepeatedOrExpanded=True,
 existingStreamTransportAndRecoveryByteIdentical=True,
 exposureAfColourWbToneRenderersNativeSourcesAssetsAndMonochromByteIdentical=True,
 photoSaveQueuesAndCrashFixesByteIdentical=True,
 behaviorChange='dedicated bounded newest-first shutter trace exporter; recover existing traces; retry failed writes')
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
