"""Verify exact source scope and reverse restoration of the 2.73 parent."""
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
assert len(changed)==4 and len(m["newFiles"])==2
assert sha((here/'aflifecycle1a.patch.gz').read_bytes())==m['patchSha256']
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp)
    for n in changed:
        (t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
    subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'aflifecycle1a.patch.gz').read_bytes()),check=True)
    for n in changed:
        if n in m['newFiles']:assert not (t/n).exists()
        else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
# Both production still routes must reach the tested shared request policy.
c=(root/'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java').read_text()
for start in ['private synchronized void captureStillPicture()', 'private void captureStillPictureMono()']:
    # Use the method's balanced body instead of accepting unrelated helper calls.
    begin=c.index('{',c.index(start));depth=1;i=begin+1
    while depth:
        depth += (c[i]=='{')-(c[i]=='}');i+=1
    body=c[begin:i]
    for call in ['prepareStillFocus(captureBuilder);','guardStillCallback(attempt, CaptureCallback)','processOwnedStill(attempt,','submitStillBurst(attempt,']:
        assert call in body,(start,call)
assert c.count('prepareStillFocus(captureBuilder);')==2
assert 'restorePreviewSettings();' in c[c.index('public void onConfigured('):c.index('public void onConfigureFailed(')]
assert 'captureController.restorePreviewSettings();' in (root/'app/src/main/java/com/particlesdevs/photoncamera/manual/ParamController.java').read_text()
assert c.count('if (!acceptsPreviewResult(session)) return;')==2
assert 'submitStillBurst(sessionAttempt, cameraCaptureSession, captures, CaptureCallback)' in c
assert 'if (!acceptsSessionConfiguration(sessionGeneration, sessionToken, sessionDevice, sessionPreview))' in c
assert 'if (useM9FocusContinuity2B() && beginStillCapture() == null) return;' in c
assert 'sessionHandler.post(command)' in c
assert 'cancelPendingStill();' in c[c.index('public void closeCamera()'):c.index('public void closeCamera()')+1200]
report={'status' :'PASS','changedScopedFiles':changed,'unchangedScopedFiles':sum(a.get(n)==v for n,v in b.items()),'reversePatchExactlyRestoresParent':True,'parentScopedSha256':fp(a),'candidateScopedSha256':fp(b),'nativeAndAssetsUnchanged':not any(n.startswith(('app/src/main/cpp/','app/src/main/assets/')) for n in changed),'phoneValidationPending':True}
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
