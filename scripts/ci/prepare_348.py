"""Reconstruct the exact 3.47 source before applying the 3.48 JPEG patch."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import fingerprint, inventory

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/jpegstore348'
subprocess.run([sys.executable, REPO / 'scripts/ci/prepare_347.py', dest], check=True)
parent = dest / 'PhotonCamera_347'
candidate = dest / 'PhotonCamera_348'
pins = json.loads((stage / 'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.47-jpegperf'], 'Unexpected 3.47 parent'
shutil.copytree(parent, candidate, ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate, dest / 'verification', 'jpegstore348', '3.48-jpegstore', '3.47-jpegperf')
assert fingerprint(inventory(candidate)) == pins['3.48-jpegstore'], 'Unexpected 3.48 candidate'
