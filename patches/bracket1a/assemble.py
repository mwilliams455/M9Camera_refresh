from pathlib import Path
import hashlib,json,subprocess,sys
here=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve()
assert not root.exists(),'Use a fresh destination'
manifest=json.loads((here/'manifest.json').read_text())
patch=(here/'bracket.patch').read_bytes()
assert hashlib.sha256(patch).hexdigest()==manifest['patchSha256']
subprocess.run([sys.executable,str(here.parent/'aelocktimer1a/assemble.py'),str(root)],check=True)
for name,digest in manifest['parentFiles'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for name in manifest['newFiles']: assert not (root/name).exists(),name
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=patch,check=True)
for name,digest in manifest['fileOverrides'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
print('M9BRACKET1A assembled; build inherited sharpness natives before Gradle. Packaging preserves all accepted 2.37 native libraries.')
