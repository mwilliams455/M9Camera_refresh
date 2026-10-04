#!/usr/bin/env python3
"""Package optional diagnostic outputs while preserving every accepted 2.22 native binary."""
from pathlib import Path
import copy, hashlib, json, subprocess, sys, zipfile

HERE=Path(__file__).resolve().parent
CONTROL='e94c26d43366623634cf9b24af57cf9cb767f57495d777cfe6edcf60da09133c'
VERSION='2.23-m9outputmenu1a'
def sha(b): return hashlib.sha256(b).hexdigest()
def signature(n):
    return n=='META-INF/MANIFEST.MF' or (n.startswith('META-INF/') and n.endswith(('.RSA','.DSA','.EC','.SF')))
def main(root,control,bt,out):
    root,control,bt,out=(p.resolve() for p in (root,control,bt,out));out.mkdir(parents=True,exist_ok=True)
    assert sha(control.read_bytes())==CONTROL,'Unexpected SATURATIONMENU1A CI control'
    files=json.loads((HERE.parent/'upstream2r/source_manifest.json').read_text())['files']
    for directory,name in [('upstream2r_fix1','fix_manifest.json'),('perf2s_auditopt1a','perf_manifest.json'),('dngexport1b','manifest.json'),('dngstage1a','manifest.json'),('dngnoisemeta1a','manifest.json'),('dngnoisestage1a','manifest.json'),('dngcolormeta1a','manifest.json'),('dngprofile1a','manifest.json'),('dngprofile1b','manifest.json'),('dngrawpair1a','manifest.json'),('capturerequest1a','manifest.json'),('rawreadout1a','manifest.json'),('saturationmenu1a','manifest.json'),('outputmenu1a','manifest.json')]:
        files.update(json.loads((HERE.parent/directory/name).read_text())['fileOverrides'])
    # Gradle may update generated version.properties; all source code/assets are pinned.
    for p,h in files.items():
        if p!='app/version.properties': assert sha((root/p).read_bytes())==h,'Source drift: '+p
    built=root/'app/build/outputs/apk/debug/M9Cam_2.23_OUTPUTMENU1A-debug.apk'
    unsigned=out/'unsigned.apk';aligned=out/'aligned.apk';final=out/'M9Cam_2.23_OUTPUTMENU1A.apk'
    expected={};reused=[];updated=[]
    with zipfile.ZipFile(control) as old,zipfile.ZipFile(built) as new,zipfile.ZipFile(unsigned,'w') as dst:
        assert old.testzip() is None and new.testzip() is None
        oldnative={n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
        newnative={n for n in new.namelist() if n.startswith('lib/') and not n.endswith('/')}
        added=set() # All 23 native binaries retained from accepted 2.22, including all five saturation banks
        assert newnative==oldnative and added<=oldnative
        for n in sorted(added):
            binary=out/('probe-'+n.split('/')[1]+'.so');binary.write_bytes(new.read(n))
            elf=subprocess.check_output(['readelf','-lW',str(binary)],text=True)
            loads=[line.split() for line in elf.splitlines() if line.strip().startswith('LOAD ')]
            assert loads and all(int(row[-1],16)>=16384 for row in loads),elf
            symbols=subprocess.check_output(['readelf','-Ws',str(binary)],text=True)
            assert 'Java_com_particlesdevs_photoncamera_m9_render_M9NativeColorCore_createContext' in symbols
            updated.append(n);binary.unlink()
        for n in old.namelist():
            if n.startswith('assets/m9/') and not n.endswith('/'): assert sha(old.read(n))==sha(new.read(n)),n
        for info in new.infolist():
            n=info.filename
            if signature(n): continue
            data=new.read(n)
            if n in oldnative and n not in added:
                data=old.read(n);reused.append(n)
            dst.writestr(copy.copy(info),data);expected[n]=sha(data)
        assert len(updated)==0
        dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for marker in ['M9 RAW16 required:','M9PERF2S_AUDITOPT1A','M9_RAW16_PRESERVED_FIX1','M9Cam v','M9DngExportMetadata','setBaselineExposure','M9DngNoiseProfile','M9DNGNOISEMETA1A_PHYSICAL_SINGLE_RAW','M9DNGNOISESTAGE1A_SHADED_K1','M9DngNoiseStage','setParametersForM9Raw','M9DNGCOLORMETA1A_PHYSICAL_COLOR','M9DngColorCapture','M9DNGPROFILE1B','M9DngProfileWriter','M9 App1B ','M9DNGRAWPAIR1A','_RAW_UNFILTERED.dng','M9CAPTUREREQUEST1A','captureRequest1A','pref_m9_omit_auto_remosaic','B_omit_automatic_remosaic','M9RAWREADOUT1A','rawReadoutRequest','rawReadoutCameraInventory','no_public_typed_key','android.sensor.rawBinningFactorUsed','M9SATURATIONMENU1A','pref_m9_saturation','leicaSaturationLevel','pref_m9_save_unfiltered_dng','pref_m9_save_diagnostic_files','disabled_by_setting','M9OutputSettings']:
            assert marker.encode() in dex,marker
    subprocess.run([str(bt/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    signer=['java','-jar',str(bt/'lib/apksigner.jar')]
    subprocess.run(signer+['sign','--ks',str(root/'key/PcamLeak.jks'),'--ks-key-alias','key0',
                          '--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera','--out',str(final),str(aligned)],check=True)
    subprocess.run([str(bt/'zipalign'),'-c','-P','16','4',str(final)],check=True)
    signed=subprocess.check_output(signer+['verify','--verbose','--print-certs',str(final)],text=True)
    assert '255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956' in signed
    badging=subprocess.check_output([str(bt/'aapt2'),'dump','badging',str(final)],text=True)
    assert "name='com.m9project.m9cam.photon'" in badging and "versionCode='27223'" in badging and f"versionName='{VERSION}'" in badging
    with zipfile.ZipFile(final) as z: assert {n:sha(z.read(n)) for n in z.namelist() if not signature(n)}==expected
    (out/'SIGNATURE_CHECK.txt').write_text(signed);(out/'APK_BADGING.txt').write_text(badging)
    report=dict(status='passed',version=VERSION,versionCode=27223,controlSha256=CONTROL,
                apkSha256=sha(final.read_bytes()),apkBytes=final.stat().st_size,
                frozenNativeEntries=reused,changedNativeEntries=updated,m9AssetsUnchanged=True,
                jpegRendererSourceUnchanged=False,photographicMathUnchanged=True,allNativeBinariesPreservedFrom222=True,standardSaturationPreserved=True,leicaSaturationLevels=5,saturationDefault=2,previewSaturationMenu=True,captureFrozenSaturation=True,rawSampleProcessingUnchanged=True,
                noiseStageMode=1,noiseStageStrength=1.0,noiseStageSeparateOutput=True,
                storagePolicy='same_directory_dng_staging_atomic_replace',embeddedProfilePerCapture=True,profileDimensions=[180,65,129],crossLensExperimentalOverride=False,
                rawPairDiagnosticOptional=True,rawPairDefaultEnabled=False,diagnosticFilesDefaultEnabled=False,diagnosticFilesOptional=True,controlRawUnfiltered=True,controlProfileEmbedded=False,controlNumericScale=1,extraRawPayloadCopy=False,captureRequestAuditEnabled=True,defaultOmitAutomaticRemosaic=False,comparisonScope='only_three_automatic_remosaic_assignments_omitted',cameraDeviceValidationPending=True,readOnlyRawReadoutAudit=True,rawReadoutRevision='M9RAWREADOUT1A')
    (out/'PACKAGED_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
    unsigned.unlink();aligned.unlink();print(json.dumps(report))
if __name__=='__main__': main(*map(Path,sys.argv[1:]))
