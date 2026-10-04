from pathlib import Path
import hashlib,json,subprocess,sys,shutil
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve();assert not root.exists(),'Use a new destination'
m=json.loads((HERE/'manifest.json').read_text());patch=(HERE/'contrast.patch').read_bytes()
assert hashlib.sha256(patch).hexdigest()==m['patchSha256']
subprocess.run([sys.executable,str(HERE.parent/'capturefreeze1a/assemble.py'),str(root)],check=True)
subprocess.run(['git','-C',str(root),'apply','--whitespace=nowarn','-'],input=patch,check=True)
shutil.copyfile(HERE/'m9_contrast_srgb_firmware.bin',root/'app/src/main/assets/m9/m9_contrast_srgb_firmware.bin')
for p,h in m['fileOverrides'].items():assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
print('M9CONTRASTMENU1A source and firmware assets verified')
