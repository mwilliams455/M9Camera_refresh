from pathlib import Path
import hashlib,json,difflib,subprocess,sys
parent,root=map(lambda x:Path(x).resolve(),sys.argv[1:]);here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):
 d={f.relative_to(p).as_posix():f for tree in ['app/src','circularbarlib/src'] for f in (p/tree).rglob('*') if f.is_file()};d['app/build.gradle']=p/'app/build.gradle';return d
old,new=files(parent),files(root)
changed=sorted(n for n in old.keys()|new.keys() if n not in old or n not in new or sha(old[n])!=sha(new[n]))
assert all(n in new for n in changed)
chunks=[]
for n in changed:
 a=old[n].read_text().splitlines(keepends=True) if n in old else []
 b=new[n].read_text().splitlines(keepends=True)
 chunks.append('diff --git a/'+n+' b/'+n+'\n')
 if n not in old: chunks.append('new file mode 100644\n')
 for line in difflib.unified_diff(a,b,fromfile='a/'+n if n in old else '/dev/null',tofile='b/'+n):
  chunks.append(line if line.endswith('\n') else line+'\n\\ No newline at end of file\n')
patch=here/'uioverlay1e.patch';patch.write_text(''.join(chunks))
manifest=dict(parentCommit=subprocess.check_output(['git','-C',str(here.parent.parent),'rev-parse','HEAD'],text=True).strip(),version='2.43-m9uioverlay1e',parentFiles={n:sha(old[n]) for n in changed if n in old},fileOverrides={n:sha(new[n]) for n in changed},newFiles=[n for n in changed if n not in old],patchSha256=sha(patch))
(here/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'changed':changed,'bytes':patch.stat().st_size},indent=2))
