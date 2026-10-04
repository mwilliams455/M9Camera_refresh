"""Apply AUTOEXPOSUREFINISH1C only after exact 1.75 M9SPOOLSTREAM1A."""
from pathlib import Path
import json,shutil,sys
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

BASE='app/src/main/java/com/particlesdevs/photoncamera/'
AUTO=BASE+'m9/preview/M9AutoExposure2D.java'
GRADLE='app/build.gradle'
ID='M9AUTOEXPOSUREFINISH1C'
CHANGED={AUTO,GRADLE}

def replace_once(text,old,new,label):
    if text.count(old)!=1:
        raise SystemExit(f'{label}: expected one anchor, found {text.count(old)}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root)
    if now!=proof['after']: raise SystemExit('AUTOEXPOSUREFINISH1C assembled source drift')
    changed={k for k,v in proof['before'].items() if now.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected changed files: '+repr(sorted(changed)))
    if (root/AUTO).read_bytes()!=(HERE/'M9AutoExposure2D.java').read_bytes():
        raise SystemExit('adaptive backlight Auto candidate mismatch')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.76-m9autoexposurefinish1c-tg1'" not in gradle or 'versionCode 26696' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1C version mismatch')
    return {
        'revision':ID,
        'policyRevision':'M9AUTOEXPOSUREFINISH1C_ADAPTIVEBACKLIGHT',
        'version':'1.76-m9autoexposurefinish1c-tg1',
        'versionCode':26696,
        'changed':sorted(CHANGED),
        'positiveSearchMaxEv':2.5,
        'backlightCenterTargetRangeCode':[58,72],
        'backlightCenterQ25TargetRangeCode':[22,32],
        'adaptiveBackgroundLossBySubjectStarvation':True,
        'wholeDarkScenePolicyChanged':False,
        'lowKeyNightPolicyChanged':False,
        'preview_TC20_shutterDrawLock_spool_JPEG_DNG_native_unchanged':True,
        'device_validation_pending':True,
    }

def main(root):
    root=root.resolve()
    receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists():
        print(json.dumps(verify(root),indent=2));return

    parent=REPO/'patches/autoexposurefinish1b/M9AutoExposure2D.java'
    if (root/AUTO).read_bytes()!=parent.read_bytes():
        raise SystemExit('AUTOEXPOSUREFINISH1C requires exact AUTOEXPOSUREFINISH1B policy source')

    gradle=(root/GRADLE).read_text()
    if "versionName '1.75-m9spoolstream1a-tg1'" not in gradle or 'versionCode 26695' not in gradle:
        raise SystemExit('AUTOEXPOSUREFINISH1C requires exact 1.75 M9SPOOLSTREAM1A build identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9AutoExposure2D.java',root/AUTO)
    gradle=replace_once(gradle,'versionCode 26695','versionCode 26696','version code')
    gradle=replace_once(gradle,
        "versionName '1.75-m9spoolstream1a-tg1'",
        "versionName '1.76-m9autoexposurefinish1c-tg1'",
        'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    changed={k for k,v in before.items() if after.get(k)!=v}
    if changed!=CHANGED: raise SystemExit('Unexpected mutation set: '+repr(sorted(changed)))

    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__':
    main(Path(sys.argv[1]))
