from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET

parent,root,out=map(lambda s:Path(s).resolve(),sys.argv[1:])
here=Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'ev.patch')==manifest['patchSha256']
for name,digest in manifest['parentFiles'].items(): assert sha(parent/name)==digest,name
for name,digest in manifest['fileOverrides'].items(): assert sha(root/name)==digest,name
a={};b={}
for tree in ['app/src','circularbarlib/src']:
 a.update({p.relative_to(parent).as_posix():p for p in (parent/tree).rglob('*') if p.is_file()})
 b.update({p.relative_to(root).as_posix():p for p in (root/tree).rglob('*') if p.is_file()})
a['app/build.gradle']=parent/'app/build.gradle';b['app/build.gradle']=root/'app/build.gradle'
assert not a.keys()-b.keys()
changed={n for n in b if n not in a or sha(a[n])!=sha(b[n])}
assert changed==set(manifest['fileOverrides']),changed
unchanged=sorted(set(a)-changed)
J='app/src/main/java/com/particlesdevs/photoncamera/'
C='circularbarlib/src/main/java/com/particlesdevs/photoncamera/circularbarlib/'
frozen=[J+'processing/parameters/IsoExpoSelector.java',J+'m9/M9ExposurePlan1A.java',
        J+'capture/CaptureController.java',J+'m9/preview/M9AutoExposure2D.java',
        'app/src/main/assets/shaders/preview/main_fs.glsl']
for prefix in [J+'m9/render/',J+'m9/export/','app/src/main/cpp/','app/src/main/assets/']:
 frozen.extend(n for n in a if n.startswith(prefix))
for n in frozen:assert n in unchanged,n

param=(root/(J+'manual/ParamController.java')).read_text()
getter=param.split('public double getM9UserEv1A() {',1)[1].split('\n    }',1)[0]
assert 'return LeicaEv.read(' in getter
for forbidden in ['exposureCompensation','getCurrentEvValue','CONTROL_AE_COMPENSATION_STEP',' + ']:
 assert forbidden not in getter,forbidden
assert 'builder.set(CaptureRequest.CONTROL_AE_EXPOSURE_COMPENSATION, 0)' in param
assert 'EV = LeicaEv.normalize(model.getCurrentEvValue());' in param
settings=(root/(J+'api/Settings.java')).read_text()
assert 'exposureCompensation = 0.0;' in settings
assert 'LeicaEv.migrate(' in settings
assert 'COMMON_KEYS.add(com.particlesdevs.photoncamera.circularbarlib.control.LeicaEv.KEY)' in (root/(J+'settings/PreferenceKeys.java')).read_text()
selector=(root/(J+'processing/parameters/IsoExpoSelector.java')).read_text()
assert '* Math.pow(2.0, input.ev + input.autoEv)' in selector
assert 'ev, placement2D.appliedEv' in selector
console=(root/(C+'console/ManualModeConsoleImpl.java')).read_text()
close=console.split('public void retractAllKnobs() {',1)[1].split('\n    @Override',1)[0]
assert 'setKnobResetCalled' not in close
assert 'evModel.resetModelSilently()' not in close
assert 'syncEvFromPreferences()' in close
properties=(root/(C+'camera/CameraProperties.java')).read_text()
assert 'CONTROL_AE_COMPENSATION' not in properties
wheel=(root/(C+'control/models/EvModel.java')).read_text()
assert 'CONTROL_AE_COMPENSATION' not in wheel and '/ evStep' not in wheel

resources=ET.parse(root/'app/src/main/res/values/m9_ev.xml').getroot()
values=[float(n.text) for n in resources.find("string-array[@name='m9_ev_values']")]
assert values==[n/3.0 for n in range(-9,10)]
assert len(resources.find("string-array[@name='m9_ev_entries']"))==19
android='{http://schemas.android.com/apk/res/android}'
menu=ET.parse(root/'app/src/main/res/xml/preferences_m9.xml').getroot()
rows=[n for n in menu.iter() if n.get(android+'key')=='@string/pref_expocompensation_seekbar_key']
assert len(rows)==1 and rows[0].tag=='ListPreference'
assert rows[0].get(android+'entryValues')=='@array/m9_ev_values'
assert rows[0].get(android+'defaultValue')=='0.0'
report=dict(status='passed',revision='M9LEICAEV1A',changedFiles=sorted(changed),
 unchangedSourceFiles=len(unchanged),frozenPhotographicFiles=len(set(frozen)),
 menuValues=values,onePersistentEvAuthority=True,vendorEvMetadataNotNeededForDial=True,
 genericPhotonOffsetNeutral=True,panelClosePreservesEv=True,evGlobalAcrossLenses=True,
 previewShaderUnchanged=True,physicalAllocationUnchanged=True,autoAndTapPolicyUnchanged=True,
 rendererAndDngCodeUnchanged=True,otherExposureStandardizationsPending=True)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
