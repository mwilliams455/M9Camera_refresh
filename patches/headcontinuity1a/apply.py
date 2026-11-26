"""Apply multi-person head continuity to the 3.26 source."""
import hashlib
import shutil
import json
from pathlib import Path
import subprocess
import sys

source, output = (Path(arg).resolve() for arg in sys.argv[1:])
here = Path(__file__).resolve().parent
hashes = json.loads((here / "source-hashes.json").read_text())

def verify(stage):
    for name, expected in hashes.items():
        path = source / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != expected[stage]:
            raise ValueError(f"{stage} fingerprint mismatch: {name}")

verify("before")
subprocess.run(["git", "apply", "--whitespace=error", here / "source.patch"], cwd=source, check=True)
assets = source / "app/src/main/assets"
model = "https://huggingface.co/Sharath33/Person/resolve/f109818fa5025b94152be2ac8353b2c473bc6c5f/yolov11_phd_s.onnx"
subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "4",
                "--retry-all-errors", "--max-time", "180", "--output", assets / "person_head.onnx", model], check=True)
shutil.copyfile(here / "PERSON_HEAD_MODEL.md", assets / "PERSON_HEAD_MODEL.md")
verify("after")
report = {"status": "STAGED_FOR_ANDROID_BUILD", "version": "3.27-headcontinuity1a",
          "parent": "3.26-headbody1a", "changedFiles": sorted(hashes), "sourceHashes": hashes}
output.write_text(json.dumps(report, indent=2) + "\n")
