#!/usr/bin/env python3
"""Check read-only source scope and exact packaged native/assets equality to 2.07."""
from pathlib import Path
import json, shutil, sys, zipfile
import apply as patch

BASE_APK='405b2cd85483d3a43f790732c0fc10505a0d3b4858b6d9d89142b771615d0afb'
def main(root, baseline, output):
    proof=json.loads((root/(patch.ID+'_SOURCE_PROOF.json')).read_text())
    expected=proof['after'];now=patch.inventory(root)
    patch.need(all(now.get(p)==h for p,h in expected.items()),'Compilation changed recorded source inputs')
    additions=sorted(set(now)-set(expected))
    patch.need(all(p.startswith('app/src/main/cpp/') for p in additions),'Unexpected generated source')
    patch.need(patch.sha(baseline.read_bytes())==BASE_APK,'Unknown baseline APK')
    apks=list((root/'app/build/outputs/apk/debug').glob('*.apk'))
    patch.need(len(apks)==1,'Expected one debug APK')
    with zipfile.ZipFile(baseline) as old,zipfile.ZipFile(apks[0]) as new:
        def frozen(z):
            return {n:patch.sha(z.read(n)) for n in z.namelist()
                    if not n.endswith('/') and n.startswith(('lib/','assets/','res/raw/'))}
        a,b=frozen(old),frozen(new)
        diff=[p for p in sorted(set(a)|set(b)) if a.get(p)!=b.get(p)]
        patch.need(a and not diff,'Frozen packaged payload mismatch: '+repr(diff))
        dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        for token in ['M9PHOTONBOUNDARY2Q_READONLY','photonBoundary2Q','cameraPlaneBeforeCopy',
                      'photonOwnedAfterCopy','rendererEntry','dngWriterInput','dngWriterReturn',
                      'raw_bytes_changed','frame_result_timestamp_mismatch',
                      'buffer_handoffs_match_saved_DNG_decode_pending','captureColorMetadata1A']:
            patch.need(token.encode() in dex,'DEX marker missing: '+token)
    output.mkdir(parents=True,exist_ok=True)
    dest=output/'M9Cam_2.08_PHOTONBOUNDARY2Q.apk';shutil.copyfile(apks[0],dest)
    result=dict(status='passed',version=patch.VERSION,versionCode=patch.CODE,
                apkSha256=patch.sha(dest.read_bytes()),baselineApkSha256=BASE_APK,
                frozenPackagedEntries=len(a),frozenPackagedEntriesByteIdentical=True,
                recordedInputsUnchanged=True,generatedNativeFiles=additions,
                rendererSourceUnchanged=True,nativeCodeUnchanged=True,exposureSourceUnchanged=True,
                phoneValidationPending=True)
    (output/'PACKAGED_VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.copyfile(root/(patch.ID+'_SOURCE_PROOF.json'),output/'SOURCE_PROOF.json')
    (output/'SHA256SUMS.txt').write_text(result['apkSha256']+'  '+dest.name+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: postbuild.py PhotonCamera BASELINE_APK OUTPUT')
    main(*map(Path,sys.argv[1:]))
