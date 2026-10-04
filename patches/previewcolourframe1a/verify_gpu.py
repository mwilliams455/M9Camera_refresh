#!/usr/bin/env python3
"""Exercise actual preview shaders on GLES with a deterministic camera-texture substitute."""
from pathlib import Path
import runpy,sys,json
import numpy as np
here=Path(__file__).resolve().parent
root,out,parent=map(Path,sys.argv[1:4]);out.mkdir(parents=True,exist_ok=True)
sys.argv=[str(here.parent/'previewbrightness1a/verify_preview.py'),str(root),str(out),str(parent)]
g=runpy.run_path(sys.argv[0]);gl=g['gl'];C=g['C'];P=g['P'];I=g['I'];U=g['U'];F=g['F'];shader=g['shader']
assets='app/src/main/assets/shaders/preview/'
for name in ['main_vs.glsl','blur_oes_fs.glsl']:
 shader(0x8b31 if name.endswith('_vs.glsl') else 0x8b30,'#version 300 es\n'+(root/assets/name).read_text())
def program(tree,blur=False):
 vertex=(tree/assets/('quad_vs.glsl' if blur else 'main_vs.glsl')).read_text()
 frag=(tree/assets/('blur_oes_fs.glsl' if blur else 'main_fs.glsl')).read_text()
 frag=frag.replace('#extension GL_OES_EGL_image_external_essl3 : require','').replace('samplerExternalOES','sampler2D')
 pr=gl('glCreateProgram',U)()
 for kind,src in [(0x8b31,vertex),(0x8b30,frag)]:gl('glAttachShader',None,U,U)(pr,shader(kind,'#version 300 es\n'+src))
 gl('glLinkProgram',None,U)(pr);ok=I();gl('glGetProgramiv',None,U,U,P)(pr,0x8b82,C.byref(ok));assert ok.value
 return pr
