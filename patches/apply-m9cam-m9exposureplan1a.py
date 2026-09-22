#!/usr/bin/env python3
"""Apply the reviewed exposure-plan overlay to the exact assembled GL1U baseline."""
from pathlib import Path
import hashlib, json, subprocess, sys
root=Path(sys.argv[1]).resolve()
here=Path(__file__).resolve().parent
manifest=json.loads((here/'m9cam-m9exposureplan1a-manifest.json').read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
# The historical GL1U replay can lose the three-line NOHDR allocator guard.
# Restore only this exact known source variant to the existing frozen parent;
# all original manifest checks below remain mandatory and unchanged.
iso_rel='app/src/main/java/com/particlesdevs/photoncamera/processing/parameters/IsoExpoSelector.java'
if sha(root/iso_rel)=='e5029f82b08f34bd55a0d2b41df4289dc4f5532d7c076fb595f5c8251009992d':
 iso=(root/iso_rel).read_text()
 anchor='    public static ExpoPair GenerateExpoPair(int step, CaptureController captureController) {\n'
 assert iso.count(anchor)==1
 restored=iso.replace(anchor,anchor+'''        // M9_NOHDR1A_EXPOSURE_ALLOCATOR
        // Bracketing preference may remain nonzero in UI, but cannot perturb M9 exposure.
        if (M9Config.usesM9Pipeline()) HDR = false;
''',1)
 if hashlib.sha256(restored.encode()).hexdigest()!=manifest['changed'][iso_rel]['before']:
  raise SystemExit('GL1U NOHDR reconstruction failed exact parent identity')
 (root/iso_rel).write_text(restored)
 print('GL1U NOHDR allocator restored to exact existing manifest hash')
for rel,item in manifest['changed'].items():
 if sha(root/rel)!=item['before']: raise SystemExit('GL1U baseline mismatch: '+rel)
for rel,expected in manifest['frozen'].items():
 if sha(root/rel)!=expected: raise SystemExit('Frozen baseline mismatch: '+rel)
patch=here/'m9cam-m9exposureplan1a.patch'
subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
subprocess.run([sys.executable,str(here/'verify-m9cam-m9exposureplan1a.py'),str(root)],check=True)
