#!/usr/bin/env python3
"""Package the exact delivered native binaries for a Java-only diagnostic.

The raw local rebuild is retained separately. This does NOT claim that freshly
compiled native libraries reproduce the delivered binary. It reuses that exact
binary and then verifies every non-signature ZIP entry against its intended input.
"""
from pathlib import Path
import json, shutil, subprocess, sys, zipfile
import apply as patch
from postbuild import BASE_APK

def main(root, baseline, build_tools, output):
    root=root.resolve();output.mkdir(parents=True,exist_ok=True)
    proof=json.loads((root/(patch.ID+'_SOURCE_PROOF.json')).read_text())
    baseline_inventory=json.loads((patch.HERE/'baseline_inventory.json').read_text())
    patch.need(proof['before']==baseline_inventory,'Unknown baseline source')
    now=patch.inventory(root)
    patch.need(all(now.get(p)==h for p,h in proof['after'].items()),'Source drift')
    patch.need(proof['changed']==sorted([patch.GRADLE,patch.HELPER,patch.FRAME,patch.SAVER,patch.QUEUE,patch.DNG]),'Unexpected Java/native changes')
    patch.need(patch.sha(baseline.read_bytes())==BASE_APK,'Unknown baseline APK')
    apks=list((root/'app/build/outputs/apk/debug').glob('*.apk'))
    patch.need(len(apks)==1,'Expected one built APK')
    original=output/'M9Cam_2.08_LOCAL_NATIVE_REBUILD_NOT_FOR_DELIVERY.apk'
    shutil.copyfile(apks[0],original)
    unsigned=output/'native-frozen-unsigned.apk';aligned=output/'native-frozen-aligned.apk'
    intended={};replaced=[]
    def signature(name):
        return name=='META-INF/MANIFEST.MF' or (name.startswith('META-INF/') and name.endswith(('.RSA','.DSA','.EC','.SF')))
    with zipfile.ZipFile(baseline) as old,zipfile.ZipFile(original) as built,zipfile.ZipFile(unsigned,'w') as out:
        old_native={n for n in old.namelist() if n.startswith('lib/') and not n.endswith('/')}
        new_native={n for n in built.namelist() if n.startswith('lib/') and not n.endswith('/')}
        patch.need(old_native==new_native,'Native library/ABI set changed')
        for info in built.infolist():
            if signature(info.filename):continue
            data=built.read(info.filename)
            if info.filename in old_native:
                data=old.read(info.filename);replaced.append(info.filename)
            out.writestr(info,data);intended[info.filename]=patch.sha(data)
    subprocess.run([str(build_tools/'zipalign'),'-f','-P','16','4',str(unsigned),str(aligned)],check=True)
    signed=output/'native-frozen-signed.apk'
    subprocess.run(['java','-jar',str(build_tools/'lib/apksigner.jar'),'sign','--ks',str(root/'key/PcamLeak.jks'),
                    '--ks-key-alias','key0','--ks-pass','pass:photoncamera','--key-pass','pass:photoncamera',
                    '--out',str(signed),str(aligned)],check=True)
    with zipfile.ZipFile(signed) as final:
        actual={n:patch.sha(final.read(n)) for n in final.namelist() if not signature(n)}
    patch.need(actual==intended,'Alignment/signing changed payload entries')
    shutil.copyfile(signed,apks[0])
    report=dict(status='passed',strategy='reuse_exact_delivered_2.07_native_binaries_for_Java_only_diagnostic',
                baselineApkSha256=BASE_APK,localRebuiltApkSha256=patch.sha(original.read_bytes()),
                finalApkSha256=patch.sha(signed.read_bytes()),nativeEntriesReused=sorted(replaced),
                allOtherUnsignedPayloadEntriesPreserved=True,
                freshNativeRebuildByteEqualityClaimed=False,deviceValidationPending=True)
    (output/'NATIVE_PAYLOAD_REUSE.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='nativeEntriesReused'},indent=2))

if __name__=='__main__':
    if len(sys.argv)!=5:raise SystemExit('usage: freeze_native.py PhotonCamera BASELINE_APK BUILD_TOOLS OUTPUT')
    main(*map(Path,sys.argv[1:]))
