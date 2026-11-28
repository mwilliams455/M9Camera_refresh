"""Reconstruct the exact 3.51 source before applying the 3.52 settle-then-meter patch."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import fingerprint, inventory

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/settlemeter352'
subprocess.run([sys.executable, REPO / 'scripts/ci/prepare_351.py', dest], check=True)
parent = dest / 'PhotonCamera_351'
candidate = dest / 'PhotonCamera_352'
pins = json.loads((stage / 'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.51-centremeter'], 'Unexpected 3.51 parent'
shutil.copytree(parent, candidate, ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate, dest / 'verification', 'settlemeter352', '3.52-settlemeter', '3.51-centremeter')
assert fingerprint(inventory(candidate)) == pins['3.52-settlemeter'], 'Unexpected 3.52 candidate'
