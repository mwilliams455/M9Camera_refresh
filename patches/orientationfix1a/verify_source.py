from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
bad,accepted,root,out=map(lambda s:Path(s).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'orientation.patch')==manifest['patchSha256']
for n,h in manifest['parentFiles'].items():assert sha(bad/n)==h,n
for n,h in manifest['fileOverrides'].items():assert sha(root/n)==h,n
for n in manifest['deletedFiles']:assert not (root/n).exists(),n
def files(p):
 result={f.relative_to(p).as_posix():f for tree in ['app/src','circularbarlib/src'] for f in (p/tree).rglob('*') if f.is_file()};result['app/build.gradle']=p/'app/build.gradle';return result
b,a,c=files(bad),files(accepted),files(root)
def changed(x,y):return {n for n in x.keys()|y.keys() if n not in x or n not in y or sha(x[n])!=sha(y[n])}
assert changed(b,c)==set(manifest['fileOverrides'])|set(manifest['deletedFiles'])
J='app/src/main/java/com/particlesdevs/photoncamera/';L='circularbarlib/src/main/java/com/particlesdevs/photoncamera/circularbarlib/'
allowed={'app/build.gradle',J+'ui/settings/M9ProfilesUi.java','app/src/main/res/values/m9_ev.xml','app/src/test/java/com/particlesdevs/photoncamera/m9/M9LeicaEvTest.java',L+'control/LeicaEv.java',L+'control/models/EvModel.java'}
assert changed(a,c)==allowed,changed(a,c)
for n in allowed-{'app/build.gradle'}:assert sha(bad/n)==sha(root/n),n
assert 'uCameraSamplingMatrix' not in (root/(J+'ui/camera/views/viewfinder/MainRenderer.java')).read_text()
assert 'getTransformMatrix' not in (root/(J+'ui/camera/views/viewfinder/MainRenderer.java')).read_text()
old=ET.parse(accepted/'app/src/main/res/values/m9_ev.xml').getroot();new=ET.parse(root/'app/src/main/res/values/m9_ev.xml').getroot()
values=lambda tree:[n.text for n in tree.find("string-array[@name='m9_ev_values']")]
assert values(old)==values(new)
labels=[n.text for n in new.find("string-array[@name='m9_ev_entries']")]
assert labels==[('0.0' if n==0 else ('+' if n>0 else '−')+f'{abs(n/3):.1f}')+' EV' for n in range(-9,10)]
report=dict(status='passed',version=manifest['version'],reference='phone-accepted 2.33',
 exactAcceptedFiles=len(a)-len(allowed),onlyDifferencesFrom233=sorted(allowed),
 completePreviewMatches233=True,allShaderAssetsMatch233=True,captureAndSavedRendererMatch233=True,
 decimalEvPresentationRetainedFrom234=True,storedExactThirdsUnchanged=True,
 parent234Changes=sorted(changed(b,c)),phoneValidationPending=True)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
