"""Apply AUTOEXPOSUREFINISH1I FASTACQUIRE1B SAFE075 after exact 1.81 FINISH1H parent."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1I'
CHANGED={AUTO,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AUTOEXPOSUREFINISH1I assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('FINISH1I Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'policy marker':'M9AUTOEXPOSUREFINISH1I_FASTACQUIRE1B_SAFE075' in auto,
      'safe075 step':'SAFE_FAST_POSITIVE_SLEW_EV=.75' in auto,
      'safe075 freshness':'SAFE_FAST_MAX_SAMPLE_AGE_NS=250000000L' in auto,
      'safe075 remaining gap':'target-current<1.25' in auto,
      'safe075 no open anchor':'openAnchorMask!=0' in auto,
      'safe075 severe scene':'s.median<=20&&s.centerMedian<=30&&s.centerQ25<=14&&s.dark>=.65' in auto,
      'safe075 severe body':'body.confidence>=.50&&body.severity>=.75' in auto,
      'target clamp retained':'if(target>0)target=Math.min(target,positiveLimit);' in auto,
      'result target clamp retained':'Math.min(target,current+positiveRiseStepEv)' in auto,
      'field ownership retained':'multifield_no_qualified_body_scene_fallback' in auto,
      'soft anchor retained':'protectedOpenAnchorLiftCap' in auto,
      'body lock retained':'latchedBodyMask' in auto and 'pendingBodyConfirmations>=2' in auto,
      'M9 ceiling retained':'v.median>=72&&v.q25>=36' in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AUTOEXPOSUREFINISH1I verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if "versionName '1.82-m9autoexposurefinish1i-fastacquire1b-safe075-tg1'" not in gradle or 'versionCode 26702' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1I version mismatch')

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
      'policyRevision':'M9AUTOEXPOSUREFINISH1I_FASTACQUIRE1B_SAFE075',
      'version':'1.82-m9autoexposurefinish1i-fastacquire1b-safe075-tg1',
      'versionCode':26702,
      'changed':sorted(CHANGED),
      'parent':'1.81_FINISH1H_FIELDOWNERSHIP1A_FASTACQUIRE1A',
      'normalPositiveSlewEv':0.25,
      'fastPositiveSlewEv':0.50,
      'safeFastPositiveSlewEv':0.75,
      'safeFastMaxSampleAgeMs':250,
      'safeFastMinimumRemainingGapEv':1.25,
      'safeFastOpenAnchorAllowed':False,
      'safeFastTargetAndHeadroomClampPreserved':True,
      'fieldOwnershipPreserved':True,
      'softAnchorPolicyPreserved':True,
      'lowerTargetTwoSampleHysteresisPreserved':True,
      'wholeSceneTargetsChanged':False,
      'backlightTargetsChanged':False,
      'JPEG_DNG_previewTC20_shader_renderer_unchanged':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent=REPO/'patches/autoexposurefinish1h/M9AutoExposure2D.java'
    if (root/AUTO).read_bytes()!=parent.read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1I requires exact AUTOEXPOSUREFINISH1H policy source')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.81-m9autoexposurefinish1h-fieldownership1a-fastacquire1a-tg1'" not in gradle or 'versionCode 26701' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1I requires exact 1.81 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26701','versionCode 26702','version code')
    gradle=one(gradle,
        "versionName '1.81-m9autoexposurefinish1h-fieldownership1a-fastacquire1a-tg1'",
        "versionName '1.82-m9autoexposurefinish1i-fastacquire1b-safe075-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))

    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
