#!/usr/bin/env python3
"""Package signed 3.10 retaining exact 3.09 native + assets/certificate."""
from pathlib import Path
import copy,hashlib,json,re,subprocess,sys,zipfile

root,built,oldapk,bt,out=(Path(s).resolve() for s in sys.argv[1:])
out.mkdir(parents=True,exist_ok=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
accepted='9f4501550ef57aeb32952efacf298a410c995400e819b16acb249202f5aaa2c8'
certificate='255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956'
assert sha(oldapk.read_bytes())==accepted,'Exact phone-positive 3.09 parent APK required'
assert built.is_file() and (root/'key/PcamLeak.jks').is_file()
scope=json.loads((out/'SOURCE_VERIFICATION.json').read_text())
assert scope['status']=='STAGED_FOR_ANDROID_BUILD'
assert scope['parent']=='3.09-aftracking5a' and scope['autoHumanEyeDefaultOn']
assert scope['oldManualEyeKeyIgnoredByNewAutoMode'] and scope['manualObjectTapHasPriority']
assert scope['strictFrontalGateUntouched'] and scope['profileEyeFourFreshObservations']
assert scope['camera2AfRegionOnly'] and scope['afCShutterPathUnchanged']
assert scope['originalModelsNativeAndAssetsUnchanged']
assert scope['aeAwbExposureRawJpegDngRenderingUnchanged']
asset=(root/'app/src/main/assets/rtm_animal_fp16.tflite')
expected_model=(Path(__file__).resolve().parent.parent/'focusanimaleye1a/MODEL_SHA256.txt').read_text().split()[0]
assert sha(asset.read_bytes())==expected_model
signing=lambda name:name=='META-INF/MANIFEST.MF' or name.startswith('META-INF/') and name.endswith(('.RSA','.DSA','.EC','.SF'))
signer=['java','-jar',str(bt/'lib/apksigner.jar')]
cert=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(oldapk)],text=True)
assert certificate in cert and 'Verified using v2 scheme (APK Signature Scheme v2): true' in cert
unsigned=out/'unsigned.apk';aligned=out/'aligned.apk';final=out/'M9Cam_3.10_AUTOEYE1A.apk'
expected={}
with zipfile.ZipFile(oldapk) as old,zipfile.ZipFile(built) as new,zipfile.ZipFile(unsigned,'w') as dst:
    assert old.testzip() is None and new.testzip() is None
    original_lib={n:old.read(n) for n in old.namelist() if n.startswith('lib/') and n.endswith('.so')}
    original_assets={n:old.read(n) for n in old.namelist() if n.startswith('assets/') and not n.endswith('/')}
    assert len(original_lib)==37,len(original_lib)
    assert len(original_assets)==301,len(original_assets)
    new_names=set(new.namelist())
    assert not any(n.startswith('lib/') and n.endswith('.so') and n not in original_lib for n in new_names), 'No new native lib allowed'
    assert not any(n.startswith('assets/') and not n.endswith('/') and n not in original_assets for n in new_names),'No new model or asset allowed'
    for n,payload in original_assets.items():assert n in new_names and new.read(n)==payload,n
    for info in new.infolist():
        name=info.filename
        if signing(name):continue
        payload=original_lib[name] if name in original_lib else new.read(name)
        expected[name]=sha(payload)
        dst.writestr(copy.copy(info),payload)
    for name in sorted(set(original_lib)-new_names):
        payload=original_lib[name];expected[name]=sha(payload)
        dst.writestr(copy.copy(old.getinfo(name)),payload)
    dex=b''.join(new.read(n) for n in new_names if n.endswith('.dex'))
    for marker in ['SubjectAppearanceDescriptor','SubjectAnchorPolicy','TrackingTogglePolicy','FocusMotionPredictor',
                   'TrackingSemanticDetector','FocusTrackingController','pref_focus_tracking_identity',
                   'pref_focus_tracking_predictive','pref_focus_tracking_semantic','HumanSubjectFocusController','AutoEyeFocusPolicy','ProfileEyeAdmissionGate','pref_focus_auto_eye_enabled',
                   'PetFocusController','AnimalSimccDecoder','TrackingFocus','M9DIAGINDEX1A_BOUNDED']:
        assert marker.encode() in dex,marker
subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),
                       '--ks-key-alias','key0','--ks-pass','pass:photoncamera',
                       '--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
cert_new=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
assert certificate in cert_new and 'Verified using v2 scheme (APK Signature Scheme v2): true' in cert_new
badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
for required in ("name='com.m9project.m9cam.photon'", "versionCode='27310'", "versionName='3.10-autoeye1a'"):
    assert required in badging,required
for profile in ('m9','monochrom'):
    menu=subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file',
        'res/xml/preferences_'+profile+'.xml',str(final)],text=True)
    for marker in ('pref_focus_tracking','pref_focus_tracking_semantic','pref_focus_tracking_predictive','pref_focus_tracking_identity',
                   'pref_focus_auto_eye_enabled','pref_focus_subject_pet'):
        assert marker in menu,(profile,marker)
with zipfile.ZipFile(final) as signed:
    assert signed.testzip() is None
    actual={n:sha(signed.read(n)) for n in signed.namelist() if not signing(n)}
    assert actual==expected,'Signed APK contents differ from validated build'
    assert all(signed.read(n)==payload for n,payload in original_lib.items())
    assert all(signed.read(n)==payload for n,payload in original_assets.items())
report=dict(status='PASS',version='3.10-autoeye1a',versionCode=27310,
            sha256=sha(final.read_bytes()),bytes=final.stat().st_size,parent=accepted,
            preserved37NativeLibraries=True,preserved301OriginalAssets=True,
            bundledModelSha256=expected_model,signatureMatchesPrior=True,
            sixteenKiBAligned=True,bothProfileMenusVerified=True,
            photoRendererUntouched=True,automaticEyeDefaultOn=True,
            phoneHumanEyeValidationPending=True)
(out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(report['sha256']+'  '+final.name+'\n')
unsigned.unlink();aligned.unlink()
print(json.dumps(report,indent=2))