new,old,blur=program(root),program(parent),program(root,True)
W,H=64,48
# R/G encode source coordinates; B supplies high-contrast asymmetric geometry.
y,x=np.mgrid[:256,:256];chart=np.dstack([x,y,((x//32+2*(y//32))%3)*100,np.full_like(x,255)]).astype(np.uint8)
def texture(unit,w,h,data=None):
 t=U();gl('glGenTextures',None,I,P)(1,C.byref(t));gl('glActiveTexture',None,U)(0x84c0+unit);gl('glBindTexture',None,U,U)(0x0de1,t)
 for pname in [0x2800,0x2801]:gl('glTexParameteri',None,U,U,I)(0x0de1,pname,0x2600)
 for pname in [0x2802,0x2803]:gl('glTexParameteri',None,U,U,I)(0x0de1,pname,0x812f)
 gl('glTexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0de1,0,0x8058,w,h,0,0x1908,0x1401,None if data is None else data.ctypes.data)
 return t
sourceTex=texture(0,256,256,chart);destination=texture(3,W,H)
fbo=U();gl('glGenFramebuffers',None,I,P)(1,C.byref(fbo));gl('glBindFramebuffer',None,U,U)(0x8d40,fbo)
gl('glFramebufferTexture2D',None,U,U,U,U,I)(0x8d40,0x8ce0,0x0de1,destination,0)
assert gl('glCheckFramebufferStatus',U,U)(0x8d40)==0x8cd5
gl('glActiveTexture',None,U)(0x84c0);gl('glBindTexture',None,U,U)(0x0de1,sourceTex)
positions=np.array([1,-1,-1,-1,1,1,-1,1],np.float32);coords=np.array([1,1,0,1,1,0,0,0],np.float32)
vbo=U();gl('glGenBuffers',None,I,P)(1,C.byref(vbo));gl('glBindBuffer',None,U,U)(0x8892,vbo)
vertices=np.c_[positions.reshape(4,2),coords.reshape(4,2)].astype(np.float32)
gl('glBufferData',None,U,C.c_ssize_t,P,U)(0x8892,vertices.nbytes,vertices.ctypes.data,0x88e4)
Fflip=np.diag([1,-1,1,1]).astype(np.float32);Fflip[1,3]=1
identity=np.eye(4,dtype=np.float32)
crop=np.diag([.75,.625,1,1]).astype(np.float32);crop[:2,3]=[.125,.1875]
producerRotation=identity.copy();producerRotation[:2,:2]=[[0,-1],[1,0]];producerRotation[0,3]=1
matrices=[Fflip,identity,crop@Fflip,producerRotation@Fflip]
def draw(pr,R,S,mirror,stage=1,isblur=False):
 gl('glUseProgram',None,U)(pr);loc=lambda n:gl('glGetUniformLocation',I,U,C.c_char_p)(pr,n.encode())
 for name,offset in [('vPosition',0),('vTexCoord',8)]:
  at=gl('glGetAttribLocation',I,U,C.c_char_p)(pr,name.encode())
  if at>=0:
   gl('glVertexAttribPointer',None,U,I,U,U,I,P)(at,2,0x1406,0,16,P(offset));gl('glEnableVertexAttribArray',None,U)(at)
 for name,value in [('sTexture',0),('uM9EvidenceStage2E',stage),('mirror',mirror),('enablePeak',0),('uM9Curve',1),('uM9Inverse2A',2)]:gl('glUniform1i',None,I,I)(loc(name),value)
 for name,m in [('uTexRotateMatrix',R),('uCameraSamplingMatrix',S@Fflip)]:
  column=np.ascontiguousarray(m.T);gl('glUniformMatrix4fv',None,I,I,U,P)(loc(name),1,0,column.ctypes.data)
 gl('glUniform1f',None,I,F)(loc('uCornerRadius'),0)
 for name,vals in [('uViewSize',(W,H)),('uFboSize',(W,H)),('uSharpSize',(W,H)),('uSharpOrigin',(0,0)),('uOffsetPx',(0,0))]:gl('glUniform2f',None,I,F,F)(loc(name),*vals)
 gl('glUniform1f',None,I,F)(loc('uCos'),R[0,0]);gl('glUniform1f',None,I,F)(loc('uSin'),R[1,0])
 gl('glViewport',None,I,I,I,I)(0,0,W,H);gl('glDrawArrays',None,U,I,I)(5,0,4)
 pixels=np.zeros((H,W,4),np.uint8);gl('glReadPixels',None,I,I,I,I,U,U,P)(0,0,W,H,0x1908,0x1401,pixels.ctypes.data)
 return pixels
# Independent coordinate oracle: invert screen rotation, then apply the producer's
# crop/rotation in canonical GL space; no production shader helper is reused.
def expected(R,S,mirror):
 yy,xx=np.mgrid[:H,:W];screen=np.stack([2*(xx+.5)/W-1,2*(yy+.5)/H-1],axis=-1)
 local=screen@R[:2,:2];uv=(local[...,::-1]+1)/2
 if mirror:uv[...,1]=1-uv[...,1]
 canonical=np.dstack([uv[...,0],1-uv[...,1],np.zeros((H,W)),np.ones((H,W))]);sample=canonical@S.T
 ix=np.clip(np.floor(sample[...,0]*256).astype(int),0,255);iy=np.clip(np.floor(sample[...,1]*256).astype(int),0,255)
 return chart[iy,ix]
legacy=0;geometry=0;blurchecks=0;maxError=0
for angle in range(4):
 R=identity.copy();R[:2,:2]=np.linalg.matrix_power(np.array([[0,-1],[1,0]]),angle)
 for mirrored in [0,1]:
  np.testing.assert_array_equal(draw(new,R,Fflip,mirrored),draw(old,R,Fflip,mirrored));legacy+=W*H
  for S in matrices:
   actual=draw(new,R,S,mirrored);want=expected(R,S,mirrored)
   # Nearest samples exactly on texel boundaries can choose either adjacent texel.
   err=np.abs(actual[...,:2].astype(int)-want[...,:2].astype(int)).max();assert err<=1,(angle,mirrored,S,err)
   maxError=max(maxError,int(err));geometry+=W*H
   b=draw(blur,R,S,mirrored,isblur=True)
   assert np.abs(b[...,:2].astype(int)-actual[...,:2].astype(int)).max()<=1
   blurchecks+=W*H
assert gl('glGetError',U)()==0
report=dict(status='passed',productionVertexAndFragmentCompiled=True,productionBlurCompiled=True,
 legacyOrientationPixelsIdentical=legacy,transformedCoordinatePixelsChecked=geometry,
 blurAndSharpCoordinatePixelsCompared=blurchecks,maximumCoordinateCodeError=maxError,
 sensorRotations=[0,90,180,270],mirrorStates=[False,True],
 transforms=['normal_producer_flip','identity_producer','asymmetric_crop','producer_rotation'],
 limitation='Synthetic 2D input replaces only external camera sampler; handset buffer contract and final JPEG framing require phone validation.')
(out/'FRAMING_GPU_VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
