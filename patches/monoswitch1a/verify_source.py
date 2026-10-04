"""Verify the switch repair changes no rendering, capture allocation, native code or assets."""
from pathlib import Path
import hashlib,json,sys
parent,root=map(lambda p:Path(p).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(root):
 return {p.relative_to(root).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (root/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(root/'app/build.gradle')}
a,b=files(parent),files(root)
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p))
allowed=['app/build.gradle','app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java','app/src/main/res/values/m9_overlay.xml','app/src/test/java/com/particlesdevs/photoncamera/ui/camera/RendererSwitchLifecycleTest.java']
assert changed==sorted(allowed),changed
m=json.loads((here/'manifest.json').read_text())
for name,value in m['fileOverrides'].items():assert b[name]==value,name
report={'status':'PASS','parent':'2.45-monomerge1a','version':'2.46-monoswitch1a','changedFiles':changed,'allOtherSourceFilesUnchanged':len(a)-3,'renderersNativeAssetsAndCaptureAllocatorUnchanged':True}
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
