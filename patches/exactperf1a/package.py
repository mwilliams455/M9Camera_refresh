#!/usr/bin/env python3
"""Package 3.43 EXACTPERF1A: accepted 3.13 native libraries and assets, except the three
libraries this stage rebuilds (libm9color, libm9dngnoise, libdngCreator for both ABIs).

Usage: package.py SOURCE BUILT_APK BASELINE_DIR BUILD_TOOLS OUTPUT_DIR
OUTPUT_DIR must already hold SOURCE_VERIFICATION.json (the exactperf1a stage report) and a
passing NATIVE_PROVENANCE.json from native_provenance.py.
"""
from pathlib import Path
import copy, hashlib, json, subprocess, sys, tarfile, zipfile

root, built, baseline_dir, bt, out = (Path(s).resolve() for s in sys.argv[1:6])
here = Path(__file__).resolve().parent
patches = here.parent
sha = lambda data: hashlib.sha256(data).hexdigest()
certificate = '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956'
version, code, filename = '3.43-exactperf1a', 27343, 'M9Cam_3.43_EXACTPERF1A.apk'
rebuilt_libs = ('libm9color.so', 'libm9dngnoise.so', 'libdngCreator.so')

provenance = json.loads((out / 'NATIVE_PROVENANCE.json').read_text())
assert provenance['status'] == 'PASS', 'Native provenance gate has not passed'
scope = json.loads((out / 'SOURCE_VERIFICATION.json').read_text())
assert scope['status'] == 'STAGED_FOR_ANDROID_BUILD' and scope['version'] == version
assert scope['parent'] == '3.42-facehighlight1b'
assert scope['sourceHashes'] == json.loads((here / 'source-hashes.json').read_text())
for path, hashes in scope['sourceHashes'].items():
    file = root / path
    if hashes['after'] is None:
        assert not file.exists(), path
    else:
        assert sha(file.read_bytes()) == hashes['after'], path
assert built.is_file() and (root / 'key/PcamLeak.jks').is_file()

manifest = json.loads((baseline_dir / 'sha256.json').read_text())
native_names = {n for n in manifest if n.startswith('lib/')}
asset_names = {n for n in manifest if n.startswith('assets/')}
assert len(native_names) == 37 and len(asset_names) == 301
rebuilt = {f'lib/{abi}/{lib}' for abi in ('arm64-v8a', 'armeabi-v7a') for lib in rebuilt_libs}
assert rebuilt <= native_names
native_overrides = {}
for abi in ('arm64-v8a', 'armeabi-v7a'):
    with tarfile.open(baseline_dir / (abi + '.tar.xz'), 'r:xz') as archive:
        for member in archive:
            assert member.isfile() and member.name in native_names
            payload = archive.extractfile(member).read()
            assert sha(payload) == manifest[member.name], member.name
            if member.name not in rebuilt:
                native_overrides[member.name] = payload
model = root / 'app/src/main/assets/rtm_animal_fp16.tflite'
expected_model = (patches / 'focusanimaleye1a/MODEL_SHA256.txt').read_text().split()[0]
assert sha(model.read_bytes()) == expected_model

signing = lambda n: n == 'META-INF/MANIFEST.MF' or n.startswith('META-INF/') and n.endswith(('.RSA', '.DSA', '.EC', '.SF'))
signer = ['java', '-jar', str(bt / 'lib/apksigner.jar')]
unsigned, aligned, final = out / 'unsigned.apk', out / 'aligned.apk', out / filename
expected, rebuilt_hashes = {}, {}
with zipfile.ZipFile(built) as new, zipfile.ZipFile(unsigned, 'w') as dst:
    assert new.testzip() is None
    new_names = set(new.namelist())
    assert len(new_names) == len(new.infolist()), 'Duplicate APK entries'
    assert rebuilt <= new_names, 'Gradle APK lacks a rebuilt library'
    extra_assets = {'assets/face_detection_yunet.onnx', 'assets/YUNET_LICENSE.txt'}
    scene_assets = {'assets/person_head.onnx', 'assets/PERSON_HEAD_MODEL.md'}
    species_assets = {'assets/pet_species_mobilenet_v2.tflite', 'assets/PET_SPECIES_LICENSE.txt', 'assets/PET_SPECIES_MODEL.md'}
    for stage, names in (('headpair1a', extra_assets), ('headcontinuity1a', scene_assets), ('petlabel1a', species_assets)):
        hashes = json.loads((patches / stage / 'source-hashes.json').read_text())
        for name in names:
            assert sha(new.read(name)) == hashes['app/src/main/' + name]['after'], name
    # A non-debuggable variant also packages the AndroidX ART baseline profile. It lets
    # Android precompile hot library code at install; it contains no app resources.
    profile_assets = {'assets/dexopt/baseline.prof', 'assets/dexopt/baseline.profm'}
    actual_assets = {n for n in new_names if n.startswith('assets/') and not n.endswith('/')}
    required_assets = asset_names | extra_assets | scene_assets | species_assets
    unexpected, missing = actual_assets - required_assets - profile_assets, required_assets - actual_assets
    assert not unexpected and not missing, f'Asset set changed: unexpected={sorted(unexpected)} missing={sorted(missing)}'
    packaged_profile_assets = sorted(actual_assets & profile_assets)
    assert {n for n in new_names if n.startswith('lib/') and n.endswith('.so')} <= native_names
    for info in new.infolist():
        name = info.filename
        if signing(name):
            continue
        payload = native_overrides[name] if name in native_overrides else new.read(name)
        expected[name] = sha(payload)
        if name in rebuilt:
            rebuilt_hashes[name] = expected[name]
            assert expected[name] == provenance['rebuiltCandidateSha256'][name], name
        dst.writestr(copy.copy(info), payload)
    for name in sorted(native_names - new_names):
        assert name not in rebuilt
        payload = native_overrides[name]
        expected[name] = sha(payload)
        dst.writestr(zipfile.ZipInfo(name), payload, compress_type=zipfile.ZIP_STORED)
    for name, digest in manifest.items():
        if name in rebuilt:
            assert expected.get(name) not in (None, digest), f'Rebuilt library unchanged: {name}'
        else:
            assert expected.get(name) == digest, f'Accepted APK payload changed: {name}'
    dex = b''.join(new.read(n) for n in new_names if n.endswith('.dex'))
    for marker in ['M9ShadingParallel1A', 'M9EXACTPERF1A_SHADING_ROWBANDS_EXACT', 'saveSingleRawM9PhysicalCfaStaged',
                   'embedInPlace', 'embedStaged', 'StagingNotRestoredException', 'publishStagedDng',
                   'M9PHASENOISEPERF1D_DYNAMIC_EXACT', 'dynamic_tiles_chunk1', 'AutomaticSubjectSelection',
                   'SubjectAnchorPolicy', 'HumanSubjectFocusController', 'PetFocusController',
                   'M9DIAGINDEX1A_BOUNDED', 'M9DngProfileWriter']:
        assert marker.encode() in dex, marker

