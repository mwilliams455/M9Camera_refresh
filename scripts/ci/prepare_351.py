"""Reconstruct the exact 3.50 source before applying the 3.51 centre-weighted metering patch."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import fingerprint, inventory

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/centremeter351'
subprocess.run([sys.executable, REPO / 'scripts/ci/prepare_350.py', dest], check=True)
parent = dest / 'PhotonCamera_350'
candidate = dest / 'PhotonCamera_351'
pins = json.loads((stage / 'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.50-amazesimd'], 'Unexpected 3.50 parent'
shutil.copytree(parent, candidate, ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate, dest / 'verification', 'centremeter351', '3.51-centremeter', '3.50-amazesimd')
assert fingerprint(inventory(candidate)) == pins['3.51-centremeter'], 'Unexpected 3.51 candidate'
