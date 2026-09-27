#!/usr/bin/env python3
"""Verify compiled input identities separately from newly generated native build files.
No recorded source file may change/disappear. New files outside the native CMake
source subtree fail. Additional native files are accepted only when every packaged
native library AND asset/raw resource is byte-identical to the delivered 2.04 APK.
The full addition/difference inventory is retained, including on failure.
"""
from pathlib import Path
import importlib.util, json, sys

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('exactpatch_postbuild_apply',HERE/'apply.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def verify(root, baseline, output):
    root=root.resolve();output.mkdir(parents=True,exist_ok=True)
    proof=json.loads((root/(m.ID+'_SOURCE_PROOF.json')).read_text())
    now=m.parent().inventory(root)
    expected=proof['after']
    added={p:now[p] for p in sorted(set(now)-set(expected))}
    missing=sorted(set(expected)-set(now))
    modified={p:{'expected':expected[p],'actual':now[p]} for p in sorted(set(expected)&set(now)) if expected[p]!=now[p]}
    report={'revision':m.ID,'stage':'post_build','auditedInputCount':len(expected),
            'postBuildInventoryCount':len(now),'addedNativeBuildFiles':added,
            'missingAuditedInputs':missing,'modifiedAuditedInputs':modified,
            'status':'checking','nativeBinaryEqualityRequired':True}
    report_path=output/'POSTBUILD_SOURCE_AUDIT.json'
    def save():report_path.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        base_proof=json.loads((baseline/'PhotonCamera/M9TAPMETER1A_SOURCE_PROOF.json').read_text())
        m.need(proof['before']==base_proof['after'],'Source parent differs from actual delivered 2.04 proof')
        m.need(proof['revision']==m.ID and len(expected)==1006,'Unexpected source receipt')
        m.need(m.changed(proof['before'],expected)=={m.AUTO,m.GRADLE},'Wrong production source change set')
        m.need(not missing and not modified,'A recorded compilation input changed or disappeared; inspect POSTBUILD_SOURCE_AUDIT.json')
        m.need(all(p.startswith('app/src/main/cpp/') for p in added),
               'Non-native source additions detected; inspect POSTBUILD_SOURCE_AUDIT.json')
        m.need(now[m.AUTO]==m.NEW_AUTO and now[m.TAP]==m.TAP_SHA,'Wrong compiled exposure source/helper')
        gradle=(root/m.GRADLE).read_text()
        m.need(gradle.count(f'versionCode {m.CODE}')==1 and gradle.count(f"versionName '{m.VERSION}'")==1,
               'Wrong compiled application identity')
        m.need(m.sha((root/m.AUTO).read_text().split('    /** Explicit user selection owns')[0].encode())==m.PREFIX_SHA,
               'Non-tap source changed')
        apks=list((root/'app/build/outputs/apk/debug').glob('*.apk'))
        m.need(len(apks)==1,'Expected one compiled APK')
        apk=m.apk_proof(apks[0],baseline/'M9Cam_2.04_TAPMETER1A.apk',output)
        report.update(status='passed',recordedInputsUnchanged=True,
                      generatedNativeAdditionsHaveIdenticalPackagedOutputs=True,
                      frozenEntriesCompared=apk['frozenEntriesCompared'],apkSha256=apk['apkSha256'])
        save()
        return {k:v for k,v in report.items() if k!='addedNativeBuildFiles'}
    except BaseException as e:
        report['status']='failed';report['failure']=str(e);save();raise

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: postbuild.py PhotonCamera BASELINE204 OUTPUT')
    print(json.dumps(verify(*map(Path,sys.argv[1:])),indent=2))
