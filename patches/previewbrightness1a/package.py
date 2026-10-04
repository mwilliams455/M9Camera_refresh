"""Package the preview brightness build with all native libraries from the accepted 2.31 APK."""
from pathlib import Path
import copy, hashlib, json, subprocess, sys, zipfile

here = Path(__file__).resolve().parent
def sha(data): return hashlib.sha256(data).hexdigest()
def signature(name):
    return name == 'META-INF/MANIFEST.MF' or (name.startswith('META-INF/') and name.endswith(('.RSA','.DSA','.EC','.SF')))

def main(root,built,control,bt,out):
    root,built,control,bt,out = [p.resolve() for p in (root,built,control,bt,out)]
    out.mkdir(parents=True,exist_ok=True)
    assert sha(control.read_bytes()) == '1a8e93e7209b8d2c59818010bfd33da0aa1c9c9b51446b913bf3c762e506bf2e'
    manifest = json.loads((here/'manifest.json').read_text())
    for name,digest in manifest['fileOverrides'].items(): assert sha((root/name).read_bytes()) == digest, name
    unsigned,aligned,final = [out/n for n in ['unsigned.apk','aligned.apk','M9Cam_2.32_PREVIEWBRIGHTNESS1A.apk']]
    expected = {}
    with zipfile.ZipFile(control) as old, zipfile.ZipFile(built) as new, zipfile.ZipFile(unsigned,'w') as dst:
        assert old.testzip() is None and new.testzip() is None
        natives = {n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
        assert len(natives) == 25
        assert {n for n in new.namelist() if n.startswith('lib/') and not n.endswith('/')} == natives
        assets = {n for n in old.namelist() if n.startswith('assets/') and not n.endswith('/')}
        assert assets == {n for n in new.namelist() if n.startswith('assets/') and not n.endswith('/')}
        changed_assets = {name for name in assets if old.read(name) != new.read(name)}
        assert changed_assets == {'assets/shaders/preview/main_fs.glsl'}
        assert new.read('assets/shaders/preview/main_fs.glsl') == (root/'app/src/main/assets/shaders/preview/main_fs.glsl').read_bytes()
        for info in new.infolist():
            name = info.filename
            if signature(name): continue
            data = old.read(name) if name in natives else new.read(name)
            expected[name] = sha(data)
            dst.writestr(copy.copy(info),data)
        dex = b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for marker in ['M9SHARPNESSMENU1A','pref_m9_sharpness','M9SharpnessStage','exact_stage_bypass_2_27_pixels','M9CONTRASTMENU1A','pref_m9_saturation','M9CaptureParameters','M9ShootingProfiles','pref_m9_shooting_profiles_v1','pref_m9_shooting_profile_active','M9DisplayAidsController','M9DisplayAidsView','pref_m9_highlight_warning','pref_m9_shadow_warning','M9PREVIEWBRIGHTNESS1A','uniformPreviewToneGain']:
            assert marker.encode() in dex, marker
        assert 'res/xml/preferences_m9.xml' in new.namelist()
    subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    signer = ['java','-jar',str(bt/'lib/apksigner.jar')]
    subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),'--ks-key-alias','key0','--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
    subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
    cert = subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
    assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in cert
    badging = subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
    for marker in ["name='com.m9project.m9cam.photon'","versionCode='27232'","versionName='2.32-m9previewbrightness1a'"]:
        assert marker in badging, marker
    xml = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/xml/preferences_m9.xml',str(final)],text=True)
    for name in ['image','capture','output','display','advanced']:
        assert 'pref_m9_'+name+'_screen' in xml
    assert 'pref_m9_profiles_screen' in xml
    for key in ['pref_m9_highlight_warning','pref_m9_shadow_warning']:
        assert key in xml
    topbar = subprocess.check_output([str(bt/'aapt2'),'dump','xmltree','--file','res/layout/layout_main_topbar.xml',str(final)],text=True)
    resources = subprocess.check_output([str(bt/'aapt2'),'dump','resources',str(final)],text=True)
    for resource in ['m9_display_aids_button','m9_display_aids_overlay','m9_display_mode_entries']:
        assert resource in resources,resource
    with zipfile.ZipFile(final) as apk:
        assert apk.testzip() is None
        assert {n:sha(apk.read(n)) for n in apk.namelist() if not signature(n)} == expected
    report = dict(status='passed',version='2.32-m9previewbrightness1a',bytes=final.stat().st_size,
        sha256=sha(final.read_bytes()),originalNativeLibrariesPreserved=sorted(natives),
        addedNativeLibraries=[],unchangedAssetsExceptPreviewShader=True,changedAssets=sorted(changed_assets),signatureMatches231=True,
        alignment16KiB=True,compiledM9MenuPresent=True,compiledProfileScreenPresent=True,compiledClippingControlsPresent=True,phoneValidationPending=True)
    (out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'SIGNATURE_CHECK.txt').write_text(cert)
    (out/'APK_BADGING.txt').write_text(badging)
    (out/'COMPILED_M9_MENU.txt').write_text(xml)
    unsigned.unlink(); aligned.unlink()
    print(json.dumps(report,indent=2))

if __name__ == '__main__': main(*map(Path,sys.argv[1:]))
