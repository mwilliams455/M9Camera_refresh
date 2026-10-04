#!/usr/bin/env python3
"""Add per-capture profiles to the verified 2.16 DNG export; preserve JPEG source."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
assert not root.exists(),'Use a new destination'
subprocess.run([sys.executable,str(HERE.parent/'dngcolormeta1a/assemble.py'),str(root)],check=True)
for src in (HERE/'overlay').rglob('*'):
    if src.is_file(): shutil.copy2(src,root/src.relative_to(HERE/'overlay'))
for src in (HERE/'src').glob('*.java'):
    shutil.copy2(src,root/'app/src/main/java/com/particlesdevs/photoncamera/processing'/src.name)
for name,digest in json.loads((HERE/'manifest.json').read_text())['fileOverrides'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('M9DNGPROFILE1A source verified; accepted photographic renderer unchanged')
