#!/usr/bin/env python3
"""Focus continuity overlay on the exact GL2A assembled source."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
m=json.loads((here/'m9cam-m9livegl2b-manifest.json').read_text())
for rel,item in m['changed'].items():
 p=root/rel;actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
 if actual!=item['before']:raise SystemExit('GL2A baseline mismatch: '+rel)
for rel,expected in m['frozen'].items():
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=expected:raise SystemExit('Frozen baseline mismatch: '+rel)
patch=here/'m9cam-m9livegl2b.patch'
subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
subprocess.run([sys.executable,str(here/'verify-m9cam-m9livegl2b.py'),str(root)],check=True)
