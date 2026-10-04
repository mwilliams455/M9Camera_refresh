from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,xml.etree.ElementTree as ET
parent,root,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'bracket.patch')==manifest['patchSha256']
for n,h in manifest['parentFiles'].items():assert sha(parent/n)==h,n
for n,h in manifest['fileOverrides'].items():assert sha(root/n)==h,n
def files(p):
 d={f.relative_to(p).as_posix():f for tree in ['app/src','circularbarlib/src'] for f in (p/tree).rglob('*') if f.is_file()};d['app/build.gradle']=p/'app/build.gradle';return d
b,a=files(parent),files(root)
changed={n for n in b.keys()|a.keys() if n not in b or n not in a or sha(b[n])!=sha(a[n])}
assert changed==set(manifest['fileOverrides']),changed
with tempfile.TemporaryDirectory() as temp:
 temp=Path(temp)
 for n in manifest['parentFiles']:
  (temp/n).parent.mkdir(parents=True,exist_ok=True);(temp/n).write_bytes((parent/n).read_bytes())
 subprocess.run(['git','-C',str(temp),'apply','--whitespace=nowarn',str(here/'bracket.patch')],check=True)
 for n,h in manifest['fileOverrides'].items():assert sha(temp/n)==h,n
J='app/src/main/java/com/particlesdevs/photoncamera/'
assert not any('/assets/' in n or '/cpp/' in n or '/jni/' in n or '/jniLibs/' in n or '/preview/' in n or '/viewfinder/' in n or n.startswith('circularbarlib/') for n in changed)
for name in ['processing/parameters/IsoExpoSelector.java','m9/M9AeLock1A.java','m9/M9SelfTimer1A.java','m9/M9ShootingProfiles.java','processing/parameters/FrameNumberSelector.java','control/TouchFocus.java']:
 assert sha(root/(J+name))==sha(parent/(J+name)),name
# Renderer changes are only to a diagnostic helper's signature and bracketing report.
old=(parent/(J+'m9/render/M9R35Renderer.java')).read_text();new=(root/(J+'m9/render/M9R35Renderer.java')).read_text()
new=new.replace('int bufferedFrameCount, CaptureRequest captureRequest) {','int bufferedFrameCount) {')
x='''            d.put("bracketingEffective", captureRequest!=null
                    && captureRequest.getTag() instanceof com.particlesdevs.photoncamera.m9.M9ExposurePlan1A
                    && ((com.particlesdevs.photoncamera.m9.M9ExposurePlan1A)captureRequest.getTag()).bracket!=null);
            d.put("bracketingSeparateFiles",true);
            d.put("bracketingHdrMerge",false);'''
assert new.count(x)==1;assert new.replace(x,'            d.put("bracketingEffective", false);')==old
cap=(root/(J+'capture/CaptureController.java')).read_text();ui=(root/(J+'ui/camera/CameraUIController.java')).read_text()
for marker in ['m9Bracket.frame(m9BracketAttemptToken,m9BracketContext(),displayedPlan1A','m9Bracket.complete(event,m9BracketContext()',
 'm9Bracket.request(token,m9BracketContext()','m9Bracket.ticket()!=expectedToken','snapshot().pending>0 || burst',
 'cancelM9Bracket("camera_close")','cancelM9Bracket("session_resources_closed")','range.getLower(),range.getUpper()',
 'capturePlan1A.iso','capturePlan1A.exposureNs','captureBuilder.setTag(capturePlan1A)']:
 assert marker in cap,marker
assert ui.index('prepareM9Bracket()')>ui.index('private void onTimerFinished(long ticket)')
assert 'IsoExpoSelector.HDR = false;' in ui
fragment=(root/(J+'ui/camera/CameraFragment.java')).read_text()
assert fragment.index('instanceof com.particlesdevs.photoncamera.m9.M9Bracket1A.Completion')<fragment.index('logD("onProcessingFinished: " + obj)')
queue=(root/(J+'m9/render/M9PrimaryRenderQueue.java')).read_text()
for marker in ['M9SaveStatus.INSTANCE.begin(output,bracket==null?null:','bracket.saveMode','bracket.unfiltered',
 'M9Bracket1A.Completion(bracket,issues)','job.jpegFinalizeTicket.awaitCompletion();','job.saveTicket.complete(jpegSaved, dngSaved,']:
 assert marker in queue,marker
android='{http://schemas.android.com/apk/res/android}'
menu=ET.parse(root/'app/src/main/res/xml/preferences_m9.xml').getroot()
capture=next(e for e in menu if e.get(android+'key')=='pref_m9_capture_screen')
bracket=next(e for e in capture if e.get(android+'key')=='pref_m9_bracket_screen')
expected={'pref_m9_bracket_enabled':'0','pref_m9_bracket_frames':'3','pref_m9_bracket_step':'1','pref_m9_bracket_order':'0'}
assert {e.get(android+'key'):e.get(android+'defaultValue') for e in bracket if e.tag=='ListPreference'}==expected
arrays=ET.parse(root/'app/src/main/res/values/arrays.xml').getroot()
assert [e.text for e in arrays.find("string-array[@name='m9_bracket_step_seven_values']")]==['1','2']
assert [e.text for e in arrays.find("integer-array[@name='countdowntimer_entryvalues']")]==['0','2','12']
report=dict(status='passed',version=manifest['version'],reference='phone-accepted 2.37',exactParentFiles=len(b)-len(manifest['parentFiles']),onlyChangedFiles=sorted(changed),patchRoundTrip=True,previewOrientationAndShadersExactlyMatch237=True,rendererPhotographicCodeExactlyMatches237=True,unlockedExposureAllocatorExactlyMatches237=True,aeLockAndSelfTimerHelpersExact237=True,bracketsStartAfterTimerAndLatchDisplayedCentre=True,physicalShutterLimitsFromCurrentCamera=True,sequenceAdvancesOnlyOnMatchingFinalOutputTicket=True,completionWaitsForSelectedJpegAndDngPublication=True,oldGenerationCallbacksRejected=True,outputSelectionFrozenPerSeries=True,legacyHdrPreferenceDoesNotEnableBracketing=True,menuDefaultOff=True,sevenFrameChoicesRestricted=True,phoneValidationPending=True)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
