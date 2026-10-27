#!/usr/bin/env python3
"""Stage M9Cam 3.07 opt-in subject-aware arbitrary tracking on exact 3.06.

3.06 patch tracker remains frozen: only its existing Camera2 AF owner is used.
Changes are limited to the tracking controller, passive amber overlay,
subject-anchor policy, optional offline detector and a disabled-by-default
Capture setting. Never changes AE/AWB, shutter, image rendering or native code.
"""
from pathlib import Path
import argparse,hashlib,shutil,json,re
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--report',type=Path)
a=p.parse_args();root=a.source.resolve();here=Path(__file__).resolve().parent
prefix=Path('app/src/main/java/com/particlesdevs/photoncamera')
changed=[]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def copy_with_parent(rel,expected_sha):
    target=root/prefix/rel
    assert target.is_file(),target
    assert sha(target)==expected_sha,(rel,sha(target))
    source=here/'src/com/particlesdevs/photoncamera'/rel
    assert source.is_file(),source
    shutil.copyfile(source,target);changed.append((prefix/rel).as_posix())
def add(rel):
    target=root/prefix/rel;source=here/'src/com/particlesdevs/photoncamera'/rel
    assert source.is_file(),source
    assert not target.exists(),target
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,target);changed.append((prefix/rel).as_posix())
def patch(rel,before,after):
    target=root/rel;s=target.read_text()
    count=s.count(before)
    if count!=1:raise ValueError(f'{rel}: expected one anchor {before[:85]!r}, got {count}')
    target.write_text(s.replace(before,after));changed.append(rel.as_posix())
copy_with_parent('ui/camera/FocusTrackingController.java','7b2054ce04b0d5712e3fd200ebfab84cf22cc79380cb77d32859175ee4394d29')
copy_with_parent('ui/camera/views/TrackingFocusView.java','6ff978ce6a1001f1c2eb806dd1a7f7f6a3c67765974812314cd6a34c2173c9ac')
add('control/tracking/SubjectAnchorPolicy.java')
add('ui/camera/TrackingSemanticDetector.java')
# The checked-in 3.06 detector model and MediaPipe runtime are byte-identical.
model=root/'app/src/main/assets/efficientdet-lite0.tflite'
assert model.is_file(),model
assert sha(model)==Path('patches/focusanimal1a/MODEL_SHA256.txt').read_text().split()[0]
# Insert the new switch immediately after the existing Focus tracking entry
# in both M9 and Monochrome menus without changing the original controls.
for menu in ('preferences_m9.xml','preferences_monochrom.xml'):
    path=Path('app/src/main/res/xml')/menu
    file=root/path
    source=file.read_text()
    matches=list(re.finditer(r'<[^>]*android:key="pref_focus_tracking"[^>]*?/>',source,re.DOTALL))
    if len(matches)!=1:raise ValueError(f'{menu}: expected one Focus tracking entry, saw {len(matches)}')
    control='''\n        <com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference
            android:key="pref_focus_tracking_semantic"
            android:title="@string/focus_tracking_semantic_title3b"
            android:summary="@string/focus_tracking_semantic_summary3b"
            android:defaultValue="false"
            android:layout="@layout/preference_with_margin"
            android:icon="@drawable/ic_focus" />'''
    point=matches[0].end()
    file.write_text(source[:point]+control+source[point:]);changed.append(path.as_posix())
resource=Path('app/src/main/res/values/focustrack3b.xml')
assert not (root/resource).exists()
(root/resource).write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="focus_tracking_semantic_title3b">Subject-aware tracking (experimental)</string>
    <string name="focus_tracking_semantic_summary3b">With Focus tracking on, recognise a tapped person, cat or dog locally; other objects keep patch tracking. Off by default.</string>
    <string name="focus_tracking_pending3b">Identifying subject - AF area held</string>
</resources>
''');changed.append(resource.as_posix())
patch(Path('app/build.gradle'),'versionCode 27306','versionCode 27307')
patch(Path('app/build.gradle'),"versionName '3.06-aftracking3a'","versionName '3.07-aftracking3b'")
patch(Path('app/build.gradle'),'M9Cam_3.06_AFTRACKING3A','M9Cam_3.07_AFTRACKING3B')
controller=(root/prefix/'ui/camera/FocusTrackingController.java').read_text()
policy=(root/prefix/'control/tracking/SubjectAnchorPolicy.java').read_text()
detector=(root/prefix/'ui/camera/TrackingSemanticDetector.java').read_text()
assert 'HYBRID_KEY = "pref_focus_tracking_semantic"' in controller
assert 'recognitionEnabled()' in controller
assert 'subjectAnchor.observe(' in controller
assert 'focus.enableArbitraryCadence();' in controller
assert 'Camera2' in controller
assert 'PatchTracker' in controller
assert 'SubjectAnchorPolicy.MAX_HOLD_MS' in controller
assert 'frame.copy(Bitmap.Config.ARGB_8888,false)' in detector
assert 'new BitmapImageBuilder(modelBitmap)' in detector
assert 'MAX_ACTION_AGE_MS = 500L' in policy
assert 'CONTROL_AF_TRIGGER' not in controller
assert 'CONTROL_AE_REGIONS' not in controller and 'CONTROL_AWB_REGIONS' not in controller
assert 'Bitmap.recycle()' not in controller
assert 'CONTROL_AE_REGIONS' not in detector
report=dict(status='STAGED_FOR_ANDROID_BUILD',version='3.07-aftracking3b',parent='3.06-aftracking3a',
    changedFiles=sorted(set(changed)),subjectAwareDefaultOff=True,
    classes=['person','cat','dog'],modelAlreadyBundledAndShaVerified=True,
    legacy256PatchRetainedWhenAssistOff=True,existingPhoneTested305Untouched=True,
    existingCamera2AfOnlyUpdates=True,AEAWBExposureAndRawJpegUnchanged=True,
    humanEyeAndPetAFControllersUntouched=True,faceAndPetExistingPrefsUnchanged=True,
    physicalDeviceValidationPending=True)
if a.report:
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

