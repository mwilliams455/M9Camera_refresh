#!/usr/bin/env python3
"""Reconstruct FIX1 on the preserved, fully pinned UPSTREAM2R source."""
from pathlib import Path
import hashlib, json, subprocess, sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'upstream2r'
root = Path(sys.argv[1]).resolve()
receipt = json.loads((HERE / 'fix_manifest.json').read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
assert not root.exists(), 'Use a new destination'
assert sha((BASE / 'source_manifest.json').read_bytes()) == receipt['baseManifestSha256']
patch = (HERE / 'raw16-fix.patch').read_bytes()
assert sha(patch) == receipt['patchSha256']
subprocess.run([sys.executable, str(BASE / 'assemble.py'), str(root)], check=True)
subprocess.run(['git', '-C', str(root), 'apply', '--binary', '--whitespace=nowarn', '-'],
               input=patch, check=True)
files = json.loads((BASE / 'source_manifest.json').read_text())['files']
files.update(receipt['fileOverrides'])
for name, digest in files.items():
    assert sha((root / name).read_bytes()) == digest, 'Source mismatch: ' + name
print(json.dumps({'status': 'passed', 'revision': receipt['revision'],
                  'verifiedFiles': len(files), 'photonCommit': receipt['photonCommit']}))
