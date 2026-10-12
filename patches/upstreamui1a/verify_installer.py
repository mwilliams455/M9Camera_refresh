"""Reopen the final package independently before offering it for installation."""
from pathlib import Path
import hashlib, json, subprocess, sys, zipfile

output, tools = (Path(x).resolve() for x in sys.argv[1:])
report = json.loads((output / 'PACKAGED_VERIFICATION.json').read_text())
apk = output / 'M9Cam_2.85_UPSTREAMUI1A.apk'
digest = hashlib.sha256(apk.read_bytes()).hexdigest()
assert digest == report['sha256'] and apk.stat().st_size == report['bytes']
with zipfile.ZipFile(apk) as archive:
    assert archive.testzip() is None
    dex = b''.join(archive.read(n) for n in archive.namelist() if n.endswith('.dex'))
    for marker in [b'ExifBackdropView', b'cancelHistogramRequest', b'exact_neutral_request_with_reported_auto_control', b'MONOAEREF1B', b'MonoAeReference1A', b'exact_neutral_request_with_active_ae', b'MONODIAGVIEW1D', b'MonoReadinessDialog1D', b'Copy details']:
        assert marker in dex, marker
signature = subprocess.check_output(['java', '-jar', str(tools / 'lib/apksigner.jar'),
    'verify', '--verbose', '--print-certs', str(apk)], text=True)
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in signature
badging = subprocess.check_output([str(tools / 'aapt2'), 'dump', 'badging', str(apk)], text=True)
for identity in ["name='com.m9project.m9cam.photon'", "versionCode='27285'", "versionName='2.85-upstreamui1a'"]:
    assert identity in badging
subprocess.run([str(tools / 'zipalign'), '-c', '-P', '16', '4', str(apk)], check=True)
(output / 'SHA256SUMS.txt').write_text(digest + '  ' + apk.name + '\n')
print(json.dumps({'status': 'PASS', 'independentReopen': True, 'bytes': apk.stat().st_size,
    'sha256': digest, 'androidV2SignatureVerified': True, 'archiveVerified': True}))
