"""Restore the exact verified, signed APK from the pinned CI artifact and binary delta."""
from pathlib import Path
import gzip, hashlib, io, json, struct, subprocess, sys, zipfile, zlib

here = Path(__file__).resolve().parent
artifact, destination = map(lambda p: Path(p).resolve(), sys.argv[1:])
m = json.loads((here / 'manifest.json').read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
source = (artifact / m['sourceFile']).read_bytes()
assert sha(source) == m['sourceSha256'], 'Wrong source APK'
delta = (here / 'installer.delta.gz').read_bytes()
assert sha(delta) == m['deltaSha256'], 'Wrong delivery delta'
stream = io.BytesIO(gzip.decompress(delta))
assert stream.read(12) == b'M9APKDELTA1\n'
parts = []
source_zip = zipfile.ZipFile(io.BytesIO(source))
while kind := stream.read(1):
    if kind == b'C':
        offset, size = struct.unpack('<QQ', stream.read(16))
        assert offset + size <= len(source)
        parts.append(source[offset:offset + size])
    elif kind == b'L':
        size, = struct.unpack('<Q', stream.read(8))
        data = stream.read(size)
        assert len(data) == size
        parts.append(data)
    elif kind == b'R':
        name_size, method = struct.unpack('<HH', stream.read(4))
        raw = source_zip.read(stream.read(name_size).decode())
        if method == 8:
            compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
            raw = compressor.compress(raw) + compressor.flush()
        else:
            assert method == 0
        parts.append(raw)
    else:
        raise ValueError('Invalid delta operation')
source_zip.close()
installer = b''.join(parts)
assert len(installer) == m['installerBytes']
assert sha(installer) == m['installerSha256'], 'Installer differs from verified package'
destination.mkdir(parents=True, exist_ok=True)
apk = destination / m['installerFile']
apk.write_bytes(installer)
with zipfile.ZipFile(apk) as archive:
    assert archive.testzip() is None
    dex = b''.join(archive.read(n) for n in archive.namelist() if n.endswith('.dex'))
    assert b'MONODIAGEXPORT1C' in dex and b'previousExposureReadinessFailure' in dex
tools = artifact / 'packaging-tools'
for name in ['aapt2', 'zipalign']:
    (tools / name).chmod(0o755)
cert = subprocess.check_output(['java', '-jar', str(tools / 'lib/apksigner.jar'),
    'verify', '--verbose', '--print-certs', str(apk)], text=True)
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in cert
assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in cert
badging = subprocess.check_output([str(tools / 'aapt2'), 'dump', 'badging', str(apk)], text=True)
for value in ["name='com.m9project.m9cam.photon'", "versionCode='27281'", "versionName='2.81-monodiagexport1c'"]:
    assert value in badging
subprocess.run([str(tools / 'zipalign'), '-c', '-P', '16', '4', str(apk)], check=True)
(destination / 'SHA256SUMS.txt').write_text(m['installerSha256'] + '  ' + apk.name + '\n')
print(json.dumps({'status': 'PASS', 'installer': apk.name, 'bytes': len(installer),
    'sha256': sha(installer), 'signatureVerified': True, 'archiveVerified': True}))
