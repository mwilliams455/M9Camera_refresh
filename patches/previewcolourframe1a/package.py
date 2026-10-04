"""Package the preview colour/framing build with all native libraries from the accepted 2.33 APK."""
from pathlib import Path
import copy, hashlib, json, re, subprocess, sys, zipfile

here = Path(__file__).resolve().parent
def sha(data): return hashlib.sha256(data).hexdigest()
def signature(name):
    return name == 'META-INF/MANIFEST.MF' or (name.startswith('META-INF/') and name.endswith(('.RSA','.DSA','.EC','.SF')))

def main(root,built,control,bt,out):
    root,built,control,bt,out = [p.resolve() for p in (root,built,control,bt,out)]
    out.mkdir(parents=True,exist_ok=True)
    assert sha(control.read_bytes()) == 'bff25f5bd8a9b92487d17bda2e984367b242d00fc449c8b7258d0c959cc4ef05'
    manifest = json.loads((here/'manifest.json').read_text())
    for name,digest in manifest['fileOverrides'].items(): assert sha((root/name).read_bytes()) == digest, name
    unsigned,aligned,final = [out/n for n in ['unsigned.apk','aligned.apk','M9Cam_2.34_PREVIEWCOLOURFRAME1A.apk']]
    expected = {}
    with zipfile.ZipFile(control) as old, zipfile.ZipFile(built) as new, zipfile.ZipFile(unsigned,'w') as dst:
        assert old.testzip() is None and new.testzip() is None
        natives = {n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
        assert len(natives) == 25
        assert {n for n in new.namelist() if n.startswith('lib/') and not n.endswith('/')} == natives
        assets = {n for n in old.namelist() if n.startswith('assets/') and not n.endswith('/')}
        assert assets == {n for n in new.namelist() if n.startswith('assets/') and not n.endswith('/')}
        changed_assets = {name for name in assets if old.read(name) != new.read(name)}
        assert changed_assets == {'assets/shaders/preview/main_fs.glsl','assets/shaders/preview/blur_oes_fs.glsl'}
        assert new.read('assets/shaders/preview/main_fs.glsl') == (root/'app/src/main/assets/shaders/preview/main_fs.glsl').read_bytes()
        for info in new.infolist():
            name = info.filename
            if signature(name): continue
            data = old.read(name) if name in natives else new.read(name)
            expected[name] = sha(data)
            dst.writestr(copy.copy(info),data)
        dex = b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for marker in ['M9SHARPNESSMENU1A','pref_m9_sharpness','M9SharpnessStage','exact_stage_bypass_2_27_pixels','M9CONTRASTMENU1A','pref_m9_saturation','M9CaptureParameters','M9ShootingProfiles','pref_m9_shooting_profiles_v1','pref_m9_shooting_profile_active','M9DisplayAidsController','M9DisplayAidsView','pref_m9_highlight_warning','pref_m9_shadow_warning','M9PREVIEWBRIGHTNESS1A','uniformPreviewToneGain','M9LEICAEV1A','shared_persistent_stop_value_menu_wheel_profiles','M9PREVIEWCOLOURFRAME1A','cameraTextureMatrix','uCameraSamplingMatrix']:
            assert marker.encode() in dex, marker
        assert 'res/xml/preferences_m9.xml' in new.namelist()
    subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    signer = ['java','-jar',str(bt/'lib/apksigner.jar')]
    subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),'--ks-key-alias','key0','--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
    subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
    cert = subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
    assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in cert
    badging = subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
    for marker in ["name='com.m9project.m9cam.photon'","versionCode='27234'","versionName='2.34-m9previewcolourframe1a'"]:
        assert marker in badging, marker
    xml = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/xml/preferences_m9.xml',str(final)],text=True)
    for name in ['image','capture','output','display','advanced']:
        assert 'pref_m9_'+name+'_screen' in xml
    assert 'pref_m9_profiles_screen' in xml
    assert 'm9_ev_info' in xml
    for key in ['pref_m9_highlight_warning','pref_m9_shadow_warning']:
        assert key in xml
    topbar = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/layout/layout_main_topbar.xml',str(final)],text=True)
    resources = subprocess.check_output([str(bt/'aapt2'),'dump','resources',str(final)],text=True)
    ev_key = re.search(r'resource (0x[0-9a-f]+) string/pref_expocompensation_seekbar_key\b', resources).group(1)
    ev_values = re.search(r'resource (0x[0-9a-f]+) array/m9_ev_values\b', resources).group(1)
    ev_nodes = [part for part in xml.split('E: ') if 'key(0x010101e8)=@'+ev_key in part]
    assert len(ev_nodes) == 1 and ev_nodes[0].startswith('ListPreference')
    assert 'entryValues(0x010101f8)=@'+ev_values in ev_nodes[0]
    for resource in ['m9_display_aids_button','m9_display_aids_overlay','m9_display_mode_entries','m9_ev_entries','m9_ev_values']:
        assert resource in resources,resource
    for label in ['−3.0 EV','−0.7 EV','0.0 EV','+0.3 EV','+3.0 EV']: assert label in resources,label
    with zipfile.ZipFile(final) as apk:
        assert apk.testzip() is None
        assert {n:sha(apk.read(n)) for n in apk.namelist() if not signature(n)} == expected
    report = dict(status='passed',version='2.34-m9previewcolourframe1a',bytes=final.stat().st_size,
        sha256=sha(final.read_bytes()),originalNativeLibrariesPreserved=sorted(natives),
        addedNativeLibraries=[],allAssetsExceptTwoPreviewShadersPreserved=True,changedAssets=sorted(changed_assets),signatureMatches233=True,
        alignment16KiB=True,compiledM9MenuPresent=True,compiledProfileScreenPresent=True,compiledClippingControlsPresent=True,phoneValidationPending=True)
    (out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'SIGNATURE_CHECK.txt').write_text(cert)
    (out/'APK_BADGING.txt').write_text(badging)
    (out/'COMPILED_M9_MENU.txt').write_text(xml)
    unsigned.unlink(); aligned.unlink()
    print(json.dumps(report,indent=2))

if __name__ == '__main__': main(*map(Path,sys.argv[1:]))
