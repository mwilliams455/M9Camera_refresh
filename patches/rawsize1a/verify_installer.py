"""Reopen the final package independently before offering it for installation."""
from pathlib import Path
import hashlib, json, re, subprocess, sys, zipfile

output, tools = (Path(x).resolve() for x in sys.argv[1:])
report = json.loads((output / 'PACKAGED_VERIFICATION.json').read_text())
apk = output / 'M9Cam_2.87_RAWSIZE1A.apk'
digest = hashlib.sha256(apk.read_bytes()).hexdigest()
assert digest == report['sha256'] and apk.stat().st_size == report['bytes']
with zipfile.ZipFile(apk) as archive:
    assert archive.testzip() is None
    dex = b''.join(archive.read(n) for n in archive.namelist() if n.endswith('.dex'))
    for marker in [b'RAWSIZE1A', b'RawSizeCompatibility1A', b'session_support_unconfirmed', b'reader_rejected', b'ExifBackdropView', b'cancelHistogramRequest', b'exact_neutral_request_with_reported_auto_control', b'MONOAEREF1B', b'MonoAeReference1A', b'exact_neutral_request_with_active_ae', b'MONODIAGVIEW1D', b'MonoReadinessDialog1D', b'Copy details']:
        assert marker in dex, marker
signature = subprocess.check_output(['java', '-jar', str(tools / 'lib/apksigner.jar'),
    'verify', '--verbose', '--print-certs', str(apk)], text=True)
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in signature
badging = subprocess.check_output([str(tools / 'aapt2'), 'dump', 'badging', str(apk)], text=True)
for identity in ["name='com.m9project.m9cam.photon'", "versionCode='27287'", "versionName='2.87-rawsize1a'"]:
    assert identity in badging
subprocess.run([str(tools / 'zipalign'), '-c', '-P', '16', '4', str(apk)], check=True)
resources = subprocess.check_output([str(tools / 'aapt2'), 'dump', 'resources', str(apk)], text=True)
def resource(kind, name):
    match = re.search(r'^    resource (0x[0-9a-f]+) ' + kind + '/' + re.escape(name)
        + r'\b[\s\S]*?(?=^    resource|\Z)', resources, re.M)
    assert match, (kind, name)
    return match.group(1), match.group(0)
style_id, slider_style = resource('style', 'Widget.Photon.Slider.Xxs')
for name, value in [('trackHeight', 10), ('trackCornerSize', 5), ('thumbHeight', 36)]:
    assert re.search(name + r'\([^)]*\)=' + str(value) + r'(?:\.0+)?dp\b', slider_style), slider_style
_, white_style = resource('style', 'ThemeOverlay.Photon.White')
assert re.search(r'colorSecondaryContainer\([^)]*\)=@color/white_theme_inactive\b', white_style)
assert re.search(r'colorOnSecondaryContainer\([^)]*\)=@0x0106000c\b', white_style)
assert '#ffacaba7' in resource('color', 'white_theme_inactive')[1].lower()
for layout in ['camera_fragment', 'preference_seekbar', 'preference_tunable_seekbar']:
    xml = subprocess.check_output([str(tools / 'aapt2'), 'dump', 'xmltree', '--file',
        'res/layout/' + layout + '.xml', str(apk)], text=True)
    blocks = re.findall(r'E: com\.google\.android\.material\.slider\.Slider[^\n]*\n((?:[ \t]+A:.*\n)*)', xml)
    assert len(blocks) == 1, layout
    slider = blocks[0]
    assert re.search(r':tickVisible\([^)]*\)=(?:false|0x0+|0)\s*$', slider, re.M), slider
    assert re.search(r':trackStopIndicatorSize\([^)]*\)=0(?:\.0+)?dp\s*$', slider, re.M), slider
    if layout != 'camera_fragment':
        assert 'style=@' + style_id in slider, slider
report['compiledUiResourcesVerified'] = True
(output / 'PACKAGED_VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n')
(output / 'SHA256SUMS.txt').write_text(digest + '  ' + apk.name + '\n')
print(json.dumps({'status': 'PASS', 'independentReopen': True, 'bytes': apk.stat().st_size,
    'sha256': digest, 'androidV2SignatureVerified': True, 'archiveVerified': True,
    'compiledUiResourcesVerified': True}))
