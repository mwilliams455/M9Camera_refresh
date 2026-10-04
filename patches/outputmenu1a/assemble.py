#!/usr/bin/env python3
"""Apply optional diagnostic output controls to the accepted 2.22 release."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
assert not root.exists(),'Use a new destination'
receipt=json.loads((HERE/'manifest.json').read_text())
patch=(HERE/'output.patch').read_bytes()
assert hashlib.sha256(patch).hexdigest()==receipt['patchSha256']
subprocess.run([sys.executable,str(HERE.parent/'saturationmenu1a/assemble.py'),str(root)],check=True)
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=patch,check=True)
for name,digest in receipt['fileOverrides'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('M9OUTPUTMENU1A verified; optional RAW/diagnostic exports, defaults off')
