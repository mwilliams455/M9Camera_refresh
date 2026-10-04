from pathlib import Path
import hashlib, json, subprocess, sys

here = Path(__file__).resolve().parent
root = Path(sys.argv[1]).resolve()
assert not root.exists(), 'Use a fresh destination'
manifest = json.loads((here/'manifest.json').read_text())
patch = (here/'brightness.patch').read_bytes()
assert hashlib.sha256(patch).hexdigest() == manifest['patchSha256']
subprocess.run([sys.executable,str(here.parent/'displayaids1a/assemble.py'),str(root)],check=True)
for name,digest in manifest['parentFiles'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, name
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=patch,check=True)
for name,digest in manifest['fileOverrides'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, name
print('M9PREVIEWBRIGHTNESS1A assembled; use sharpnessmenu1a/build_native.py before Gradle. Packaging preserves all 2.31 native libraries.')
