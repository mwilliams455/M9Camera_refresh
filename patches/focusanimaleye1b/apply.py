#!/usr/bin/env python3
"""Stage exact 3.02 -> 3.03 AP10K bitmap-ownership + SimCC decoder fix.

Accepts only the SHA256-matched 3.02 source files. No native library, models,
Camera2 AF engine, M9/Mono RAW, exposure, WB or colour renderer is changed.
"""
from pathlib import Path
import argparse,hashlib,json,shutil

args=argparse.ArgumentParser()
args.add_argument('source',type=Path)
args.add_argument('--report',type=Path)
ns=args.parse_args()
root=ns.source.resolve()
here=Path(__file__).resolve().parent
prefix=Path('app/src/main/java/com/particlesdevs/photoncamera')
sha=lambda d:hashlib.sha256(d).hexdigest()
changed=[]
parent_paths={
    'ui/camera/PetObjectDetector.java':(
        here.parent/'focusanimal1b/src/com/particlesdevs/photoncamera/ui/camera/PetObjectDetector.java'),
    'ui/camera/AnimalEyePoseEstimator.java':(
        here.parent/'focusanimaleye1a/src/com/particlesdevs/photoncamera/ui/camera/AnimalEyePoseEstimator.java'),
    'ui/camera/PetFocusController.java':(
        here.parent/'focusanimaleye1a/src/com/particlesdevs/photoncamera/ui/camera/PetFocusController.java'),
}
for rel,prior in parent_paths.items():
    current=root/prefix/rel
    replacement=here/'src/com/particlesdevs/photoncamera'/rel
    assert prior.is_file() and replacement.is_file() and current.is_file()
    assert sha(current.read_bytes())==sha(prior.read_bytes()),'Not exact 3.02 source: '+rel
    current.write_bytes(replacement.read_bytes())
    changed.append((prefix/rel).as_posix())

rel='control/subject/AnimalSimccDecoder.java'
target=root/prefix/rel
assert not target.exists(),'AnimalSimccDecoder is a new verified pure Java source'
target.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(here/'src/com/particlesdevs/photoncamera'/rel,target)
changed.append((prefix/rel).as_posix())

build=Path('app/build.gradle')
f=root/build
data=f.read_text()
for old,new in [
    ('versionCode 27302','versionCode 27303'),
    ("versionName '3.02-animaleye1a'","versionName '3.03-animaleye1b'"),
    ('M9Cam_3.02_ANIMALEYE1A','M9Cam_3.03_ANIMALEYE1B')
]:
    assert data.count(old)==1,(old,data.count(old))
    data=data.replace(old,new)
f.write_text(data)
changed.append(build.as_posix())

detector=(root/prefix/'ui/camera/PetObjectDetector.java').read_text()
pose=(root/prefix/'ui/camera/AnimalEyePoseEstimator.java').read_text()
ctrl=(root/prefix/'ui/camera/PetFocusController.java').read_text()
assert 'Bitmap detectorFrame=image.copy(Bitmap.Config.ARGB_8888,false)' in detector
assert 'new BitmapImageBuilder(detectorFrame)' in detector
assert 'new BitmapImageBuilder(image)' not in detector
assert 'mpImage.close()' in detector and 'if(image.isRecycled())' in detector
assert 'AnimalSimccDecoder.decode(sx,sy,' in pose
assert 'peakProbability' not in pose and 'Math.exp(' not in pose
assert 'pose_null_recycled' in ctrl
assert 'AnimalEyeTargetPolicy.Target eye=' in ctrl
assert 'selectedEye==null?target.x:selectedEye.x' in ctrl
assert 'CONTROL_AF_TRIGGER_START' not in ctrl
assert 'CaptureRequest.CONTROL_AE_REGIONS' not in ctrl
assert 'CaptureRequest.CONTROL_AWB_REGIONS' not in ctrl
model=root/'app/src/main/assets/rtm_animal_fp16.tflite'
assert model.is_file()
expected=(here.parent/'focusanimaleye1a/MODEL_SHA256.txt').read_text().split()[0]
assert sha(model.read_bytes())==expected,'Pinned AP10K model changed'

record=dict(status='STAGED_FOR_BUILD',
    version='3.03-animaleye1b',parent='3.02-animaleye1a',
    changedFiles=sorted(set(changed)),
    rootCause='MediaPipe BitmapImageContainer.close recycles shared PixelCopy input',
    correctedPetDetectorImageOwnership=True,
    simccConfidenceMatchesMMPoseRawPeakDecoder=True,
    originalAnimalEyePolicyUnchanged=True,
    originalHumanEyeAfUnchanged=True,
    originalBodyFocusPolicyUnchanged=True,
    modelByteIdenticalTo302=True,modelSha256=expected,
    originalRenderExposureWbRawNativeUnchanged=True,
    deviceEyeSharpnessPending=True)
if ns.report:
    ns.report.parent.mkdir(parents=True,exist_ok=True)
    ns.report.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
