"""Reconstruct the exact 3.49 source before applying the 3.50 arm64 SIMD AMaZE patch."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import fingerprint, inventory

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/amazesimd350'
subprocess.run([sys.executable, REPO / 'scripts/ci/prepare_349.py', dest], check=True)
parent = dest / 'PhotonCamera_349'
candidate = dest / 'PhotonCamera_350'
pins = json.loads((stage / 'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.49-jpegperf'], 'Unexpected 3.49 parent'
shutil.copytree(parent, candidate, ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate, dest / 'verification', 'amazesimd350', '3.50-amazesimd', '3.49-jpegperf')
assert fingerprint(inventory(candidate)) == pins['3.50-amazesimd'], 'Unexpected 3.50 candidate'
