"""Reconstruct 2.66. Optional --parent uses an already verified 2.65 source tree."""
from pathlib import Path
import argparse,hashlib,json,gzip,subprocess,shutil,sys
here=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('destination');p.add_argument('--parent');args=p.parse_args();root=Path(args.destination).resolve()
assert not root.exists(),'Use a fresh destination'
m=json.loads((here/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def scoped_fingerprint(r):
 files={p.relative_to(r).as_posix():sha(p) for d in ['app/src','circularbarlib/src'] for p in (r/d).rglob('*') if p.is_file()}
 files['app/build.gradle']=sha(r/'app/build.gradle')
 return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert sha(here/'exposuresettle1a.patch.gz')==m['patchSha256']
if args.parent:
 shutil.copytree(Path(args.parent).resolve(),root,ignore=shutil.ignore_patterns('.git','.gradle','.cxx','build'))
else:subprocess.run([sys.executable,str(here.parent/'anchorsettle1a/assemble.py'),str(root)],check=True)
assert scoped_fingerprint(root)==m['parentScopedSha256'],'Parent source fingerprint mismatch: reconstruct 2.65 from the full pinned chain'
for name,digest in m['parentFiles'].items():assert sha(root/name)==digest,name
for name in m['newFiles']:assert not (root/name).exists(),name
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=gzip.decompress((here/'exposuresettle1a.patch.gz').read_bytes()),check=True)
for name in m['binaryPayloads']:
 target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(here/'payload'/name,target)
for name,digest in m['fileOverrides'].items():assert sha(root/name)==digest,name
assert scoped_fingerprint(root)==m['candidateScopedSha256'],'Candidate source fingerprint mismatch'
print('EXPOSURESETTLE1A exact reconstruction passed. Package using the 2.65 native-library baseline.')
