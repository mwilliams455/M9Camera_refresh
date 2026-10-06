"""Preserve every 2.56 native library and asset for the preview probe scheduling fix."""
from pathlib import Path
import copy,hashlib,json,re,subprocess,sys,zipfile
root,built,control,bt,out=map(lambda p:Path(p).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent;out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def signature(n):return n=='META-INF/MANIFEST.MF' or n.startswith('META-INF/') and n.endswith(('.RSA','.DSA','.EC','.SF'))
assert sha(control.read_bytes())=='7a565fc60bb1fc7c86dae42d1d38e34f29e83e6ba565f8ed625511b215be4d40'
m=json.loads((here/'manifest.json').read_text())
for name,digest in m['fileOverrides'].items():assert sha((root/name).read_bytes())==digest,name
unsigned,aligned,final=[out/n for n in ['unsigned.apk','aligned.apk','M9Cam_2.57_PREVIEWPROBE1A.apk']];expected={};addedNative={}
with zipfile.ZipFile(control) as old,zipfile.ZipFile(built) as new,zipfile.ZipFile(unsigned,'w') as dst:
 assert old.testzip() is None and new.testzip() is None
 oldNativeBytes={n:old.read(n) for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
 natives={n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')};assert len(natives)==27
 added={'lib/arm64-v8a/libmonocolor.so','lib/armeabi-v7a/libmonocolor.so'}
 builtNatives={n for n in new.namelist() if n.startswith('lib/') and not n.endswith('/')}
 restoredOnly={'lib/arm64-v8a/libm9sharpness.so','lib/armeabi-v7a/libm9sharpness.so'}
 assert builtNatives<=natives and natives-builtNatives<=restoredOnly, (builtNatives-natives,natives-builtNatives)
 assets={n for n in old.namelist() if n.startswith('assets/') and not n.endswith('/')}
 for n in assets:assert old.read(n)==new.read(n),n
 newAssets={n for n in new.namelist() if n.startswith('assets/') and not n.endswith('/')}-assets
 assert not newAssets, newAssets
 assert len(assets)==285
 for n in newAssets:assert new.read(n)==(root/'app/src/main'/n).read_bytes(),n
 for info in new.infolist():
  n=info.filename
  if signature(n):continue
  data=old.read(n) if n in natives else new.read(n);expected[n]=sha(data);dst.writestr(copy.copy(info),data)
  if n in added:addedNative[n]=sha(data)
 for n in sorted(natives-builtNatives):
  data=old.read(n);expected[n]=sha(data);dst.writestr(copy.copy(old.getinfo(n)),data)
 dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
 for marker in ['MonoSaveQueue','ProfileCapture','RenderProfile','MonoRenderer','MONODARKFRAME1A','MONOOUTPUT1B_DURABLE_EXPORT','pref_mono_contrast_key','pref_mono_sharpness_key','pref_mono_toning_hue_key','pref_mono_toning_strength_key','pref_active_render_profile','M9BracketRuntime','M9ShootingControls','MonoImageProfiles','MonoProfilesUi','pref_mono_image_profiles_v1','M9PERF1A','discardedLegacyShadingAuditsExecuted','imageReportPerformanceRevision','readOnlyImageAuditsExecuted','diagnostic_files_disabled','nativeColorArgbFallbackAllocatedBytes','M9DngProfileWriter',' C-','JPEGQUEUE1A','jpegOnlyCompletionRetainsRaw','panelViewActive','lensOffsetObserver','galleryGeneration','galleryTarget','lensModelObserver','ShadingXCoordinates']:
  assert marker.encode() in dex,marker
subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
signer=['java','-jar',str(bt/'lib/apksigner.jar')]
subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),'--ks-key-alias','key0','--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
cert=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True);assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in cert
badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
for marker in ["name='com.m9project.m9cam.photon'","versionCode='27257'","versionName='2.57-previewprobe1a'"]:assert marker in badging,marker
menus={}
for kind in ['m9','monochrom']:
 xml=subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/xml/preferences_'+kind+'.xml',str(final)],text=True)
 for key in ['image','capture','output','display','advanced']:assert 'pref_m9_'+key+'_screen' in xml
 menus[kind]=xml
resources=subprocess.check_output([str(bt/'aapt2'),'dump','resources',str(final)],text=True)
for key in ['pref_mono_contrast_key','pref_mono_sharpness_key','pref_mono_toning_hue_key','pref_mono_toning_strength_key']:
 resource=re.search(r'resource (0x[0-9a-f]+) string/'+key+r'\b',resources).group(1);assert '@'+resource in menus['monochrom']
assert 'pref_m9_profiles_screen' not in menus['monochrom'] and 'pref_m9_saturation' not in menus['monochrom']
assert 'pref_mono_profiles_screen' in menus['monochrom'] and 'pref_mono_profiles_screen' not in menus['m9']
for key in ['mono_profile_current','mono_profile_save','mono_profile_reset','mono_profile_saved']:assert key in menus['monochrom'],key
with zipfile.ZipFile(final) as apk:
 assert apk.testzip() is None
 assert {n:sha(apk.read(n)) for n in apk.namelist() if not signature(n)}==expected
 for n in natives:assert apk.read(n)==oldNativeBytes[n],n
 for n in added:
  target=out/Path(n).parts[1];target.mkdir(exist_ok=True);lib=target/'libmonocolor.so';lib.write_bytes(apk.read(n))
  headers=subprocess.check_output(['readelf','-lW',str(lib)],text=True)
  for line in headers.splitlines():
   if line.strip().startswith('LOAD'):assert int(line.split()[-1],16)>=16384,line
  symbols=subprocess.check_output(['readelf','--dyn-syms','--wide',str(lib)],text=True)
  assert 'Java_com_particlesdevs_photoncamera_monochrom_render_M9NativeColorCore_renderMonochrome1ARawScalarSharpStdDirectBitmap' in symbols
  lib.unlink();target.rmdir()
report=dict(status='PASS',version='2.57-previewprobe1a',versionCode=27257,bytes=final.stat().st_size,sha256=sha(final.read_bytes()),acceptedM9NativeLibrariesPreserved=sorted(natives-added),all27NativeLibrariesByteIdenticalTo256=True,preservedMonochromNativeLibraries=addedNative,all256AssetsUnchanged=True,addedAssets=sorted(newAssets),signatureMatchesAcceptedM9=True,zipAlignment16KiB=True,monochromElfAlignment16KiB=True,bothCompiledMenusVerified=True,phoneValidationPending=True)
for destination in [out,here]:(destination/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'SIGNATURE_CHECK.txt').write_text(cert);(out/'APK_BADGING.txt').write_text(badging)
for kind,xml in menus.items():(out/('COMPILED_'+kind.upper()+'_MENU.txt')).write_text(xml)
unsigned.unlink();aligned.unlink();print(json.dumps(report,indent=2))
