#!/usr/bin/env python3
"""2.04 TAPMETER1A. Decode audited transport, check exact source and change only listed files."""
from pathlib import Path
import base64,gzip,hashlib,importlib.util,json,subprocess,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
ID='M9TAPMETER1A'
VERSION='2.04-m9tapmeter1a-ae1n-perf3i'
CODE=26724
PAYLOAD_SHA256='900134bfe9b12770c75eef0e1d69697336103b0c8f4e0d4cedc2b93f6931720a'
GRADLE='app/build.gradle'

def digest(data):return hashlib.sha256(data).hexdigest()

def load():
    text=''.join((HERE/f'payload.{i:02d}').read_text().strip() for i in range(8))
    raw=gzip.decompress(base64.b64decode(text,validate=True))
    if digest(raw)!=PAYLOAD_SHA256:raise SystemExit('TAPMETER1A payload checksum mismatch')
    data=json.loads(raw)
    if set(data)!={'patch','manifest','tapTest'}:raise SystemExit('Unexpected payload structure')
    for name in data['manifest']:
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or not name.startswith('app/src/main/java/'):
            raise SystemExit('Unsafe source path')
    return data

def decode(destination):
    data=load();destination.mkdir(parents=True,exist_ok=True)
    (destination/'tapmeter1a.patch').write_text(data['patch'])
    (destination/'manifest.json').write_text(json.dumps(data['manifest'],indent=2)+'\n')
    (destination/'TapMeterTest.java').write_text(data['tapTest'])
    return data

def inventory(root):
    sys.path.insert(0,str(REPO/'patches'))
    from m9rbrollback1a import inventory as parent_inventory
    return parent_inventory(root)

def verify(root):
    data=load();proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']:raise SystemExit('TAPMETER1A assembled source drift')
    changed={k for k in set(proof['before'])|set(now) if proof['before'].get(k)!=now.get(k)}
    if changed!=set(data['manifest'])|{GRADLE}:raise SystemExit('Unexpected TAPMETER mutation set')
    for name,item in data['manifest'].items():
        if digest((root/name).read_bytes())!=item['after']:raise SystemExit('Candidate mismatch: '+name)
    gradle=(root/GRADLE).read_text()
    if f'versionCode {CODE}' not in gradle or f"versionName '{VERSION}'" not in gradle:
        raise SystemExit('TAPMETER1A Android identity mismatch')
    return {'revision':ID,'version':VERSION,'versionCode':CODE,'parent':'2.03_FINISH1N',
      'payloadSha256':PAYLOAD_SHA256,'changed':sorted(changed),
      'tapUsesActualRenderedProbePixels':True,'tapPatchVisible':True,
      'tapPatchTracksObjects':False,'selectionLifetimeSeconds':15,
      'clearByTappingSelectedPatch':True,'rotationAndLensChangeClearSelection':True,
      'automaticRegionReplacedOnTap':True,'automaticLockRenewalOtherwiseChanged':False,
      'automaticNoTapPolicyChanged':False,'existingGlobalHighlightThresholdsChanged':False,
      'tapReadabilityTargetMedian':58,'tapReadabilityTargetQ25':22,
      'tapTargetUsesExistingMinimumBacklightFloors':True,
      'tapBranchRemovesUpperTailSubstitution':True,'tapIsPositiveAssistNotNegativeSpotMeter':True,
      'rendererChanged':False,'tc20Changed':False,'colourChanged':False,'sat2Changed':False,
      'curve02Changed':False,'tg1Changed':False,'noiseChanged':False,'dngChanged':False,
      'spoolChanged':False,'previewShaderChanged':False,'localHdr':False,'multiFrameHdr':False,
      'deviceValidationPending':True}

def replace_one(s,old,new):
    if s.count(old)!=1:raise SystemExit('Version anchor mismatch: '+old)
    return s.replace(old,new,1)

def main(root):
    root=root.resolve();receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():print(json.dumps(verify(root),indent=2));return
    data=decode(HERE/'decoded')
    spec=importlib.util.spec_from_file_location('parent_ae1n',REPO/'patches/autoexposurefinish1n/apply.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    parent.verify(root)
    for name,item in data['manifest'].items():
        p=root/name;actual=digest(p.read_bytes()) if p.exists() else None
        if actual!=item['before']:raise SystemExit('Exact FINISH1N baseline mismatch: '+name)
    before=inventory(root)
    patch=HERE/'decoded/tapmeter1a.patch'
    subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
    subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
    gradle=(root/GRADLE).read_text()
    gradle=replace_one(gradle,'versionCode 26723',f'versionCode {CODE}')
    gradle=replace_one(gradle,"versionName '2.03-m9ae1n-bodyqual1a-subjecthl1a-perf3i'",f"versionName '{VERSION}'")
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
    if changed!=set(data['manifest'])|{GRADLE}:raise SystemExit('Unexpected mutations: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--check-payload':
        data=load();print(json.dumps({'sha256':PAYLOAD_SHA256,'sourceFiles':len(data['manifest']),'checksum':'passed'}))
    elif len(sys.argv)>1 and sys.argv[1]=='--decode':
        decode(Path(sys.argv[2]).resolve());print('Decoded readable patch, manifest and test')
    else:main(Path(sys.argv[1]))
