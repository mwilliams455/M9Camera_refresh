"""Apply AUTOEXPOSUREFINISH1G soft-anchor middle ground after exact 1.79 FINISH1F parent."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1G'
CHANGED={AUTO,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AUTOEXPOSUREFINISH1G assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('soft-anchor Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'policy marker':'M9AUTOEXPOSUREFINISH1G_SOFTANCHOR1A' in auto,
      'body lock state':'latchedBodyMask' in auto and 'latchedBodyTargetMedian' in auto,
      'overlap hold':'overlap>=.50' in auto,
      'two-confirm switch':'pendingBodyConfirmations>=2' in auto,
      'same target retained':'candidateForMask(base,latchedBodyMask' in auto,
      'read-only diagnostics':'bodyLockMaskForDiagnostics' in auto,
      'protected open anchor':'protectedOpenAnchorMask' in auto,
      'open anchor coherent':'hasInner&&count>=2' in auto,
      'open anchor excludes windows':'hi<=235' in auto and 's.fieldBright[f]<=.12' in auto,
      'soft anchor cap method':'protectedOpenAnchorLiftCap' in auto,
      'ordinary cap':'PROTECTED_ANCHOR_ORDINARY_MAX_EV=.25' in auto,
      'severe cap':'PROTECTED_ANCHOR_SEVERE_MAX_EV=.50' in auto,
      'hard anchor veto removed':'protected_open_anchor_present' not in auto,
      '1F field map retained':'FIELD_ROWS=4, FIELD_COLS=6' in auto,
      '1F M9 ceiling retained':'v.median>=72&&v.q25>=36' in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AUTOEXPOSUREFINISH1G verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if "versionName '1.80-m9autoexposurefinish1g-softanchor1a-tg1'" not in gradle or 'versionCode 26700' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1G version mismatch')

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
      'policyRevision':'M9AUTOEXPOSUREFINISH1G_SOFTANCHOR1A',
      'version':'1.80-m9autoexposurefinish1g-softanchor1a-tg1',
      'versionCode':26700,
      'changed':sorted(CHANGED),
      'multifieldFrom1F':True,
      'bodyMaskTemporalLock':True,
      'bodyTargetTemporalLock':True,
      'bodyOverlapHoldFraction':0.50,
      'disjointBodySwitchFreshConfirmations':2,
      'invalidBodyReleaseFreshConfirmations':2,
      'protectedOpenAnchorGuard':True,
      'protectedOpenAnchorPolicy':'soft_positive_lift_cap',
      'protectedOpenAnchorOrdinaryMaxEv':0.25,
      'protectedOpenAnchorSevereMaxEv':0.50,
      'hardOpenAnchorVetoRemoved':True,
      'openAnchorRequiresCoherentInnerComponent':True,
      'openAnchorWindowExclusion':True,
      'quarterStopRiseUnchanged':True,
      'lowerTargetTwoSampleHysteresisPreserved':True,
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

    parent=REPO/'patches/autoexposurefinish1f/M9AutoExposure2D.java'
    if (root/AUTO).read_bytes()!=parent.read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1G requires exact AUTOEXPOSUREFINISH1F policy source')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.79-m9autoexposurefinish1f-tg1'" not in gradle or 'versionCode 26699' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1G requires exact 1.79 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26699','versionCode 26700','version code')
    gradle=one(gradle,
        "versionName '1.79-m9autoexposurefinish1f-tg1'",
        "versionName '1.80-m9autoexposurefinish1g-softanchor1a-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))

    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
