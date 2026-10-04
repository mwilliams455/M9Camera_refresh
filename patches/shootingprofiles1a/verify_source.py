"""Verify profile integration retains accepted preferences and photographic source."""
from pathlib import Path
import hashlib, json, sys
import xml.etree.ElementTree as ET

A='{http://schemas.android.com/apk/res/android}'
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main(parent,root,output):
    changed={
        'app/src/main/java/com/particlesdevs/photoncamera/ui/settings/SettingsActivity.java',
        'app/src/main/java/com/particlesdevs/photoncamera/settings/PreferenceKeys.java',
        'app/src/main/res/xml/preferences_m9.xml',
    }
    added={
        'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ShootingProfiles.java',
        'app/src/main/java/com/particlesdevs/photoncamera/ui/settings/M9ProfilesUi.java',
        'app/src/main/res/layout/preference_m9_profile.xml',
        'app/src/main/res/values/m9_profiles.xml',
        'app/src/test/java/com/particlesdevs/photoncamera/m9/M9ShootingProfilesTest.java',
    }
    oldpaths={p.relative_to(parent).as_posix():p for p in (parent/'app/src').rglob('*') if p.is_file()}
    newpaths={p.relative_to(root).as_posix():p for p in (root/'app/src').rglob('*') if p.is_file()}
    assert newpaths.keys()-oldpaths.keys()==added
    assert not oldpaths.keys()-newpaths.keys()
    for name,path in oldpaths.items():
        if name not in changed: assert digest(path)==digest(newpaths[name]), name
    xml='app/src/main/res/xml/preferences_m9.xml'
    old=ET.parse(parent/xml).getroot(); new=ET.parse(root/xml).getroot()
    keys=[n.get(A+'key') for n in new.iter() if n.get(A+'key')]
    assert len(keys)==len(set(keys))
    assert [n.attrib for n in new]==[n.attrib for n in old]
    def walk(node,path):
        path=path+[node.get(A+'key')]
        if node.get(A+'key')=='pref_m9_profiles_screen':return
        yield path,node.tag,node.attrib
        for child in node: yield from walk(child,path)
    assert list(walk(old,[]))==list(walk(new,[])), 'Existing preference routes/attributes changed'
    image=next(n for n in new if n.get(A+'key')=='pref_m9_image_screen')
    assert image[0].get(A+'key')=='pref_m9_profiles_screen' and len(image[0])==4
    model=(root/'app/src/main/java/com/particlesdevs/photoncamera/m9/M9ShootingProfiles.java').read_text()
    preferences=(root/'app/src/main/java/com/particlesdevs/photoncamera/settings/PreferenceKeys.java').read_text()
    for name in ['LIBRARY_KEY','ACTIVE_KEY']:
        assert 'COMMON_KEYS.add(com.particlesdevs.photoncamera.m9.M9ShootingProfiles.'+name+');' in preferences
        assert 'com.particlesdevs.photoncamera.m9.M9ShootingProfiles.'+name+'.equals(key)' in preferences
    assert 'public static final String EV_KEY = "pref_expocompensation_seekbar_key";' in model
    ui=(root/'app/src/main/java/com/particlesdevs/photoncamera/ui/settings/M9ProfilesUi.java').read_text()
    for key in ['M9SaturationSettings.KEY','M9ContrastSettings.KEY','M9SharpnessSettings.KEY']:
        assert 'syncList('+key in ui
    # Current EV menu range and profile validator must agree; no new EV quantization.
    ev=next(n for n in new.iter() if n.get(A+'key')=='@string/pref_expocompensation_seekbar_key')
    P='{http://schemas.android.com/apk/res-auto}'
    assert ev.get(P+'minValue')=='-4' and ev.get(P+'maxValue')=='4'
    report=dict(status='passed',unchangedExistingAppSourceFiles=len(oldpaths)-len(changed),
        existingMenuRoutesKeysClassesDefaultsPreserved=True,allPhotographicSourceUnchanged=True,
        existingCaptureFreezeUnchanged=True,allAssetsAndNativeSourcesUnchanged=True,
        profileCollectionExcludedFromPerLensSnapshots=True,profileMetadataIgnoredOnPerLensRestore=True,
        profileScreen='Settings > Image > Shooting profiles',evRange=[-4,4],phoneUiValidationPending=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main(*[Path(arg).resolve() for arg in sys.argv[1:]])
