#!/usr/bin/env python3
"""Stage opt-in 3.02 AP10K Animal Eye AF on EXACT 3.01 pet AF source.

Changes only PetFocusController, one shared preference, two profile menus,
human-readable strings, a model asset and LiteRT dependency/toolchain.
Never changes Camera2 AF engine, AE/AWB, RAW, colour or native renderer sources.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil

args=argparse.ArgumentParser()
args.add_argument('source',type=Path)
args.add_argument('--report',type=Path)
ns=args.parse_args()
root=ns.source.resolve()
here=Path(__file__).resolve().parent
prefix=Path('app/src/main/java/com/particlesdevs/photoncamera')
sha=lambda b:hashlib.sha256(b).hexdigest()
changed=[]
def patch(path,old,new):
    f=root/path
    data=f.read_text()
    count=data.count(old)
    if count!=1:raise ValueError(f'Expected exactly one anchor {path}: {old!r}, got {count}')
    f.write_text(data.replace(old,new))
    changed.append(path.as_posix())

relative='ui/camera/PetFocusController.java'
prior=here.parent/'focusanimal1c/src/com/particlesdevs/photoncamera'/relative
current=root/prefix/relative
assert sha(prior.read_bytes())==sha(current.read_bytes()),'Not exact 3.01 pet-focus controller'
current.write_bytes((here/'src/com/particlesdevs/photoncamera'/relative).read_bytes())
changed.append((prefix/relative).as_posix())

for rel in ('control/subject/AnimalEyeTargetPolicy.java',
            'ui/camera/AnimalEyePoseEstimator.java'):
    output=root/prefix/rel
    src=here/'src/com/particlesdevs/photoncamera'/rel
    assert src.exists() and not output.exists(),(src,output)
    output.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,output)
    changed.append((prefix/rel).as_posix())

prefs=prefix/'settings/PreferenceKeys.java'
patch(prefs,'COMMON_KEYS.add("pref_focus_subject_pet");',
    'COMMON_KEYS.add("pref_focus_subject_pet");\n'
    '        COMMON_KEYS.add("pref_focus_subject_pet_eye");')

for profile in ('m9','monochrom'):
    xml=Path('app/src/main/res/xml')/('preferences_'+profile+'.xml')
    # Place the secondary opt-in switch immediately next to Pet AF; it has no
    # effect when the parent Pet AF switch is disabled.
    pet='<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference android:key="pref_focus_subject_pet"'
    eye=('<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference '
         'android:key="pref_focus_subject_pet_eye" '
         'android:title="@string/focus_subject_pet_eye_title" '
         'android:summary="@string/focus_subject_pet_eye_summary" '
         'android:defaultValue="false" android:layout="@layout/preference_with_margin" '
         'android:icon="@drawable/ic_focus" />\n        ')
    patch(xml,pet,eye+pet)

strings=Path('app/src/main/res/values/strings.xml')
patch(strings,'</resources>',
    '    <string name="focus_subject_pet_eye_title">Animal Eye AF (experimental)</string>\n'
    '    <string name="focus_subject_pet_eye_summary">Requires Cat/Dog AF. '
    'Uses offline AP-10K eye and nose localisation; falls back to body AF '
    'if unverified. Default off.</string>\n'
    '</resources>')

gradle=Path('app/build.gradle')
patch(gradle,'versionCode 27301','versionCode 27302')
patch(gradle,"versionName '3.01-focusanimal1c'",
             "versionName '3.02-animaleye1a'")
patch(gradle,'M9Cam_3.01_FOCUSANIMAL1C','M9Cam_3.02_ANIMALEYE1A')
patch(gradle,
    "    implementation 'com.google.mediapipe:tasks-vision:0.10.35'",
    "    implementation 'com.google.mediapipe:tasks-vision:0.10.35'\n"
    "    // Bundled 16-KiB-compatible LiteRT CompiledModel for offline AP-10K pose.\n"
    "    implementation 'com.google.ai.edge.litert:litert:2.3.0'\n"
    "    implementation 'com.google.ai.edge.litert:litert-gpu:2.3.0'")

# LiteRT 2.3.0's Kotlin metadata is newer than the Photon 2.2.0 KGP.
# A toolchain update is isolated to the root build script, not camera sources.
build=Path('build.gradle')
buildSrc=(root/build).read_text()
m=re.search(r"ext\.kotlin_version\s*=\s*['\"]([^'\"]+)['\"]",buildSrc)
if m is None:raise ValueError('Cannot verify Photon Kotlin plugin version')
if m.group(1)!='2.3.21':
    if m.group(1) not in ('2.2.0','2.2.10','2.2.20','2.2.21','2.3.0','2.3.10'):
        raise ValueError('Unexpected Kotlin plugin version: '+m.group(1))
    patch(build,m.group(0),"ext.kotlin_version = '2.3.21'")

# The separate verified model download step stages the byte-pinned TFLite file.
model=root/'app/src/main/assets/rtm_animal_fp16.tflite'
assert model.is_file(),'Missing AP-10K model; run SHA-256-verified download stage first'
expected=Path(here/'MODEL_SHA256.txt').read_text().split()[0]
assert sha(model.read_bytes())==expected,'AP-10K model hash differs from published SHA-256'

controller=current.read_text()
assert 'eyePolicy.update(token,nowNs,pose,target)' in controller
assert 'AnimalEyePoseEstimator' in controller and 'EYE_KEY="pref_focus_subject_pet_eye"' in controller
assert 'selectedEye==null?target.x:selectedEye.x' in controller
assert 'Dog Eye AF' in controller and 'Cat Eye AF' in controller
assert 'if(!received(' in controller
assert 'CaptureRequest.CONTROL_AE_REGIONS' not in controller
assert 'CaptureRequest.CONTROL_AWB_REGIONS' not in controller
assert 'CONTROL_AF_TRIGGER_START' not in controller

report=dict(status='STAGED_FOR_BUILD',parent='3.01-focusanimal1c',
    version='3.02-animaleye1a',changedFiles=sorted(set(changed)),
    newModel='rtm_animal_fp16.tflite',newModelSha256=expected,
    newRuntime='com.google.ai.edge.litert:litert:2.3.0 + litert-gpu',
    animalEyeSwitchDefaultOff=True,bodyFocusFallbackRetained=True,
    m9MonochromRendererUnchanged=True,humanEyeAfUnchanged=True,
    noNetworkRuntimeInference=True,phoneCalibrationPending=True)
if ns.report:
    ns.report.parent.mkdir(parents=True,exist_ok=True)
    ns.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
