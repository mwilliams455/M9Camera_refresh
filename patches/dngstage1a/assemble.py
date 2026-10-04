#!/usr/bin/env python3
"""Reconstruct DNGSTAGE1A on verified DNGEXPORT1B source."""
from pathlib import Path
import hashlib, json, subprocess, sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'dngexport1b'
root=Path(sys.argv[1]).resolve()
receipt=json.loads((HERE/'manifest.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
assert not root.exists(),'Use a new destination'
patch=(HERE/'stage.patch').read_bytes()
assert sha(patch)==receipt['patchSha256']
subprocess.run([sys.executable,str(BASE/'assemble.py'),str(root)],check=True)
subprocess.run(['git','-C',str(root),'apply','--binary','--whitespace=nowarn','-'],input=patch,check=True)
files=json.loads((HERE.parent/'upstream2r/source_manifest.json').read_text())['files']
files.update(json.loads((HERE.parent/'upstream2r_fix1/fix_manifest.json').read_text())['fileOverrides'])
files.update(json.loads((HERE.parent/'perf2s_auditopt1a/perf_manifest.json').read_text())['fileOverrides'])
files.update(json.loads((BASE/'manifest.json').read_text())['fileOverrides'])
files.update(receipt['fileOverrides'])
for name,digest in files.items():
    assert sha((root/name).read_bytes())==digest,'Source mismatch: '+name
print(json.dumps(dict(status='passed',revision=receipt['revision'],verifiedFiles=len(files),photonCommit=receipt['photonCommit'])))
