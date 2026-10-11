"""Verify exact source scope and reverse restoration of the 2.82 parent."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,tempfile
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def files(r):
    return {p.relative_to(r).as_posix():sha(p.read_bytes()) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha((r/'app/build.gradle').read_bytes())}
a,b=files(parent),files(root);m=json.loads((here/'manifest.json').read_text())
fp=lambda f:sha(json.dumps(f,sort_keys=True,separators=(',',':')).encode())
assert fp(a)==m['parentScopedSha256'] and fp(b)==m['candidateScopedSha256']
changed=sorted(n for n in a.keys()|b.keys() if a.get(n)!=b.get(n));assert changed==sorted(m['fileOverrides'])
assert len(changed)==5 and len(m["newFiles"])==1
assert sha((here/'monoaeref1a.patch.gz').read_bytes())==m['patchSha256']
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp)
    for n in changed:
        (t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
    subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'monoaeref1a.patch.gz').read_bytes()),check=True)
    for n in changed:
        if n in m['newFiles']:assert not (t/n).exists()
        else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
# Keep exposure plans, rendering, both save pipelines and capture lifecycle byte-identical.
for n in ['capture/CaptureController.java','manual/ParamController.java','monochrom/render/M9R35Renderer.java','monochrom/render/MonoSaveQueue.java','monochrom/export/MonoDngExport1A.java','monochrom/export/MonoDngSpool1B.java','monochrom/exposure/MonoExposureStore1A.java','monochrom/exposure/MonoExposurePlan1A.java','m9/render/M9PrimaryRenderQueue.java','m9/M9DiagnosticBurstSpool.java','monochrom/M9DiagnosticBurstSpool.java']:
 p='app/src/main/java/com/particlesdevs/photoncamera/'+n
 assert (parent/p).read_bytes()==(root/p).read_bytes(),p
c=(root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java').read_text()
# The M9 still route itself is unchanged.
old=(parent/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java').read_text()
start='    private synchronized void captureStillPicture()';end='    private static boolean'
def body(s,start):
 begin=s.index('{',s.index(start));depth=1;i=begin+1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[begin:i]
assert body(c,start)==body(old,start)
reject=body(c,'    void rejectUnsubmittedExposurePlan(')
assert reject.index('!attempt.finish()')<reject.index('recordMonoExposureReadinessFailure1B(attempt)')<reject.index('activeStillCapture = null')
# The allocator differs only in its observation qualification guard, not numerical math.
p='app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/MonoIsoExpoSelector.java'
old=(parent/p).read_text();new=(root/p).read_text()
oldGuard='        Integer ae=observation.get(CaptureResult.CONTROL_AE_MODE);\n        Integer aeComp=observation.get(CaptureResult.CONTROL_AE_EXPOSURE_COMPENSATION);\n        if(iso==null || iso<=0 || exposure==null || exposure<=0 || ae==null || ae==0 || (aeComp!=null && aeComp!=0))return null;'
newGuard='        if(iso==null || iso<=0 || exposure==null || exposure<=0 || !entry.neutralAeReference.usable)return null;'
assert old.count(oldGuard)==1 and old.replace(oldGuard,newGuard)==new
p='app/src/main/java/com/particlesdevs/photoncamera/monochrom/preview/MonoGpuPreview2A.java'
old=(parent/p).read_text();new=(root/p).read_text()
for start in ['    public static synchronized void configure(', '    public static synchronized void observe(',
              '    private static Context context(', '    private static String curveEvidence(',
              '    public static synchronized Binding bind(', '    public static synchronized void publish(',
              '    public static final class Context {','    public static final class Binding {']:
 assert body(old,start)==body(new,start),start
assert 'private static final long MAX_CONTEXT_AGE_NS=250000000L;' in new
report={'status':'PASS','changedScopedFiles':changed,'unchangedScopedFiles':sum(a.get(n)==v for n,v in b.items()),'reversePatchExactlyRestoresParent':True,'parentScopedSha256':fp(a),'candidateScopedSha256':fp(b),'nativeAndAssetsUnchanged':not any(n.startswith(('app/src/main/cpp/','app/src/main/assets/')) for n in changed),'phoneValidationPending':True}
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
