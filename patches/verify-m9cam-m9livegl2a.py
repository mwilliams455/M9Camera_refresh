#!/usr/bin/env python3
"""Exact source and photographic-asset verification; behaviour is tested separately."""
from pathlib import Path
import hashlib, json, sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
manifest=json.loads((here/'m9cam-m9livegl2a-manifest.json').read_text())
for rel,item in manifest['changed'].items():
 actual=hashlib.sha256((root/rel).read_bytes()).hexdigest()
 if actual!=item['after']: raise SystemExit('Exposure-plan source mismatch: '+rel)
for rel,expected in manifest['frozen'].items():
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=expected: raise SystemExit('Photographic freeze mismatch: '+rel)
import re
renderer=root/'app/src/main/java/com/particlesdevs/photoncamera/m9/render/M9R35Renderer.java'
s=renderer.read_text()
s,n=re.subn(r'    // M9LIVEGL2A_EXPORT_BEGIN[\s\S]*?    // M9LIVEGL2A_EXPORT_END\n\n','',s)
if n!=1 or hashlib.sha256(s.encode()).hexdigest()!=manifest['renderer_without_export']:
 raise SystemExit('Still renderer changed outside read-only exporter')
print('M9LIVEGL2A SOURCE PASS: controlled preview verified; still renderer executable path, native kernel, exposure allocator and firmware assets frozen')
