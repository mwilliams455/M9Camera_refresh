#!/usr/bin/env python3
"""Apply the controlled native detail candidate to exact GL2G INSTALLFIX1."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent;repo=here.parent
m=json.loads((here/'m9cam-m9detail1h-manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,want in {**m['frozen'],**{p:v['before'] for p,v in m['changed'].items()}}.items():
    if not (root/p).exists() or sha(root/p)!=want:raise SystemExit('DETAIL1H baseline mismatch: '+p)
for p,v in m['added'].items():
    if (root/p).exists():raise SystemExit('DETAIL1H unexpected existing target: '+p)
    if sha(repo/v['source'])!=v['sha256']:raise SystemExit('DETAIL1H payload mismatch: '+p)
subprocess.run(['git','-C',str(root),'apply','--check',str(here/'m9cam-m9detail1h.patch')],check=True)
subprocess.run(['git','-C',str(root),'apply',str(here/'m9cam-m9detail1h.patch')],check=True)
for p,v in m['added'].items():
    target=root/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/v['source'],target)
subprocess.run([sys.executable,str(here/'verify-m9cam-m9detail1h.py'),str(root)],check=True)
