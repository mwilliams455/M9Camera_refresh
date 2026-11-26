"""Build the 3.26 camera as an in-place update for installations of 3.27."""
import json
from pathlib import Path
import subprocess
import sys

stage = Path(__file__).resolve().parent
ci = stage.parents[1] / "scripts/ci"
sys.path.insert(0, str(ci))
from prepare_source import fingerprint, inventory

source, report = (Path(arg).resolve() for arg in sys.argv[1:])
before = inventory(source)
if fingerprint(before) != (ci / "source-326.sha256").read_text().strip():
    raise ValueError("Expected the complete pinned 3.26 production source")

subprocess.run(["git", "apply", "--whitespace=error", stage / "source.patch"], cwd=source, check=True)
after = inventory(source)
changes = {p: {"before": before.get(p), "after": after.get(p)}
           for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
if set(changes) != {"app/build.gradle"} or changes != json.loads((stage / "source-hashes.json").read_text()):
    raise ValueError("Only the pinned version metadata may differ from 3.26")
if fingerprint(after) != (ci / "source-328.sha256").read_text().strip():
    raise ValueError("Unexpected 3.28 production source")

result = {"status": "STAGED_FOR_ANDROID_BUILD", "version": "3.28-trackingstability1a",
          "parent": "3.26-headbody1a", "changedFiles": sorted(changes), "sourceHashes": changes}
report.write_text(json.dumps(result, indent=2) + "\n")
