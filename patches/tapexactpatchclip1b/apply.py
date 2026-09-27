#!/usr/bin/env python3
"""Recreated exact-patch repair: one tap-only predicate, diagnostics and app identity.
The archived 1A ZIP was not retrievable. This 1B source is independently hashed/tested.
No private capture fixtures, threshold changes, renderer changes or no-tap policy edits.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, sys, zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ID='M9EXACTPATCHCLIP1B'
VERSION='2.05-m9exactpatch1b-ae1n-perf3i'
CODE=26725
AUTO='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java'
TAP='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9TapMeter1A.java'
GRADLE='app/build.gradle'
BASE_AUTO='c62023a38af3bea4ca94ae24f2f28fe51259a3c86cea6fccfbe915d330753427'
NEW_AUTO='df6b82ecf84762aeafe0a9b151ed921247833a47c2ff9d1e61353100d3cd8448'
TAP_SHA='36d0505daf98e12f0b943d7afa7a14440af9404210bc528f836ec4a5ae5efbdf'
BASE_GRADLE='5a8bcca8db638531e576a5cada3d001b859235c26ebc942ed09793d8cfaf97be'
PREFIX_SHA='dd6082a8fe553298ef2681bf16ac852c62fe418e192513c238bf8bbb76a00d4f'
BASE_APK='3e388141678287b6a1c1c05b643f695969887c2939b4b39a269cf8c2b16bfb7c'


def sha(data): return hashlib.sha256(data).hexdigest()

def need(ok,message):
    if not ok: raise SystemExit(message)

def once(text,old,new):
    need(text.count(old)==1,'Exact source anchor mismatch: '+old)
    return text.replace(old,new,1)

def transformed(raw):
    need(sha(raw)==BASE_AUTO,'Unknown 2.04 source; refusing reconstruction')
    s=raw.decode('utf-8')
    s=once(s,'                    &&(!defer||(mask&(1<<f))!=0))clips++;',
             '                    &&!defer)clips++;')
    a='        boolean defer=brightBackground&&!priorReached&&progress;\n'
    s=once(s,a,a+'        // EXACTPATCHCLIP1B: the direct patch check above owns subject clipping.\n'
        '        // Intersecting coarse fields also contain background outside the visible box.\n'
        '        // Defer their channel growth only under the inherited progress/evidence rule.\n')
    a='                .put("tapTargetReached",reached).put("tapLimitingReason",stop)\n'
    s=once(s,a,a+'                .put("tapClippingRevision","EXACTPATCHCLIP1B")\n'
        '                .put("tapSubjectClipAuthority","exact_probePixelRect_not_intersecting_fields")\n')
    need(sha(s.encode())==NEW_AUTO,'Recreated candidate checksum mismatch')
    need(sha(s.split('    /** Explicit user selection owns')[0].encode())==PREFIX_SHA,
         'Non-tap source prefix changed')
    return s.encode()

def parent():
    spec=importlib.util.spec_from_file_location('m9_exact_parent',REPO/'patches/tapmeter1a/apply.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def changed(before,after):
    return {k for k in set(before)|set(after) if before.get(k)!=after.get(k)}

def atomic(path,data):
    tmp=path.with_name(path.name+'.exactpatch1b.tmp')
    with open(tmp,'xb') as f: f.write(data)
    os.replace(tmp,path)

def verify(root,mod):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=mod.inventory(root)
    need(proof['revision']==ID,'Wrong source receipt')
    need(len(proof['before'])==1006,'Unexpected baseline inventory size')
    need(now==proof['after'],'Assembled candidate drift')
    need(changed(proof['before'],now)=={AUTO,GRADLE},'Unexpected production mutation set')
    need(now[AUTO]==NEW_AUTO and now[TAP]==TAP_SHA,'Meter/helper checksum mismatch')
    need(proof['before'][AUTO]==BASE_AUTO and proof['before'][GRADLE]==BASE_GRADLE,
         'Unknown source parent in receipt')
    text=(root/GRADLE).read_text()
    need(text.count(f'versionCode {CODE}')==1 and text.count(f"versionName '{VERSION}'")==1,
         'Android identity mismatch')
    need(sha((root/AUTO).read_text().split('    /** Explicit user selection owns')[0].encode())==PREFIX_SHA,
         'No-tap source changed')
    return {'revision':ID,'tapClippingRevision':'EXACTPATCHCLIP1B','version':VERSION,
            'versionCode':CODE,'parent':'2.04_TAPMETER1A','baselineInventoryEntries':1006,
            'changed':sorted(changed(proof['before'],now)), 'candidateAutoSha256':NEW_AUTO,
            'tapHelperSha256':TAP_SHA,'noTapSourcePrefixSha256':PREFIX_SHA,
            'original1AArchiveBytesRetrieved':False,'recreatedFromDocumentedOnePredicateFix':True,
            'thresholdsChanged':False,'noTapPolicyChanged':False,'rendererChanged':False,
            'cameraOwnershipChanged':False,'trackingAdded':False,'hdrAdded':False,
            'phoneValidationPending':True}

def apply(root):
    root=root.resolve(); mod=parent(); receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists(): return verify(root,mod)
    mod.verify(root) # Verify the exact parent before any intentional child mutation.
    before=mod.inventory(root)
    need(len(before)==1006 and before.get(GRADLE)==BASE_GRADLE,'Unknown 2.04 inventory/Gradle')
    need(before.get(TAP)==TAP_SHA,'Unknown tap helper')
    candidate=transformed((root/AUTO).read_bytes())
    gradle=(root/GRADLE).read_text()
    gradle=once(gradle,'versionCode 26724',f'versionCode {CODE}')
    gradle=once(gradle,"versionName '2.04-m9tapmeter1a-ae1n-perf3i'",f"versionName '{VERSION}'")
    atomic(root/AUTO,candidate); atomic(root/GRADLE,gradle.encode())
    after=mod.inventory(root)
    need(changed(before,after)=={AUTO,GRADLE},'Unexpected production mutations')
    atomic(receipt,(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n').encode())
    return verify(root,mod)

def apk_proof(candidate,baseline,output):
    need(sha(baseline.read_bytes())==BASE_APK,'Unknown baseline APK')
    with zipfile.ZipFile(baseline) as old,zipfile.ZipFile(candidate) as new:
        frozen=lambda z:{n:sha(z.read(n)) for n in z.namelist()
                         if not n.endswith('/') and n.startswith(('lib/','assets/','res/raw/'))}
        old_frozen=frozen(old); new_frozen=frozen(new)
        need(old_frozen and old_frozen==new_frozen,'Photographic/native APK assets changed')
        dex=b''.join(new.read(n) for n in new.namelist() if n.endswith('.dex'))
        markers=[b'M9TAPMETER1A',b'explicit_tap_patch',b'probePixelRect',b'tapBracket',
                 b'Tap box: Auto',b'EXACTPATCHCLIP1B',b'tapClippingRevision',
                 b'tapSubjectClipAuthority',b'exact_probePixelRect_not_intersecting_fields',
                 b'M9AUTOEXPOSUREFINISH1N_BODYQUAL1A_SUBJECTHEADROOM1A']
        for marker in markers: need(marker in dex,'Missing APK marker: '+repr(marker))
    output.mkdir(parents=True,exist_ok=True)
    out=output/'M9Cam_2.05_EXACTPATCHCLIP1B.apk'; out.write_bytes(candidate.read_bytes())
    proof={'apkSha256':sha(out.read_bytes()),'baselineApkSha256':BASE_APK,
           'frozenEntriesCompared':len(old_frozen),'frozenEntriesByteIdentical':True,
           'frozenEntries':old_frozen,'dexMarkers':[m.decode() for m in markers],
           'version':VERSION,'versionCode':CODE,'deviceValidationPending':True}
    (output/'APK_PROOF.json').write_text(json.dumps(proof,indent=2)+'\n')
    (output/'SHA256SUMS.txt').write_text(proof['apkSha256']+'  '+out.name+'\n')
    return {k:v for k,v in proof.items() if k!='frozenEntries'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['apply','source','apk'])
    p.add_argument('paths',nargs='+');a=p.parse_args()
    if a.mode=='apply':
        need(len(a.paths)==1,'apply requires PhotonCamera root');result=apply(Path(a.paths[0]))
    elif a.mode=='source':
        need(len(a.paths)==2,'source requires baseline input and candidate output')
        data=transformed(Path(a.paths[0]).read_bytes());out=Path(a.paths[1]);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_bytes(data);result={'candidateSha256':sha(data)}
    else:
        need(len(a.paths)==3,'apk requires candidate baseline outputDirectory')
        result=apk_proof(*map(Path,a.paths))
    print(json.dumps(result,indent=2))
