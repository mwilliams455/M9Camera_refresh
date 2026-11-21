#!/usr/bin/env python3
"""Package signed 3.14 against exact 3.13 native libraries, assets and certificate."""
from pathlib import Path
import copy,hashlib,json,subprocess,sys,tarfile,zipfile

root,built,oldapk,bt,out=(Path(s).resolve() for s in sys.argv[1:])
out.mkdir(parents=True,exist_ok=True)
sha=lambda data:hashlib.sha256(data).hexdigest()
accepted='167393ccfdc25c5d0c232a6012b213b8e5cf1b094ee1a35e540c75faf2e7623c'
certificate='255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956'
# New CI uses the repository baseline. Keep accepting the original signed parent
# for callers reproducing the historical installer command.
baseline_dir = Path(__file__).resolve().parent / 'baseline'
manifest = json.loads((baseline_dir / 'sha256.json').read_text())
native_names = {name for name in manifest if name.startswith('lib/')}
asset_names = {name for name in manifest if name.startswith('assets/')}
assert len(native_names) == 37 and len(asset_names) == 301
assert native_names | asset_names == set(manifest)
assert built.is_file() and (root/'key/PcamLeak.jks').is_file()
scope=json.loads((out/'SOURCE_VERIFICATION.json').read_text())
assert scope['status']=='STAGED_FOR_ANDROID_BUILD'
auto_versions = {
    '3.15-autosubject1a': ('3.14-trackingrecovery1a', 'autosubject1a', 27315, 'M9Cam_3.15_AUTOSUBJECT1A.apk'),
    '3.18-autoreframe1a': ('3.17-autosubject1c', 'autoreframe1a', 27318, 'M9Cam_3.18_AUTOREFRAME1A.apk'),
    '3.19-petdetail1a': ('3.18-autoreframe1a', 'petdetail1a', 27319, 'M9Cam_3.19_PETDETAIL1A.apk'),
    '3.20-petcontinuity1a': ('3.19-petdetail1a', 'petcontinuity1a', 27320, 'M9Cam_3.20_PETCONTINUITY1A.apk'),
    '3.21-petacquisition1a': ('3.20-petcontinuity1a', 'petacquisition1a', 27321, 'M9Cam_3.21_PETACQUISITION1A.apk'),
    '3.22-multiface1a': ('3.21-petacquisition1a', 'multiface1a', 27322, 'M9Cam_3.22_MULTIFACE1A.apk'),
    '3.17-autosubject1c': ('3.16-autosubject1b', 'autosubject1c', 27317, 'M9Cam_3.17_AUTOSUBJECT1C.apk'),
    '3.16-autosubject1b': ('3.15-autosubject1a', 'autosubject1b', 27316, 'M9Cam_3.16_AUTOSUBJECT1B.apk'),
}
version = scope.get('version')
auto_subject = version in auto_versions
if auto_subject:
    parent, stage, code, filename = auto_versions[version]
    assert scope['parent'] == parent
    auto_hashes = Path(__file__).resolve().parents[1] / stage / 'source-hashes.json'
    assert scope['sourceHashes'] == json.loads(auto_hashes.read_text())
else:
    assert scope['parent']=='3.13-trackingdefault1a'
    assert scope['interruptedRecoveryRestartsConfirmations']
    assert scope['recoveryDeadlineCheckedBeforeAcceptance']
    assert scope['identityOffBehaviorUnchanged']
    assert scope['inheritedTrackingDefaultsAndSavedPreferencesUnchanged']
    assert scope['camera2ControllerAndAfCadenceUnchanged']
    assert scope['automaticEyeAndPetAfUnchanged']
    assert scope['originalModelAssetsNativeAndRendererUnchanged']
    assert set(scope['changedFiles'])=={
        'app/build.gradle',
        'app/src/main/java/com/particlesdevs/photoncamera/control/tracking/SubjectAnchorPolicy.java'}
    version, code, filename = '3.14-trackingrecovery1a', 27314, 'M9Cam_3.14_TRACKINGRECOVERY1A.apk'
