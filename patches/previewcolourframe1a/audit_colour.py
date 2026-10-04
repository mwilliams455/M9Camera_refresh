#!/usr/bin/env python3
"""Replay historical controlled colour contexts through GPU and an independent matrix/firmware oracle."""
from pathlib import Path
import sys,runpy,json
import numpy as np
root,out,parent,evidence=map(Path,sys.argv[1:5]);here=Path(__file__).resolve().parent
sys.argv=[str(here.parent/'previewbrightness1a/verify_preview.py'),str(root),str(out),str(parent)]
g=runpy.run_path(sys.argv[0]);gl,C,P,I,U,F=[g[k] for k in ['gl','C','P','I','U','F']];draw=g['draw'];programs=[g['candidate'],g['control']];curve=g['curve'];firmware=g['m']
records=[]
for path in sorted(evidence.glob('*.json')):
 r=json.loads(path.read_text())['renderer'];e=r['toneBound1A']['exposurePlan1A']['shutterPreview1W']['pairedPixels2E'];s=e['sourceContract']
 curves=[np.array(c).reshape(-1,2) for c in s['reportedToneCurveRgb2E']]
 lookup=np.stack([np.rint(np.interp(np.arange(1024)/1023,c[:,1],c[:,0])*65535) for c in curves],axis=-1).astype(np.uint16)
 inv=np.zeros((2,1024,4),np.uint8);inv[0,:,:3]=lookup>>8;inv[1,:,:3]=lookup&255
 gl('glActiveTexture',None,U)(0x84c2);gl('glTexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0de1,0,0x8058,1024,2,0,0x1908,0x1401,inv.ctypes.data)
 matrices=[np.array(s[key],np.float32).reshape(3,3).T for key in ['inputToSensorGL','sensorToProPhotoGL','proPhotoToM9GL']]
 tungsten=np.float32(s['tungstenWeight']);white=np.array(s['clipWhite'],np.float32)
 for pr in programs:
  gl('glUseProgram',None,U)(pr);loc=lambda n:gl('glGetUniformLocation',I,U,C.c_char_p)(pr,n.encode())
  for uniform,mat in zip(['uM9InputToSensor2A','uM9SensorToPp2A','uM9PpToTarget2A'],matrices):
   m=np.ascontiguousarray(mat.T);gl('glUniformMatrix3fv',None,I,I,U,P)(loc(uniform),1,0,m.ctypes.data)
  gl('glUniform3f',None,I,F,F,F)(loc('uM9ClipWhite2A'),*white);gl('glUniform1f',None,I,F)(loc('uM9Tungsten2A'),tungsten)
 def oracle(rgb,gain,exposure,bank,contrast):
  lin=np.array([np.interp(np.float32(rgb[c]),np.arange(1024)/1023,lookup[:,c]/65535) for c in range(3)],np.float32)
  sensor=np.minimum(np.maximum(matrices[0]@lin,0)*np.float32(exposure),white)
  pp=np.clip(matrices[1]@sensor,0,1);m9=np.maximum(matrices[2]@pp,0)*np.float32(gain)
  c=np.rint(np.clip(m9*np.float32(16383),0,16383)).astype(np.int64)
  enc=curve[contrast,np.clip((firmware[bank,int(c[0]<c[1])]@c)>>16,0,2047)].astype(np.int64)
  red,green,blue=enc;y=(4899*red+9617*green+1868*blue)>>14
  cb=((-2765*red-5427*green+8192*blue)>>14);cr=((8192*red-6860*green-1332*blue)>>14)
  cb=((cb+128)&255)-128;cr=((cr+128)&255)-128
  cb=cb*(1-.25*tungsten if cb<0 else 1);cr=cr*(1-.16*tungsten if cr<0 else 1)
  return np.floor(np.clip([y+1.402*cr,y-.344136*cb-.714136*cr,y+1.772*cb],0,255)+.5).astype(np.uint8)
 pixels=np.frombuffer(bytes.fromhex(e['panels']['incomingOes']['rgbHex']),np.uint8).reshape(-1,3)/255
 # Spatially distributed real preview pixels, plus dark/neutral/saturated synthetic inputs.
 inputs=np.r_[pixels[::48],[[0,0,0],[.05,.05,.05],[.25,.25,.25],[.6,.2,.1],[.1,.5,.2],[.1,.2,.7]]]
 count=0;maximum=0
 for bank in range(5):
  for contrast in range(5):
   for rgb in inputs:
    gain=np.float32(2**.25);exposure=np.float32(e['referenceExposureScale'])
    actual=draw(programs[0],rgb,gain,exposure,bank,contrast)[:3]
    np.testing.assert_array_equal(actual,draw(programs[1],rgb,gain,exposure,bank,contrast)[:3])
    expected=oracle(rgb,gain,exposure,bank,contrast)
    err=int(np.abs(actual.astype(int)-expected.astype(int)).max());assert err<=1,(path.name,rgb,actual,expected,err)
    maximum=max(maximum,err);count+=1
 records.append(dict(file=path.name,cameraId=e['cameraId'],pixels=count,maximumOracleChannelError=maximum,
  sourceReady=s['ready'],textureMinusResultNs=e['textureMinusResultNs'],tungstenWeight=float(tungsten)))
report=dict(status='passed',previewColourMathUnchanged=True,all25SaturationContrastCombinations=True,samples=records,
 limitations=['Matrix and firmware math check, not paired preview-versus-RAW image validation','Historical OES inputs have already passed through ISP demosaic, shading and clipping','No lens colour offsets, white balance fits or changes to accepted JPEG rendering'])
(out/'COLOUR_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
