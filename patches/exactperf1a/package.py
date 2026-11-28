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
scope = json.loads((out / 'SOURCE_VERIFICATION.json').read_text())
integrated = scope['version'] in ('3.45-performance', '3.46-jpegperf', '3.47-jpegperf', '3.48-jpegstore', '3.49-jpegperf',
                                  '3.50-amazesimd', '3.51-centremeter', '3.52-settlemeter')
settle352 = scope['version'] == '3.52-settlemeter'
centre351 = settle352 or scope['version'] == '3.51-centremeter'
amaze350 = centre351 or scope['version'] == '3.50-amazesimd'
jpeg349 = amaze350 or scope['version'] == '3.49-jpegperf'
jpeg348 = jpeg349 or scope['version'] == '3.48-jpegstore'
jpeg347 = jpeg348 or scope['version'] == '3.47-jpegperf'
jpegperf = jpeg347 or scope['version'] == '3.46-jpegperf'
if settle352:
    version, code, filename = '3.52-settlemeter', 27352, 'M9Cam_3.52_SETTLEMETER.apk'
    stage, parent = patches / 'settlemeter352', '3.51-centremeter'
elif centre351:
    version, code, filename = '3.51-centremeter', 27351, 'M9Cam_3.51_CENTREMETER.apk'
    stage, parent = patches / 'centremeter351', '3.50-amazesimd'
elif amaze350:
    version, code, filename = '3.50-amazesimd', 27350, 'M9Cam_3.50_AMAZESIMD.apk'
    stage, parent = patches / 'amazesimd350', '3.49-jpegperf'
elif jpeg349:
    version, code, filename = '3.49-jpegperf', 27349, 'M9Cam_3.49_JPEGPERF.apk'
    stage, parent = patches / 'jpegperf349', '3.48-jpegstore'
elif jpeg348:
    version, code, filename = '3.48-jpegstore', 27348, 'M9Cam_3.48_JPEGSTORE.apk'
    stage, parent = patches / 'jpegstore348', '3.47-jpegperf'
elif jpeg347:
    version, code, filename = '3.47-jpegperf', 27347, 'M9Cam_3.47_JPEGPERF.apk'
    stage, parent = patches / 'jpegperf347', '3.46-jpegperf'
elif jpegperf:
    version, code, filename = '3.46-jpegperf', 27346, 'M9Cam_3.46_JPEGPERF.apk'
    stage, parent = patches / 'jpegperf346', '3.45-performance'
elif integrated:
    version, code, filename = '3.45-performance', 27345, 'M9Cam_3.45_Performance.apk'
    stage, parent = patches / 'performance345', '3.44-lensfalloff'
else:
    version, code, filename = '3.43-exactperf1a', 27343, 'M9Cam_3.43_EXACTPERF1A.apk'
    stage, parent = here, '3.42-facehighlight1b'
rebuilt_libs = ('libm9color.so', 'libm9dngnoise.so', 'libdngCreator.so')

provenance = json.loads((out / 'NATIVE_PROVENANCE.json').read_text())
assert provenance['status'] == 'PASS', 'Native provenance gate has not passed'
assert scope['status'] == 'STAGED_FOR_ANDROID_BUILD' and scope['version'] == version
assert scope['parent'] == parent
assert scope['sourceHashes'] == json.loads((stage / 'source-hashes.json').read_text())
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
    preview_shader = 'assets/shaders/preview/main_fs.glsl'
    if integrated:
        # The released 3.44 shader is the only optical asset changed since the native baseline.
        assert expected[preview_shader] == sha((root / 'app/src/main' / preview_shader).read_bytes())
        assert expected[preview_shader] == '40f0123d6cf5a00df07ef4c06154cdd0429d639d43b09286148c298c0dd79231'
    for name, digest in manifest.items():
        if name in rebuilt:
            assert expected.get(name) not in (None, digest), f'Rebuilt library unchanged: {name}'
        elif not (integrated and name == preview_shader):
            assert expected.get(name) == digest, f'Accepted APK payload changed: {name}'
    dex = b''.join(new.read(n) for n in new_names if n.endswith('.dex'))
    if integrated:
        for marker in ('M9DngPublication', 'M9SubjectMeterFrames', 'M9TungstenGuardSettings', 'M9TargetFalloff1A'):
            assert marker.encode() in dex, marker
    if jpegperf:
        for marker in ('M9JPEGPERF346_GATE_ROWBANDS_EXACT', 'M9JpegOverlap346', 'jpegOverlapMode',
                       'JPEGPERF346_dynamic_rows', ('JPEGPERF349_bounded_rows_work_queue_42_row_floor' if jpeg349 else 'JPEGPERF347_bounded_rows_work_queue' if jpeg347 else 'JPEGPERF346_up_to_64_preloaded_bands_work_queue'),
                       '.jpegperf346', 'postRenderDiagnosticsElapsedMs'):
            assert marker.encode() in dex, marker
    if jpeg347:
        for marker in ('M9PendingJpeg', 'edgeGridSkippedForLockedExposure', 'JPEG encoder returned false'):
            assert marker.encode() in dex, marker
    if jpeg348:
        assert b'Unable to reserve JPEG in MediaStore' in dex
    if amaze350:
        for marker in ('M9AMAZESIMD350', 'amazeSimdPath'):
            assert marker.encode() in dex, marker
    if centre351:
        for marker in ('M9STEADYGATE351', 'M9CENTREMETER351', 'pref_m9_centre_metering', 'centreMetering351'):
            assert marker.encode() in dex, marker
    if settle352:
        for marker in ('M9SETTLEMETER352', 'pref_m9_settle_meter', 'settleMeter352', 'refreshing_while_moving'):
            assert marker.encode() in dex, marker
    if jpeg349:
        for marker in ('M9JPEGPERF349_UNSYNCHRONIZED_64K_READER', 'JPEGPERF349_jpeg_encode_thread',
                       'mediaStoreReserveElapsedMs', 'indexedByMediaStore'):
            assert marker.encode() in dex, marker
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
# Non-debuggable variants shorten resource file paths inside the APK (AGP resource
# optimization). The app addresses resources by ID, so resolve each menu's packaged
# file from the resource table instead of assuming res/xml/<name>.xml.
resource_table = subprocess.check_output([str(bt / 'aapt2'), 'dump', 'resources', str(final)], text=True).splitlines()


