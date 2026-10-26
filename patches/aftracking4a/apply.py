#!/usr/bin/env python3
"""Stage M9Cam 3.08 safe AF-C preview-motion lead and dependent tracking switches.

Parent must be EXACT reconstructed signed 3.07 source. This stage changes
neither the image renderer nor 3.07 detector/matcher algorithms; prediction is
an independently switchable Camera2 AF-region coordinate policy only.
"""
from pathlib import Path
import argparse, hashlib, shutil, json, re
arg=argparse.ArgumentParser()
arg.add_argument('source',type=Path)
arg.add_argument('--report',type=Path)
a=arg.parse_args()
root=a.source.resolve()
here=Path(__file__).resolve().parent
prefix=Path('app/src/main/java/com/particlesdevs/photoncamera')
changes=[]
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def replace_exact(rel, expected):
    dest=root/prefix/rel
    new=here/'src/com/particlesdevs/photoncamera'/rel
    assert dest.is_file() and new.is_file(),rel
    actual=sha(dest)
    assert actual==expected, f'{rel} unexpected inherited 3.07 source: {actual}'
    shutil.copyfile(new,dest)
    changes.append((prefix/rel).as_posix())

def add(rel):
    dest=root/prefix/rel
    src=here/'src/com/particlesdevs/photoncamera'/rel
    assert src.is_file() and not dest.exists(),rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dest)
    changes.append((prefix/rel).as_posix())

def patch(path,old,new):
    f=root/path
    text=f.read_text()
    count=text.count(old)
    assert count==1, f'{path}: expected one {old[:80]!r}, got {count}'
    f.write_text(text.replace(old,new))
    changes.append(path.as_posix())

replace_exact('ui/camera/FocusTrackingController.java',
              '5b761c5cb60af7cb7dffaa15049b6e70e98cfbeb8771957811b6dc486c9619db')
replace_exact('ui/settings/custompreferences/ManagedSwitchPreference.java',
              'c7059656c620b36fca19e01ba94a7e3833ccdaf920b35b83ca239fc416260cab')
add('control/tracking/FocusMotionPredictor.java')
add('control/tracking/TrackingTogglePolicy.java')
for menu in ('preferences_m9.xml','preferences_monochrom.xml'):
    rel=Path('app/src/main/res/xml')/menu
    f=root/rel
    content=f.read_text()
    controls=list(re.finditer(r'<[^>]*android:key="pref_focus_tracking_semantic"[^>]*?/>',
                              content,re.DOTALL))
    assert len(controls)==1, f'{rel}: missing unique 3.07 subject-aware switch'
    assert 'pref_focus_tracking_predictive' not in content
    extra='''
        <com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference
            android:key="pref_focus_tracking_predictive"
            android:title="@string/focus_predictive_title4a"
            android:summary="@string/focus_predictive_summary4a"
            android:defaultValue="false"
            android:layout="@layout/preference_with_margin"
            android:icon="@drawable/ic_focus" />'''
    end=controls[0].end()
    f.write_text(content[:end]+extra+content[end:])
    changes.append(rel.as_posix())
resource=Path('app/src/main/res/values/focuspredict4a.xml')
assert not (root/resource).exists()
(root/resource).write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="focus_predictive_title4a">Predictive AF-C (experimental)</string>
    <string name="focus_predictive_summary4a">Automatically enables Focus tracking. Gently leads the autofocus region using observed screen movement. Does not predict distance or command the lens. Off by default.</string>
</resources>
''')
changes.append(resource.as_posix())

build=Path('app/build.gradle')
patch(build,'versionCode 27307','versionCode 27308')
patch(build,"versionName '3.07-aftracking3b'","versionName '3.08-aftracking4a'")
patch(build,'M9Cam_3.07_AFTRACKING3B','M9Cam_3.08_AFTRACKING4A')

controller=(root/prefix/'ui/camera/FocusTrackingController.java').read_text()
preferences=(root/prefix/'ui/settings/custompreferences/ManagedSwitchPreference.java').read_text()
predictor=(root/prefix/'control/tracking/FocusMotionPredictor.java').read_text()
assert 'focus.enableArbitraryCadence();' in controller
assert 'focusPredictor.observe(' in controller
assert 'focusPredictor.hold(epoch)' in controller
assert 'reconcileTrackingSwitches();' in controller
assert 'TrackingTogglePolicy.onPersist(key,value,settingInitialValue)' in preferences
assert 'refreshDependentSwitch(TrackingTogglePolicy.TRACKING,true)' in preferences
assert 'MAX_LEAD_FRACTION = .045f' in predictor
assert 'MAX_SAMPLE_AGE_MS = 480L' in predictor
assert 'CONTROL_AF_TRIGGER' not in controller
assert 'CONTROL_AE_REGIONS' not in controller and 'CONTROL_AWB_REGIONS' not in controller
assert 'LENS_FOCUS_DISTANCE' not in controller
assert 'recognitionEnabled()' in controller and 'subjectAnchor.observe(' in controller
assert 'patchInitialized' in controller and 'PatchTracker' in controller
for menu in ('preferences_m9.xml','preferences_monochrom.xml'):
    assert 'pref_focus_tracking_predictive' in (root/'app/src/main/res/xml'/menu).read_text()
report=dict(status='STAGED_FOR_ANDROID_BUILD',version='3.08-aftracking4a',
    parent='3.07-aftracking3b',changedFiles=sorted(set(changes)),
    predictiveDefaultOff=True,personPetAndPatchTrackersUnchanged=True,
    oldInertSubjectSwitchAutoHealed=True,dependentSwitchesSynchronized=True,
    cappedNormalizedAfLead=0.045,clampLeadMs=140,lead2DNotOpticalDepth=True,
    holdOcclusionAndSourceChangesResetVelocity=True,
    autofocusRegionOnly=True,aeAwbCaptureAndRenderingUnchanged=True,
    originalModelsNativeAndAssetsUnchanged=True,phoneValidationPending=True)
if a.report:
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
