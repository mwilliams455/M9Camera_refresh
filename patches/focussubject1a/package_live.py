#!/usr/bin/env python3
"""Package opt-in 2.97 Face/Eye AF over the exact accepted 2.95 M9/Monochrom APK.

Preserve every original lib and asset byte-for-byte. Add bundled detector
libraries/models from the verified Gradle output when present. Fail closed on
signature, native alignment, version, menu or source-scope surprises.
"""
from pathlib import Path
import copy
import hashlib
import json
import re
import subprocess
import sys
import zipfile

root,built,control,bt,out=map(lambda x:Path(x).resolve(),sys.argv[1:])
out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
accepted='e305c046a425ab79e89727045c53e414b5578873d333cbfe91dc5be33ac5c45c'
cert_sha='255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956'
assert sha(control.read_bytes())==accepted,'Wrong 2.95 accepted parent; refuse repackaging'
assert built.is_file() and root.is_dir() and (root/'key/PcamLeak.jks').is_file()
def old_signature(n):
    return n=='META-INF/MANIFEST.MF' or n.startswith('META-INF/') and n.endswith(('.RSA','.DSA','.EC','.SF'))

scope=json.loads((out/'SOURCE_VERIFICATION.json').read_text())
assert scope['status']=='STAGED_FOR_ANDROID_BUILD' and scope['parent']=='2.95-diagindex1a'
assert scope['renderExposureRawNativeModified'] is False and scope['default']=='off'
required={
 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/CameraFragment.java',
 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/FocusTrackingController.java',
 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/HumanSubjectFocusController.java',
 'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/HumanFaceLandmarkDetector.java',
 'app/src/main/java/com/particlesdevs/photoncamera/control/subject/SubjectFocusPolicy.java',
 'app/src/main/java/com/particlesdevs/photoncamera/control/subject/FocusAreaPolicy.java',
 'app/src/main/java/com/particlesdevs/photoncamera/settings/PreferenceKeys.java',
 'app/src/main/res/xml/preferences_m9.xml',
 'app/src/main/res/xml/preferences_monochrom.xml',
 'app/src/main/res/values/strings.xml',
 'app/build.gradle'
}
assert set(scope['changedFiles'])==required,scope['changedFiles']

signer=['java','-jar',str(bt/'lib/apksigner.jar')]
orig_sig=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(control)],text=True)
assert cert_sha in orig_sig and 'Verified using v2 scheme (APK Signature Scheme v2): true' in orig_sig
old_badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(control)],text=True)
assert "versionCode='27295'" in old_badging and "name='com.m9project.m9cam.photon'" in old_badging

unsigned=out/'unsigned.apk'
aligned=out/'aligned.apk'
final=out/'M9Cam_2.97_FOCUSSUBJECT1A.apk'
expected={}
added_native=set()
added_assets=set()
natives=set()
oldnative={}
with zipfile.ZipFile(control) as old, zipfile.ZipFile(built) as new, zipfile.ZipFile(unsigned,'w') as dst:
    assert old.testzip() is None and new.testzip() is None
    natives={n for n in old.namelist() if n.startswith('lib/') and n.endswith('.so')}
    assert len(natives)==27,len(natives)
    oldnative={n:old.read(n) for n in natives}
    newnames=set(new.namelist())
    extra_native={n for n in newnames if n.startswith('lib/') and n.endswith('.so')}-natives
    for n in extra_native:
        assert re.match(r'^lib/(arm64-v8a|armeabi-v7a)/lib[A-Za-z0-9_+.-]+\.so$',n),n
    added_native=extra_native
    old_assets={n for n in old.namelist() if n.startswith('assets/') and not n.endswith('/')}
    assert len(old_assets)==285,len(old_assets)
    for n in old_assets:
        assert n in newnames and new.read(n)==old.read(n),f'Unexpected original asset modification: {n}'
    added_assets={n for n in newnames if n.startswith('assets/') and not n.endswith('/')}-old_assets

    for info in new.infolist():
        n=info.filename
        if old_signature(n):continue
        contents=oldnative[n] if n in natives else new.read(n)
        expected[n]=sha(contents)
        dst.writestr(copy.copy(info),contents)
    for n in sorted(natives-newnames):
        data=oldnative[n]
        expected[n]=sha(data)
        dst.writestr(copy.copy(old.getinfo(n)),data)
    # Ensure only the requested live focus and preserved inherited camera code
    # are present. New model packaging is retained; original native bits frozen.
    dex=b''.join(new.read(n) for n in newnames if n.endswith('.dex'))
    for token in [
        'HumanSubjectFocusController','HumanFaceLandmarkDetector',
        'pref_focus_subject_eye','SubjectFocusPolicy','TrackingFocus',
        'com/google/mlkit/vision/face','FaceDetectorOptions','M9DIAGINDEX1A_BOUNDED',
        'MONOAEREF1B','MONODIAGVIEW1D','AFTAPHANDOVER1A'
    ]:
        assert token.encode() in dex,f'Missing DEX symbol: {token}'
    assert b'M9 processing queue full - try again shortly' not in dex

# Check any newly introduced model-native libraries for modern 16 KiB devices.
for n in sorted(added_native):
    with zipfile.ZipFile(unsigned) as apk:
        data=apk.read(n)
    disk=out/(Path(n).name+'.elf-check')
    disk.write_bytes(data)
    try:
        headers=subprocess.check_output(['readelf','-lW',str(disk)],text=True)
        for line in headers.splitlines():
            if line.strip().startswith('LOAD'):
                assert int(line.split()[-1],16)>=16384,(n,line)
    finally:disk.unlink(missing_ok=True)

subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),
                        '--ks-key-alias','key0','--ks-pass','pass:photoncamera',
                        '--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
signed=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
assert cert_sha in signed and 'Verified using v2 scheme (APK Signature Scheme v2): true' in signed
badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
for token in ["name='com.m9project.m9cam.photon'",
              "versionCode='27297'","versionName='2.97-focussubject1a'"]:
    assert token in badging,token
for profile in ['m9','monochrom']:
    xml=subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file',
                                'res/xml/preferences_'+profile+'.xml',str(final)],text=True)
    assert 'pref_focus_subject_eye' in xml and 'pref_focus_tracking' in xml,profile
with zipfile.ZipFile(final) as apk:
    assert apk.testzip() is None
    found={n:sha(apk.read(n)) for n in apk.namelist() if not old_signature(n)}
    assert found==expected,'Final APK differs from independently assembled payload'
    assert all(apk.read(n)==oldnative[n] for n in natives)
report={
 'status':'PASS','version':'2.97-focussubject1a','versionCode':27297,
 'sha256':sha(final.read_bytes()),'bytes':final.stat().st_size,
 'acceptedParentVersion':'2.95-diagindex1a','acceptedParentSha256':accepted,
 'acceptedCertificateMatched':True,'all27PreviousNativeLibrariesIdentical':True,
 'all285PreviousAssetsIdentical':True,
 'modelNativeLibrariesAdded':sorted(added_native),'modelAssetsAdded':sorted(added_assets),
 'bothCompiledFocusMenusVerified':True,'androidV2SignatureVerified':True,
 'zipAlignment16KiB':True,'phoneValidationPending':True,
 'photographicRenderingUnchangedFrom295':True
}
(out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(report['sha256']+'  '+final.name+'\n')
unsigned.unlink();aligned.unlink()
print(json.dumps(report,indent=2))