subprocess.run([str(bt / 'zipalign'), '-f', '-P', '16', '4', str(unsigned), str(aligned)], check=True)
subprocess.run(signer + ['sign', '--ks', str(root / 'key/PcamLeak.jks'), '--ks-key-alias', 'key0',
                         '--ks-pass', 'pass:photoncamera', '--key-pass', 'pass:photoncamera',
                         '--out', str(final), str(aligned)], check=True)
subprocess.run([str(bt / 'zipalign'), '-c', '-P', '16', '4', str(final)], check=True)
cert = subprocess.check_output(signer + ['verify', '--verbose', '--print-certs', str(final)], text=True)
assert certificate in cert and 'Verified using v2 scheme (APK Signature Scheme v2): true' in cert
badging = subprocess.check_output([str(bt / 'aapt2'), 'dump', 'badging', str(final)], text=True)
for required in ("name='com.m9project.m9cam.photon'", f"versionCode='{code}'", f"versionName='{version}'"):
    assert required in badging, required
assert 'application-debuggable' not in badging, 'EXACTPERF1A installer must not be debuggable'
for profile in ('m9', 'monochrom'):
    menu = subprocess.check_output([str(bt / 'aapt2'), 'dump', 'xmltree', '--file',
                                    'res/xml/preferences_' + profile + '.xml', str(final)], text=True)
    for marker in ('pref_focus_tracking', 'pref_focus_tracking_semantic', 'pref_focus_tracking_predictive',
                   'pref_focus_tracking_identity', 'pref_focus_auto_eye_enabled', 'pref_focus_subject_pet',
                   'pref_export_tracking_trace'):
        assert marker in menu, (profile, marker)
with zipfile.ZipFile(final) as signed:
    assert signed.testzip() is None
    actual = {n: sha(signed.read(n)) for n in signed.namelist() if not signing(n)}
    assert actual == expected, 'Signed APK contents differ from validated build'
    for name in sorted(rebuilt):
        lib = out / name.replace('/', '_')
        lib.write_bytes(signed.read(name))
        for line in subprocess.check_output(['readelf', '-lW', str(lib)], text=True).splitlines():
            if line.strip().startswith('LOAD'):
                assert int(line.split()[-1], 16) >= 16384, (name, line)
        assert 'libomp.so' not in subprocess.check_output(['readelf', '-dW', str(lib)], text=True), name
        symbols = subprocess.check_output(['readelf', '--dyn-syms', '--wide', str(lib)], text=True)
        marker = {'libm9color.so': 'phase_noise_symtile_adaptive_exact',
                  'libm9dngnoise.so': 'phone_noise_shaded_parallel',
                  'libdngCreator.so': 'Java_com_particlesdevs_photoncamera_processing_DngCreator_createDNG'}[Path(name).name]
        assert marker in symbols, (name, marker)
        lib.unlink()
report = dict(status='PASS', version=version, versionCode=code, sha256=sha(final.read_bytes()),
              bytes=final.stat().st_size, parent='3.42-facehighlight1b',
              rebuiltNativeLibraries=rebuilt_hashes,
              otherNativeLibrariesByteIdenticalTo313=sorted(native_names - rebuilt),
              preserved301OriginalAssets=True, bundledModelSha256=expected_model,
              artBaselineProfileAssets=packaged_profile_assets,
              applicationDebuggable=False, signatureMatchesPrior=True, sixteenKiBAligned=True,
              bothProfileMenusVerified=True, nativeProvenance='PASS',
              phoneTimingAndVisualValidationPending=True)
(out / 'PACKAGED_VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'SHA256SUMS.txt').write_text(report['sha256'] + '  ' + final.name + '\n')
unsigned.unlink(); aligned.unlink()
print(json.dumps(report, indent=2))
