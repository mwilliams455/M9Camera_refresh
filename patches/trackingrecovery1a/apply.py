#!/usr/bin/env python3
"""Apply bounded identity-recovery corrections to the exact 3.13 candidate."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
root = args.source.resolve()
here = Path(__file__).resolve().parent
rel = Path("app/src/main/java/com/particlesdevs/photoncamera/control/tracking/SubjectAnchorPolicy.java")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def inventory():
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*")
            if p.is_file() and not any(x in {".git", ".gradle", ".cxx", "build"}
                                      for x in p.relative_to(root).parts)}

assert sha(root / rel) == "c221a2c663461ffecf8535a7fc72b2d9aa21c6c201b7cdf7a4149c309f5f2a5f", "Identity policy parent changed"
before = inventory()
build = root / "app/build.gradle"
text = build.read_text()
for old, new in (
    ("versionCode 27313", "versionCode 27314"),
    ("versionName '3.13-trackingdefault1a'", "versionName '3.14-trackingrecovery1a'"),
    ("M9Cam_3.13_TRACKINGDEFAULT1A", "M9Cam_3.14_TRACKINGRECOVERY1A"),
):
    assert text.count(old) == 1, ("3.13 build anchor", old)
    text = text.replace(old, new)
shutil.copyfile(here / "src/com/particlesdevs/photoncamera/control/tracking/SubjectAnchorPolicy.java", root / rel)
build.write_text(text)
after = inventory()
changed = sorted(n for n in before.keys() | after.keys() if before.get(n) != after.get(n))
assert changed == sorted([rel.as_posix(), "app/build.gradle"]), changed
report = dict(
    status="STAGED_FOR_ANDROID_BUILD", version="3.14-trackingrecovery1a",
    parent="3.13-trackingdefault1a", changedFiles=changed,
    sourceHashes={n: {"before": before[n], "after": after[n]} for n in changed},
    unchangedFiles=len(before) - len(changed),
    interruptedRecoveryRestartsConfirmations=True,
    recoveryDeadlineCheckedBeforeAcceptance=True,
    identityOffBehaviorUnchanged=True,
    inheritedTrackingDefaultsAndSavedPreferencesUnchanged=True,
    camera2ControllerAndAfCadenceUnchanged=True,
    automaticEyeAndPetAfUnchanged=True,
    originalModelAssetsNativeAndRendererUnchanged=True,
    phoneTrackingAndOpticalSharpnessValidationPending=True,
)
if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
