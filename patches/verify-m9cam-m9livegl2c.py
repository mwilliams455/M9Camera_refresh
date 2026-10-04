#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
m=json.loads((here/'m9cam-m9livegl2c-manifest.json').read_text())
expected={k:v['after'] for k,v in m['changed'].items()};expected.update(m['frozen'])
for rel,wanted in expected.items():
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=wanted:raise SystemExit('GL2C source mismatch: '+rel)
print('M9LIVEGL2C SOURCE PASS: inverse sampler precision; focus fix, colour context, RAW renderer, exposure allocator and assets frozen')
