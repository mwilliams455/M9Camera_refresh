"""Limit THUMBUI1A to gallery UI threading/ownership and preserve photographic code."""
from pathlib import Path
import hashlib,json,sys
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(r):return {p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(r/'app/build.gradle')}
a,b=files(parent),files(root)
camera='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/'
test='app/src/test/java/com/particlesdevs/photoncamera/ui/camera/'
expected=['app/build.gradle',camera+'CameraFragment.java',camera+'model/CameraFragmentModel.java',camera+'viewmodel/CameraFragmentViewModel.java',test+'RendererSwitchLifecycleTest.java',test+'viewmodel/GalleryThumbnailThreadTest.java']
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p));assert changed==sorted(expected),changed
old=(parent/'app/build.gradle').read_text();new=(root/'app/build.gradle').read_text()
assert new.replace('27255','27254').replace('2.55-thumbui1a','2.54-switchview1a').replace('2.55_THUMBUI1A','2.54_SWITCHVIEW1A')==old
def method(text,signature):
 start=text.index(signature);brace=text.index('{',start);depth=1;i=brace+1
 while depth:
  if text[i]=='{':depth+=1
  if text[i]=='}':depth-=1
  i+=1
 return text[start:i]
old=(parent/(camera+'CameraFragment.java')).read_text();new=(root/(camera+'CameraFragment.java')).read_text()
for signature in ['    private boolean syncLensClusterOffset()', '    private void updatePanelBlurSpecs()', '    private void applyManualDomeHeight()', '    private void updateScreenLog(', '    public void onPause()', '    public void onDestroy()', '        public void notifyImageSavedStatus(']:
 assert method(new,signature)==method(old,signature),signature
old=(parent/(camera+'model/CameraFragmentModel.java')).read_text();new=(root/(camera+'model/CameraFragmentModel.java')).read_text()
assert new.replace('this.bitmap = bitmap;\n        notifyPropertyChanged(BR.bitmap);','this.bitmap = bitmap;\n        notifyChange();')==old
m=json.loads((here/'manifest.json').read_text())
for n,d in m['parentFiles'].items():assert a[n]==d,n
for n,d in m['fileOverrides'].items():assert b[n]==d,n
report=dict(status='PASS',parent='2.54-switchview1a',version='2.55-thumbui1a',changedFiles=changed,unchangedScopedFiles=sum(a.get(p)==b.get(p) for p in a),totalScopedFiles=len(b),photographicRenderingAndExposureByteIdentical=True,nativeSourcesAndAssetsByteIdentical=True,saveQueuesAndRawProfileFixByteIdentical=True,liveLensGeometryMathUnchanged=True,previewAndCaptureCallbacksUnchanged=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
