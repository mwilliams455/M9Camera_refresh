"""Freeze the integration against the 2.46 integration assembled source."""
from pathlib import Path
import hashlib,json,difflib,shutil,gzip,sys
parent,root=map(lambda x:Path(x).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):
 d={f.relative_to(p).as_posix():f for tree in ['app/src','circularbarlib/src'] for f in (p/tree).rglob('*') if f.is_file()};d['app/build.gradle']=p/'app/build.gradle';return d
old,new=files(parent),files(root)
changed=sorted(n for n in old.keys()|new.keys() if n not in old or n not in new or sha(old[n])!=sha(new[n]))
assert all(n in new for n in changed)
chunks=[];binaries=[]
for n in changed:
 try:
  a=old[n].read_text().splitlines(keepends=True) if n in old else []
  b=new[n].read_text().splitlines(keepends=True)
  if b'\0' in new[n].read_bytes():raise UnicodeDecodeError('utf-8',b'\0',0,1,'binary')
 except UnicodeDecodeError:
  binaries.append(n);target=here/'payload'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(new[n],target);continue
 chunks.append('diff --git a/'+n+' b/'+n+'\n')
 if n not in old:chunks.append('new file mode 100644\n')
 for line in difflib.unified_diff(a,b,fromfile='a/'+n if n in old else '/dev/null',tofile='b/'+n):
  chunks.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
patch=here/'monolabel1a.patch.gz';patch.write_bytes(gzip.compress(''.join(chunks).encode(),mtime=0))
manifest=dict(parentCommit='775989a0009faee89104e13e532c14506e39e945',monochromCommit='cf5e00e23ea47920fb863eb7abb0fa423885786a',version='2.47-monolabel1a',parentFiles={n:sha(old[n]) for n in changed if n in old},fileOverrides={n:sha(new[n]) for n in changed},newFiles=[n for n in changed if n not in old],binaryPayloads=binaries,patchSha256=sha(patch))
(here/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(changed=len(changed),existing=len(manifest['parentFiles']),new=len(manifest['newFiles']),binary=binaries,patchBytes=patch.stat().st_size),indent=2))
