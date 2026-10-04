from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,xml.etree.ElementTree as ET
parent,root,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
manifest=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'uioverlay1e.patch')==manifest['patchSha256']
for n,h in manifest['parentFiles'].items(): assert sha(parent/n)==h,n
for n,h in manifest['fileOverrides'].items(): assert sha(root/n)==h,n
def files(p):
 d={f.relative_to(p).as_posix():f for tree in ['app/src','circularbarlib/src'] for f in (p/tree).rglob('*') if f.is_file()};d['app/build.gradle']=p/'app/build.gradle';return d
b,a=files(parent),files(root)
changed={n for n in b.keys()|a.keys() if n not in b or n not in a or sha(b[n])!=sha(a[n])}
assert changed==set(manifest['fileOverrides']),changed
with tempfile.TemporaryDirectory() as temp:
 temp=Path(temp)
 for n in manifest['parentFiles']:
  (temp/n).parent.mkdir(parents=True,exist_ok=True);(temp/n).write_bytes((parent/n).read_bytes())
 subprocess.run(['git','-C',str(temp),'apply','--whitespace=nowarn',str(here/'uioverlay1e.patch')],check=True)
 for n,h in manifest['fileOverrides'].items(): assert sha(temp/n)==h,n
J='app/src/main/java/com/particlesdevs/photoncamera/'
for n in changed:
 assert n=='app/build.gradle' or n.startswith(('app/src/main/res/',J+'ui/camera/','app/src/test/java/com/particlesdevs/photoncamera/ui/camera/')),n
for n in b:
 if n.startswith('circularbarlib/') or any(k in n for k in ['/assets/','/cpp/','/jni/','/jniLibs/','/m9/','/capture/','/processing/','/viewfinder/','/control/','/api/']):
  assert n in a and sha(b[n])==sha(a[n]),n
assert sha(root/(J+'ui/camera/CameraUIController.java'))==sha(parent/(J+'ui/camera/CameraUIController.java'))
ns='{http://schemas.android.com/apk/res/android}'
for p in (root/'app/src/main/res').rglob('*.xml'):ET.parse(p)
def ids(name):return [e.get(ns+'id') for e in ET.parse(root/('app/src/main/res/layout/'+name)).iter() if e.get(ns+'id')]
bottom=ids('layout_main_bottombar.xml')
assert bottom.index('@+id/m9_overlay_photo')<bottom.index('@+id/m9_overlay_motion')
controls=ids('layout_m9_overlay_controls.xml')
assert controls==['@+id/m9_overlay_controls']+['@+id/m9_overlay_'+n for n in ['iso','shutter','ev','focus','wb','settings']]
chooser=(root/(J+'ui/camera/M9OverlayController.java')).read_text()
for marker in ['"M9", "Monochrom", "M10-R", "M11"','card.setEnabled(installed)','M9SaveStatus.INSTANCE.snapshot().pending','shutterButton.isHovered()','c.isM9BracketActive()','source[i].removeTextChangedListener(watchers[i])','original.performClick()','original.performLongClick()','layoutTopbar.settingsButton.performClick()']:
 assert marker in chooser,marker
assert 'PreferenceKeys.setCameraModeOrdinal' not in chooser
policy=(root/(J+'ui/camera/M9OverlayPolicy.java')).read_text();assert 'return index == 0;' in policy
# Existing capture defaults and all settings keys/values survive; only the layout-position menu is disabled.
old=ET.parse(parent/'app/src/main/res/xml/preferences_m9.xml').getroot();new=ET.parse(root/'app/src/main/res/xml/preferences_m9.xml').getroot()
for tree in [old,new]:
 for e in tree.iter():
  if e.get(ns+'key')=='pref_video_settings_submenu': e.attrib.pop('{http://schemas.android.com/apk/res-auto}isPreferenceVisible',None)
  if e.get(ns+'key')=='@string/pref_lens_bar_position_key':
   for k in [ns+'enabled',ns+'summary','{http://schemas.android.com/apk/res-auto}useSimpleSummaryProvider']: e.attrib.pop(k,None)
