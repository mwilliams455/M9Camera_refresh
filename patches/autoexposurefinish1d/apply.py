"""Apply AUTOEXPOSUREFINISH1D only after exact 1.76 adaptive-backlight parent."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1D'
CHANGED={AUTO,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AUTOEXPOSUREFINISH1D assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('M9 highlight-guard Auto candidate mismatch')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.77-m9autoexposurefinish1d-tg1'" not in gradle or 'versionCode 26697' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1D version mismatch')

    frozen=[
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/M9DiagnosticBurstSpool.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/cpp/m9color_jni.cpp',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)

    return {
      'revision':ID,
      'policyRevision':'M9AUTOEXPOSUREFINISH1D_M9HIGHLIGHTGUARD',
      'version':'1.77-m9autoexposurefinish1d-tg1',
      'versionCode':26697,
      'changed':sorted(CHANGED),
      'adaptiveBacklightFrom1C':True,
      'm9CharacterHighlightGuard':True,
      'softCenterClipCapRangeApprox':[0.075,0.12],
      'softCenterBrightCapRangeApprox':[0.20,0.28],
      'fullFrameSoftClipCeiling':0.30,
      'backlightConfidenceEngage':0.22,
      'backlightConfidenceRelease':0.12,
      'lowerTargetFreshConfirmations':2,
      'hardSafetyReleaseImmediate':True,
      'wholeDarkScenePolicyChanged':False,
      'lowKeyNightPolicyChanged':False,
      'JPEG_DNG_previewTC20_shader_shutterDrawLock_spool_unchanged':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent=REPO/'patches/autoexposurefinish1c/M9AutoExposure2D.java'
    if (root/AUTO).read_bytes()!=parent.read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1D requires exact AUTOEXPOSUREFINISH1C policy source')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.76-m9autoexposurefinish1c-tg1'" not in gradle or 'versionCode 26696' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1D requires exact 1.76 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26696','versionCode 26697','version code')
    gradle=one(gradle,
        "versionName '1.76-m9autoexposurefinish1c-tg1'",
        "versionName '1.77-m9autoexposurefinish1d-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))

    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
