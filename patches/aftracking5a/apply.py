#!/usr/bin/env python3
"""Apply M9Cam 3.09 tap-pinned appearance / safe identity recovery to exact 3.08 source.

The 3.08 predictive AF-C gate and all imaging routines remain unchanged.
Only opt-in semantic tracking, the shared dependency switches and the menu change.
"""
from pathlib import Path
import argparse,hashlib,shutil,json,re
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--report',type=Path)
a=p.parse_args()
root=a.source.resolve();here=Path(__file__).resolve().parent
prefix=Path('app/src/main/java/com/particlesdevs/photoncamera')
changes=[]
sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()

def replace_exact(rel, expected):
    dest=root/prefix/rel
    src=here/'src/com/particlesdevs/photoncamera'/rel
    assert dest.is_file() and src.is_file(),rel
    actual=sha(dest)
    assert actual==expected, f'3.08 parent mismatch for {rel}: {actual}'
    shutil.copyfile(src,dest);changes.append((prefix/rel).as_posix())
def add(rel):
    dest=root/prefix/rel
    src=here/'src/com/particlesdevs/photoncamera'/rel
    assert src.is_file() and not dest.exists(),rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dest);changes.append((prefix/rel).as_posix())
def patch(rel,old,new):
    f=root/rel
    s=f.read_text();count=s.count(old)
    assert count==1, f'{rel} expected one anchor got {count}: {old[:70]}'
    f.write_text(s.replace(old,new));changes.append(rel.as_posix())

# Frozen exact-source checks: no global rewrite or unreviewed code mutations.
for rel, hash_value in (
    ('control/tracking/SubjectAnchorPolicy.java','95f9c75431dead8a65050d3a0a7b9172196f7db343285be3a265167bf7141ae1'),
    ('ui/camera/TrackingSemanticDetector.java','8709d9dc7b36ba53384c1a4fe2840c9471e9fa32a29aba581415c81d758e145a'),
    ('ui/camera/FocusTrackingController.java','0c05e122d67c49f366221baf62b8b7a404f51f25789e86e8bf99679c3cae860d'),
    ('control/tracking/TrackingTogglePolicy.java','a7d04ebe57f0fe6daccffff08966337bc98ca015b12b45132bf98005ebb2085a'),
    ('ui/settings/custompreferences/ManagedSwitchPreference.java','62a44a2f6feb662d1aec8ff5a7ca335b5b37fabb4dc0dad08b1b2883b2e386a6'),
):
    replace_exact(rel,hash_value)
add('control/tracking/SubjectAppearanceDescriptor.java')

for menu in ('preferences_m9.xml','preferences_monochrom.xml'):
    path=Path('app/src/main/res/xml')/menu
    f=root/path;content=f.read_text()
    controls=list(re.finditer(r'<[^>]*android:key="pref_focus_tracking_predictive"[^>]*?/>',content,re.DOTALL))
    assert len(controls)==1, f'Missing 3.08 predictive control in {menu}: {len(controls)}'
    assert 'pref_focus_tracking_identity' not in content
    insert='''
        <com.particlesdevs.photoncamera.ui.settings.custompreferences.ManagedSwitchPreference
            android:key="pref_focus_tracking_identity"
            android:title="@string/focus_tracking_identity_title5a"
            android:summary="@string/focus_tracking_identity_summary5a"
            android:defaultValue="false"
            android:layout="@layout/preference_with_margin"
            android:icon="@drawable/ic_focus" />'''
    i=controls[0].end()
    f.write_text(content[:i]+insert+content[i:]);changes.append(path.as_posix())
res=Path('app/src/main/res/values/focusidentity5a.xml')
assert not (root/res).exists()
(root/res).write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="focus_tracking_identity_title5a">Persistent subject identity (experimental)</string>
    <string name="focus_tracking_identity_summary5a">Enable Subject-aware tracking and Focus tracking automatically. Use on-device appearance clues to reject another person/pet during crossings. Holds AF if uncertain; retap after a long obstruction. Off by default.</string>
</resources>
''')
changes.append(res.as_posix())

build=Path('app/build.gradle')
patch(build,'versionCode 27308','versionCode 27309')
patch(build,"versionName '3.08-aftracking4a'","versionName '3.09-aftracking5a'")
patch(build,'M9Cam_3.08_AFTRACKING4A','M9Cam_3.09_AFTRACKING5A')

controller=(root/prefix/'ui/camera/FocusTrackingController.java').read_text()
policy=(root/prefix/'control/tracking/SubjectAnchorPolicy.java').read_text()
detector=(root/prefix/'ui/camera/TrackingSemanticDetector.java').read_text()
preferences=(root/prefix/'ui/settings/custompreferences/ManagedSwitchPreference.java').read_text()
assert 'focusPredictor.observe(' in controller and 'focusPredictor.hold(epoch)' in controller
assert 'focus.enableArbitraryCadence();' in controller
assert 'subjectAnchor.useAppearance(identityForTap);' in controller
assert 'semanticDetector.detect(bitmap, framePixels,dw,dh,identity)' in controller
assert 'identityForTap != persistentIdentityEnabled()' in controller
assert 'appearanceEnabled && recoveryNeeded' in policy
assert 'pinnedAppearance.similarity(candidate.appearance)' in policy
assert 'SubjectAppearanceDescriptor.sample(pixels,width,height,l,t,r,bt)' in detector
assert 'Bitmap modelBitmap=frame.copy(Bitmap.Config.ARGB_8888,false);' in detector
assert 'TrackingTogglePolicy.IDENTITY' in preferences
assert 'CONTROL_AF_TRIGGER' not in controller
assert 'CONTROL_AE_REGIONS' not in controller and 'CONTROL_AWB_REGIONS' not in controller
assert 'LENS_FOCUS_DISTANCE' not in controller
assert 'CONTROL_AE_REGIONS' not in detector
assert 'CONTROL_AF_TRIGGER' not in policy
for menu in ('preferences_m9.xml','preferences_monochrom.xml'):
    assert (root/'app/src/main/res/xml'/menu).read_text().count('android:key="pref_focus_tracking_identity"')==1
report=dict(status='STAGED_FOR_ANDROID_BUILD',version='3.09-aftracking5a',parent='3.08-aftracking4a',
    changedFiles=sorted(set(changes)),persistentIdentityOptInDefaultOff=True,
    phonePositive308LegacyModeWhenOff=True,appearancePixelsSaved=False,
    semanticPersonCatDogOnly=True,arbitraryPatchFallbackRetained=True,
    twoFreshObservationsAfterHold=True,ambiguousCandidatesNeverMoveAf=True,
    predictorAndAfCadenceUnchanged=True,
    camera2AfRegionOnly=True,aeAwbShutterExposureRawJpegRenderingUnchanged=True,
    originalModelsNativeAndAssetsUnchanged=True,phoneValidationPending=True)
if a.report:
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
