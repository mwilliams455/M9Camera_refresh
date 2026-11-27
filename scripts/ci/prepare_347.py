"""Reconstruct the exact 3.46 source before applying the 3.47 JPEG patch."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import fingerprint, inventory

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/jpegperf347'
subprocess.run([sys.executable, REPO / 'scripts/ci/prepare_346.py', dest], check=True)
parent = dest / 'PhotonCamera_346'
candidate = dest / 'PhotonCamera_347'
pins = json.loads((stage / 'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.46-jpegperf'], 'Unexpected 3.46 parent'
shutil.copytree(parent, candidate, ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate, dest / 'verification', 'jpegperf347', '3.47-jpegperf', '3.46-jpegperf')
assert fingerprint(inventory(candidate)) == pins['3.47-jpegperf'], 'Unexpected 3.47 candidate'
