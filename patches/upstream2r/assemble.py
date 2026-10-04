#!/usr/bin/env python3
"""Assemble the reviewed M9 overlay on the exact current Photon upstream commit."""
from pathlib import Path
import gzip, hashlib, json, subprocess, sys
HERE=Path(__file__).resolve().parent
PIN='4ee108e169496f429c0afa0cc33e57bb6b2ec724'
root=Path(sys.argv[1]).resolve()
assert not root.exists(),'Use a new destination; existing source is never overwritten'
receipt=json.loads((HERE/'source_manifest.json').read_text())
blob=(HERE/'m9-overlay.patch.gz').read_bytes()
assert hashlib.sha256(blob).hexdigest()==receipt['overlayGzipSha256']
subprocess.run(['git','clone','--no-checkout','--depth','1','--branch','dev','https://github.com/eszdman/PhotonCamera.git',str(root)],check=True)
subprocess.run(['git','-C',str(root),'fetch','--depth','1','origin',PIN],check=True)
subprocess.run(['git','-C',str(root),'checkout','--detach',PIN],check=True)
subprocess.run(['git','-C',str(root),'apply','--binary','--whitespace=nowarn','-'],input=gzip.decompress(blob),check=True)
for name,digest in receipt['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,'Source mismatch: '+name
print(json.dumps({'status':'passed','photonCommit':PIN,'verifiedFiles':len(receipt['files'])}))
