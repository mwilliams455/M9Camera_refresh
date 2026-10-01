#!/usr/bin/env python3
"""Package firmware DNG defaults while preserving accepted native rendering binaries."""
from pathlib import Path
import copy, hashlib, json, subprocess, sys, zipfile

HERE=Path(__file__).resolve().parent
CONTROL='db34f276498568a27d04d1ee9b78d399af6dcddf10b3b06c5412990710674a33'
VERSION='2.13-m9dngstage1a'
def sha(b): return hashlib.sha256(b).hexdigest()
def signature(n):
    return n=='META-INF/MANIFEST.MF' or (n.startswith('META-INF/') and n.endswith(('.RSA','.DSA','.EC','.SF')))
def main(root,control,bt,out):
    root,control,bt,out=(p.resolve() for p in (root,control,bt,out));out.mkdir(parents=True,exist_ok=True)
    assert sha(control.read_bytes())==CONTROL,'Unexpected PERF2S CI control'
    files=json.loads((HERE.parent/'upstream2r/source_manifest.json').read_text())['files']
    for directory,name in [('upstream2r_fix1','fix_manifest.json'),('perf2s_auditopt1a','perf_manifest.json'),('dngexport1b','manifest.json'),('dngstage1a','manifest.json')]:
        files.update(json.loads((HERE.parent/directory/name).read_text())['fileOverrides'])
    # Gradle may update generated version.properties; all source code/assets are pinned.
    for p,h in files.items():
        if p!='app/version.properties': assert sha((root/p).read_bytes())==h,'Source drift: '+p
    built=root/'app/build/outputs/apk/debug/M9Cam_2.13_DNGSTAGE1A-debug.apk'
    unsigned=out/'unsigned.apk';aligned=out/'aligned.apk';final=out/'M9Cam_2.13_DNGSTAGE1A.apk'
    expected={};reused=[];updated=[]
    with zipfile.ZipFile(control) as old,zipfile.ZipFile(built) as new,zipfile.ZipFile(unsigned,'w') as dst:
        assert old.testzip() is None and new.testzip() is None
        oldnative={n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
        newnative={n for n in new.namelist() if n.startswith('lib/') and not n.endswith('/')}
        assert oldnative==newnative
        for n in old.namelist():
            if n.startswith('assets/m9/') and not n.endswith('/'): assert sha(old.read(n))==sha(new.read(n)),n
        for info in new.infolist():
            n=info.filename
            if signature(n): continue
            data=new.read(n)
            if n in newnative:
                if n.endswith('/libdngCreator.so'):
                    assert sha(data)!=sha(old.read(n));updated.append(n)
                else: data=old.read(n);reused.append(n)
            dst.writestr(copy.copy(info),data);expected[n]=sha(data)
        assert len(updated)==2
        dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for marker in ['M9 RAW16 required:','M9PERF2S_AUDITOPT1A','M9_RAW16_PRESERVED_FIX1','M9Cam v','M9DngExportMetadata','setBaselineExposure']:
            assert marker.encode() in dex,marker
    subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    signer=['java','-jar',str(bt/'lib/apksigner.jar')]
    subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),'--ks-key-alias','key0',
                          '--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
    subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
    signed=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
    assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in signed
    badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
    assert "name='com.m9project.m9cam.photon'" in badging and "versionCode='27213'" in badging and f"versionName='{VERSION}'" in badging
    with zipfile.ZipFile(final) as z: assert {n:sha(z.read(n)) for n in z.namelist() if not signature(n)}==expected
    (out/'SIGNATURE_CHECK.txt').write_text(signed);(out/'APK_BADGING.txt').write_text(badging)
    report=dict(status='passed',version=VERSION,versionCode=27213,controlSha256=CONTROL,
                apkSha256=sha(final.read_bytes()),apkBytes=final.stat().st_size,
                frozenNativeEntries=reused,changedNativeEntries=updated,m9AssetsUnchanged=True,
                jpegRendererSourceUnchanged=True,rawSampleProcessingUnchanged=True,
                cameraDeviceValidationPending=True)
    (out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    unsigned.unlink();aligned.unlink();print(json.dumps(report))
if __name__=='__main__': main(*map(Path,sys.argv[1:]))
