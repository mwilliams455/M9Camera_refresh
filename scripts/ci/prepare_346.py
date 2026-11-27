"""Rebuild the released 3.45 source and apply the 3.46 JPEG performance changes."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import inventory, fingerprint

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/jpegperf346'
# Reconstructs PhotonCamera_344 (native provenance parent) and PhotonCamera_345 (pinned).
subprocess.run([sys.executable, REPO/'scripts/ci/prepare_345.py', dest], check=True)
parent = dest/'PhotonCamera_345'
pins = json.loads((stage/'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.45-performance'], '3.45 source differs from released parent'
candidate = dest/'PhotonCamera_346'
shutil.copytree(parent,candidate,ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate,dest/'verification','jpegperf346','3.46-jpegperf','3.45-performance')
assert fingerprint(inventory(candidate)) == pins['3.46-jpegperf'], '3.46 source differs from verified candidate'
