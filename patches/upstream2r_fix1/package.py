#!/usr/bin/env python3
"""Package current upstream binaries while freezing only the M9 colour library.
Usage: package.py PHOTON_SOURCE CONTROL_208_APK ANDROID_BUILD_TOOLS OUTPUT
"""
from pathlib import Path
import copy, hashlib, io, json, subprocess, sys, zipfile

HERE=Path(__file__).resolve().parent
CONTROLS={
    '84ba09678751001469be7a684102e2e15c574356fe94bae550c32ba683591224':'2.08 PHOTONBOUNDARY2Q',
    # 2.08 deliberately reuses every 2.07 native library and M9 asset unchanged.
    '405b2cd85483d3a43f790732c0fc10505a0d3b4858b6d9d89142b771615d0afb':'2.07 CAPTURECOLOR1A (identical M9 native/assets)',
}
UPSTREAM='4ee108e169496f429c0afa0cc33e57bb6b2ec724'
VERSION='2.10-m9upstream2r-fix1-raw16'
def sha(data):return hashlib.sha256(data).hexdigest()
def signature(n):
    return n=='META-INF/MANIFEST.MF' or (n.startswith('META-INF/') and n.endswith(('.RSA','.DSA','.EC','.SF')))
def main(root,control,bt,out):
    root,control,bt,out=(p.resolve() for p in (root,control,bt,out))
    out.mkdir(parents=True,exist_ok=True)
    control_bytes=control.read_bytes()
    control_hash=sha(control_bytes)
    assert control_hash in CONTROLS,'Unknown control APK'
    manifest=json.loads((HERE.parent/'upstream2r/frozen_m9_inventory.json').read_text())
    for p,h in manifest.items():assert sha((root/p).read_bytes())==h,'M9 source/asset drift: '+p
    built=root/'app/build/outputs/apk/debug/M9Cam_2.10_UPSTREAM2R_FIX1-debug.apk'
    assert built.is_file(),built
    built_bytes=built.read_bytes()
    unsigned=out/'upstream-unsigned.apk';aligned=out/'upstream-aligned.apk'
    final=out/'M9Cam_2.10_UPSTREAM2R_FIX1.apk'
    expected={};reused=[];changed_native=[]
    with zipfile.ZipFile(io.BytesIO(control_bytes)) as old,zipfile.ZipFile(io.BytesIO(built_bytes)) as new,zipfile.ZipFile(unsigned,'w') as target:
        assert old.testzip() is None and new.testzip() is None,'Input ZIP CRC failure'
        native_m9={n for n in old.namelist() if n.startswith('lib/') and n.endswith('/libm9color.so')}
        assert len(native_m9)==2 and native_m9.issubset(new.namelist())
        frozen_assets={n:sha(old.read(n)) for n in old.namelist() if n.startswith('assets/m9/') and not n.endswith('/')}
        for n,h in frozen_assets.items():assert sha(new.read(n))==h,'M9 packaged asset drift: '+n
        for info in new.infolist():
            n=info.filename
            if signature(n):continue
            data=new.read(n)
            if n in native_m9:
                data=old.read(n);reused.append(n)
            elif n.startswith('lib/') and not n.endswith('/'):
                if n not in old.namelist() or sha(data)!=sha(old.read(n)):changed_native.append(n)
            # writestr mutates offsets and CRC on ZipInfo; keep the input archive intact.
            target.writestr(copy.copy(info),data);expected[n]=sha(data)
        dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for marker in ['M9UPSTREAM2R_FIX1','M9_RAW16_PRESERVED_FIX1','M9 RAW16 required:',UPSTREAM,'photonBoundary2Q','cameraPlaneBeforeCopy',
                       'rendererEntry','dngWriterInput','dngWriterReturn','captureColorMetadata1A']:
            assert marker.encode() in dex,'Missing DEX marker '+marker
    subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    subprocess.run(['java','-jar',str(bt/'lib/apksigner.jar'),'sign','--ks',str(root/'key/PcamLeak.jks'),
                    '--ks-key-alias','key0','--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera',
                    '--out',str(final),str(aligned)],check=True)
    with zipfile.ZipFile(final) as z:
        actual={n:sha(z.read(n)) for n in z.namelist() if not signature(n)}
    assert actual==expected,'Payload changed during signing/alignment'
    subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
    signer=subprocess.check_output(['java','-jar',str(bt/'lib/apksigner.jar'),'verify','--verbose','--print-certs',str(final)],text=True)
    assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in signer
    (out/'SIGNATURE_CHECK.txt').write_text(signer)
    badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
    assert "name='com.m9project.m9cam.photon'" in badging and "versionCode='27210'" in badging and f"versionName='{VERSION}'" in badging
    assert any(line in ("sdkVersion:'26'", "minSdkVersion:'26'") for line in badging.splitlines())
    assert "targetSdkVersion:'35'" in badging
    (out/'APK_BADGING.txt').write_text(badging)
    report=dict(status='passed',version=VERSION,versionCode=27210,photonCommit=UPSTREAM,
                controlSha256=control_hash,controlIdentity=CONTROLS[control_hash],apkSha256=sha(final.read_bytes()),apkBytes=final.stat().st_size,
                compiledApkSha256=sha(built_bytes),frozenM9SourceAndAssetFiles=len(manifest),
                frozenM9NativeEntries=reused,frozenM9PackagedAssets=frozen_assets,
                updatedOrNewNativeEntries=changed_native,otherBuiltPayloadPreserved=True,
                strategy='new_upstream_native_libraries_plus_exact_control_M9_colour_library',
                rawBoundaryDiagnosticsRetained=True,digitalRawCropEnabled=False,
                arrivalPackingPolicy="M9_RAW16_PRESERVED_FIX1",nativeDngRaw16LayoutChecked=True,
                cameraDeviceValidationPending=True)
    (out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'SHA256SUMS.txt').write_text(report['apkSha256']+'  '+final.name+'\n')
    unsigned.unlink();aligned.unlink()
    print(json.dumps(report,indent=2))
if __name__=='__main__':main(*map(Path,sys.argv[1:]))
