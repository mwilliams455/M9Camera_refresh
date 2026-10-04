from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,xml.etree.ElementTree as ET
parent,root,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'aelocktimer.patch')==manifest['patchSha256']
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
 subprocess.run(['git','-C',str(temp),'apply','--whitespace=nowarn',str(here/'aelocktimer.patch')],check=True)
 for n,h in manifest['fileOverrides'].items():assert sha(temp/n)==h,n
J='app/src/main/java/com/particlesdevs/photoncamera/'
assert not any('/assets/' in n or '/jni/' in n or '/jniLibs/' in n or '/render/' in n or '/preview/' in n or '/viewfinder/' in n for n in changed)
old=(parent/(J+'processing/parameters/IsoExpoSelector.java')).read_text();new=(root/(J+'processing/parameters/IsoExpoSelector.java')).read_text()
start=new.index('    /** Neutral metering remains live during AE-L');end=new.index('    public static ExpoPair getM9LiveHudPair1A',start)
assert new[:start]+new[end:]==old,'Unlocked allocator must be byte-identical'
capture=(root/(J+'capture/CaptureController.java')).read_text()
assert capture.count('&& acceptsM9AeLockPlan(plan) ? plan : null;')==2
assert 'M9ExposurePlan1A displayed=getM9DisplayedExposurePlan1A(' in capture
assert 'clearM9AeLock("camera_close")' in capture and 'clearM9AeLock("session_resources_closed")' in capture
assert 'neutralReferenceForAeLock1A(this,iso,time,autoIso)' in capture
assert 'reference.iso,reference.exposure)' in capture
assert 'm9AeLock.stamp(plan,context,token)' in capture
assert 'if (acceptsM9AeLockPlan(plan)) m9ExposurePlan1A = plan;' in capture
fragment=(root/(J+'ui/camera/CameraFragment.java')).read_text()
assert 'captureController.createM9ExposurePlan1A(result)' in fragment
ui=(root/(J+'ui/camera/CameraUIController.java')).read_text()
assert 'if (timerGate.running()) resetTimer();' in ui
assert 'timerGate.finish(ticket,context)' in ui and 'isM9TimerCaptureReady()' in ui
assert 'this.countdownTimer.cancelCountdown()' in ui and 'M9SelfTimer1A.seconds(PreferenceKeys.getCountdownTimerIndex())' in ui
assert ui.index('cameraFragment.captureController.takePicture();')>ui.index('private void onTimerFinished(long ticket)')
focus=(root/(J+'control/TouchFocus.java')).read_text()
assert focus.index('if (captureController.isM9AeLocked())')<focus.index('M9TapMeter1A.choose(x,y,now)')
assert '(m9tap || captureController.isM9AeLocked())' in focus
android='{http://schemas.android.com/apk/res/android}';app='{http://schemas.android.com/apk/res-auto}'
arrays=ET.parse(root/'app/src/main/res/values/arrays.xml').getroot()
assert [n.text for n in arrays.find("integer-array[@name='countdowntimer_entryvalues']")]==['0','2','12']
menu=ET.parse(root/'app/src/main/res/values/m9_menu.xml').getroot()
assert [n.text for n in menu.find("string-array[@name='m9_menu_timer_entries']")]==['@string/off','2 seconds','12 seconds']
assert [n.text for n in menu.find("string-array[@name='m9_menu_timer_indices']")]==['0','1','2']
layout=ET.parse(root/'app/src/main/res/layout/layout_main_topbar.xml').getroot()
views={e.get(android+'id'):e for e in layout.iter() if e.get(android+'id')}
lock=views['@+id/m9_ae_lock_button'];display=views['@+id/m9_display_aids_button'];flash=views['@+id/flash_button']
assert lock.get(app+'layout_constraintStart_toEndOf')=='@id/m9_display_aids_button'
assert lock.get(app+'layout_constraintEnd_toStartOf')=='@id/flash_button'
assert display.get(app+'layout_constraintEnd_toStartOf')=='@id/m9_ae_lock_button'
assert flash.get(app+'layout_constraintStart_toEndOf')=='@id/m9_ae_lock_button'
assert lock.get(android+'minHeight')=='48dp' and lock.get(android+'contentDescription')=='@string/m9_ae_lock_auto'
report=dict(status='passed',version=manifest['version'],reference='phone-accepted 2.36',exactParentFiles=len(b)-len(manifest['parentFiles']),onlyChangedFiles=sorted(changed),patchRoundTrip=True,previewOrientationAndShadersExactlyMatch236=True,savedRendererExactlyMatches236=True,unlockedExposureAllocatorExactlyMatches236=True,lockUsesDisplayedPairWithLiveNeutralReference=True,bothPlanAccessorsAndPublicationCheckGeneration=True,closeAndSessionSwitchClearLock=True,tapsRemainFocusOnlyWhileLocked=True,timerReleaseOnlyAfterCurrentUncanceledCountdown=True,compiledMenuCheckDeferredToPackaging=True,phoneValidationPending=True)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
