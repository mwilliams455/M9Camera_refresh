"""Correct the head detector JNI output list in the 3.27 source."""
import hashlib
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
verify("after")
report = {"status": "STAGED_FOR_ANDROID_BUILD", "version": "3.29-headjni1a",
          "parent": "3.27-headcontinuity1a", "changedFiles": sorted(hashes), "sourceHashes": hashes}
output.write_text(json.dumps(report, indent=2) + "\n")
