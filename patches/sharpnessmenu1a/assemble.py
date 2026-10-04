from pathlib import Path
import hashlib,json,subprocess,sys,shutil
here=Path(__file__).resolve().parent;root=Path(sys.argv[1]).resolve()
assert not root.exists(),'Use a fresh destination'
m=json.loads((here/'manifest.json').read_text());patch=(here/'sharpness.patch').read_bytes()
assert hashlib.sha256(patch).hexdigest()==m['patchSha256']
subprocess.run([sys.executable,str(here.parent/'contrastmenu1a/assemble.py'),str(root)],check=True)
for n,h in m['parentFiles'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=patch,check=True)
for n in ['m9_sharpness.cpp','m9_sharpness_bank.h']:shutil.copyfile(here/n,root/'app/src/main/cpp'/n)
for n,h in m['fileOverrides'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
print('M9SHARPNESSMENU1A assembled; run build_native.py with NDK 27.0.12077973 before Gradle')
