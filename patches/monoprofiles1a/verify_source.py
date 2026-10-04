"""Verify the complete 2.47 -> 2.48 source delta; all renderer/capture code stays identical."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
parent,root=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(root):
 return {p.relative_to(root).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (root/d).rglob('*') if p.is_file()}|{'app/build.gradle':sha(root/'app/build.gradle')}
a,b=files(parent),files(root)
changed=sorted(p for p in a.keys()|b.keys() if a.get(p)!=b.get(p))
expected=['app/build.gradle','app/src/main/java/com/particlesdevs/photoncamera/monochrom/MonoImageProfiles.java','app/src/main/java/com/particlesdevs/photoncamera/ui/settings/MonoProfilesUi.java','app/src/main/java/com/particlesdevs/photoncamera/ui/settings/SettingsActivity.java','app/src/main/java/com/particlesdevs/photoncamera/settings/PreferenceKeys.java','app/src/main/res/xml/preferences_monochrom.xml','app/src/main/res/values/mono_profiles.xml','app/src/test/java/com/particlesdevs/photoncamera/monochrom/MonoImageProfilesTest.java','app/src/test/java/com/particlesdevs/photoncamera/ui/settings/MonoProfilesUiTest.java']
assert changed==sorted(expected),changed
m=json.loads((here/'manifest.json').read_text())
for name,digest in m['parentFiles'].items():assert a[name]==digest,name
for name,digest in m['fileOverrides'].items():assert b[name]==digest,name
ns='{http://schemas.android.com/apk/res/android}'
for kind in ['m9','monochrom']:
 xml=ET.parse(root/('app/src/main/res/xml/preferences_'+kind+'.xml')).getroot()
 keys=[e.attrib[ns+'key'] for e in xml.iter() if ns+'key' in e.attrib]
 assert len(keys)==len(set(keys)),kind
 assert ('pref_mono_profiles_screen' in keys)==(kind=='monochrom')
 assert ('pref_m9_profiles_screen' in keys)==(kind=='m9')
report=dict(status='PASS',parent='2.47-monolabel1a',version='2.48-monoprofiles1a',changedFiles=changed,unchangedParentSourceFiles=len(a)-len([p for p in changed if p in a]),rendererCaptureAndM9ProfilesUnchanged=True,independentMenus=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
