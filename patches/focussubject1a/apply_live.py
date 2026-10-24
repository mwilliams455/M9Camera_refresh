#!/usr/bin/env python3
"""Apply the opt-in live Face/Eye focus adapter to exact reconstructed 2.95.
No camera colour, exposure, RAW processing or native code is modified.
A failed/missing/ambiguous anchor rejects the build instead of guessing.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

p=argparse.ArgumentParser()
p.add_argument("source", type=Path)
p.add_argument("--report", type=Path)
args=p.parse_args()
root=args.source.resolve()
base=root/"app/src/main"
patch_root=Path(__file__).resolve().parent
assert (root/"app/build.gradle").exists(),"Source not assembled"

changed=[]
def replace(path,old,new):
    file=root/path
    content=file.read_text()
    count=content.count(old)
    if count!=1:
        raise ValueError(f"Expected exactly one anchor in {path}: {old!r}, found {count}")
    file.write_text(content.replace(old,new))
    changed.append(str(path))

pkg=Path("app/src/main/java/com/particlesdevs/photoncamera")
for sub in ("control/subject/SubjectFocusPolicy.java",
            "control/subject/FocusAreaPolicy.java",
            "ui/camera/HumanFaceLandmarkDetector.java",
            "ui/camera/HumanSubjectFocusController.java"):
    rel=pkg/sub
    dst=root/rel
    assert not dst.exists(),f"Unexpected existing file: {rel}"
    src=patch_root/"src"/("com/particlesdevs/photoncamera")/sub
    assert src.is_file(),src
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst)
    changed.append(rel.as_posix())

frag=pkg/"ui/camera/CameraFragment.java"
replace(frag,
    "    private FocusTrackingController focusTracking;",
    "    private FocusTrackingController focusTracking;\n    private HumanSubjectFocusController focusSubject;")
replace(frag,
    "        return focusTracking != null && focusTracking.tap(x, y, auto);",
    "        if (focusSubject != null && focusSubject.tap(x, y, auto)) return true;\n"
    "        return focusTracking != null && focusTracking.tap(x, y, auto);")
replace(frag,
    "    public void clearFocusTracking() { if (focusTracking != null) focusTracking.clear(); }",
    "    public void clearFocusTracking() {\n"
    "        if (focusTracking != null) focusTracking.clear();\n"
    "        if (focusSubject != null) focusSubject.clear();\n"
    "    }")
replace(frag,
    "        focusTracking = new FocusTrackingController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);",
    "        focusTracking = new FocusTrackingController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);\n"
    "        focusSubject = new HumanSubjectFocusController(this, textureView, cameraFragmentBinding.layoutViewfinder.trackingFocus);")
replace(frag,
    "        if (focusTracking != null) focusTracking.start();",
    "        if (focusTracking != null) focusTracking.start();\n"
    "        if (focusSubject != null) focusSubject.start();")
replace(frag,
    "        if (focusTracking != null) focusTracking.stop();",
    "        if (focusSubject != null) focusSubject.stop();\n"
    "        if (focusTracking != null) focusTracking.stop();")
replace(frag,
    "        if (focusTracking != null) focusTracking.close();\n        focusTracking = null;",
    "        if (focusSubject != null) focusSubject.close();\n        focusSubject = null;\n"
    "        if (focusTracking != null) focusTracking.close();\n        focusTracking = null;")

track=pkg/"ui/camera/FocusTrackingController.java"
replace(track,
    "&& PhotonCamera.getSettingsManagerStatic().getBoolean(com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, KEY, false);",
    "&& PhotonCamera.getSettingsManagerStatic().getBoolean(com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, KEY, false)\n"
    "                && !PhotonCamera.getSettingsManagerStatic().getBoolean(com.particlesdevs.photoncamera.settings.SettingsManager.SCOPE_GLOBAL, HumanSubjectFocusController.KEY, false);")

prefs=pkg/"settings/PreferenceKeys.java"
replace(prefs,
    'COMMON_KEYS.add("pref_focus_tracking");',
    'COMMON_KEYS.add("pref_focus_tracking");\n'
    '        COMMON_KEYS.add("pref_focus_subject_eye");')

gradle=Path("app/build.gradle")
replace(gradle,
    "    implementation 'org.opencv:opencv:4.13.0'",
    "    implementation 'org.opencv:opencv:4.13.0'\n"
    "    // Bundled on-device ML Kit face model: no Play Services model download.\n"
    "    implementation 'com.google.mlkit:face-detection:16.1.7'")

existing_switch='<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference android:key="pref_focus_tracking"'
addition=(
    '<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference '
    'android:key="pref_focus_subject_eye" android:title="@string/focus_subject_eye_title" '
    'android:summary="@string/focus_subject_eye_summary" android:defaultValue="false" '
    'android:layout="@layout/preference_with_margin" android:icon="@drawable/ic_focus" />\n        '
)
for name in ("preferences_m9.xml","preferences_monochrom.xml"):
    replace(Path("app/src/main/res/xml")/name,existing_switch,addition+existing_switch)

strings=Path("app/src/main/res/values/strings.xml")
replace(strings,"</resources>",
    '    <string name="focus_subject_eye_title">Human Face/Eye AF (experimental)</string>\n'
    '    <string name="focus_subject_eye_summary">Opt-in AF-C eye priority with face fallback. '
    'Overrides patch tracking when enabled. Bundled offline model; for PHOTO, NIGHT and MOTION.</string>\n'
    '</resources>')

# Code-level non-interference invariants; builds independently verify real AF
# ownership through CaptureController.TrackingFocus and inherited regressions.
controller=(root/(pkg/"ui/camera/HumanSubjectFocusController.java")).read_text()
assert "focus.update(g,target.x,target.y" in controller
assert "getBoolean(" in controller and 'KEY = "pref_focus_subject_eye"' in controller
assert "CaptureRequest.CONTROL_AE_REGIONS" not in controller
assert "CaptureRequest.CONTROL_AWB_REGIONS" not in controller
assert "CONTROL_AF_TRIGGER_START" not in controller

unique=sorted(set(changed))
report={
  "status":"STAGED_FOR_ANDROID_BUILD",
  "parent":"2.95-diagindex1a",
  "scope":"opt-in human face-eye AF",
  "changedFiles":unique,
  "modelDependency":"com.google.mlkit:face-detection:16.1.7 (bundled)",
  "default":"off",
  "renderExposureRawNativeModified":False,
  "phoneFocusAccuracyEstablished":False,
}
if args.report:
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
