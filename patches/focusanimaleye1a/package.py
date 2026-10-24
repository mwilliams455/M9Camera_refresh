#!/usr/bin/env python3
"""Sign 3.02 opt-in AP10K Animal Eye AF over exact accepted 3.01 native/asset base.

Fail closed if any previously accepted camera native library or photographic
asset changes, model SHA differs, new ARM64 ELF alignment is not 16 KiB,
the two profile settings are missing or the app signing certificate changes.
"""
from pathlib import Path
import copy,hashlib,json,re,subprocess,sys,zipfile

root,built,oldapk,bt,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
accepted='17b397681fb4e59145cd77da42128959646a048fec4003a60a7638691f200f0c'
cert_sha='255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956'
assert sha(oldapk.read_bytes())==accepted,'Unexpected 3.01 signed parent'
assert built.is_file() and (root/'key/PcamLeak.jks').is_file()
scope=json.loads((out/'SOURCE_VERIFICATION.json').read_text())
assert scope['status']=='STAGED_FOR_BUILD' and scope['parent']=='3.01-focusanimal1c'
assert scope['animalEyeSwitchDefaultOff'] and scope['bodyFocusFallbackRetained']
assert scope['m9MonochromRendererUnchanged'] and scope['humanEyeAfUnchanged']
pose=root/'app/src/main/assets/rtm_animal_fp16.tflite'
expected_pose_sha=scope['newModelSha256']
assert sha(pose.read_bytes())==expected_pose_sha,'AP10K model mismatch'
assert len(pose.read_bytes())==27526176

def is_signing(n):
    return n=='META-INF/MANIFEST.MF' or n.startswith('META-INF/') and n.endswith(
       ('.RSA','.DSA','.EC','.SF'))
signer=['java','-jar',str(bt/'lib/apksigner.jar')]
old_cert=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(oldapk)],text=True)
assert cert_sha in old_cert and 'Verified using v2 scheme (APK Signature Scheme v2): true' in old_cert

unsigned=out/'unsigned.apk'
aligned=out/'aligned.apk'
final=out/'M9Cam_3.02_ANIMALEYE1A.apk'
expect={}
new_native={}
new_assets={}
with zipfile.ZipFile(oldapk) as old,zipfile.ZipFile(built) as new,zipfile.ZipFile(unsigned,'w') as dst:
    assert old.testzip() is None and new.testzip() is None
    native={n:old.read(n) for n in old.namelist()
            if n.startswith('lib/') and n.endswith('.so')}
    assert len(native)==31,len(native)
    assets={n:old.read(n) for n in old.namelist()
            if n.startswith('assets/') and not n.endswith('/')}
    assert len(assets)==300,len(assets)
    new_names=set(new.namelist())
    for n,contents in assets.items():
        assert n in new_names and new.read(n)==contents,'Photo asset changed: '+n
    # Gradle's rebuilt native binaries may differ bytewise from the accepted
    # installer because of toolchain/non-deterministic build output. Repackaging
    # must REPLACE those rebuilt copies with exactly the accepted parent bytes,
    # never accept a new photographic library. New LiteRT .so names are separate.
    rebuiltParentChanges=sorted(
        n for n,contents in native.items()
        if n in new_names and new.read(n)!=contents)

    fresh_native={n for n in new_names if n.startswith('lib/')
                  and n.endswith('.so') and n not in native}
    new_native={n:new.read(n) for n in fresh_native}
    assert fresh_native,'LiteRT CompiledModel runtime missing from Android build'
    assert all('litert' in n.lower() for n in fresh_native),sorted(fresh_native)
    assert all(re.fullmatch(r'lib/(?:arm64-v8a|armeabi-v7a)/lib[\w.+-]+\.so',n)
            for n in fresh_native), sorted(fresh_native)
    fresh_assets={n for n in new_names if n.startswith('assets/')
            and not n.endswith('/') and n not in assets}
    new_assets={n:new.read(n) for n in fresh_assets}
    assert set(new_assets)=={'assets/rtm_animal_fp16.tflite'},sorted(new_assets)
    assert sha(new_assets['assets/rtm_animal_fp16.tflite'])==expected_pose_sha

    for info in new.infolist():
        n=info.filename
        if is_signing(n):continue
        contents=native[n] if n in native else new.read(n)
        expect[n]=sha(contents)
        dst.writestr(copy.copy(info),contents)
    for n in sorted(set(native)-new_names):
        payload=native[n]
        expect[n]=sha(payload)
        dst.writestr(copy.copy(old.getinfo(n)),payload)

    dex=b''.join(new.read(n) for n in new_names if n.endswith('.dex'))
    for name in ['AnimalEyePoseEstimator','AnimalEyeTargetPolicy',
                 'pref_focus_subject_pet_eye','Cat Eye AF','Dog Eye AF',
                 'PetPreviewRetryPolicy','PetFocusController',
                 'HumanEyeAdmissionGate','HumanSubjectFocusController',
                 'TrackingFocus','M9DIAGINDEX1A_BOUNDED']:
        assert name.encode() in dex,'Missing Android DEX marker: '+name

