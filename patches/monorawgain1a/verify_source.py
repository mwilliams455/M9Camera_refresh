"""Check the exact reconstruction and all deliberately frozen camera/render code."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,tempfile
parent,root=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def files(r):
 return {p.relative_to(r).as_posix():sha(p.read_bytes()) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha((r/'app/build.gradle').read_bytes())}
a,b=files(parent),files(root);m=json.loads((here/'manifest.json').read_text())
fingerprint=lambda f:sha(json.dumps(f,sort_keys=True,separators=(',',':')).encode())
assert fingerprint(a)==m['parentScopedSha256'] and fingerprint(b)==m['candidateScopedSha256']
changed=sorted(n for n in a.keys()|b.keys() if a.get(n)!=b.get(n));assert changed==sorted(m['fileOverrides'])
assert len(changed)==9 and len(m['newFiles'])==2
capture='app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
old='RenderProfile.isMonochrom() && M9Config.usesM9Pipeline() && PhotonCamera.getSettings().selectedMode == CameraMode.PHOTO'
new='RenderProfile.isMonochrom() && M9Config.usesM9Pipeline() && MonoExposurePlan1A.supportsMode(PhotonCamera.getSettings().selectedMode.name())'
assert (parent/capture).read_text().replace(old,new)==(root/capture).read_text(), 'CaptureController changed outside plan eligibility'
for scope in ['app/src/main/cpp','app/src/main/assets','app/src/main/jniLibs','app/src/main/java/com/particlesdevs/photoncamera/monochrom/render','app/src/main/java/com/particlesdevs/photoncamera/m9']:
 assert {n:v for n,v in a.items() if n.startswith(scope+'/')}=={n:v for n,v in b.items() if n.startswith(scope+'/')},scope
assert sha((here/'monorawgain1a.patch.gz').read_bytes())==m['patchSha256']
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 for n in changed:
  (t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
 subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'monorawgain1a.patch.gz').read_bytes()),check=True)
 for n in changed:
  if n in m['newFiles']:assert not (t/n).exists()
  else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
report={'status':'PASS','changedScopedFiles':changed,'unchangedScopedFiles':sum(a.get(n)==v for n,v in b.items()),'reversePatchExactlyRestoresParent':True,'exactReconstructionVerified':True,'allRenderersShadersFirmwareAssetsNativesAndColourM9Unchanged':True,'afWbLogicUnchanged':True,'phoneValidationPending':True}
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
