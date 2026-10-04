#!/usr/bin/env python3
"""Reproduce 2.17's file-type rejection and test 2.18 commit/failure preservation.

The Java 17 policy models media-directory filename rejection only. Device FUSE and
Lightroom behaviour still need phone validation. All data is synthetic.
"""
from pathlib import Path
import hashlib, json, subprocess, sys
import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); out.mkdir(parents=True,exist_ok=True)
src=root/'app/src/main/java/com/particlesdevs/photoncamera/processing'
curve=root/'app/src/main/assets/m9/m9_curve02_firmware.bin'
results=[]
for mode in ['old_writer','success','deny_commit']:
    case=out/mode; case.mkdir(exist_ok=True); classes=case/'classes'; classes.mkdir(exist_ok=True)
    writer=HERE.parent/'dngprofile1a/src/M9DngProfileWriter.java' if mode=='old_writer' else src/'M9DngProfileWriter.java'
    subprocess.run(['java','com.sun.tools.javac.Main','-d',str(classes),*map(str,src.glob('M9Saturation.java')),str(src/'M9DngProfile.java'),str(writer),str(HERE/'StorageHostProbe.java')],check=True)
    path=case/'capture.dng'; raw=np.arange(48*64,dtype=np.uint16).reshape(48,64)+1024
    cm=[10000,10000,0,10000,0,10000,0,10000,10000,10000,0,10000,0,10000,0,10000,10000,10000]
    tags=[(50706,'B',4,[1,3,0,0],False),(50708,'s',0,'Synthetic storage regression',False),
          (33421,'H',2,[2,2],False),(33422,'B',4,[0,1,1,2],False),
          (50728,'2I',3,[1,2,1,1,2,3],False),(50721,'2i',9,cm,False),
          (50778,'H',1,21,False),(50730,'2i',1,[-1,2],False)]
    tifffile.imwrite(path,raw,photometric=32803,metadata=None,extratags=tags)
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    output=subprocess.check_output(['java','-Xmx128m','-Djava.security.manager=allow','-cp',str(classes),
        'com.particlesdevs.photoncamera.processing.StorageHostProbe',str(curve),str(path),mode],text=True).strip()
    with tifffile.TiffFile(path) as f:
        np.testing.assert_array_equal(f.pages[0].asarray(),raw)
        assert (50936 in f.pages[0].tags)==(mode=='success')
    if mode!='success': assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    results.append(dict(mode=mode,status='passed',rawExact=True,output=output))
report=dict(status='passed',cases=results,scope='Host file-policy simulation and failure injection; Android FUSE/device validation pending')
(out/'STORAGE_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print('Storage regression and commit-failure preservation passed')