elf={}
for n,data in sorted(new_native.items()):
    probe=out/(Path(n).name+'.elf-review')
    probe.write_bytes(data)
    try:
        headers=subprocess.check_output(['readelf','-lW',str(probe)],text=True)
        alignments=[int(line.split()[-1],16) for line in headers.splitlines()
                     if line.strip().startswith('LOAD')]
        assert alignments,'No LOAD segments: '+n
        low=min(alignments)
        assert low>=16384 or n.startswith('lib/armeabi-v7a/'),(n,low)
        elf[n]=low
    finally:probe.unlink(missing_ok=True)
assert any(n.startswith('lib/arm64-v8a/') for n in new_native)

subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',
                str(unsigned),str(aligned)],check=True)
subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),
                       '--ks-key-alias','key0','--ks-pass','pass:photoncamera',
                       '--key-pass','pass:photoncamera',
                       '--out',str(final),str(aligned)],check=True)
subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
cert=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
assert cert_sha in cert and 'Verified using v2 scheme (APK Signature Scheme v2): true' in cert
badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
for token in ("name='com.m9project.m9cam.photon'",
              "versionCode='27302'","versionName='3.02-animaleye1a'"):
    assert token in badging,token
for profile in ('m9','monochrom'):
    menu=subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file',
                      'res/xml/preferences_'+profile+'.xml',str(final)],text=True)
    for token in ['pref_focus_subject_pet','pref_focus_subject_pet_eye',
                  'pref_focus_subject_eye']:
        assert token in menu,(profile,token)
with zipfile.ZipFile(final) as apk:
    assert apk.testzip() is None
    actual={n:sha(apk.read(n)) for n in apk.namelist() if not is_signing(n)}
    assert actual==expect,'Verified signed APK contents changed'
    for n,body in native.items():assert apk.read(n)==body,n
    for n,body in assets.items():assert apk.read(n)==body,n

report=dict(status='PASS',version='3.02-animaleye1a',versionCode=27302,
    sha256=sha(final.read_bytes()),bytes=final.stat().st_size,
    acceptedParentSha256=accepted,
    previous31NativeLibrariesByteIdentical=True,
    previous300AssetsByteIdentical=True,
    rebuiltParentLibrariesReplacedWithAcceptedBytes=rebuiltParentChanges,
    poseModelSha256=expected_pose_sha,
    poseModelBytes=pose.stat().st_size,
    newNativeElfAlignment=elf,allNewArm64Libs16KiB=True,
    signatureMatchesAcceptedCamera=True,bothProfileMenusVerified=True,
    defaultAnimalEyeOff=True,renderersUnchanged=True,phoneValidationPending=True)
(out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(report['sha256']+'  '+final.name+'\n')
unsigned.unlink();aligned.unlink()
print(json.dumps(report,indent=2))
