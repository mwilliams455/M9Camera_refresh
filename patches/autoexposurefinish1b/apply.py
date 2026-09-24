"""Apply AUTOEXPOSUREFINISH1B only after the exact AUTOEXPOSUREFINISH1A assembly."""
from pathlib import Path
import json,hashlib,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory
BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1B'
CHANGED={AUTO,GRADLE}

def replace_once(text,old,new,label):
    if text.count(old)!=1: raise SystemExit(f'{label}: expected one anchor, found {text.count(old)}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AUTOEXPOSUREFINISH1B assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('Auto target-placement candidate mismatch')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.69-m9autoexposurefinish1b-tg1'" not in gradle or 'versionCode 26689' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1B version mismatch')
    return {
        'revision':ID,'version':'1.69-m9autoexposurefinish1b-tg1','versionCode':26689,
        'changed':sorted(CHANGED),'positiveSearchMaxEv':2.0,
        'sceneTargetMedianCode':60,'backlightTargetCenterMedianCode':60,
        'backlightTargetCenterQ25Code':30,
        'render_native_colour_preview_shader_JPEG_DNG_unchanged':True,
        'device_validation_pending':True
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return
    parent=REPO/'patches/autoexposurefinish1a/M9AutoExposure2D.java'
    if (root/AUTO).read_bytes()!=parent.read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1B requires exact AUTOEXPOSUREFINISH1A Auto source')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.68-m9autoexposurefinish1a-tg1'" not in gradle or 'versionCode 26688' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1B requires 1.68 parent build identity')
    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=replace_once(gradle,'versionCode 26688','versionCode 26689','version code')
    gradle=replace_once(gradle,"versionName '1.68-m9autoexposurefinish1a-tg1'",
        "versionName '1.69-m9autoexposurefinish1b-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__': main(Path(sys.argv[1]))
