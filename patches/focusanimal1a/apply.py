#!/usr/bin/env python3
"""FOCUSANIMAL1A: cat/dog AF on verified 2.98 Eye AF source; no RAW, AE or renderer changes."""
from pathlib import Path
import argparse,json,shutil

p=argparse.ArgumentParser()
p.add_argument("root",type=Path)
p.add_argument("--report",type=Path)
args=p.parse_args()
root=args.root.resolve()
here=Path(__file__).resolve().parent
prefix=Path("app/src/main/java/com/particlesdevs/photoncamera")
changed=[]
def replace(name,old,new):
    target=root/name
    data=target.read_text()
    count=data.count(old)
    if count!=1:raise ValueError(f"Expected one exact anchor in {name}: {old!r}, got {count}")
    target.write_text(data.replace(old,new))
    changed.append(name.as_posix())

for rel in ("control/subject/PetTargetPolicy.java",
            "ui/camera/PetObjectDetector.java",
            "ui/camera/PetFocusController.java"):
    target=root/prefix/rel
    source=here/"src"/"com/particlesdevs/photoncamera"/rel
    assert source.exists() and not target.exists(),(source,target)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target)
    changed.append((prefix/rel).as_posix())

frag=prefix/"ui/camera/CameraFragment.java"
replace(frag,
    "    private HumanSubjectFocusController focusSubject;",
    "    private HumanSubjectFocusController focusSubject;\n    private PetFocusController focusAnimal;")
replace(frag,
    "        if (focusSubject != null && focusSubject.tap(x, y, auto)) return true;",
    "        if (focusAnimal != null && focusAnimal.tap(x, y, auto)) return true;\n"
    "        if (focusSubject != null && focusSubject.tap(x, y, auto)) return true;")
replace(frag,
    "        if (focusSubject != null) focusSubject.clear();",
    "        if (focusSubject != null) focusSubject.clear();\n"
    "        if (focusAnimal != null) focusAnimal.clear();")
replace(frag,
    "        focusSubject = new HumanSubjectFocusController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);",
    "        focusSubject = new HumanSubjectFocusController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);\n"
    "        focusAnimal = new PetFocusController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);")
replace(frag,
    "        if (focusSubject != null) focusSubject.start();",
    "        if (focusSubject != null) focusSubject.start();\n"
    "        if (focusAnimal != null) focusAnimal.start();")
replace(frag,
    "        if (focusSubject != null) focusSubject.stop();",
    "        if (focusAnimal != null) focusAnimal.stop();\n"
    "        if (focusSubject != null) focusSubject.stop();")
replace(frag,
    "        if (focusSubject != null) focusSubject.close();\n        focusSubject = null;",
    "        if (focusAnimal != null) focusAnimal.close();\n        focusAnimal = null;\n"
    "        if (focusSubject != null) focusSubject.close();\n        focusSubject = null;")

human=prefix/"ui/camera/HumanSubjectFocusController.java"
replace(human,
    "                        SettingsManager.SCOPE_GLOBAL, KEY, false);",
    "                        SettingsManager.SCOPE_GLOBAL, KEY, false)\n"
    "                && !PhotonCamera.getSettingsManagerStatic().getBoolean(\n"
    "                        SettingsManager.SCOPE_GLOBAL, PetFocusController.KEY, false);")
patch=prefix/"ui/camera/FocusTrackingController.java"
replace(patch,
    "HumanSubjectFocusController.KEY, false);",
    "HumanSubjectFocusController.KEY, false)\n"
    "                && !PhotonCamera.getSettingsManagerStatic().getBoolean(\n"
    "                        com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, PetFocusController.KEY, false);")
prefs=prefix/"settings/PreferenceKeys.java"
replace(prefs,'COMMON_KEYS.add("pref_focus_subject_eye");',
              'COMMON_KEYS.add("pref_focus_subject_eye");\n'
              '        COMMON_KEYS.add("pref_focus_subject_pet");')

gradle=Path("app/build.gradle")
replace(gradle,"versionCode 27298","versionCode 27299")
replace(gradle,"versionName '2.98-focussubject1b'","versionName '2.99-focusanimal1a'")
replace(gradle,"M9Cam_2.98_FOCUSSUBJECT1B","M9Cam_2.99_FOCUSANIMAL1A")
replace(gradle,
    "    implementation 'com.google.mlkit:face-detection:16.1.7'",
    "    implementation 'com.google.mlkit:face-detection:16.1.7'\n"
    "    // Offline COCO animal detector, 16 KiB-capable MediaPipe runtime.\n"
    "    implementation 'com.google.mediapipe:tasks-vision:0.10.35'")

for name in ("preferences_m9.xml","preferences_monochrom.xml"):
    xml=Path("app/src/main/res/xml")/name
    marker='<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference android:key="pref_focus_subject_eye"'
    pet=('<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference '
         'android:key="pref_focus_subject_pet" android:title="@string/focus_subject_pet_title" '
         'android:summary="@string/focus_subject_pet_summary" android:defaultValue="false" '
         'android:layout="@layout/preference_with_margin" android:icon="@drawable/ic_focus" />\n        ')
    replace(xml,marker,pet+marker)

strings=Path("app/src/main/res/values/strings.xml")
replace(strings,"</resources>",
    '    <string name="focus_subject_pet_title">Cat / Dog AF (experimental)</string>\n'
    '    <string name="focus_subject_pet_summary">Offline pet detection with continuous AF. '
    'Focuses on the pet body, not animal eyes. Overrides Eye AF when enabled.</string>\n'
    '</resources>')

controller=(root/prefix/"ui/camera/PetFocusController.java").read_text()
human_source=(root/human).read_text()
assert "PetObjectDetector" in controller and "af.update(g,target.x,target.y" in controller
assert "PetFocusController.KEY, false" in human_source
assert "CaptureRequest.CONTROL_AE_REGIONS" not in controller
assert "CaptureRequest.CONTROL_AWB_REGIONS" not in controller
assert "CONTROL_AF_TRIGGER_START" not in controller
report=dict(status="SOURCE_STAGED",version="2.99-focusanimal1a",
            parent="2.98-focussubject1b",addedAndModifiedFiles=sorted(set(changed)),
            model="efficientdet-lite0.tflite",
            modelRuntime="com.google.mediapipe:tasks-vision:0.10.35",
            catDogAFEnabledByDefault=False,faceEyeFunctionRetained=True,
            photoRenderExposureWbRawNativeChanges=False,phoneValidationPending=True)
if args.report:
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
