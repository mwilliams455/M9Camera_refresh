#!/usr/bin/env python3
"""M9Cam 3.10 AUTOEYE1A: default-on verified eye AF (full+profile).

Apply ONLY to exact reconstructed 3.09 source. Do not modify Camera2
capture, AE/AWB, DNG/JPEG, image processing or native libraries.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,re
p=argparse.ArgumentParser()
p.add_argument('source',type=Path)
p.add_argument('--report',type=Path)
a=p.parse_args()
root=a.source.resolve()
here=Path(__file__).resolve().parent
prefix=Path('app/src/main/java/com/particlesdevs/photoncamera')
changes=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parent_hashes={
  'ui/camera/HumanSubjectFocusController.java':'78f6610499b1b02cbb4bfd906ffe35c9a572e7232074583d505aa8ee5e46b0b8',
  'ui/camera/FocusTrackingController.java':'99c040220e38929424ee381ea95c6ebb507afcb8ed31f053a1db854dc6eb6a24',
}
for rel,expected in parent_hashes.items():
    file=root/prefix/rel
    assert file.is_file() and sha(file)==expected,(rel,sha(file))
    new=here/'src/com/particlesdevs/photoncamera'/rel
    assert new.is_file(),new
    shutil.copy2(new,file)
    changes.append(file.relative_to(root).as_posix())
# Fragment is over 120 KB; use two narrow, hash-pinned substitutions
# rather than copying it. This makes a focus-selection-only change.
fragment=root/prefix/'ui/camera/CameraFragment.java'
assert sha(fragment)=='f584f9ae784f31bd1bdda0e9fcd35f6e684082ac738465be79162f5b78d6c15c'
fragment_text=fragment.read_text()
face_tap='        if (focusSubject != null && focusSubject.tap(x, y, auto)) return true;'
assert fragment_text.count(face_tap)==1
fragment_text=fragment_text.replace(face_tap,'''        if (focusSubject != null && focusSubject.tap(x, y, auto)) {
            // An explicitly chosen eye supersedes a previous arbitrary object.
            if (focusTracking != null) focusTracking.clear();
            return true;
        }''')
clear_marker='    public void clearFocusTracking() {'
assert fragment_text.count(clear_marker)==1
fragment_text=fragment_text.replace(clear_marker,'''    /** Explicit tap-selected objects outrank unrequested automatic eye AF. */
    boolean hasExplicitArbitraryTrackingSelection() {
        return focusTracking != null && focusTracking.hasExplicitTrackingTarget();
    }
    public void clearFocusTracking() {''')
fragment.write_text(fragment_text)
changes.append(fragment.relative_to(root).as_posix())

for rel in ('control/subject/AutoEyeFocusPolicy.java','control/subject/ProfileEyeAdmissionGate.java'):
    file=root/prefix/rel
    assert not file.exists(),file
    new=here/'src/com/particlesdevs/photoncamera'/rel
    file.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(new,file)
    changes.append(file.relative_to(root).as_posix())

def patch(path,before,after):
    file=root/path
    contents=file.read_text()
    count=contents.count(before)
    assert count==1,(str(path),count,before[:120])
    file.write_text(contents.replace(before,after))
    changes.append(path.as_posix())

# Legacy mode-specific Eye AF preference is superseded by one opt-out switch,
# default ON even for upgrades with a stored 3.09 opt-in value of false.
for profile,expected_sha in (
    ('m9','4770f57a6ebe70ab1c88c2130290a28d232a86b7df211847dbc89bcc5f3d7152'),
    ('monochrom','f4af05312dec0d17e08947dfcdb16d151de9eca7ecc2286b455d0cd20ac6a5f2')):
    path=Path('app/src/main/res/xml')/('preferences_'+profile+'.xml')
    f=root/path
    assert sha(f)==expected_sha,(profile,sha(f))
    text=f.read_text()
    pattern=r'<com\.particlesdevs\.photoncamera\.ui\.settings\.custompreferences\.ManagedSwitchPreference\s+android:key="pref_focus_subject_eye"[^>]*?\s*/>'
    matches=list(re.finditer(pattern,text,re.DOTALL))
    assert len(matches)==1,(profile,len(matches))
    old=matches[0].group(0)
    new='''<com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference
            android:key="pref_focus_auto_eye_enabled"
            android:title="@string/auto_eye_title1a"
            android:summary="@string/auto_eye_summary1a"
            android:defaultValue="true"
            android:layout="@layout/preference_with_margin"
            android:icon="@drawable/ic_focus" />'''
    patch(path,old,new)

# An old hidden Eye-AF preference must not continue disabling Spot/Custom or
# voluntary arbitrary tracking. Auto Eye is only allowed under Wide+AF-C.
focus_area=prefix/'ui/camera/FocusAreaTouchController.java'
patch(focus_area,
'''                ||PhotonCamera.getSettingsManagerStatic().getBoolean(
                    SettingsManager.SCOPE_GLOBAL,HumanSubjectFocusController.KEY,false)
''','')

resource=Path('app/src/main/res/values/autoeye1a.xml')
assert not (root/resource).exists()
(root/resource).write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="auto_eye_title1a">Automatic human Eye AF</string>
    <string name="auto_eye_summary1a">On by default. In Wide AF-C, finds a visible human eye automatically, including a verified side profile. Tap a different object to override. Turn off to use ordinary AF-C only.</string>
</resources>
''')
changes.append(resource.as_posix())

build=Path('app/build.gradle')
assert sha(root/build)=='bb44d792cdda970cc3ea0f4e35cc7ee1cd4f62f15b0d1054d3b1c203be0ed527'
patch(build,'versionCode 27309','versionCode 27310')
patch(build,"versionName '3.09-aftracking5a'","versionName '3.10-autoeye1a'")
patch(build,'M9Cam_3.09_AFTRACKING5A','M9Cam_3.10_AUTOEYE1A')

human=(root/prefix/'ui/camera/HumanSubjectFocusController.java').read_text()
tracking=(root/prefix/'ui/camera/FocusTrackingController.java').read_text()
fragment=(root/prefix/'ui/camera/CameraFragment.java').read_text()
assert 'manager.getBoolean(SettingsManager.SCOPE_GLOBAL,AUTO_EYE_KEY,true)' in human
assert 'ProfileEyeAdmissionGate' in human
assert 'profileEyeGate.admit(epoch,startedNs,nowNs,faces)' in human
assert 'fragment.hasExplicitArbitraryTrackingSelection()' in human
assert 'hasExplicitTrackingTarget()' in tracking
assert 'hasExplicitArbitraryTrackingSelection()' in fragment
assert 'HumanSubjectFocusController.KEY' not in tracking
assert 'CONTROL_AF_TRIGGER' not in human and 'CONTROL_AE_REGIONS' not in human and 'CONTROL_AWB_REGIONS' not in human
for name in ('m9','monochrom'):
    contents=(root/'app/src/main/res/xml'/('preferences_'+name+'.xml')).read_text()
    assert 'android:key="pref_focus_auto_eye_enabled"' in contents
    assert 'android:key="pref_focus_subject_eye"' not in contents
assert (root/'app/src/main/res/values/autoeye1a.xml').is_file()

report=dict(status='STAGED_FOR_ANDROID_BUILD',version='3.10-autoeye1a',parent='3.09-aftracking5a',
    changedFiles=sorted(set(changes)),autoHumanEyeDefaultOn=True,
    oldManualEyeKeyIgnoredByNewAutoMode=True,automaticHumanEyeNoTapRequired=True,
    continuousPictureAfRequired=True,wideAreaRequired=True,
    manualObjectTapHasPriority=True,petAfHasPriorityWhenEnabled=True,
    strictFrontalGateUntouched=True,profileEyeFourFreshObservations=True,
    camera2AfRegionOnly=True,afCShutterPathUnchanged=True,
    aeAwbExposureRawJpegDngRenderingUnchanged=True,
    originalModelsNativeAndAssetsUnchanged=True,phoneEyeFocusValidationPending=True)
if a.report:
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
