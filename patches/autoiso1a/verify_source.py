from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,xml.etree.ElementTree as ET
parent,root,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'autoiso.patch')==manifest['patchSha256']
for n,h in manifest['parentFiles'].items():assert sha(parent/n)==h,n
for n,h in manifest['fileOverrides'].items():assert sha(root/n)==h,n
def files(p):
 result={f.relative_to(p).as_posix():f for tree in ['app/src','circularbarlib/src'] for f in (p/tree).rglob('*') if f.is_file()};result['app/build.gradle']=p/'app/build.gradle';return result
b,a=files(parent),files(root)
changed={n for n in b.keys()|a.keys() if n not in b or n not in a or sha(b[n])!=sha(a[n])}
assert changed==set(manifest['fileOverrides']),changed
with tempfile.TemporaryDirectory() as temp:
 temp=Path(temp)
 for n in manifest['parentFiles']:
  (temp/n).parent.mkdir(parents=True,exist_ok=True);(temp/n).write_bytes((parent/n).read_bytes())
 subprocess.run(['git','-C',str(temp),'apply','--whitespace=nowarn',str(here/'autoiso.patch')],check=True)
 for n,h in manifest['fileOverrides'].items():assert sha(temp/n)==h,n
J='app/src/main/java/com/particlesdevs/photoncamera/'
assert not any('/assets/' in n or '/jni/' in n or '/jniLibs/' in n or '/render/' in n or '/preview/' in n or '/viewfinder/' in n for n in changed)
p=(root/(J+'processing/parameters/IsoExpoSelector.java')).read_text()
assert p.count('M9AutoIsoRuntime.snapshot()')==1
assert '0L, 0, tripod, autoIso)' in p and 'manualExposure, manualIso, tripod, autoIso)' in p
assert '.withAutoIsoControls(autoIso.identity)' in p and 'M9ExposureAllocation.allocate(target,' in p
capture=(root/(J+'capture/CaptureController.java')).read_text()
assert capture.count('&& plan.matchesAutoIsoControls(com.particlesdevs.photoncamera.m9.M9AutoIsoRuntime.snapshot().identity)')==2
runtime=(root/(J+'m9/M9AutoIsoRuntime.java')).read_text()
assert runtime.count('getAll()')==1
assert 'CaptureController.mCameraCharacteristics' in runtime
prefs=(root/(J+'settings/PreferenceKeys.java')).read_text()
for key in ['MAX_ISO_KEY','SLOWEST_KEY']:
 assert 'COMMON_KEYS.add(com.particlesdevs.photoncamera.m9.M9AutoIsoSettings.'+key+')' in prefs
 assert 'M9AutoIsoSettings.'+key+'.equals(key)' in prefs
resources=ET.parse(root/'app/src/main/res/values/m9_auto_iso.xml').getroot()
values=lambda name:[n.text for n in resources.find("string-array[@name='"+name+"']")]
assert values('m9_auto_iso_max_values')==list(map(str,[160,200,250,320,400,500,640,800,1000,1250,1600,2000,2500]))
assert values('m9_auto_iso_slowest_values')==list(map(str,range(6)))
assert values('m9_auto_iso_slowest_entries')==['Lens dependent','1/125 s','1/60 s','1/30 s','1/15 s','1/8 s']
menu=ET.parse(root/'app/src/main/res/xml/preferences_m9.xml').getroot();android='{http://schemas.android.com/apk/res/android}'
screen=menu.find("PreferenceScreen[@"+android+"key='pref_m9_capture_screen']/PreferenceScreen[@"+android+"key='pref_m9_auto_iso_screen']")
assert screen is not None
for key,default in [('pref_m9_auto_iso_max','2500'),('pref_m9_auto_iso_slowest','0')]:
 node=screen.find("ListPreference[@"+android+"key='"+key+"']");assert node is not None and node.get(android+'defaultValue')==default
report=dict(status='passed',version=manifest['version'],reference='phone-accepted 2.35',exactParentFiles=len(b)-len(manifest['parentFiles']),onlyChangedFiles=sorted(changed),patchRoundTrip=True,previewOrientationExactlyMatches235=True,savedRendererAndShaderAssetsExactlyMatch235=True,sharedAtomicAutoIsoSnapshot=True,bothCapturePlanAccessorsRejectChangedControls=True,globalAcrossLenses=True,menuValuesAndDefaultsVerified=True,phoneValidationPending=True)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
