"""Reconstruct 2.51. Optional --parent uses an already verified 2.50 source tree."""
from pathlib import Path
import argparse,hashlib,json,gzip,subprocess,shutil,sys
here=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('destination');p.add_argument('--parent');args=p.parse_args();root=Path(args.destination).resolve()
assert not root.exists(),'Use a fresh destination'
m=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(here/'m9perf1b.patch.gz')==m['patchSha256']
if args.parent:
 shutil.copytree(Path(args.parent).resolve(),root,ignore=shutil.ignore_patterns('.git','.gradle','.cxx','build'))
else:subprocess.run([sys.executable,str(here.parent/'m9perf1a/assemble.py'),str(root)],check=True)
for name,digest in m['parentFiles'].items():assert sha(root/name)==digest,name
for name in m['newFiles']:assert not (root/name).exists(),name
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=gzip.decompress((here/'m9perf1b.patch.gz').read_bytes()),check=True)
for name in m['binaryPayloads']:
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(here/'payload'/name,target)
for name,digest in m['fileOverrides'].items():assert sha(root/name)==digest,name
print('M9PERF1B exact reconstruction passed. Package using the 2.50 native-library baseline.')
