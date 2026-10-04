"""Apply NOISECANCEL1A quiet-chroma cancellation after exact 1.82 FINISH1I."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

CPP='app/src/main/cpp/m9detail1h_guard.cpp'
JAVA='app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9Detail1H.java'
GRADLE='app/build.gradle'
ID='M9NOISECANCEL1A'
CHANGED={CPP,JAVA,GRADLE}

def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('NOISECANCEL1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/CPP).read_bytes()!=(HERE/'m9detail1h_guard.cpp').read_bytes():
        raise SystemExit('NOISECANCEL1A native guard mismatch')
    if (root/JAVA).read_bytes()!=(HERE/'M9Detail1H.java').read_bytes():
        raise SystemExit('NOISECANCEL1A Java diagnostics mismatch')

    cpp=(root/CPP).read_text();java=(root/JAVA).read_text();gradle=(root/GRADLE).read_text()
    checks={
      'native marker':'NOISECANCEL1A_QUIETCHROMA' in cpp,
      'gate start':'c<=.65' in cpp,
      'gate full':'(c-.65)/.25' in cpp,
      'bounded blend':'c + .50*gate*(1.-c)' in cpp,
      'base classifier retained':'const double trust = unit(2. - (e / 5.) / std::max(v / 5., 1e-12));' in cpp,
      'base weight retained':'const double weight = unit(1. - std::abs(r) / (2. * std::sqrt(std::max(double(vr[i]), 1e-12))));' in cpp,
      'strength1 caller retained':'noiseCancelBaseProfileStrength",1.0' in java,
      'green luma frozen':'noiseCancelGreenLumaMutation",false' in java,
      'diagnostic marker':'NOISECANCEL1A_QUIETCHROMA' in java,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('NOISECANCEL1A verify failed: '+name)
    if "versionName '1.83-m9noisecancel1a-quietchroma-tg1'" not in gradle or 'versionCode 26703' not in gradle:
        raise SystemExit('NOISECANCEL1A version mismatch')

    frozen=[
      'app/src/main/cpp/m9detail1h.cpp',
      'app/src/main/cpp/m9detail1h_rb.cpp',
      'app/src/main/cpp/m9color_jni.cpp',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewMeter2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/assets/m9/m9_curve02_firmware.bin',
    ]
    for rel in frozen:
        if proof['before'][rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)

    return {
      'revision':ID,
      'policyRevision':'NOISECANCEL1A_QUIETCHROMA',
      'version':'1.83-m9noisecancel1a-quietchroma-tg1',
      'versionCode':26703,
      'changed':sorted(CHANGED),
      'parent':'1.82_FINISH1I_FASTACQUIRE1B_SAFE075',
      'carrier':'R/B_minus_green_only',
      'greenLumaMutation':False,
      'baseNoiseProfileStrength':1.0,
      'confidenceGateStart':0.65,
      'confidenceGateFull':0.90,
      'maxRemainingBlendFraction':0.50,
      'censoredNeighbourhoodPolicyChanged':False,
      'sharpnessChanged':False,
      'autoExposureChanged':False,
      'TC20ToneColourChanged':False,
      'JPEG_DNG_preview_shader_unchanged':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent_cpp=REPO/'research/detail1a/noise2_guard_native.cpp'
    parent_java=REPO/'patches/m9detail1h/M9Detail1H.java'
    if (root/CPP).read_bytes()!=parent_cpp.read_bytes():
        raise SystemExit('NOISECANCEL1A requires exact DETAIL1H native guard parent')
    if (root/JAVA).read_bytes()!=parent_java.read_bytes():
        raise SystemExit('NOISECANCEL1A requires exact DETAIL1H Java parent')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.82-m9autoexposurefinish1i-fastacquire1b-safe075-tg1'" not in gradle or 'versionCode 26702' not in gradle:
        raise SystemExit('NOISECANCEL1A requires exact 1.82 parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'m9detail1h_guard.cpp',root/CPP)
    shutil.copyfile(HERE/'M9Detail1H.java',root/JAVA)
    gradle=one(gradle,'versionCode 26702','versionCode 26703','version code')
    gradle=one(gradle,
        "versionName '1.82-m9autoexposurefinish1i-fastacquire1b-safe075-tg1'",
        "versionName '1.83-m9noisecancel1a-quietchroma-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
