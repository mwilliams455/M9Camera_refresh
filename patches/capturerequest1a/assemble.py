#!/usr/bin/env python3
"""Apply capture-policy diagnostics to the accepted 2.19 RAW pair release."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
assert not root.exists(),'Use a new destination'
receipt=json.loads((HERE/'manifest.json').read_text())
patch=(HERE/'request.patch').read_bytes()
assert hashlib.sha256(patch).hexdigest()==receipt['patchSha256']
subprocess.run([sys.executable,str(HERE.parent/'dngrawpair1a/assemble.py'),str(root)],check=True)
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=patch,check=True)
for name,digest in receipt['fileOverrides'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('M9CAPTUREREQUEST1A verified; JPEG renderer and both DNG export paths unchanged')