def resource_file(name):
    for index, line in enumerate(resource_table):
        words = line.split()
        if len(words) >= 3 and words[0] == 'resource' and words[2] == name:
            for entry in resource_table[index + 1:]:
                if entry.split()[:1] == ['resource']:
                    break
                if '(file)' in entry:
                    return entry.split('(file)', 1)[1].split()[0]
    raise AssertionError(f'Resource file not found: {name}')


menu_files = {}
for profile in ('m9', 'monochrom'):
    menu_files[profile] = resource_file('xml/preferences_' + profile)
    menu = subprocess.check_output([str(bt / 'aapt2'), 'dump', 'xmltree', '--file',
                                    menu_files[profile], str(final)], text=True)
    if integrated:
        for control in ('pref_m9_lens_falloff', 'pref_m9_tungsten_guard'):
            assert (control in menu) == (profile == 'm9'), (profile, control)
    if centre351:
        assert ('pref_m9_centre_metering' in menu) == (profile == 'm9'), (profile, 'pref_m9_centre_metering')
    if settle352:
        assert ('pref_m9_settle_meter' in menu) == (profile == 'm9'), (profile, 'pref_m9_settle_meter')
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
        if amaze350 and Path(name).name == 'libm9color.so':
            # The phone's arm64 library carries the vector AMaZE; 32-bit ARM keeps the scalar path.
            assert 'm9_amaze_simd_path' in symbols, name
            vector = b'M9AMAZESIMD350_PORTABLE_VECTOR' in lib.read_bytes()
            assert vector == ('arm64-v8a' in name), (name, vector)
        lib.unlink()
report = dict(status='PASS', version=version, versionCode=code, sha256=sha(final.read_bytes()),
              bytes=final.stat().st_size, parent=parent,
              rebuiltNativeLibraries=rebuilt_hashes,
              otherNativeLibrariesByteIdenticalTo313=sorted(native_names - rebuilt),
              preserved301OriginalAssets=not integrated, bundledModelSha256=expected_model,
              artBaselineProfileAssets=packaged_profile_assets,
              applicationDebuggable=False, signatureMatchesPrior=True, sixteenKiBAligned=True,
              bothProfileMenusVerified=True, packagedMenuFiles=menu_files, nativeProvenance='PASS',
              phoneTimingAndVisualValidationPending=True)
if integrated:
    report['released344ShaderSha256'] = expected[preview_shader]
if amaze350:
    report['amazePathByAbi'] = {'arm64-v8a': 'M9AMAZESIMD350_PORTABLE_VECTOR', 'armeabi-v7a': 'SCALAR'}
if jpeg347:
    report['nativeSourceChangesSince346'] = ['libm9color.so']
elif jpegperf:
    report['nativeSourceChangesSince345'] = ['libm9color.so']
(out / 'PACKAGED_VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'SHA256SUMS.txt').write_text(report['sha256'] + '  ' + final.name + '\n')
unsigned.unlink(); aligned.unlink()
print(json.dumps(report, indent=2))
