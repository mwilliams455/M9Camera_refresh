#!/usr/bin/env python3
"""Apply bounded diagnostic and latency-aware Cat/Dog focus fix on EXACT 2.99 source."""
from pathlib import Path
import argparse,hashlib,json,shutil
parser=argparse.ArgumentParser()
parser.add_argument("source",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
root=args.source.resolve()
here=Path(__file__).resolve().parent
prefix=Path("app/src/main/java/com/particlesdevs/photoncamera")
parent=here.parent/"focusanimal1a"/"src"/"com/particlesdevs/photoncamera"
candidate=here/"src"/"com/particlesdevs/photoncamera"
changed=[]
sha=lambda b:hashlib.sha256(b).hexdigest()

for rel in ("control/subject/PetTargetPolicy.java",
            "ui/camera/PetObjectDetector.java",
            "ui/camera/PetFocusController.java"):
    before=parent/rel
    target=root/prefix/rel
    replacement=candidate/rel
    assert sha(before.read_bytes())==sha(target.read_bytes()),f"Not the verified 2.99 parent: {rel}"
    target.write_bytes(replacement.read_bytes())
    changed.append((prefix/rel).as_posix())

new=prefix/"ui/camera/PetAfStatusBadge.java"
assert not (root/new).exists(),"The diagnostic status overlay already exists"
(root/new).write_bytes((candidate/"ui/camera/PetAfStatusBadge.java").read_bytes())
changed.append(new.as_posix())

gradle=root/"app/build.gradle"
gradle_text=gradle.read_text()
for old,new in [
    ("versionCode 27299","versionCode 27300"),
    ("versionName '2.99-focusanimal1a'","versionName '3.00-focusanimal1b'"),
    ("M9Cam_2.99_FOCUSANIMAL1A","M9Cam_3.00_FOCUSANIMAL1B"),
]:
    assert gradle_text.count(old)==1,(old,gradle_text.count(old))
    gradle_text=gradle_text.replace(old,new)
gradle.write_text(gradle_text)
changed.append("app/build.gradle")

controller=(root/prefix/"ui/camera/PetFocusController.java").read_text()
detector=(root/prefix/"ui/camera/PetObjectDetector.java").read_text()
policy=(root/prefix/"control/subject/PetTargetPolicy.java").read_text()
assert "PetAfStatusBadge" in controller
assert "inferMs" in controller and "copyMs" in controller and "ageMs" in controller
assert "Pet AF: model error" in controller and "Pet AF: AF-C region unavailable" in controller
assert "MAX_AUTO_AF_AGE_MS=900" in controller
assert "CaptureRequest.CONTROL_AE_REGIONS" not in controller
assert "CaptureRequest.CONTROL_AWB_REGIONS" not in controller
assert "CONTROL_AF_TRIGGER_START" not in controller
assert "finally {mpImage.close();}" in detector
assert "lastDecision" in policy and "inference_too_old" in policy
assert (root/"app/src/main/assets/efficientdet-lite0.tflite").exists()
report=dict(
    status="STAGED_FOR_BUILD",version="3.00-focusanimal1b",parent="2.99-focusanimal1a",
    changedFiles=sorted(changed),modelAssetUnchanged=True,
    humanEyeAfUnchanged=True,photoRenderingUnchanged=True,
    defaultFocusModeUnchanged=True,diagnosticUiOnlyWhenPetEnabled=True,
    physicalPhoneValidationPending=True)
if args.report:
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
