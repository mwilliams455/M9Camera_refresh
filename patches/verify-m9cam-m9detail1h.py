#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
m=json.loads((here/'m9cam-m9detail1h-manifest.json').read_text())
expected={**m['frozen'],**{p:v['after'] for p,v in m['changed'].items()},**{p:v['sha256'] for p,v in m['added'].items()}}
for p,sha in expected.items():
    if not (root/p).exists() or hashlib.sha256((root/p).read_bytes()).hexdigest()!=sha:raise SystemExit('DETAIL1H source mismatch: '+p)
print('M9DETAIL1H SOURCE PASS: tiled D/G candidate; GL2G exposure, preview, green/Sharp and downstream native colour authorities retained')
