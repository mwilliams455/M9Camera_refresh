"""Verify exact source scope and reverse restoration of the 2.76 parent."""
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
assert len(changed)==8 and not m["newFiles"]
assert sha((here/'uisettings1a.patch.gz').read_bytes())==m['patchSha256']
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp)
    for n in changed:
        (t/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/n,t/n)
    subprocess.run(['git','apply','--reverse','--whitespace=nowarn','-'],cwd=t,input=gzip.decompress((here/'uisettings1a.patch.gz').read_bytes()),check=True)
    for n in changed:
        if n in m['newFiles']:assert not (t/n).exists()
        else:assert (t/n).read_bytes()==(parent/n).read_bytes(),n
# Production retirement happens before model binding. The XML starts hidden.
import xml.etree.ElementTree as ET
fragment=(root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java').read_text()
assert fragment.index('initMembers();') < fragment.index('setModelsToLayout();')
init=fragment[fragment.index('private void initMembers()'):fragment.index('private void setModelsToLayout()')]
assert 'getCameraFragmentModel().disableLegacySettingsBar();' in init
model=(root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/model/CameraFragmentModel.java').read_text()
assert 'legacySettingsBarEnabled && settingsBarVisibility' in model
assert 'legacySettingsBarEnabled = false;' in model
binding=(root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/binding/CustomBinding.java').read_text()
body=binding[binding.index('public static void toggleSettingsBarVisibility'):binding.index('@BindingAdapter("setAuxButtonModel")')]
assert '.post(' not in body and 'viewGroup.setVisibility(View.GONE);' in body
android='{http://schemas.android.com/apk/res/android}'
layout=ET.parse(root/'app/src/main/res/layout/camera_fragment.xml').getroot()
panels=[e for e in layout.iter() if e.attrib.get(android+'id')=='@+id/settings_bar']
assert len(panels)==1 and panels[0].attrib[android+'visibility']=='gone'
ui=(root/'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraUIController.java').read_text()
assert 'getString(R.string.photo_processing_busy)' in ui
assert 'M9 processing queue full - try again shortly' not in ui
for n in ['capture/CaptureController.java','monochrom/render/MonoSaveQueue.java','m9/render/M9PrimaryRenderQueue.java']:
 p='app/src/main/java/com/particlesdevs/photoncamera/'+n
 assert (parent/p).read_bytes()==(root/p).read_bytes(),p
report={'status' :'PASS','changedScopedFiles':changed,'unchangedScopedFiles':sum(a.get(n)==v for n,v in b.items()),'reversePatchExactlyRestoresParent':True,'parentScopedSha256':fp(a),'candidateScopedSha256':fp(b),'nativeAndAssetsUnchanged':not any(n.startswith(('app/src/main/cpp/','app/src/main/assets/')) for n in changed),'phoneValidationPending':True}
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
