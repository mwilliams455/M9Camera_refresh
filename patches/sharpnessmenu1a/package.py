from pathlib import Path
import copy,hashlib,json,subprocess,sys,zipfile
here=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def sig(n):return n=='META-INF/MANIFEST.MF' or (n.startswith('META-INF/') and n.endswith(('.RSA','.DSA','.EC','.SF')))
def main(root,built,control,bt,out):
    root,built,control,bt,out=map(lambda p:p.resolve(),(root,built,control,bt,out));out.mkdir(parents=True,exist_ok=True)
    assert sha(control.read_bytes())=='ec51ec331b825eb8398984f19e16d6c5065ffa0d6ce0b9ecf8ac2c09a787b66e'
    manifest=json.loads((here/'manifest.json').read_text())
    for n,h in manifest['fileOverrides'].items():assert sha((root/n).read_bytes())==h,n
    unsigned=out/'unsigned.apk';aligned=out/'aligned.apk';final=out/'M9Cam_2.28_SHARPNESSMENU1A.apk'
    added={f'lib/{a}/libm9sharpness.so' for a in ['arm64-v8a','armeabi-v7a']};expected={}
    with zipfile.ZipFile(control) as old,zipfile.ZipFile(built) as new,zipfile.ZipFile(unsigned,'w') as dst:
        assert old.testzip() is None and new.testzip() is None
        natives={n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
        assert len(natives)==23
        assert {n for n in new.namelist() if n.startswith('lib/') and not n.endswith('/')}==natives|added
        for n in old.namelist():
            if n.startswith('assets/') and not n.endswith('/'):assert old.read(n)==new.read(n),n
        for n in added:
            temp=out/('inspect-'+n.split('/')[1]+'.so');temp.write_bytes(new.read(n))
            symbols=subprocess.check_output(['readelf','-Ws',str(temp)],text=True)
            assert 'Java_com_particlesdevs_photoncamera_m9_render_M9SharpnessStage_applyNative' in symbols
            loads=[l.split() for l in subprocess.check_output(['readelf','-lW',str(temp)],text=True).splitlines() if l.strip().startswith('LOAD ')]
            assert loads and all(int(l[-1],16)>=16384 for l in loads)
            temp.unlink()
        for info in new.infolist():
            n=info.filename
            if sig(n):continue
            data=old.read(n) if n in natives else new.read(n)
            expected[n]=sha(data);dst.writestr(copy.copy(info),data)
        dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for marker in ['M9SHARPNESSMENU1A','pref_m9_sharpness','M9SharpnessStage','reader_controls_spatial_detail_profile_is_colour_and_tone_only','exact_stage_bypass_2_27_pixels','M9CONTRASTMENU1A','pref_m9_saturation','M9CaptureParameters']:
            assert marker.encode() in dex,marker
    subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    signer=['java','-jar',str(bt/'lib/apksigner.jar')]
    subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),'--ks-key-alias','key0','--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
    subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
    cert=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
    assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in cert
    badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
    for marker in ["name='com.m9project.m9cam.photon'","versionCode='27228'","versionName='2.28-m9sharpnessmenu1a'"]:assert marker in badging
    with zipfile.ZipFile(final) as z:
        assert z.testzip() is None
        assert {n:sha(z.read(n)) for n in z.namelist() if not sig(n)}==expected
    report=dict(status='passed',version='2.28-m9sharpnessmenu1a',bytes=final.stat().st_size,sha256=sha(final.read_bytes()),
        originalNativeLibrariesPreserved=sorted(natives),addedNativeLibraries=sorted(added),allInheritedAssetsPreserved=True,
        signatureMatches227=True,alignment16KiB=True,default='Standard',previewSharpnessSimulation=False,dngSpatialSharpnessEmbedded=False,
        phoneValidationPending=True)
    (out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');(out/'SIGNATURE_CHECK.txt').write_text(cert);(out/'APK_BADGING.txt').write_text(badging)
    unsigned.unlink();aligned.unlink();print(json.dumps(report,indent=2))
if __name__=='__main__':main(*map(Path,sys.argv[1:]))
