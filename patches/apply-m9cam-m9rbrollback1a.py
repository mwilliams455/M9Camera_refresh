#!/usr/bin/env python3
"""Bypass the complete D/H overwrite after the validated TG2STILL1A parent."""
from pathlib import Path
import json,sys
from m9rbrollback1a import RENDERER,GRADLE,VERSION,sha,transform,inventory,verify

if len(sys.argv)!=2:raise SystemExit('usage: apply-m9cam-m9rbrollback1a.py PhotonCamera')
root=Path(sys.argv[1]).resolve()
m=json.loads(Path(__file__).with_name('m9rbrollback1a-manifest.json').read_text())
for rel,want in {**m['frozen'],**{p:v['before'] for p,v in m['changed'].items()}}.items():
    if sha(root/rel)!=want:raise SystemExit('RBROLLBACK1A parent mismatch: '+rel)
receipt=root/'M9RBROLLBACK1A_SOURCE_PROOF.json'
if receipt.exists():raise SystemExit('RBROLLBACK1A unexpected existing receipt')
j=transform((root/RENDERER).read_text())
g=(root/GRADLE).read_text();old="versionName '1.61-m9detail1h-tg2still1a'"
if g.count(old)!=1:raise SystemExit('RBROLLBACK1A version anchor mismatch')
g=g.replace(old,"versionName '"+VERSION+"'",1)
before=inventory(root)
receipt.write_text(json.dumps(dict(parent='M9TG2STILL1A',before=before),indent=2)+'\n')
(root/RENDERER).write_text(j);(root/GRADLE).write_text(g)
print(json.dumps(verify(root),indent=2))
