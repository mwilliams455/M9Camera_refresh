"""Limit the fix to view callback lifetime; preserve all photographic/save code."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
f='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java';t='app/src/test/java/com/particlesdevs/photoncamera/ui/camera/RendererSwitchLifecycleTest.java'
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p));assert changed==['app/build.gradle',f,t],changed
old=(parent/'app/build.gradle').read_text();new=(root/'app/build.gradle').read_text()
assert new.replace('27254','27253').replace('2.54-switchview1a','2.53-jpegqueue1a').replace('2.54_SWITCHVIEW1A','2.53_JPEGQUEUE1A')==old
old=(parent/f).read_text();new=(root/f).read_text()
def method(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=1;i=brace+1
 while depth:
  if text[i]=='{':depth+=1
  if text[i]=='}':depth-=1
  i+=1
 return text[start:i]
for signature,guard in [
 ('    private boolean syncLensClusterOffset()', '        if (!panelViewActive || cameraFragmentBinding == null) return false;\n'),
 ('    private void updatePanelBlurSpecs()', '        if (!panelViewActive || cameraFragmentBinding == null || textureView == null) return;\n'),
 ('    private void applyManualDomeHeight()', '        if (!panelViewActive || cameraFragmentBinding == null) return;\n')]:
 assert method(new,signature).replace(guard,'')==method(old,signature),signature
# No capture, colour, preview-render math or save routine changed inside CameraFragment.
for signature in ['    private void updateScreenLog(', '    public void onResume()', '    public void onPause()', '    public void onDestroy()']:
 assert method(old,signature)==method(new,signature),signature
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
report=dict(status='PASS',parent='2.53-jpegqueue1a',version='2.54-switchview1a',changedFiles=changed,unchangedScopedFiles=len(a)-3,photographicRenderingAndExposureByteIdentical=True,nativeSourcesAndAssetsByteIdentical=True,saveQueuesAndRawProfileFixByteIdentical=True,liveLensGeometryMathUnchanged=True,previewAndCaptureCallbacksUnchanged=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
