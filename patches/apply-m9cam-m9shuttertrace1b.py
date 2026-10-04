from pathlib import Path
import json,subprocess,sys
from m9shuttertrace1b import BASE,HERE,CHANGES,inventory,verify
root=Path(sys.argv[1]).resolve();proof=root/'M9SHUTTERTRACE1B_SOURCE_PROOF.json'
if proof.exists():print(json.dumps(verify(root),indent=2));sys.exit(0)
subprocess.run([sys.executable,str(HERE/'verify-m9cam-m9shuttertrace1a.py'),str(root)],check=True)
before=inventory(root);updates={}
for rel,replacements in CHANGES.items():
 s=(root/rel).read_text()
 for old,new in replacements:assert s.count(old)==1,(rel,old);s=s.replace(old,new,1)
 updates[rel]=s.encode()
for p in (HERE/'shuttertrace1b').glob('*.java'):updates[BASE+'m9/preview/'+p.name]=p.read_bytes()
for rel,data in updates.items():(root/rel).write_bytes(data)
proof.write_text(json.dumps(dict(revision='M9SHUTTERTRACE1B',before=before,after=inventory(root)),indent=2)+'\n')
print(json.dumps(verify(root),indent=2))
