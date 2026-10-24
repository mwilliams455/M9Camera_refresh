#!/usr/bin/env python3
"""Sign 3.04 focus areas and AF feedback preserving accepted 3.03 native/asset bytes."""
from pathlib import Path
import copy,hashlib,json,re,subprocess,sys,zipfile

root,built,oldapk,bt,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
accepted='068ddf7da274ecbb6d0ed9cb7f1a786c2454283ea6bac663e38806aea7abd41d'
certificate='255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956'
assert sha(oldapk.read_bytes())==accepted,'Expected exact signed 3.03 accepted autofocus baseline'
assert built.is_file() and (root/'key/PcamLeak.jks').exists()
scope=json.loads((out/'SOURCE_VERIFICATION.json').read_text())
assert scope['status']=='STAGED_FOR_BUILD' and scope['parent']=='3.03-animaleye1b'
assert all(scope['implementation'][key] for key in ('spot','expandSpot','custom','wide'))
assert scope['implementation']['afStateReportedFromCamera2']
assert scope['nativeAndOriginalAssetsUnchanged']
model=(root/'app/src/main/assets/rtm_animal_fp16.tflite')
expected_model_sha=(Path(__file__).resolve().parent.parent/'focusanimaleye1a/MODEL_SHA256.txt').read_text().split()[0]
assert sha(model.read_bytes())==expected_model_sha
def signing(n):
    return n=='META-INF/MANIFEST.MF' or (
        n.startswith('META-INF/') and n.endswith(('.RSA','.DSA','.EC','.SF')))
signer=['java','-jar',str(bt/'lib/apksigner.jar')]
orig_cert=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(oldapk)],text=True)
assert certificate in orig_cert and 'Verified using v2 scheme (APK Signature Scheme v2): true' in orig_cert
unsigned=out/'unsigned.apk'
aligned=out/'aligned.apk'
final=out/'M9Cam_3.04_FOCUSCONTROL1A.apk'
expected={}
extra_native={}
extra_assets={}
with zipfile.ZipFile(oldapk) as old,zipfile.ZipFile(built) as new,zipfile.ZipFile(unsigned,'w') as dst:
    assert old.testzip() is None and new.testzip() is None
    original_lib={n:old.read(n) for n in old.namelist() if n.startswith('lib/') and n.endswith('.so')}
    assert len(original_lib)==37,len(original_lib)
    original_assets={n:old.read(n) for n in old.namelist() if n.startswith('assets/') and not n.endswith('/')}
    assert len(original_assets)==301,len(original_assets)
    new_names=set(new.namelist())
    for n,v in original_assets.items():
        assert n in new_names and new.read(n)==v,f'Original asset mutated: {n}'
    for n in set(original_lib)&new_names:
        assert n.startswith('lib/'),n
    new_lib={n for n in new_names if n.startswith('lib/') and n.endswith('.so')}
    extra_native={n:new.read(n) for n in new_lib-set(original_lib)}
    assert not extra_native,'Image ownership correction must not add native libraries'
    assert all(re.fullmatch(r'lib/(?:arm64-v8a|armeabi-v7a)/lib[\w.+-]+\.so',n)
               for n in extra_native)
    extra_assets={n:new.read(n) for n in new_names if n.startswith('assets/')
                  and not n.endswith('/') and n not in original_assets}
    assert not extra_assets,'Image ownership correction must not add assets'
    assert original_assets['assets/rtm_animal_fp16.tflite']==model.read_bytes(),'Pinned original AP10K model changed'
    for info in new.infolist():
        n=info.filename
        if signing(n):continue
        payload=original_lib[n] if n in original_lib else new.read(n)
        expected[n]=sha(payload)
        dst.writestr(copy.copy(info),payload)
    for n in sorted(set(original_lib)-new_names):
        payload=original_lib[n]
        expected[n]=sha(payload)
        dst.writestr(copy.copy(old.getinfo(n)),payload)
    dex=b''.join(new.read(n) for n in new_names if n.endswith('.dex'))
    for marker in ['PetFocusController','PetObjectDetector','PetTargetPolicy','PetAfStatusBadge','PetPreviewRetryPolicy','AnimalSimccDecoder','FocusControlPolicy','FocusAreaTouchController','FocusStateSnapshot',
                   'pref_focus_subject_pet','Cat AF','Dog AF','Dog Eye AF','Cat Eye AF','pose_null_recycled','inference_too_old','pref_focus_area_mode','pref_focus_af_state_feedback',
                   'HumanSubjectFocusController','HumanEyeAdmissionGate',
                   'TrackingFocus','M9DIAGINDEX1A_BOUNDED']:
        assert marker.encode() in dex,marker

elf={}
for n,data in sorted(extra_native.items()):
    temp=out/(Path(n).name+'.readelf')
    temp.write_bytes(data)
    try:
        headers=subprocess.check_output(['readelf','-lW',str(temp)],text=True)
        align=[int(l.split()[-1],16) for l in headers.splitlines()
               if l.strip().startswith('LOAD')]
        assert align,(n,'Missing ELF LOAD segments')
        min_align=min(align)
        # All new arm64-v8a libs MUST work on 16 KiB page systems.
        # The known original ML Kit 32bit exception remains unchanged.
        assert min_align>=16384 or n.startswith('lib/armeabi-v7a/'),(n,min_align)
        elf[n]=min_align
    finally:temp.unlink(missing_ok=True)
# No new native libraries are permitted: the accepted 2.99 runtime is preserved.
subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),
                        '--ks-key-alias','key0','--ks-pass','pass:photoncamera',
                        '--key-pass','pass:photoncamera',
                        '--out',str(final),str(aligned)],check=True)
subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
sig=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
assert certificate in sig and 'Verified using v2 scheme (APK Signature Scheme v2): true' in sig
badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
for m in ("name='com.m9project.m9cam.photon'",
          "versionCode='27304'","versionName='3.04-focuscontrol1a'"):
    assert m in badging,m
for profile in ('m9','monochrom'):
    menu=subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file',
        'res/xml/preferences_'+profile+'.xml',str(final)],text=True)
    assert 'pref_focus_subject_pet' in menu and 'pref_focus_subject_eye' in menu and 'pref_focus_subject_pet_eye' in menu and 'pref_focus_area_mode' in menu and 'pref_focus_af_state_feedback' in menu,profile
with zipfile.ZipFile(final) as result:
    assert result.testzip() is None
    actual={n:sha(result.read(n)) for n in result.namelist() if not signing(n)}
    assert actual==expected,'Signed archive content differs from verified build'
    assert all(result.read(n)==payload for n,payload in original_lib.items())
    assert all(result.read(n)==payload for n,payload in original_assets.items())
report=dict(status='PASS',version='3.04-focuscontrol1a',versionCode=27304,
    sha256=sha(final.read_bytes()),bytes=final.stat().st_size,
    parent=accepted,preserved37NativeLibraries=True,preserved301OriginalAssets=True,
    bundledModelSha256=expected_model_sha,newNativeElfAlignments=elf,
    allNewArm64Libs16kAligned=True,signatureMatchesPrior=True,
    bothProfileMenusVerified=True,photoRendererUntouched=True,
    phoneFocusAreaValidationPending=True,halFeedbackPendingPhone=True)
(out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(report['sha256']+'  '+final.name+'\n')
unsigned.unlink();aligned.unlink()
print(json.dumps(report,indent=2))
