from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as E
parent,mono,root=map(Path,sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();j='app/src/main/java/com/particlesdevs/photoncamera/'
manifest=json.loads((here/'manifest.json').read_text())
for name,digest in manifest['fileOverrides'].items():assert sha(root/name)==digest,name
# Existing assets and both M9 photographic stages remain byte-identical.
assets=[]
for p in (parent/'app/src/main/assets').rglob('*'):
 if p.is_file():
  name=p.relative_to(parent).as_posix();assert sha(p)==sha(root/name),name;assets.append(name)
unchangedM9=[];allowed={'M9SaveSelection.java','M9DisplayAids.java','render/M9PrimaryRenderQueue.java'}
for p in (parent/j/'m9').rglob('*.java'):
 name=p.relative_to(parent/j/'m9').as_posix()
 if name not in allowed:assert sha(p)==sha(root/j/'m9'/name),name;unchangedM9.append(name)
assert sha(parent/'app/src/main/cpp/m9color_jni.cpp')==sha(root/'app/src/main/cpp/m9color_jni.cpp')
# The new native target differs only in JNI namespace, never pixel math or compiler options.
expected=(mono/'app/src/main/cpp/m9color_jni.cpp').read_text().replace('_photoncamera_m9_','_photoncamera_monochrom_')
assert expected==(root/'app/src/main/cpp/monochrom/monocolor_jni.cpp').read_text()
for p in (mono/'app/src/main/cpp').glob('mm_monochrom*.inc'):assert sha(p)==sha(root/'app/src/main/cpp/monochrom'/p.name)
monoCount=0
for p in (mono/j/'m9').rglob('*.java'):
 n=p.relative_to(mono/j/'m9').as_posix()
 expected=p.read_text().replace('com.particlesdevs.photoncamera.m9','com.particlesdevs.photoncamera.monochrom').replace('"m9/m9_r35_calibration.bin"','"monochrom/m9_r35_calibration.bin"').replace('System.loadLibrary("m9color")','System.loadLibrary("monocolor")')
 if n!='export/MonoDngExport1A.java':assert expected==(root/j/'monochrom'/n).read_text(),n;monoCount+=1
for p in (mono/'app/src/main/assets/mono').rglob('*'):
 if p.is_file():assert sha(p)==sha(root/'app/src/main/assets/mono'/p.relative_to(mono/'app/src/main/assets/mono'))
assert sha(mono/'app/src/main/assets/shaders/preview/main_fs.glsl')==sha(root/'app/src/main/assets/shaders/preview/monochrom_fs.glsl')
assert (mono/j/'processing/parameters/IsoExpoSelector.java').read_text().replace('com.particlesdevs.photoncamera.m9','com.particlesdevs.photoncamera.monochrom').replace('IsoExpoSelector','MonoIsoExpoSelector')==(root/j/'processing/parameters/MonoIsoExpoSelector.java').read_text()
ns='{http://schemas.android.com/apk/res/android}'
a=E.parse(root/'app/src/main/res/xml/preferences_m9.xml').getroot();b=E.parse(root/'app/src/main/res/xml/preferences_monochrom.xml').getroot()
assert [e.get(ns+'key') for e in a]==[e.get(ns+'key') for e in b]
image=next(e for e in b if e.get(ns+'key')=='pref_m9_image_screen')
assert [e.get(ns+'key') for e in image]==['@string/pref_mono_'+s+'_key' for s in ['contrast','sharpness','toning_hue','toning_strength']]
assert 'pref_m9_saturation' not in E.tostring(image).decode() and 'profiles' not in E.tostring(image).decode()
assert sha(parent/'app/src/main/res/xml/preferences_m9.xml')==sha(root/'app/src/main/res/xml/preferences_m9.xml')
selector=(root/j/'ui/camera/M9OverlayController.java').read_text();assert 'requireActivity().recreate()' in selector and 'M9SaveStatus.INSTANCE.snapshot().pending' in selector
capture=(root/j/'capture/CaptureController.java').read_text();assert 'configureMonoPreview(true)' in capture and 'ProfileCapture.bind(captureBuilder.build(),shutterSettings)' in capture
queue=(root/j/'monochrom/render/MonoSaveQueue.java').read_text()
assert 'settings.open();M9CaptureParameters.Scope inputs=parameters.open()' in queue
assert 'awaitPublished(destination,60000)' in queue and 'ticket.complete(jpeg,dng,true,original,published)' in queue
report=dict(status='PASS',revision='MONOMERGE1A',existingM9AssetsUnchanged=len(assets),existingM9PhotographicJavaUnchanged=len(unchangedM9),monochromJavaExactAfterNamespaceMove=monoCount,monochromNativeMathExact=True,monochromNativeLutsExact=True,monochromShaderExact=True,monochromExposureAllocatorExact=True,sharedSettingsHierarchy=True,independentImageKeys=True,m9MenuUnchanged=True,shutterSettingsFrozen=True,finalOutputGatesRendererSwitch=True,phoneValidationPending=True)
(here/'SOURCE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
