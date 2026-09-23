from pathlib import Path
import ast,hashlib,json,sys
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
sys.path.insert(0,str(here));from m9rbrollback1a import inventory
proof=json.loads((root/'M9SHUTTERTRACE1A_SOURCE_PROOF.json').read_text());current=inventory(root)
assert current==proof['after'],'source changed after instrumentation receipt'
manifest=json.loads((here/'m9shuttertrace1a-parent.json').read_text())
for rel,digest in manifest.items():assert proof['before'][rel]==digest,(rel,'wrong baseline')
base='app/src/main/java/com/particlesdevs/photoncamera/'
node=next(n for n in ast.parse((here/'apply-m9cam-m9shuttertrace1a.py').read_text()).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='changes')
changes=eval(compile(ast.Expression(node.value),'<literal replacements>','eval'),{'base':base})
assert sorted(k for k in proof['before'] if proof['before'][k]!=current[k])==sorted(changes)
for rel,replacements in changes.items():
 s=(root/rel).read_text()
 for old,new in reversed(replacements):assert s.count(new)==1;s=s.replace(new,old,1)
 assert hashlib.sha256(s.encode()).hexdigest()==proof['before'][rel],('non-diagnostic edit',rel)
for p in (here/'shuttertrace1a').glob('*.java'):
 assert (root/base/'m9/preview'/p.name).read_bytes()==p.read_bytes(),p.name
assert len(proof['added'])==7
assert all(current[k]==h for k,h in proof['before'].items() if k.startswith(('app/src/main/assets/','app/src/main/cpp/')))
assert current[base+'api/ParseExif.java']==proof['before'][base+'api/ParseExif.java']
print(json.dumps(dict(revision='M9SHUTTERTRACE1A',reverse_hooks_exact=True,source_files=len(current),
 photographic_assets_and_native_code_exact=True,exif_writer_unchanged=True,
 baseline='DETAIL1H_TG1ROLLBACK1A',full_phone_validation_pending=True),indent=2))