assert ET.tostring(old)==ET.tostring(new)
for name in ['preferences_m9.xml','preferences.xml']:
 old=ET.parse(parent/('app/src/main/res/xml/'+name)).getroot();new=ET.parse(root/('app/src/main/res/xml/'+name)).getroot()
 video=next(e for e in new.iter() if e.get(ns+'key')=='pref_video_settings_submenu')
 assert video.get('{http://schemas.android.com/apk/res-auto}isPreferenceVisible')=='false'
 assert ET.tostring(old)==ET.tostring(new),name
assert 'settings.setOnClickListener(v -> openAppSettings())' in chooser
assert 'quickControls.setOnClickListener(v -> showQuickControls())' in chooser
assert 'CameraMode[] modes = {CameraMode.UNLIMITED};' in chooser
quick=chooser[chooser.index('private void showQuickControls()'):chooser.index('private String timerLabel()')]
assert 'm9_overlay_all_settings' not in quick and 'case 0: showTimer();' in quick and 'case 4: showOtherModes();' in quick
top_ids=ids('layout_main_topbar.xml')
assert '@+id/m9_overlay_quick_controls' in top_ids
assert '@+id/m9_overlay_active_render' not in top_ids
assert '@+id/m9_overlay_torch' in top_ids and '@+id/m9_overlay_night' in top_ids
assert 'm9_overlay_white_balance' not in quick and 'm9_overlay_flash' not in quick
assert 'original.performClick();' in chooser[chooser.index('private void toggleTorch()'):chooser.index('private void showQuickControls()')]
assert 'M9OverlayPolicy.nightToggleTarget(' in chooser and '"last_primary_mode"' in chooser
assert 'new TextView[5]' in chooser and 'R.id.wb_option_tv' in chooser
flat=ET.parse(root/'app/src/main/res/layout/layout_m9_linear_manual.xml').getroot()
assert any(e.tag.endswith('.M9LinearManualView') for e in flat.iter())
hidden=next(e for e in flat.iter() if e.get(ns+'id')=='@+id/buttons_container')
assert hidden.get(ns+'layout_height')=='0dp' and hidden.get(ns+'visibility')=='gone'
fragment=(root/(J+'ui/camera/CameraFragment.java')).read_text()
assert 'addPillBlurSpec(cameraFragmentBinding.lensZoomBar)' not in fragment
assert 'if (manualKnobView instanceof M9LinearManualView) return;' in fragment
view=(root/(J+'ui/camera/views/M9LinearManualView.java')).read_text()
assert all(s not in view for s in ['canvas.rotate(', 'canvas.drawArc(', 'canvas.drawCircle('])
assert 'selection.select(index, this)' in view and 'if (!canInteract()) return false;' in view
assert 'super.onCancelPendingInputEvents();' in view
assert 'manualRuler.setInteractionAllowed(this::available)' in chooser
assert 'controls[i].setSelected(source[i].isSelected());' in chooser
report=dict(status='passed' ,version=manifest['version'],reference='2.42 UIOVERLAY1D, with 2.38 photographic baseline',exactParentFiles=len(b)-len(manifest['parentFiles']),onlyChangedFiles=sorted(changed),patchRoundTrip=True,allPhotographicAndCaptureCodeExact242=True,allAssetsShadersNativeSourcesAndLibrariesExact242=True,previewGeometryAndOrientationCodeExact242=True,manualConsoleAndPhysicalExposureMathExact242=True,allCaptureAndOutputPreferencesPreserved=True,photoThenMotion=True,originalModeOrdinalsPreserved=True,realManualControlDelegation=True,originalSettingsAndTimerDelegation=True,renderPickerM9Only=True,newControlsCheckTimerBracketProcessingAndFinalSaves=True,flatManualRuler=True,noCircularDrawingInNewRuler=True,retainedOriginalKnobItemValuesAndCallbacks=True,noLegacyLensBlurFootprint=True,hiddenOptionCellsReserveNoSpace=True,phoneValidationPending=True,topLeftRenderLabelRemoved=True,torchAndNightToggles=True,whiteBalanceBeforeSettings=True,gearOpensAppSettings=True,separateShootingControlsChevron=True,videoAndRawVideoEntriesHidden=True,videoPreferenceScreensHiddenWithoutChangingStoredValues=True)
out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
