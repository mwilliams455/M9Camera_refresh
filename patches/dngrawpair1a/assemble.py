#!/usr/bin/env python3
"""Add a same-frame unfiltered RAW control to the accepted 2.18 capture path."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
assert not root.exists(),'Use a new destination'
receipt=json.loads((HERE/'manifest.json').read_text())
patch=(HERE/'pair.patch').read_bytes()
assert hashlib.sha256(patch).hexdigest()==receipt['patchSha256']
subprocess.run([sys.executable,str(HERE.parent/'dngprofile1b/assemble.py'),str(root)],check=True)
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=patch,check=True)
for src in (HERE/'src').glob('*.java'):
    shutil.copy2(src,root/'app/src/main/java/com/particlesdevs/photoncamera/processing'/src.name)
for name,digest in receipt['fileOverrides'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('M9DNGRAWPAIR1A source verified; normal JPEG, DNG filter and M9 profile unchanged')
