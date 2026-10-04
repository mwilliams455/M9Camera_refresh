#!/usr/bin/env python3
"""Production Java profile transport on synthetic Bayer files, with failure preservation."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
import numpy as np
import tifffile
HERE=Path(__file__).resolve().parent
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
classes=out/'classes';classes.mkdir(exist_ok=True)
src=root/'app/src/main/java/com/particlesdevs/photoncamera/processing'
subprocess.run(['java','com.sun.tools.javac.Main','-d',str(classes),*map(str,src.glob('M9Saturation.java')),str(src/'M9DngProfile.java'),str(src/'M9DngProfileWriter.java'),str(HERE/'ProfileHostProbe.java')],check=True)
curve=root/'app/src/main/assets/m9/m9_curve02_firmware.bin'
def run(gain,*args):
 return subprocess.check_output(['java','-Xmx128m','-cp',str(classes),'com.particlesdevs.photoncamera.processing.ProfileHostProbe',str(curve),str(gain),*map(str,args)],text=True).strip()
assert 'INVALID_INPUT_GATES=4' in run(1,'invalid')
patterns=[[0,1,1,2],[1,0,2,1],[1,2,0,1],[2,1,1,0]]
results=[]
for index,pattern in enumerate(patterns):
 path=out/f'cfa{index}.dng';raw=np.random.default_rng(171+index).integers(1024,16369,(96,128),dtype=np.uint16)
 cm=[10000,10000,0,10000,0,10000,0,10000,10000,10000,0,10000,0,10000,0,10000,10000,10000]
 tags=[(50706,'B',4,[1,4,0,0],False),(50707,'B',4,[1,4,0,0],False),(50708,'s',0,'Synthetic active physical camera',False),
 (33421,'H',2,[2,2],False),(33422,'B',4,pattern,False),(50714,'H',1,1024,False),(50717,'I',1,16368,False),
 (50728,'2I',3,[1,2,1,1,2,3],False),(50721,'2i',9,cm,False),(50778,'H',1,21,False),(50730,'2i',1,[-1,2],False)]
 if index>=2:tags +=[(50722,'2i',9,cm,False),(50779,'H',1,17,False)]
 tifffile.imwrite(path,raw,photometric=32803,metadata=None,extratags=tags)
 original=path.read_bytes()
 with tifffile.TiffFile(path) as f:before={t.code:(t.dtype,t.count,t.value) for t in f.pages[0].tags}
 info=run(1.25,path);new=path.read_bytes()
 assert new[:4]==original[:4] and new[8:len(original)]==original[8:]
 with tifffile.TiffFile(path) as f:
  p=f.pages[0];np.testing.assert_array_equal(p.asarray(),raw)
  for code,expected in before.items():
   if code not in (50706,50707):assert (p.tags[code].dtype,p.tags[code].count,p.tags[code].value)==expected,code
  assert p.tags[50981].value==(180,65,129)
  table=np.array(p.tags[50982].value).reshape(129,180,65,3)
  assert np.isfinite(table).all();np.testing.assert_array_equal(table[:,:,0],np.broadcast_to([0,1,1],(129,180,3)))
  attrs=ET.fromstring(p.tags[700].value).find('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF/{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description').attrib
  crs='{http://ns.adobe.com/camera-raw-settings/1.0/}'
  assert attrs[crs+'CameraProfile']==p.tags[50936].value==p.tags[50934].value
  assert attrs[crs+'CameraProfileDigest'] in info and attrs[crs+'AlreadyApplied']=='False'
  for field in ('Sharpness','LuminanceSmoothing','ColorNoiseReduction','HDREditMode'):assert attrs[crs+field]=='0'
 results.append(dict(cfa=index,rawAndPhysicalTagsExact=True,originalPayloadPrefixExact=True,reexportRejectedWithoutMutation=True,output=info))
assert not list(out.glob('.m9-profile-*'))
# Independently solve the specified spline and inspect each cubic's derivative controls.
for gain in [.015625,.0625,.25,.5,1,2,4,16,64,256]:
 path=out/'tone.bin';run(gain,'tone',path)
 xy=np.frombuffer(path.read_bytes(),'<f4').reshape(-1,2).astype(float);x,y=xy.T;n=len(x);dx=np.diff(x);sec=np.diff(y)/dx
 initial=np.zeros(n);initial[1:-1]=(sec[:-1]*dx[1:]+sec[1:]*dx[:-1])/(dx[:-1]+dx[1:]);initial[0]=2*sec[0]-initial[1];initial[-1]=2*sec[-1]-initial[-2]
 A=np.eye(n);rhs=1.5*initial;A[0,1]=A[-1,-2]=.5;rhs[0]=.75*(initial[0]+initial[1]);rhs[-1]=.75*(initial[-2]+initial[-1])
 for i in range(1,n-1):A[i,i-1]=dx[i]/(2*(dx[i-1]+dx[i]));A[i,i+1]=dx[i-1]/(2*(dx[i-1]+dx[i]))
 d=np.linalg.solve(A,rhs);controls=np.array([dx*d[:-1],3*np.diff(y)-dx*(d[:-1]+d[1:]),dx*d[1:]])
 assert controls.min()>-1e-6,(gain,controls.min())
 assert xy[0].tolist()==[0,0] and xy[-1].tolist()==[1,1]
(out/'PROFILE_VERIFICATION.json').write_text(json.dumps(dict(status='passed',cases=results,invalidInputGates=4,gainSweep=[.015625,.0625,.25,.5,1,2,4,16,64,256],hostHeapLimitMiB=128,scope='Synthetic data only. Actual Adobe SDK oracle and phone tests are separate.'),indent=2)+'\n')
print('Profile export synthetic gates passed')
