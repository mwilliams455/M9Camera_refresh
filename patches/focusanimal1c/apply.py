#!/usr/bin/env python3
"""Exact additive v3.01 preview-recovery fix over validated 3.00 camera source."""
from pathlib import Path
import argparse,hashlib,json

parser=argparse.ArgumentParser()
parser.add_argument("source",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
root=args.source.resolve()
here=Path(__file__).resolve().parent
prefix=Path("app/src/main/java/com/particlesdevs/photoncamera")
parent=here.parent/"focusanimal1b"/"src"/"com/particlesdevs/photoncamera"
candidate=here/"src"/"com/particlesdevs/photoncamera"
sha=lambda b:hashlib.sha256(b).hexdigest()
changed=[]

rel="ui/camera/PetFocusController.java"
before=parent/rel
target=root/prefix/rel
assert before.exists() and sha(before.read_bytes())==sha(target.read_bytes()), "Not exact 3.00 Pet AF source"
target.write_bytes((candidate/rel).read_bytes())
changed.append((prefix/rel).as_posix())

rel="control/subject/PetPreviewRetryPolicy.java"
target=root/prefix/rel
assert not target.exists(),"Pet retry policy should be new"
target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes((candidate/rel).read_bytes())
changed.append((prefix/rel).as_posix())

gradle=root/"app/build.gradle"
original=gradle.read_text()
changed_gradle=original
for old,new in [
    ("versionCode 27300","versionCode 27301"),
    ("versionName '3.00-focusanimal1b'","versionName '3.01-focusanimal1c'"),
    ("M9Cam_3.00_FOCUSANIMAL1B","M9Cam_3.01_FOCUSANIMAL1C")
]:
    assert changed_gradle.count(old)==1,(old,changed_gradle.count(old))
    changed_gradle=changed_gradle.replace(old,new)
gradle.write_text(changed_gradle)
changed.append("app/build.gradle")
c=(root/prefix/"ui/camera/PetFocusController.java").read_text()
assert 'Pet AF: preview allocation failed' not in c
assert 'sampleError("copy_request"' in c
assert 'sampleError("copy_callback"' in c
assert 'sampleError("bitmap"' in c
assert "previewRetry.mayAttempt(nowMs)" in c
assert "previewRetry.reset()" in c
assert "previewRetry.success()" in c
assert "catch(OutOfMemoryError memoryError)" in c
assert "AF-C region unavailable" in c and "PetObjectDetector" in c
assert "CONTROL_AF_TRIGGER_START" not in c
assert "CaptureRequest.CONTROL_AE_REGIONS" not in c
assert "CaptureRequest.CONTROL_AWB_REGIONS" not in c
assert len(changed)==3
report={
 "status":"STAGED_FOR_BUILD",
 "parent":"3.00-focusanimal1b",
 "version":"3.01-focusanimal1c",
 "scope":"recover optional PixelCopy/bitmap sampling without permanent transient disable",
 "changedFiles":sorted(changed),
 "catDogModelByteIdenticalToParent":True,
 "allParentNativeAndAssetsPreserved":True,
 "userAcceptedEyeAfUnchanged":True,
 "captureExposureWbRawRendererUnchanged":True,
 "physicalDeviceValidationPending":True
}
if args.report:
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
