"""Apply AUTOEXPOSUREFINISH1E only after exact 1.77 M9-character-guard parent."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1E'
CHANGED={AUTO,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AUTOEXPOSUREFINISH1E assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('multi-field Auto candidate mismatch')

    auto=(root/AUTO).read_text()
    checks={
      'policy marker':'M9AUTOEXPOSUREFINISH1E_MULTIFIELD_BODY' in auto,
      '4x6 topology':'FIELD_ROWS=4, FIELD_COLS=6' in auto and 'FIELD_COUNT=FIELD_ROWS*FIELD_COLS' in auto,
      'coherent components':'no_coherent_dark_body' in auto and 'count>14' in auto,
      'deep floor ignored':'deepFloor=med<7&&hi<24' in auto,
      'edge strip rejected':'count==2&&!hasInner' in auto,
      'high-key suppression':'scene_already_high_key' in auto,
      'relative body target':'body.median+16+6*(1-severity)' in auto,
      'body target max 60':',44,60)' in auto,
      'M9 body ceiling':'v.median>=72&&v.q25>=36' in auto,
      'global highlight ceiling':'scene.clipped>.30' in auto,
      'M10R topology attribution':'M10R_4x6_topology_only_not_numerical_parity' in auto,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('AUTOEXPOSUREFINISH1E verify failed: '+name)

    gradle=(root/GRADLE).read_text()
    if "versionName '1.78-m9autoexposurefinish1e-tg1'" not in gradle or 'versionCode 26698' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1E version mismatch')

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
      'policyRevision':'M9AUTOEXPOSUREFINISH1E_MULTIFIELD_BODY',
      'version':'1.78-m9autoexposurefinish1e-tg1',
      'versionCode':26698,
      'changed':sorted(CHANGED),
      'renderedFieldTopology':'4x6_24_regions',
      'topologyProvenance':'M10R_architecture_borrowed_not_numerical_parity',
      'bodySelection':'coherent_dark_component_not_center_rectangle',
      'deepFeaturelessShadowExcluded':True,
      'isolatedEdgeShadowSuppressed':True,
      'alreadyHighKeyDarkPatchSuppressed':True,
      'bodyReadabilityTarget':'relative_baseline_plus_16_to_22_codes_clamped_44_to_60',
      'bodyQ25Target':'relative_baseline_plus_8_to_12_codes_clamped_14_to_26',
      'm9CharacterBodyCeiling':{'median':72,'q25':36},
      'fullFrameClipCeiling':0.30,
      'wholeDarkScenePolicyChanged':False,
      'lowKeyNightPolicyChanged':False,
      'temporalHysteresisFrom1DPreserved':True,
      'JPEG_DNG_previewTC20_shader_shutterDrawLock_spool_unchanged':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent=REPO/'patches/autoexposurefinish1d/M9AutoExposure2D.java'
    if (root/AUTO).read_bytes()!=parent.read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1E requires exact AUTOEXPOSUREFINISH1D policy source')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.77-m9autoexposurefinish1d-tg1'" not in gradle or 'versionCode 26697' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1E requires exact 1.77 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=one(gradle,'versionCode 26697','versionCode 26698','version code')
    gradle=one(gradle,
        "versionName '1.77-m9autoexposurefinish1d-tg1'",
        "versionName '1.78-m9autoexposurefinish1e-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))

    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
