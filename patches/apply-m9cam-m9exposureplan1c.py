#!/usr/bin/env python3
"""Apply the reviewed EV-energy overlay to the exact assembled M9LIVEGL1W baseline."""
from pathlib import Path
import hashlib, json, subprocess, sys
root=Path(sys.argv[1]).resolve()
here=Path(__file__).resolve().parent
manifest=json.loads((here/'m9cam-m9exposureplan1c-manifest.json').read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
for rel,item in manifest['changed'].items():
 if sha(root/rel)!=item['before']: raise SystemExit('M9LIVEGL1W baseline mismatch: '+rel)
for rel,expected in manifest['frozen'].items():
 if sha(root/rel)!=expected: raise SystemExit('Frozen baseline mismatch: '+rel)
patch=here/'m9cam-m9exposureplan1c.patch'
subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
subprocess.run([sys.executable,str(here/'verify-m9cam-m9exposureplan1c.py'),str(root)],check=True)
