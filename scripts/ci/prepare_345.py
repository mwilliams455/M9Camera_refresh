"""Rebuild the installed 3.44 parent and apply the 3.45 performance changes."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

from prepare_314 import REPO, apply_exposure_stage
from prepare_source import inventory, fingerprint

dest = Path(sys.argv[1]).resolve()
stage = REPO / 'patches/performance345'
subprocess.run([sys.executable, REPO/'scripts/ci/prepare_314.py', dest, '--adaptive-face-highlight'], check=True)
parent = dest/'PhotonCamera_344'
(dest/'PhotonCamera_342').rename(parent)
for patch in ('tungsten-guard.patch', 'lens-falloff.patch'):
    subprocess.run(['git','apply',stage/'parents'/patch],cwd=parent,check=True)
pins = json.loads((stage/'source-fingerprints.json').read_text())
assert fingerprint(inventory(parent)) == pins['3.44-lensfalloff'], '3.44 source differs from released parent'
candidate = dest/'PhotonCamera_345'
shutil.copytree(parent,candidate,ignore=shutil.ignore_patterns('.git'))
apply_exposure_stage(candidate,dest/'verification','performance345','3.45-performance','3.44-lensfalloff')
assert fingerprint(inventory(candidate)) == pins['3.45-performance'], '3.45 source differs from verified candidate'
