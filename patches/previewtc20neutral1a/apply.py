"""Apply neutral-reference preview TC20 stabilization after exact M9SHUTTERDRAWLOCK1A."""
from pathlib import Path
import hashlib,json,shutil,sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'patches'))
from m9rbrollback1a import inventory

GRADLE='app/build.gradle'
EVIDENCE='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewEvidence2E.java'
MATH='app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9PreviewTc20Math1A.java'
ID='M9PREVIEWTC20NEUTRAL1A'

BASELINE={
 GRADLE:'8df376a61fbfbaa26b8ed51d0813595b915a0b8ad1aac354b161332b413b1cda',
 EVIDENCE:'74506e6333efaad118ed64ed0b8e949fff268e75ee06c45583bac01e60a3dfc7',
 MATH:'668ad747a5942af174c6cd51cac2cc66a5619789040b3c5f269b6990f0598fbc',
}
CHANGED=set(BASELINE)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def one(text,old,new,label):
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected one anchor, found {n}')
    return text.replace(old,new,1)

def verify(root):
    proof=json.loads((root/(ID+'_SOURCE_PROOF.json')).read_text())
    now=inventory(root);before=proof['before']
    if now!=proof['after']: raise SystemExit('PREVIEWTC20NEUTRAL assembled source drift')
    changed={k for k in before if now.get(k)!=before[k]}
    added=set(now)-set(before);removed=set(before)-set(now)
    if changed!=CHANGED or added or removed:
        raise SystemExit('unexpected delta changed=%r added=%r removed=%r'%
                         (sorted(changed),sorted(added),sorted(removed)))
    if (root/EVIDENCE).read_bytes()!=(HERE/'M9PreviewEvidence2E.java').read_bytes():
        raise SystemExit('neutral evidence candidate mismatch')
    if (root/MATH).read_bytes()!=(HERE/'M9PreviewTc20Math1A.java').read_bytes():
        raise SystemExit('neutral math candidate mismatch')
    e=(root/EVIDENCE).read_text();m=(root/MATH).read_text()
    checks={
      'neutral TC20 panel':'(i==1||i==TC20_PANEL)?referenceScale:frame.exposureScale' in e,
      'no display-domain TC20 panel':'i==1?referenceScale:frame.exposureScale' not in e,
      'neutral diagnostic':'previewTc20Domain","neutral_reference_not_display_intent' in e,
      'parent marker preserved':'M9PREVIEWTC20NEG1A' in e and 'M9PREVIEWTC20NEG1A' in m,
      'new revision':'M9PREVIEWTC20NEUTRAL1A' in e and 'M9PREVIEWTC20NEUTRAL1A' in m,
      'eighth stop slew':'MAX_SLEW_EV=.125' in m,
      'deadband':'DEADBAND_EV=.04' in m,
    }
    for name,ok in checks.items():
        if not ok: raise SystemExit('PREVIEWTC20NEUTRAL verify failed: '+name)
    gradle=(root/GRADLE).read_text()
    if "versionName '1.72-m9previewtc20neutral1a-tg1'" not in gradle or 'versionCode 26692' not in gradle:
        raise SystemExit('PREVIEWTC20NEUTRAL build identity mismatch')
    # All capture, Auto, shutter-lock, shader and still photographic seams are frozen.
    for rel in [
      'app/src/main/java/com/particlesdevs/photoncamera/capture/CaptureController.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/GLPreview.java',
      'app/src/main/java/com/particlesdevs/photoncamera/ui/camera/views/viewfinder/MainRenderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/preview/M9AutoExposure2D.java',
      'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java',
      'app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java',
      'app/src/main/assets/shaders/preview/main_fs.glsl',
      'app/src/main/cpp/m9color_jni.cpp',
    ]:
        if before[rel]!=now[rel]: raise SystemExit('frozen seam changed '+rel)
    return {
      'revision':ID,'version':'1.72-m9previewtc20neutral1a-tg1','versionCode':26692,
      'changed':sorted(CHANGED),
      'tc20ProbeDomain':'neutral_reference',
      'displayIntentAffectsTc20Prediction':False,
      'maxSlewEvPerSample':0.125,
      'deadbandEv':0.04,
      'sampleIntervalMs':250,
      'shutterDrawLock_Auto_still_shader_frozen':True,
      'device_validation_pending':True,
    }

def main(root):
    root=root.resolve();receipt=root/(ID+'_SOURCE_PROOF.json')
    if receipt.exists(): print(json.dumps(verify(root),indent=2));return
    for rel,expected in BASELINE.items():
        actual=sha(root/rel)
        if actual!=expected: raise SystemExit(f'PREVIEWTC20NEUTRAL baseline mismatch {rel}: {actual}')
    gradle=(root/GRADLE).read_text()
    if "versionName '1.71-m9shutterdrawlock1a-tg1'" not in gradle or 'versionCode 26691' not in gradle:
        raise SystemExit('PREVIEWTC20NEUTRAL requires exact SHUTTERDRAWLOCK1A parent identity')

    before=inventory(root)
    shutil.copyfile(HERE/'M9PreviewEvidence2E.java',root/EVIDENCE)
    shutil.copyfile(HERE/'M9PreviewTc20Math1A.java',root/MATH)
    gradle=one(gradle,'versionCode 26691','versionCode 26692','version code')
    gradle=one(gradle,"versionName '1.71-m9shutterdrawlock1a-tg1'",
               "versionName '1.72-m9previewtc20neutral1a-tg1'",'version name')
    (root/GRADLE).write_text(gradle)
    after=inventory(root)
    receipt.write_text(json.dumps({'revision':ID,'before':before,'after':after},indent=2)+'\n')
    print(json.dumps(verify(root),indent=2))

if __name__=='__main__': main(Path(sys.argv[1]))
