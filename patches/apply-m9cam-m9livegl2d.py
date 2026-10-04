#!/usr/bin/env python3
"""Rendered Auto placement overlay on the exact GL2C assembled source."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
m=json.loads((here/'m9cam-m9livegl2d-manifest.json').read_text())
for rel,item in m['changed'].items():
 p=root/rel;actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
 if actual!=item['before']:raise SystemExit('GL2C baseline mismatch: '+rel)
for rel,expected in m['frozen'].items():
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=expected:raise SystemExit('Frozen baseline mismatch: '+rel)
patch=here/'m9cam-m9livegl2d.patch'
subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
subprocess.run([sys.executable,str(here/'verify-m9cam-m9livegl2d.py'),str(root)],check=True)
