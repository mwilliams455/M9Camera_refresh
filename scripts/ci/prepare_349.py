"""Reconstruct the exact 3.48 source before applying the 3.49 JPEG performance patch."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import fingerprint, inventory

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/jpegperf349'
subprocess.run([sys.executable, REPO / 'scripts/ci/prepare_348.py', dest], check=True)
parent = dest / 'PhotonCamera_348'
candidate = dest / 'PhotonCamera_349'
pins = json.loads((stage / 'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.48-jpegstore'], 'Unexpected 3.48 parent'
shutil.copytree(parent, candidate, ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate, dest / 'verification', 'jpegperf349', '3.49-jpegperf', '3.48-jpegstore')
assert fingerprint(inventory(candidate)) == pins['3.49-jpegperf'], 'Unexpected 3.49 candidate'
