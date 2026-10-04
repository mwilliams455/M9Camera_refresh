#!/usr/bin/env python3
"""Exact source and photographic-asset verification; behaviour is tested separately."""
from pathlib import Path
import hashlib, json, sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
manifest=json.loads((here/'m9cam-m9exposureplan1a-manifest.json').read_text())
for rel,item in manifest['changed'].items():
 actual=hashlib.sha256((root/rel).read_bytes()).hexdigest()
 if actual!=item['after']: raise SystemExit('Exposure-plan source mismatch: '+rel)
for rel,expected in manifest['frozen'].items():
 if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=expected: raise SystemExit('Photographic freeze mismatch: '+rel)
print('M9EXPOSUREPLAN1A SOURCE PASS: exact overlay; native color, SAT2/curve02 assets, shader, tone model, frame count and GL1U sidecar preserved')