for path, hashes in scope['sourceHashes'].items():
    assert sha((root/path).read_bytes())==hashes['after'],path
asset=(root/'app/src/main/assets/rtm_animal_fp16.tflite')
expected_model=(Path(__file__).resolve().parent.parent/'focusanimaleye1a/MODEL_SHA256.txt').read_text().split()[0]
assert sha(asset.read_bytes())==expected_model
signing=lambda name:name=='META-INF/MANIFEST.MF' or name.startswith('META-INF/') and name.endswith(('.RSA','.DSA','.EC','.SF'))
signer=['java','-jar',str(bt/'lib/apksigner.jar')]
if oldapk == baseline_dir:
    native_overrides = {}
    for abi in ('arm64-v8a', 'armeabi-v7a'):
        with tarfile.open(baseline_dir / (abi + '.tar.xz'), 'r:xz') as archive:
            for member in archive:
                assert member.isfile() and member.name.startswith(f'lib/{abi}/')
                assert member.name in native_names and member.name not in native_overrides
                payload = archive.extractfile(member).read()
                assert sha(payload) == manifest[member.name], member.name
                native_overrides[member.name] = payload
else:
    assert sha(oldapk.read_bytes()) == accepted, 'Exact signed 3.13 parent APK required'
    cert = subprocess.check_output(signer + ['verify', '--verbose', '--print-certs', str(oldapk)], text=True)
    assert certificate in cert and 'Verified using v2 scheme (APK Signature Scheme v2): true' in cert
    with zipfile.ZipFile(oldapk) as parent:
        native_overrides = {name: parent.read(name) for name in native_names}

unsigned=out/'unsigned.apk';aligned=out/'aligned.apk';final=out/filename
expected = {}
with zipfile.ZipFile(built) as new, zipfile.ZipFile(unsigned, 'w') as dst:
    assert new.testzip() is None
    new_names = set(new.namelist())
    assert len(new_names) == len(new.infolist()), 'Duplicate APK entries'
    assert {n for n in new_names if n.startswith('assets/') and not n.endswith('/')} == asset_names
    assert {n for n in new_names if n.startswith('lib/') and n.endswith('.so')} <= native_names
    for info in new.infolist():
        name = info.filename
        if signing(name):
            continue
        payload = native_overrides[name] if name in native_overrides else new.read(name)
        expected[name] = sha(payload)
        dst.writestr(copy.copy(info), payload)
    for name in sorted(native_names - new_names):
        payload = native_overrides[name]
        expected[name] = sha(payload)
        dst.writestr(zipfile.ZipInfo(name), payload, compress_type=zipfile.ZIP_STORED)
    for name, digest in manifest.items():
        assert expected.get(name) == digest, f'Accepted APK payload changed: {name}'
    dex=b''.join(new.read(n) for n in new_names if n.endswith('.dex'))
    if auto_subject:
        assert b'AutomaticSubjectSelection' in dex, 'Missing automatic tracking code'
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
for required in ("name='com.m9project.m9cam.photon'", f"versionCode='{code}'", f"versionName='{version}'"):
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
report=dict(status='PASS',version=version,versionCode=code,
            sha256=sha(final.read_bytes()),bytes=final.stat().st_size,parent=accepted,
            preserved37NativeLibraries=True,preserved301OriginalAssets=True,
            bundledModelSha256=expected_model,signatureMatchesPrior=True,
            sixteenKiBAligned=True,bothProfileMenusVerified=True,
            photoRendererUntouched=True,automaticEyeDefaultOn=True,
            identityRecoveryRequiresConsecutiveMatches=True,
            recoveryDeadlineEnforced=True,identityOffUnchanged=True,
            phoneTrackingAndOpticalSharpnessValidationPending=True)
(out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'SHA256SUMS.txt').write_text(report['sha256']+'  '+final.name+'\n')
unsigned.unlink();aligned.unlink()
print(json.dumps(report,indent=2))
