"""Disable legacy heavy preview diagnostics in normal M9 Modern on exact 1.74 parent."""
from pathlib import Path
import hashlib,json,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

GRADLE='app/build.gradle'
CONTROLLER='app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java'
MAIN='app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java'
ID='M9PREVIEWLEAN1A'

BASELINE={
 GRADLE:'010f2b4ddfc73c78af7285aa37a612b4a5a2104b416958cb7a3d0294c81b6d47',
 CONTROLLER:'b35adf80a63667bc9ac2318af1b542755336d840fd0b1c80378dae3dfe3f7e67',
 MAIN:'8a3bf1a9ed1abbc535e1efec5aebf40c6c46d3a427fe1ded76dbe98ac81d27a9',
}
CHANGED=set(BASELINE)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def transform_controller(s):
    return one(
      s,
      '''            if (M9Config.isCaptureTest()) {
                com.particlesdevs.photoncamera.m9.preview.M9RootCauseTrace1A.observe(
                    request, result, PhotonCamera.getSettings().mCameraID, paramController.getM9UserEv1A());
            }''',
      '''            // M9PREVIEWLEAN1A: this 30 s root-cause recorder is diagnostic-only.
            // Do not run it continuously in the normal M9 Modern viewfinder.
            if (!M9Config.isM9Modern() && M9Config.isCaptureTest()) {
                com.particlesdevs.photoncamera.m9.preview.M9RootCauseTrace1A.observe(
                    request, result, PhotonCamera.getSettings().mCameraID, paramController.getM9UserEv1A());
            }''',
      'root-cause preview callback gate')

def transform_main(s):
    return one(
      s,
      '''        mM9ShutterPixels = new com.particlesdevs.photoncamera.m9.preview.M9RootCausePixels1A();
        com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.registerPixels(mM9ShutterPixels);''',
      '''        // M9PREVIEWLEAN1A: the 64x64 x 9 shutter-trace preview history is
        // diagnostic-only and must not run continuously in M9 Modern.
        mM9ShutterPixels = null;
        com.particlesdevs.photoncamera.m9.preview.M9ShutterTrace1A.registerPixels(null);
        Log.d("M9PreviewLean1A", "M9PREVIEWLEAN1A heavy live root-cause diagnostics disabled");''',
      'root-cause pixel collector disable')

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root); before=proof['before']
    if now!=proof['after']: raise SystemExit('PREVIEWLEAN assembled source drift')
    changed={k for k in before if now.get(k)!=before[k]}
    added=set(now)-set(before); removed=set(before)-set(now)
    if changed!=CHANGED or added or removed:
        raise SystemExit('unexpected delta changed=%r added=%r removed=%r'%
                         (sorted(changed),sorted(added),sorted(removed)))
    c=(root/CONTROLLER).read_text(); m=(root/MAIN).read_text()
    checks={
      'modern root trace off':'!M9Config.isM9Modern() && M9Config.isCaptureTest()' in c,
      'shutter pixel collector null':'mM9ShutterPixels = null;' in m,
      'shutter pixel register null':'M9ShutterTrace1A.registerPixels(null);' in m,
      'packaged revision marker':'M9PREVIEWLEAN1A heavy live root-cause diagnostics disabled' in m,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PREVIEWLEAN verify failed: '+name)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.75-m9previewlean1a-tg1'" not in gradle or 'versionCode 26695' not in gradle:
        raise SystemExit('PREVIEWLEAN build identity mismatch')

    # Freeze all photographic and exposure behavior.
    for rel in [
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/cpp/m9color_jni.cpp',
    ]:
        if before[rel]!=now[rel]: raise SystemExit('frozen photographic seam changed '+rel)

    return {
      'revision':ID,'version':'1.75-m9previewlean1a-tg1','versionCode':26695,
      'changed':sorted(CHANGED),
      'normalM9ModernRootCauseTrace':False,
      'normalM9ModernRootCausePixels':False,
      'auto_JPEG_DNG_previewTC20_shader_shutterDrawLock_frozen':True,
      'deviceValidationPending':True,
    }

def main(root):
    root=root.resolve(); receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2)); return
    for rel,expected in BASELINE.items():
        actual=sha(root/rel)
        if actual!=expected: raise SystemExit(f'PREVIEWLEAN baseline mismatch {rel}: {actual}')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.74-m9previewheap1a-tg1'" not in gradle or 'versionCode 26694' not in gradle:
        raise SystemExit('PREVIEWLEAN requires exact 1.74 parent identity')

    before=inventory(root)
    (root/CONTROLLER).write_text(transform_controller((root/CONTROLLER).read_text()))
    (root/MAIN).write_text(transform_main((root/MAIN).read_text()))
    gradle=one(gradle,'versionCode 26694','versionCode 26695','version code')
    gradle=one(gradle,"versionName '1.74-m9previewheap1a-tg1'",
               "versionName '1.75-m9previewlean1a-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
