"""Apply AUTOEXPOSUREFINISH1A only after the exact released COLOURTRIAL1E assembly."""
from pathlib import Path
import hashlib,json,shutil,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
ISO=BASE+'processing/parameters/IsoExpoSelector.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1A'
CHANGED={AUTO,ISO,GRADLE}
EXPECTED_ISO_SHA256='fe2b5106eb55188c9bf040d2900cf1787c41d6e1cc38e89ad64264cada1b3fee'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replace_once(text,old,new,label):
    if text.count(old)!=1:
        raise SystemExit(f'{label}: expected one anchor, found {text.count(old)}')
    return text.replace(old,new,1)

def verify(root):
    receipt=root/(ID+'_SOURCE_PROOF.json')
    proof=json.loads(receipt.read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AUTOEXPOSUREFINISH1A assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('Auto candidate mismatch')
    iso=(root/ISO).read_text()
    if iso.count('manualExposure, manualIso, feedback.appliedEv, eligible);')!=1:
        raise SystemExit('Auto eligibility ownership join missing')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.68-m9autoexposurefinish1a-tg1'" not in gradle or 'versionCode 26688' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1A version mismatch')
    return {
        'revision':ID,
        'version':'1.68-m9autoexposurefinish1a-tg1',
        'versionCode':26688,
        'changed':sorted(CHANGED),
        'backlightAssistMaxEv':0.5,
        'render_native_colour_preview_shader_JPEG_DNG_unchanged':True,
        'device_validation_pending':True
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    old_auto=REPO/'patches/colourtrial1a/M9AutoExposure2D.java'
    if (root/AUTO).read_bytes()!=old_auto.read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1A requires exact COLOURTRIAL1A Auto source from released 1E')
    if sha(root/ISO)!=EXPECTED_ISO_SHA256:
        raise SystemExit('AUTOEXPOSUREFINISH1A IsoExpoSelector baseline mismatch')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.67-m9colourtrial1e-tg1'" not in gradle or 'versionCode 26687' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1A requires released 1.67 COLOURTRIAL1E build identity')

    iso=(root/ISO).read_text()
    iso=replace_once(
        iso,
        'manualExposure, manualIso, feedback.appliedEv);',
        'manualExposure, manualIso, feedback.appliedEv, eligible);',
        'IsoExpoSelector eligibility join')
    gradle=replace_once(gradle,'versionCode 26687','versionCode 26688','version code')
    gradle=replace_once(gradle,
        "versionName '1.67-m9colourtrial1e-tg1'",
        "versionName '1.68-m9autoexposurefinish1a-tg1'",
        'version name')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    (root/ISO).write_text(iso)
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED:
        raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
